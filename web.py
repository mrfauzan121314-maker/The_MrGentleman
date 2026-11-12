#!/usr/bin/env python3
"""MrGentleman's parlour on the web.

A small local page, and a server that streams his words into it as he speaks
them. Standard library only, exactly as before:

    python3 web.py                      # http://127.0.0.1:8000
    python3 web.py --port 3000          # another door
    python3 web.py --host 0.0.0.0       # open to the household
    python3 web.py --offline            # his own wit, no language model

The key, should there be one, is read exactly as the terminal version reads it:
from the environment or from .env, and it never leaves this machine.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import secrets
import sys
import threading
import time
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from llm import MAX_HISTORY_TURNS, Config, GentlemanLLM, LLMError
from mrgentleman import Gentleman

ROOT = Path(__file__).resolve().parent
PAGE = ROOT / "static" / "index.html"

MAX_BODY = 8_192          # a visitor's line, in bytes
MAX_SESSIONS = 64         # parlours remembered at once
MAX_LINE = 2_000          # characters accepted from the page
COOKIE = "mrg"

ORACLE: "GentlemanLLM | None" = None
SESSIONS: dict[str, "Session"] = {}
SESSIONS_LOCK = threading.Lock()


# --------------------------------------------------------------------------
# A visitor's parlour: his own wit, and their half of the conversation
# --------------------------------------------------------------------------


class Session:
    """One visitor's conversation, with the gentleman who attends them."""

    def __init__(self) -> None:
        self.gentleman = Gentleman(random.Random())
        self.history: list[dict[str, str]] = []
        self.lock = threading.Lock()

    def stream(self, said: str):
        """Yield his reply a piece at a time, keeping the record straight."""
        if ORACLE is None:
            for piece in _gradually(self.gentleman.reply(said)):
                yield piece
            return

        with self.lock:
            self.history.append({"role": "user", "content": said})
        pieces: list[str] = []
        try:
            for piece in ORACLE.stream(self.history):
                pieces.append(piece)
                yield piece
        except LLMError:
            with self.lock:
                if self.history and self.history[-1]["role"] == "user":
                    self.history.pop()
            raise

        answer = "".join(pieces).strip()
        if answer:
            with self.lock:
                self.history.append({"role": "assistant", "content": answer})
                del self.history[:-2 * MAX_HISTORY_TURNS]


def _gradually(reply: str):
    """Let his own wit arrive word by word, as the oracle's does."""
    for word in re.findall(r"\S+\s*", reply):
        yield word
        time.sleep(0.02)


def mode_note() -> str:
    if ORACLE is None:
        return "speaking from his own wit (no key found)"
    return f"conversing by way of {ORACLE.config.model}"


# --------------------------------------------------------------------------
# The parlour door
# --------------------------------------------------------------------------


