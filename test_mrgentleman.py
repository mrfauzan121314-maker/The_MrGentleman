#!/usr/bin/env python3
"""Tests for MrGentleman's own wit, and for the reading of .env.

    python3 -m unittest discover -v

Standard library only, exactly as the gentleman himself.
"""

from __future__ import annotations

import os
import random
import re
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

import llm
import mrgentleman as mg

#: Words a gentleman of 1700 would never be heard to use.
MODERN_SLANG = [
    "okay", "ok", "yeah", "yup", "cool", "awesome", "lol", "lmao", "gonna",
    "wanna", "guys", "texting", "selfie", "vibe", "sorry not sorry",
]

#: A spread of things a visitor might say.
UTTERANCES = [
    "hello", "how are you", "what is your name", "my name is Fauzan",
    "thank you", "would you care for some tea?", "what is a computer",
    "i think you are a fool", "what is the meaning of life?",
    "it rains again", "i have no money", "tell me a joke", "", "???",
    "goodbye", "why are we here?", "I am sad today", "play me a song",
    "what say you of the king?", "my hat is very fine",
]


@contextmanager
def barren_environment(**values: str):
    """An environment with nothing in it, and no .env to find."""
    with mock.patch.dict(os.environ, values, clear=True), \
            mock.patch("llm.find_dotenv", return_value=None):
        yield


class OfflineWitTest(unittest.TestCase):
    """The rule-based gentleman, without any oracle to consult."""

    def setUp(self) -> None:
        self.gentleman = mg.Gentleman(random.Random(2024))

    def test_replies_are_never_empty_or_unresolved(self):
        for said in UTTERANCES:
            with self.subTest(said=said):
                reply = self.gentleman.reply(said)
                self.assertTrue(reply.strip(), "he said nothing")
                self.assertNotIn("{", reply, "a placeholder was left unfilled")
                self.assertNotIn("}", reply, "a placeholder was left unfilled")
                self.assertNotIn("None", reply)

    def test_he_never_slips_into_modern_slang(self):
        gentleman = mg.Gentleman(random.Random(7))
        for said in UTTERANCES:
            for _ in range(10):
                reply = gentleman.reply(said)
                for word in MODERN_SLANG:
                    with self.subTest(said=said, word=word):
                        self.assertIsNone(
                            re.search(rf"\b{re.escape(word)}\b", reply, re.I),
                            f"modern slang crept in: {reply!r}",
                        )

    def test_every_scripted_reply_fills_its_placeholders(self):
        for keys, replies in mg.RULES:
            for reply in replies:
                with self.subTest(keys=keys[:2]):
                    polished = self.gentleman._polish(reply, "a thing")
                    self.assertNotIn("{", polished)
                    self.assertNotIn("}", polished)

    def test_he_remembers_the_visitors_name(self):
        reply = self.gentleman.reply("my name is Fauzan")
        self.assertIn("Fauzan", reply)
        self.assertEqual(self.gentleman._address(), "Fauzan")
        later = [self.gentleman.reply("how are you") for _ in range(20)]
        self.assertTrue(
            any("Fauzan" in answer for answer in later),
            "he never used the name he was given",
        )

    def test_a_question_about_tea_earns_an_answer_about_tea(self):
        for seed in range(10):
            gentleman = mg.Gentleman(random.Random(seed))
            reply = gentleman.reply("will you have some tea?").lower()
            self.assertIn("tea", reply, "he answered a tea question without tea")

    def test_he_does_not_repeat_himself_twice_running(self):
        previous = ""
        for index in range(60):
            said = UTTERANCES[index % len(UTTERANCES)]
            reply = self.gentleman.reply(said)
            self.assertNotEqual(reply, previous, "he said the same thing twice")
            previous = reply

    def test_the_same_seed_gives_the_same_conversation(self):
        first = [mg.Gentleman(random.Random(11)).reply(s) for s in UTTERANCES]
        second = [mg.Gentleman(random.Random(11)).reply(s) for s in UTTERANCES]
        self.assertEqual(first, second)

    def test_a_flourish_never_mangles_a_name(self):
        reply = mg.Gentleman._lower_first("MrGentleman, good soul.")
        self.assertTrue(reply.startswith("MrGentleman"))
        self.assertEqual(
            mg.Gentleman._lower_first("The pleasure is mine."),
            "the pleasure is mine.",
        )
        self.assertEqual(mg.Gentleman._lower_first("I know it."), "I know it.")

    def test_modern_words_are_quoted_in_period_dress(self):
        self.assertEqual(mg.topic("what is a computer"), "computer")
        dressed = mg.archaic("hello, you are very kind")
        self.assertIn("good morrow", dressed.lower())
        self.assertIn("thou art", dressed)
        self.assertIn("passing", dressed)
        self.assertIsNone(re.search(r"\byou\b", dressed))

    def test_a_long_speech_is_trimmed_when_quoted_back(self):
        echo = mg.archaic("you " + "nonsense " * 40)
        self.assertLessEqual(len(echo), 120)
        self.assertTrue(echo.endswith("..."))

    def test_farewells_are_recognised_and_ordinary_words_are_not(self):
        for farewell in ("farewell", "goodbye", "bye", "good night", "quit"):
            self.assertTrue(mg.FAREWELL.search(farewell), farewell)
        for ordinary in ("buy", "goodness", "quiet", "nearby"):
            self.assertFalse(mg.FAREWELL.search(ordinary), ordinary)


