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


class TestSonorityVowelAccumulation:
    """SyllableTokenizer.assign_values remembers every unknown char as a vowel and
    builds a pattern from the accumulated set; the set must stay bounded so a
    stream of distinct codepoints cannot grow the source past the redos cap."""

    def test_ordinary_tokenisation_unchanged(self):
        from nltk.tokenize import SyllableTokenizer

        assert SyllableTokenizer().tokenize("justification") == [
            "jus",
            "ti",
            "fi",
            "ca",
            "tion",
        ]

    def test_distinct_codepoint_stream_stays_bounded(self):
        from nltk.tokenize.sonority_sequencing import (
            _MAX_VOWEL_CHARS,
            SyllableTokenizer,
        )

        ssp = SyllableTokenizer()
        # Many tokens on one reused instance, each within MAX_TOKEN_LEN but
        # carrying thousands of distinct exotic codepoints; pre-fix this grew
        # self.vowels without limit until the joined pattern tripped the cap.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            for k in range(30):
                base = 0x4E00 + k * 4000
                ssp.tokenize("ae" + "".join(chr(base + i) for i in range(4000)))
        assert len(ssp.vowels) <= _MAX_VOWEL_CHARS
        assert len("|".join(ssp.vowels)) < BIG
        # Still works after the flood.
        assert ssp.tokenize("justification") == ["jus", "ti", "fi", "ca", "tion"]


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


class TestTgrepNodeLiteralRefusal:
    def test_ordinary_query_unchanged(self):
        from nltk import tgrep

        assert tgrep.tgrep_compile("NN") is not None

    def test_oversized_regex_literal_is_a_tgrep_error(self):
        from nltk import tgrep

        with pytest.raises(tgrep.TgrepException):
            tgrep.tgrep_compile("/" + "a" * (BIG + 10) + "/")


class TestHelpTagpatternRefusal:
    def test_oversized_tagpattern_fails_closed(self, capsys):
        # The refusal is the library-wide fail-closed contract (PR 3910): an
        # oversized pattern must RAISE, never degrade to a printed warning.
        import nltk.help as help_module

        with pytest.raises(ValueError, match="Invalid or oversized tag pattern"):
            try:
                help_module._format_tagset("upenn_tagset", "N" * (BIG + 10))
            except LookupError:
                pytest.skip("upenn_tagset data unavailable")
        assert "Invalid or oversized tag pattern" not in capsys.readouterr().out
