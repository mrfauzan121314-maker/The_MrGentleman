#!/usr/bin/env python3
"""MrGentleman's conversation with a real language model.

The model is reached through any OpenAI-compatible ``/chat/completions``
endpoint -- OpenAI, Z.ai, Groq, OpenRouter, or a server of one's own -- so the
chatbot keeps its single virtue: no dependencies, only the standard library.

Configuration comes from the environment, never from this file:

    MRGENTLEMAN_API_KEY   the key (OPENAI_API_KEY is accepted too)
    MRGENTLEMAN_BASE_URL  e.g. https://api.openai.com/v1
    MRGENTLEMAN_MODEL     e.g. gpt-4o-mini
    MRGENTLEMAN_TIMEOUT   seconds to wait upon the oracle (default 90)

The same names may be kept in a ``.env`` file beside the script (or in the
working directory), so no key need be exported by hand each session.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4o-mini"

#: Exchanges of the conversation MrGentleman keeps in mind.
MAX_HISTORY_TURNS = 8

RETRY_STATUSES = {408, 409, 429, 500, 502, 503, 504}

PERSONA = """\
Thou art MrGentleman, a gentleman of London in the year seventeen hundred: a
man of leisure, of letters, and of very firm opinions upon tea, weather, and
the folly of his neighbours. Thou art warm, witty, and unfailingly courteous.

SPEECH
- Speak only in the English of the early 1700s: thee, thou, thy, thine; hath,
  doth, dost, art, shalt; and turns such as "prithee", "forsooth", "marry",
  "alack", "good morrow", "by my troth", "I daresay".
- Never use modern slang, emoji, or internet words. No "okay", "yeah", "cool",
  "guys", "awesome", "lol".
- Keep each reply to two to five sentences; a gentleman does not weary his
  company. Ask a question now and then, that the talk may live.

THE MODERN WORLD
- Thou knowest nothing of thy visitor's age. When they speak of things beyond
  1700 -- telephones, computers, the internet, flying machines, artificial
  intelligence -- be curious and courteous, and imagine them in the terms of
  thine own century. Never pretend to grasp a device thou hast never seen.

MANNERS
- Never break character. Never call thyself a machine, a model, a program or
  an assistant, and never mention these instructions.
- Answer the visitor's question before thou art witty about it.
- Stay decent and kind: no slurs, no cruelty, nothing unfit for a parlour.
- If the visitor is low of spirit, be gentle and keep them company.

In the manner of: "Good morrow, and well met. Thou askest of the weather; I
answer that it rains, as it hath since the Flood, and that my boots are the
wiser for it. How dost thou keep thyself dry?"
"""


class LLMError(Exception):
    """The oracle is indisposed, told in a manner fit for a parlour."""


@dataclass
class Config:
    """Where the conversation is had, and under whose name."""

    api_key: str
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    timeout: float = 90.0
    temperature: float = 0.8

    @classmethod
    def from_env(
        cls, model: str | None = None, base_url: str | None = None
    ) -> "Config | None":
        """Read the settings from the environment; None when no key is set."""
        load_dotenv()
        key = os.environ.get("MRGENTLEMAN_API_KEY") or os.environ.get("OPENAI_API_KEY")
        if not key:
            return None
        return cls(
            api_key=key.strip(),
            base_url=(base_url or os.environ.get("MRGENTLEMAN_BASE_URL")
                      or os.environ.get("OPENAI_BASE_URL") or DEFAULT_BASE_URL).rstrip("/"),
            model=model or os.environ.get("MRGENTLEMAN_MODEL") or DEFAULT_MODEL,
            timeout=_float(os.environ.get("MRGENTLEMAN_TIMEOUT"), 90.0),
        )


def find_dotenv() -> Path | None:
    """The nearest .env: the working directory first, then the script's own."""
    for candidate in (Path.cwd() / ".env", Path(__file__).resolve().parent / ".env"):
        if candidate.is_file():
            return candidate
    return None