class DotEnvTest(unittest.TestCase):
    """The reading of a .env file, and the settings it feeds."""

    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / ".env"

    def write(self, text: str) -> Path:
        self.path.write_text(text, encoding="utf-8")
        return self.path

    def test_plain_export_quoted_and_commented_forms(self):
        self.write(
            "# a comment\n"
            "\n"
            'MRGENTLEMAN_API_KEY="from-dotenv"\n'
            "export MRGENTLEMAN_BASE_URL=http://127.0.0.1:8000/v1\n"
            "MRGENTLEMAN_MODEL='my model'   # a trailing note\n"
            "MRGENTLEMAN_TIMEOUT=12\n"
        )
        with barren_environment():
            used = llm.load_dotenv(self.path)
            self.assertEqual(used, self.path)
            self.assertEqual(os.environ["MRGENTLEMAN_API_KEY"], "from-dotenv")
            self.assertEqual(os.environ["MRGENTLEMAN_BASE_URL"], "http://127.0.0.1:8000/v1")
            self.assertEqual(os.environ["MRGENTLEMAN_MODEL"], "my model")
            self.assertEqual(os.environ["MRGENTLEMAN_TIMEOUT"], "12")

    def test_a_hash_inside_quotes_is_kept(self):
        self.write('MRGENTLEMAN_MODEL="a#b"\n')
        with barren_environment():
            llm.load_dotenv(self.path)
            self.assertEqual(os.environ["MRGENTLEMAN_MODEL"], "a#b")

    def test_the_shell_wins_over_the_file(self):
        self.write("MRGENTLEMAN_MODEL=from-file\n")
        with barren_environment(MRGENTLEMAN_MODEL="from-shell"):
            llm.load_dotenv(self.path)
            self.assertEqual(os.environ["MRGENTLEMAN_MODEL"], "from-shell")

    def test_nonsense_lines_are_ignored_without_complaint(self):
        self.write("this line has no equals sign\n= nameless\n# only a comment\n")
        with barren_environment():
            self.assertEqual(llm.load_dotenv(self.path), self.path)
            self.assertEqual(os.environ, {})

    def test_a_missing_file_is_simply_absent(self):
        with barren_environment():
            self.assertIsNone(llm.load_dotenv(Path(self.directory.name) / "nope.env"))

    def test_find_dotenv_prefers_the_working_directory(self):
        self.write("MRGENTLEMAN_MODEL=here\n")
        here = os.getcwd()
        os.chdir(self.directory.name)
        self.addCleanup(os.chdir, here)
        with mock.patch.dict(os.environ, {}, clear=True):  # find_dotenv left alone
            found = llm.find_dotenv()
        self.assertIsNotNone(found)
        self.assertEqual(Path(found).resolve(), self.path.resolve())

    def test_config_without_a_key_is_none(self):
        with barren_environment():
            self.assertIsNone(llm.Config.from_env())

    def test_config_is_built_from_the_file(self):
        self.write(
            "MRGENTLEMAN_API_KEY=a-key\n"
            "MRGENTLEMAN_BASE_URL=https://api.example.test/v1/\n"
            "MRGENTLEMAN_MODEL=a-model\n"
        )
        here = os.getcwd()
        os.chdir(self.directory.name)
        self.addCleanup(os.chdir, here)
        with mock.patch.dict(os.environ, {}, clear=True):  # find_dotenv left alone
            config = llm.Config.from_env()
        self.assertIsNotNone(config)
        self.assertEqual(config.api_key, "a-key")
        self.assertEqual(config.base_url, "https://api.example.test/v1")
        self.assertEqual(config.model, "a-model")

    def test_openai_names_are_accepted_as_fallbacks(self):
        with barren_environment(OPENAI_API_KEY="an-openai-key"):
            config = llm.Config.from_env()
        self.assertEqual(config.api_key, "an-openai-key")
        self.assertEqual(config.base_url, llm.DEFAULT_BASE_URL)

    def test_arguments_beat_the_environment(self):
        with barren_environment(
            MRGENTLEMAN_API_KEY="a-key",
            MRGENTLEMAN_MODEL="from-env",
            MRGENTLEMAN_BASE_URL="https://env.test/v1",
        ):
            config = llm.Config.from_env(
                model="from-argument", base_url="https://argument.test/v1"
            )
        self.assertEqual(config.model, "from-argument")
        self.assertEqual(config.base_url, "https://argument.test/v1")


if __name__ == "__main__":
    unittest.main(verbosity=2)
