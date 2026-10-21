"""Regression tests for graceful handling of redos's MAX_PATTERN_LENGTH refusal.

Every regex in NLTK compiles through ``nltk.redos``, which refuses a source
larger than ``MAX_PATTERN_LENGTH`` (a compile-time DoS guard). These tests cover
the sites where a pattern SOURCE is built from untrusted input, so an oversized
source must be handled cleanly (a bounded source or an explained error) rather
than surfacing as an uncaught refusal. Each test also pins that ordinary input
still works.
"""

import warnings

import pytest

import nltk.redos as redos

BIG = redos.MAX_PATTERN_LENGTH


class TestTokenSearcherFindallRefusal:
    def _text(self):
        from nltk.text import Text

        return Text("a b a c a b d".split())

    def test_ordinary_query_unchanged(self):
        # A normal query runs (Text.findall prints and returns None).
        assert self._text().findall("<a> (<.>)") is None

    def test_oversized_query_is_a_clean_error(self):
        # An oversized query is refused at compile time; findall must report it
        # as a bad query, not leak the raw redos refusal.
        with pytest.raises(ValueError):
            self._text().findall("<" + "a" * BIG + ">")
