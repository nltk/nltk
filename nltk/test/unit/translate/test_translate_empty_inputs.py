"""
Regression tests for ZeroDivisionError in NLTK translate metrics
when called with empty sequences.

Bugs fixed:
  1. corpus_chrf([], [])                    -> ZeroDivisionError (num_sents == 0)
  2. corpus_chrf(refs, hyps, min_len=N, max_len=M) where N > M
                                            -> ZeroDivisionError (num_ngram_sizes == 0)
  3. sentence_ribes(refs, [])               -> ZeroDivisionError (len(hypothesis) == 0)
  4. corpus_ribes([], [])                   -> ZeroDivisionError (len(hypotheses) == 0)

All four functions now return 0.0 for degenerate inputs instead of crashing.
"""
import pytest

from nltk.translate.chrf_score import corpus_chrf
from nltk.translate.ribes_score import corpus_ribes, sentence_ribes


# ── corpus_chrf ────────────────────────────────────────────────────────────────


def test_corpus_chrf_empty_corpus_returns_zero():
    """corpus_chrf([], []) must return 0.0 not raise ZeroDivisionError."""
    assert corpus_chrf([], []) == 0.0


def test_corpus_chrf_min_len_greater_than_max_len_returns_zero():
    """corpus_chrf with min_len > max_len produces no n-gram orders; must not crash."""
    ref = ["hello", "world"]
    hyp = ["hello", "world"]
    assert corpus_chrf([ref], [hyp], min_len=4, max_len=3) == 0.0


def test_corpus_chrf_identical_sentences_returns_one():
    """Regression: corpus_chrf on identical sentences must still return 1.0."""
    sent = "It is a guide to action".split()
    result = corpus_chrf([sent], [sent])
    assert result == pytest.approx(1.0)


# ── sentence_ribes ─────────────────────────────────────────────────────────────


def test_sentence_ribes_empty_hypothesis_returns_zero():
    """sentence_ribes with empty hypothesis must return 0.0 not raise ZeroDivisionError."""
    assert sentence_ribes([["hello", "world"]], []) == 0.0


def test_sentence_ribes_identical_returns_one():
    """Regression: sentence_ribes on identical sentences must still return 1.0."""
    sent = ["hello", "world"]
    result = sentence_ribes([sent], sent)
    assert result == pytest.approx(1.0)


# ── corpus_ribes ───────────────────────────────────────────────────────────────


def test_corpus_ribes_empty_corpus_returns_zero():
    """corpus_ribes([], []) must return 0.0 not raise ZeroDivisionError."""
    assert corpus_ribes([], []) == 0.0


def test_corpus_ribes_identical_returns_one():
    """Regression: corpus_ribes on identical sentences must still return 1.0."""
    sent = ["hello", "world"]
    result = corpus_ribes([[sent]], [sent])
    assert result == pytest.approx(1.0)
