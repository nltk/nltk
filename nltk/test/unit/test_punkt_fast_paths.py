# Natural Language Toolkit: Punkt token fast-path equivalence tests
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""PunktToken's shortcuts around its timed regex calls must change nothing.

Every regex call runs on the ``regex`` engine under a timeout, and the engine
reads the process clock when each call starts, so the two to three calls
Punkt made per token dominated ``sent_tokenize``. Three properties now skip
the call when the token's leading characters already rule a match out, for
PunktToken's own patterns only (a subclass that overrides one is untouched):
the numeric type (an ASCII first character other than "-", ".", "," or a
digit), ``is_ellipsis`` (no leading "..") and ``is_initial`` (no period
second). Each is compared with its regex on an exhaustive enumeration, and
``sent_tokenize`` on real text is compared with the shortcuts switched off.
"""

import itertools

import pytest

import nltk.tokenize.punkt as punkt
from nltk.tokenize.punkt import PunktSentenceTokenizer, PunktToken

_TAILS = ["", "1", ".5", "5.", "abc", "-", ",9", "1,000.", "..", "\n", "a1", "\u00e9"]


def _firsts():
    return [chr(c) for c in range(0x80)] + ["\u0130", "\u00e9", "\u0661", "\uff11"]


def test_numeric_type_matches_the_regex_for_every_first_character():
    for first in _firsts():
        for tail in _TAILS:
            tok = first + tail
            want = punkt._DEFAULT_RE_NUMERIC.sub("##number##", tok.lower())
            assert PunktToken(tok).type == want, repr(tok)


def _same_match(got, want):
    if want is None:
        return got is None
    return got is not None and got.span() == want.span() and got.group() == want.group()


def _tokens(alphabet, longest):
    for n in range(1, longest + 1):
        yield from ("".join(t) for t in itertools.product(alphabet, repeat=n))


def test_is_ellipsis_matches_the_regex():
    for tok in _tokens([".", "a", "\n", "\u2026", " "], 5):
        want = punkt._DEFAULT_RE_ELLIPSIS.match(tok)
        assert _same_match(PunktToken(tok).is_ellipsis, want), repr(tok)


def test_is_initial_matches_the_regex():
    alphabet = ["a", "Z", "1", ".", "_", "\u00e9", "\u0661", "\n", " ", "-"]
    for tok in _tokens(alphabet, 3):
        want = punkt._DEFAULT_RE_INITIAL.match(tok)
        assert _same_match(PunktToken(tok).is_initial, want), repr(tok)


def test_a_subclass_pattern_is_still_asked():
    from nltk import redos

    class XToken(PunktToken):
        _RE_NUMERIC = redos.compile(r"^x$")
        _RE_ELLIPSIS = redos.compile(r"e")
        _RE_INITIAL = redos.compile(r"i")

    tok = XToken("x")
    assert tok.type == "##number##"
    assert XToken("e").is_ellipsis and XToken("i").is_initial


def _corpus_texts():
    from nltk.corpus import gutenberg

    try:
        fileids = gutenberg.fileids()
    except LookupError:
        pytest.skip("gutenberg corpus not installed")
    return [gutenberg.raw(f)[:200_000] for f in fileids[:6]]


def test_sent_tokenize_is_unchanged_on_real_text(monkeypatch):
    texts = _corpus_texts()
    tokenizer = PunktSentenceTokenizer()
    fast = [tokenizer.tokenize(t) for t in texts]
    monkeypatch.setattr(punkt, "_NOT_NUMBER_START", frozenset())
    monkeypatch.setattr(punkt, "_DEFAULT_RE_ELLIPSIS", None)
    monkeypatch.setattr(punkt, "_DEFAULT_RE_INITIAL", None)
    slow = [tokenizer.tokenize(t) for t in texts]
    assert fast == slow
    assert sum(len(s) for s in fast) > 1000
