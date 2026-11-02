"""
Regression tests for empty-input handling in NLTK translation metrics.

The score functions return 0.0 for empty corpora or hypotheses. Invalid CHRF
n-gram ranges raise ValueError instead of causing ZeroDivisionError.
"""

import pytest

from nltk.translate.chrf_score import corpus_chrf
from nltk.translate.ribes_score import corpus_ribes, sentence_ribes

# corpus_chrf


def test_corpus_chrf_empty_corpus_returns_zero():
    """corpus_chrf([], []) must return 0.0 not raise ZeroDivisionError."""
    assert corpus_chrf([], []) == 0.0


def test_corpus_chrf_min_len_greater_than_max_len_raises_value_error():
    """An invalid n-gram range should raise a clear error, not ZeroDivisionError."""
    ref = ["hello", "world"]
    hyp = ["hello", "world"]
    with pytest.raises(
        ValueError, match="min_len must be less than or equal to max_len"
    ):
        corpus_chrf([ref], [hyp], min_len=4, max_len=3)


def test_corpus_chrf_identical_sentences_returns_one():
    """Regression: corpus_chrf on identical sentences must still return 1.0."""
    sent = "It is a guide to action".split()
    result = corpus_chrf([sent], [sent])
    assert result == pytest.approx(1.0)


# sentence_ribes


def test_sentence_ribes_empty_hypothesis_returns_zero():
    """sentence_ribes with empty hypothesis must return 0.0 not raise ZeroDivisionError."""
    assert sentence_ribes([["hello", "world"]], []) == 0.0


def test_sentence_ribes_identical_returns_one():
    """Regression: sentence_ribes on identical sentences must still return 1.0."""
    sent = ["hello", "world"]
    result = sentence_ribes([sent], sent)
    assert result == pytest.approx(1.0)


# corpus_ribes


def test_corpus_ribes_empty_corpus_returns_zero():
    """corpus_ribes([], []) must return 0.0 not raise ZeroDivisionError."""
    assert corpus_ribes([], []) == 0.0


def test_corpus_ribes_identical_returns_one():
    """Regression: corpus_ribes on identical sentences must still return 1.0."""
    sent = ["hello", "world"]
    result = corpus_ribes([[sent]], [sent])
    assert result == pytest.approx(1.0)
