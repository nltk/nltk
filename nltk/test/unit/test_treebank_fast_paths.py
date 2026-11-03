# Natural Language Toolkit: TreebankWordTokenizer fast-path equivalence tests
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""TreebankWordTokenizer's skipped substitutions must change no token.

TreebankWordTokenizer runs 22 timed regex substitutions per text, and every
match of each of them contains one of a few characters (a quote, a period, a
bracket, ...), so a text holding none of a pattern's characters is passed over
without its regex call (``destructive._sub``, with treebank's own map). Each
pattern's characters are checked against the pattern on every short string,
and the tokens of real sentences with the shortcut switched off.
"""

import itertools

import pytest

import nltk.tokenize.treebank as treebank_module
from nltk import redos
from nltk.tokenize.treebank import TreebankWordTokenizer

_T = TreebankWordTokenizer
_RULES = (
    _T.STARTING_QUOTES
    + _T.ENDING_QUOTES
    + _T.PUNCTUATION
    + _T.CONVERT_PARENTHESES
    + [_T.PARENS_BRACKETS, _T.DOUBLE_DASHES]
)
_ALL_NEEDED = sorted(set("".join(treebank_module._NEEDS_BY_SOURCE.values())))
_OTHERS = ["a", "Z", "1", " ", "\n", "s", "t", "n", "\u00e9", "_"]


def test_every_pattern_is_filtered():
    sources = [pattern.pattern for pattern, _repl in _RULES]
    assert set(treebank_module._NEEDS_BY_SOURCE) == set(sources)
    assert len(treebank_module._NEEDS) == len(sources) == 22


@pytest.mark.parametrize(
    "pattern,repl",
    [
        pytest.param(pattern, repl, id=f"rule{i}")
        for i, (pattern, repl) in enumerate(_RULES)
    ],
)
def test_no_match_without_a_needed_character(pattern, repl):
    """Every string of up to two characters over all the needed characters
    and ten others, and of three over a smaller set, that holds none of this
    pattern's needed characters is left unchanged by its substitution."""
    needs = treebank_module._NEEDS[id(pattern)]
    wide = [c for c in _ALL_NEEDED + _OTHERS if c not in needs]
    narrow = [c for c in _ALL_NEEDED[::3] + _OTHERS[:6] if c not in needs]
    strings = [""]
    strings += ["".join(t) for n in (1, 2) for t in itertools.product(wide, repeat=n)]
    strings += ["".join(t) for t in itertools.product(narrow, repeat=3)]
    for text in strings:
        assert pattern.sub(repl, text) == text, repr(text)
        assert pattern.search(text) is None, repr(text)


def _real_sentences():
    from nltk.corpus import brown, gutenberg, treebank, webtext
    from nltk.tokenize import sent_tokenize

    try:
        out = [" ".join(s) for s in brown.sents()[:4000]]
        out += [" ".join(s) for s in treebank.sents()[:1500]]
        out += sent_tokenize(gutenberg.raw("austen-emma.txt")[:150_000])
        out += sent_tokenize(webtext.raw("overheard.txt")[:150_000])
    except LookupError:
        pytest.skip("brown, treebank, gutenberg or webtext not installed")
    return out


def test_tokens_are_unchanged_on_real_sentences(monkeypatch):
    sentences = _real_sentences()
    tokenizer = TreebankWordTokenizer()
    fast = [tokenizer.tokenize(s) for s in sentences]
    fast_ptb = [tokenizer.tokenize(s, convert_parentheses=True) for s in sentences]
    monkeypatch.setattr(treebank_module, "_NEEDS", {})
    assert fast == [tokenizer.tokenize(s) for s in sentences]
    assert fast_ptb == [
        tokenizer.tokenize(s, convert_parentheses=True) for s in sentences
    ]
    assert len(sentences) > 5000


def test_a_substituted_pattern_is_always_run():
    """A subclass's own pattern, even with the same source, is not filtered."""

    class Mine(TreebankWordTokenizer):
        PUNCTUATION = [(redos.compile(r"x"), "y")] + TreebankWordTokenizer.PUNCTUATION
        DOUBLE_DASHES = (redos.compile(r"--"), r" -- ")

    assert Mine().tokenize("ax b--c") == ["ay", "b", "--", "c"]