class Parlour(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "MrGentleman"

    # -- housekeeping -----------------------------------------------------
    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write(f"  {self.address_string()} - {fmt % args}\n")

    def _token(self) -> str | None:
        raw = self.headers.get("Cookie")
        if not raw:
            return None
        try:
            jar = SimpleCookie(raw)
        except Exception:
            return None
        morsel = jar.get(COOKIE)
        return morsel.value if morsel else None

    def _session(self) -> tuple[str, "Session", bool]:
        """Find this visitor's parlour, or open a new one for them."""
        token = self._token()
        with SESSIONS_LOCK:
            if token and token in SESSIONS:
                return token, SESSIONS[token], False
            token = secrets.token_urlsafe(16)
            SESSIONS[token] = Session()
            while len(SESSIONS) > MAX_SESSIONS:
                SESSIONS.pop(next(iter(SESSIONS)))
            return token, SESSIONS[token], True

    def _read_body(self) -> bytes | None:
        """Read the visitor's words, whether measured or sent in chunks.

        Proxies and some clients send a chunked body with no Content-Length;
        reading only the measured kind left the page speechless behind them.
        """
        if "chunked" in (self.headers.get("Transfer-Encoding") or "").lower():
            return self._read_chunks()
        measured = self.headers.get("Content-Length")
        if measured is None:
            return b""
        try:
            length = int(measured)
        except ValueError:
            return None
        if length < 0 or length > MAX_BODY:
            return None
        return self.rfile.read(length) if length else b""

    def _read_chunks(self) -> bytes | None:
        """Assemble a chunked body, refusing one larger than we will read."""
        body = b""
        while True:
            header = self.rfile.readline(64).strip()
            if not header:
                return body
            try:
                size = int(header.split(b";")[0], 16)
            except ValueError:
                return None
            if size == 0:
                while True:  # discard any trailers
                    trailer = self.rfile.readline(64)
                    if trailer in (b"\r\n", b"\n", b""):
                        return body
            if len(body) + size > MAX_BODY:
                return None
            body += self.rfile.read(size)
            self.rfile.read(2)  # the CRLF that closeth the chunk

    def _cross_site(self) -> bool:
        """Refuse a page from elsewhere speaking on the visitor's behalf."""
        origin = self.headers.get("Origin")
        if not origin:
            return False
        return urlsplit(origin).netloc != (self.headers.get("Host") or "")

    def _cookie(self, token: str, new: bool) -> None:
        if new:
            self.send_header(
                "Set-Cookie",
                f"{COOKIE}={token}; Path=/; HttpOnly; SameSite=Strict",
            )

    # -- replies ----------------------------------------------------------
    def _json(self, body: dict, status: int = 200, token: str = "", new: bool = False):
        raw = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self._cookie(token, new)
        self.end_headers()
        self.wfile.write(raw)

    def _file(self, path: Path, content_type: str) -> None:
        try:
            raw = path.read_bytes()
        except OSError:
            self._json({"error": "the page is missing"}, status=404)
            return
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def _event(self, payload) -> None:
        if payload == "DONE":
            self.wfile.write(b"data: [DONE]\n\n")
        else:
            self.wfile.write(
                b"data: " + json.dumps(payload).encode("utf-8") + b"\n\n"
            )
        self.wfile.flush()

    # -- routes -----------------------------------------------------------
    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        if path in ("/", "/index.html"):
            self._file(PAGE, "text/html; charset=utf-8")
        elif path == "/hello":
            token, session, new = self._session()
            opening = session.gentleman.reply("good day")
            self._json(
                {"greeting": opening, "mode": mode_note()},
                token=token,
                new=new,
            )
        elif path == "/favicon.ico":
            self.send_response(204)
            self.send_header("Content-Length", "0")
            self.end_headers()
        else:
            self._json({"error": "no such page"}, status=404)

    def do_POST(self) -> None:
        if urlsplit(self.path).path != "/chat":
            self._json({"error": "no such door"}, status=404)
            return
        raw = self._read_body()  # always drained, that the socket stay honest
        if raw is None:
            self.close_connection = True
            self._json({"error": "ill-measured request"}, status=400)
            return
        if self._cross_site():
            self._json({"error": "a stranger's page may not speak for thee"}, status=403)
            return
        try:
            payload = json.loads(raw or b"{}")
        except json.JSONDecodeError:
            self._json({"error": "that was no sentence I could read"}, status=400)
            return

        said = str(payload.get("message", "")).strip()[:MAX_LINE]
        if not said:
            self._json({"error": "thou saidst nothing"}, status=400)
            return

        token, session, new = self._session()

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Accel-Buffering", "no")
        self.send_header("Connection", "close")
        self._cookie(token, new)
        self.end_headers()
        self.close_connection = True

        try:
            for piece in session.stream(said):
                self._event({"delta": piece})
        except LLMError as exc:
            self._event({"error": f"Alack! Mine oracle is indisposed -- {exc}"})
        except (BrokenPipeError, ConnectionResetError):
            return
        except Exception as exc:  # never leave the page hanging in silence
            self._event({"error": f"Alack! Something is amiss -- {exc}"})
        try:
            self._event("DONE")
        except (BrokenPipeError, ConnectionResetError):
            pass


# --------------------------------------------------------------------------
# Setting the table
# --------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="web.py",
        description="Open MrGentleman's parlour on a local web page.",
    )
    parser.add_argument("--host", default="127.0.0.1",
                        help="address to listen upon (default 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000,
                        help="port to listen upon (default 8000)")
    parser.add_argument("--offline", action="store_true",
                        help="speak only from his own wit, without a model")
    parser.add_argument("--model", help="model name (else MRGENTLEMAN_MODEL)")
    parser.add_argument("--base-url", help="OpenAI-compatible base URL")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    global ORACLE
    args = parse_args(argv)

    if not args.offline:
        config = Config.from_env(model=args.model, base_url=args.base_url)
        if config is not None:
            try:
                ORACLE = GentlemanLLM(config)
            except LLMError as exc:
                print(f"  (mine oracle is misaddressed: {exc})")

    try:
        server = ThreadingHTTPServer((args.host, args.port), Parlour)
    except OSError as exc:
        print(f"The parlour door will not open: {exc}", file=sys.stderr)
        return 1
    server.daemon_threads = True

    host = "localhost" if args.host in ("127.0.0.1", "0.0.0.0") else args.host
    print(f"MrGentleman: Good morrow! {mode_note().capitalize()}.")
    print(f"He awaits thee at  http://{host}:{args.port}")
    print("Press Ctrl+C to close the door.\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nMrGentleman: Farewell, and shut the door behind thee.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