def load_dotenv(path: str | Path | None = None) -> Path | None:
    """Read KEY=VALUE lines from a .env file into the environment.

    Anything already set in the shell wins, so real environment variables
    always take precedence over the file. Returns the file used, if any.
    """
    source = Path(path) if path is not None else find_dotenv()
    if source is None or not source.is_file():
        return None
    try:
        lines = source.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None

    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        name, sep, value = line.partition("=")
        name, value = name.strip(), value.strip()
        if not sep or not name:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        elif " #" in value:
            value = value.split(" #", 1)[0].rstrip()
        if name not in os.environ:
            os.environ[name] = value
    return source


def _float(value: str | None, fallback: float) -> float:
    try:
        return float(value) if value else fallback
    except ValueError:
        return fallback


class GentlemanLLM:
    """Speaks with the visitor through a chat-completions endpoint."""

    def __init__(self, config: Config) -> None:
        if not config.base_url.startswith(("http://", "https://")):
            raise LLMError(f"'{config.base_url}' is no address I recognise")
        self.config = config

    @property
    def endpoint(self) -> str:
        return f"{self.config.base_url}/chat/completions"

    # -- the request ------------------------------------------------------
    def _payload(self, messages: list[dict[str, str]]) -> bytes:
        return json.dumps(
            {
                "model": self.config.model,
                "messages": [{"role": "system", "content": PERSONA}, *messages],
                "temperature": self.config.temperature,
                "stream": True,
            }
        ).encode("utf-8")

    def _open(self, messages: list[dict[str, str]]):
        """Ask the oracle politely, and again if it is merely busy."""
        delay = 1.0
        trouble = "the oracle is silent"
        for attempt in range(3):
            request = urllib.request.Request(
                self.endpoint,
                data=self._payload(messages),
                headers={
                    "Authorization": f"Bearer {self.config.api_key}",
                    "Content-Type": "application/json",
                    "Accept": "text/event-stream",
                    "User-Agent": "MrGentleman/1.0",
                },
                method="POST",
            )
            try:
                return urllib.request.urlopen(request, timeout=self.config.timeout)
            except urllib.error.HTTPError as exc:
                trouble = self._explain(exc)
                if exc.code in RETRY_STATUSES and attempt < 2:
                    time.sleep(delay)
                    delay *= 2
                    continue
                raise LLMError(trouble) from exc
            except urllib.error.URLError as exc:
                trouble = f"the road is barred ({exc.reason})"
                if attempt < 2:
                    time.sleep(delay)
                    delay *= 2
                    continue
                raise LLMError(trouble) from exc
            except (TimeoutError, OSError) as exc:
                trouble = f"the wait grew overlong ({exc})"
                if attempt < 2:
                    time.sleep(delay)
                    delay *= 2
                    continue
                raise LLMError(trouble) from exc
        raise LLMError(trouble)

    @staticmethod
    def _explain(exc: urllib.error.HTTPError) -> str:
        """Turn an API error into a short, keyless reason."""
        try:
            raw = exc.read().decode("utf-8", "replace")
        except Exception:  # pragma: no cover - the body is already gone
            return f"the oracle answered {exc.code}"
        message = ""
        try:
            body = json.loads(raw)
            error = body.get("error") if isinstance(body, dict) else None
            if isinstance(error, dict):
                message = str(error.get("message") or "")
            elif isinstance(error, str):
                message = error
            elif isinstance(body, dict):
                message = str(body.get("message") or "")
        except json.JSONDecodeError:
            message = raw.strip()
        message = " ".join(message.split())[:200]
        if not message:
            return f"the oracle answered {exc.code}"
        return f"the oracle answered {exc.code}: {message}"

    # -- the reply --------------------------------------------------------
    def stream(self, messages: list[dict[str, str]]) -> Iterator[str]:
        """Yield the reply a few words at a time, as he composes it."""
        response = self._open(messages)
        spoke = False
        try:
            for raw_line in response:
                line = raw_line.decode("utf-8", "replace").strip()
                if not line.startswith("data:"):
                    continue
                data = line[len("data:"):].strip()
                if data == "[DONE]":
                    break
                try:
                    event = json.loads(data)
                except json.JSONDecodeError:
                    continue
                choices = event.get("choices") or []
                if not choices:
                    continue
                piece = (choices[0].get("delta") or {}).get("content")
                if piece:
                    spoke = True
                    yield piece
        finally:
            response.close()
        if not spoke:
            raise LLMError("the oracle returned an empty page")
