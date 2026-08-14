"""GHSA-f8m6-h2c7-8h9x [high] -- Inefficient Regular Expression Complexity in nltk (word_tokenize, sent_tokenize)"""
from ._base import DOS_BUDGET, FIXED, VULNERABLE, probe, timed


@probe("GHSA-f8m6-h2c7-8h9x")
def _word_tokenize_redos():
    """Inefficient regular expression complexity in word_tokenize."""
    from nltk.tokenize import word_tokenize

    payload = "a" * 40000
    try:
        seconds = timed(word_tokenize, payload)
    except Exception as exc:
        return FIXED, "rejected (%s)" % type(exc).__name__
    if seconds > DOS_BUDGET:
        return VULNERABLE, "word_tokenize took %.1fs" % seconds
    return FIXED, "40k-char token in %.3fs" % seconds
