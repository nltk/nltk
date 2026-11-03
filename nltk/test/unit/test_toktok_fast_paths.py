# Natural Language Toolkit: ToktokTokenizer fast-path equivalence tests
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""ToktokTokenizer's skipped substitutions must change no token.

ToktokTokenizer runs 24 timed regex substitutions per text. For 18 of its own
patterns every match contains one of a few characters, so a text holding
none of them is passed over without the regex call. Each pattern's
characters are checked against the pattern on every short string, and the
tokens of real sentences with the shortcut switched off.
"""

import itertools

import pytest

import nltk.tokenize.toktok as toktok
from nltk import redos
from nltk.tokenize.toktok import ToktokTokenizer

_RULES = ToktokTokenizer.TOKTOK_REGEXES
_ALL_NEEDED = sorted(set("".join(toktok._NEEDS_BY_SOURCE.values())))
_OTHERS = ["a", "Z", "1", " ", "\n", "/", "s", "\u00e9", "_", "\u00a1"]


def test_filtered_patterns_are_the_ones_with_a_short_character_list():
    sources = [pattern.pattern for pattern, _repl in _RULES]
    assert set(toktok._NEEDS_BY_SOURCE) <= set(sources)
    assert len(toktok._NEEDS) == 18
    assert r" {2,}" not in toktok._NEEDS_BY_SOURCE


@pytest.mark.parametrize(
    "pattern,repl",
    [
        pytest.param(pattern, repl, id=f"rule{i}")
        for i, (pattern, repl) in enumerate(_RULES)
        if id(pattern) in toktok._NEEDS
    ],
)
def test_no_match_without_a_needed_character(pattern, repl):
    needs = toktok._NEEDS[id(pattern)]
    wide = [c for c in _ALL_NEEDED + _OTHERS if c not in needs]
    narrow = [c for c in _ALL_NEEDED[::2] + _OTHERS[:6] if c not in needs]
    strings = [""]
    strings += ["".join(t) for n in (1, 2) for t in itertools.product(wide, repeat=n)]
    strings += ["".join(t) for t in itertools.product(narrow, repeat=3)]
    for text in strings:
        assert pattern.sub(repl, text) == text, repr(text)
        assert pattern.search(text) is None, repr(text)


def test_tokens_are_unchanged_on_real_sentences(monkeypatch):
    from nltk.corpus import brown, udhr

    try:
        sentences = [" ".join(s) for s in brown.sents()[:4000]]
        for fileid in ("French_Francais-Latin1", "Arabic_Alarabia-Arabic"):
            sentences += udhr.raw(fileid).splitlines()
    except LookupError:
        pytest.skip("brown or udhr not installed")
    tokenizer = ToktokTokenizer()
    fast = [tokenizer.tokenize(s) for s in sentences]
    monkeypatch.setattr(toktok, "_NEEDS", {})
    assert fast == [tokenizer.tokenize(s) for s in sentences]


def test_a_substituted_pattern_is_always_run():
    class Mine(ToktokTokenizer):
        TOKTOK_REGEXES = [(redos.compile(r"x"), "y")] + ToktokTokenizer.TOKTOK_REGEXES

    assert Mine().tokenize("ax b") == ["ay", "b"]
