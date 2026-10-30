# Natural Language Toolkit: expanded attack harness for the tokenizer guards
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""The Treebank and NLTK word tokenizers' span alignment driven with hostile
and benign input and judged against a reference implementation of the previous
quote matching on the same text, on random and on real corpus text, in linear
time. Nothing is mocked."""

import random

import pytest

from nltk import redos
from nltk.test.unit.test_quadratic_dos import _assert_subquadratic
from nltk.tokenize import NLTKWordTokenizer, TreebankWordTokenizer, word_tokenize
from nltk.tokenize.util import align_tokens

TOKENIZERS = [NLTKWordTokenizer, TreebankWordTokenizer]


def _reference_spans(tokenizer, text):
    """The pre-fix alignment, kept as the oracle: pop the matched quotes off
    the front of a list, one per quote token."""
    raw_tokens = tokenizer.tokenize(text)
    if ('"' in text) or ("''" in text):
        matched = [m.group() for m in redos.finditer(r"``|'{2}|\"", text)]
        tokens = [
            matched.pop(0) if tok in ['"', "``", "''"] else tok for tok in raw_tokens
        ]
    else:
        tokens = raw_tokens
    return list(align_tokens(tokens, text))


QUOTED = [
    'He said "hello" and left.',
    "''quoted'' and ``more'' and \"mixed\"",
    '"" "" ""',
    "''''",
    "``````",
    'a "b" c "d" e "f"',
    "it's ''not'' \"a\" 'quote'",
    '"unterminated',
    "nested \"outer 'inner' outer\" end",
    '“unicode quotes” and "ascii"',
    'quotes "at" line\nbreaks "and" tabs\t"here"',
    '"' * 200,
    "Good muffins cost $3.88\nin New York.  Please buy me\ntwo of them.\n\nThanks.",
]


class TestSpanAlignmentAgainstTheReference:
    @pytest.mark.parametrize("cls", TOKENIZERS, ids=lambda c: c.__name__)
    @pytest.mark.parametrize("text", QUOTED, ids=lambda t: repr(t)[:16])
    def test_quoted_text_aligns_as_before(self, cls, text):
        tokenizer = cls()
        spans = list(tokenizer.span_tokenize(text))
        assert spans == _reference_spans(tokenizer, text)
        # every span slices the text back to its token, quotes included
        tokens = tokenizer.tokenize(text)
        sliced = [text[s:e] for s, e in spans]
        assert len(sliced) == len(tokens)
        for got, tok in zip(sliced, tokens):
            assert got == tok or (tok in ("``", "''") and got in ('"', "``", "''")), (
                got,
                tok,
            )

    @pytest.mark.parametrize("cls", TOKENIZERS, ids=lambda c: c.__name__)
    @pytest.mark.parametrize("seed", range(20))
    def test_random_quote_mixes_align_as_before(self, cls, seed):
        rng = random.Random(seed)
        alphabet = [
            "word",
            "a",
            "it's",
            '"',
            "''",
            "``",
            "'",
            " ",
            "\n",
            ".",
            ",",
            "(",
            ")",
            "3.88",
            "$",
        ]
        text = "".join(rng.choice(alphabet) for _ in range(rng.randint(1, 300)))
        tokenizer = cls()
        try:
            expected = _reference_spans(tokenizer, text)
        except IndexError:
            expected = IndexError
        if expected is IndexError:
            with pytest.raises((IndexError, StopIteration, RuntimeError)):
                list(tokenizer.span_tokenize(text))
        else:
            assert list(tokenizer.span_tokenize(text)) == expected

    @pytest.mark.parametrize("cls", TOKENIZERS, ids=lambda c: c.__name__)
    def test_a_flood_of_quotes_aligns_in_linear_time(self, cls):
        tokenizer = cls()

        def op(n):
            text = ' "q" ' * n
            spans = list(tokenizer.span_tokenize(text))
            assert len(spans) == 3 * n

        _assert_subquadratic(op, 10_000, 40_000)


class TestRealText:
    def _needs(self, name):
        import nltk.data

        try:
            nltk.data.find(name)
        except LookupError:
            pytest.skip(f"{name} is not installed")

    @pytest.mark.parametrize("cls", TOKENIZERS, ids=lambda c: c.__name__)
    def test_real_corpus_text_aligns_as_before(self, cls):
        self._needs("corpora/webtext")
        from nltk.corpus import webtext

        tokenizer = cls()
        text = webtext.raw("overheard.txt")[:200_000]
        spans = list(tokenizer.span_tokenize(text))
        assert spans == _reference_spans(tokenizer, text)
        assert len(spans) > 30_000

    def test_word_tokenize_is_unchanged(self):
        self._needs("tokenizers/punkt_tab")
        text = 'He said "hello" and left. It\'s fine.'
        assert word_tokenize(text) == [
            "He",
            "said",
            "``",
            "hello",
            "''",
            "and",
            "left",
            ".",
            "It",
            "'s",
            "fine",
            ".",
        ]
        assert TreebankWordTokenizer().tokenize('"a" b') == ["``", "a", "''", "b"]
        assert NLTKWordTokenizer().tokenize("''a'' b") == ["''", "a", "''", "b"]
