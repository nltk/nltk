"""GHSA-fg7f-2386-8897 [high] -- ReDoS in NLTK ReviewsCorpusReader FEATURES regex"""

from ._base import DOS_BUDGET, FIXED, VULNERABLE, probe, timed


@probe("GHSA-fg7f-2386-8897")
def _reviews_features_redos():
    """Unbounded greedy label run in the ReviewsCorpusReader FEATURES regex."""
    from nltk.corpus.reader.reviews import FEATURES

    payload = "a " * 4000 + "["
    try:
        seconds = timed(FEATURES.findall, payload)
    except Exception as exc:
        return FIXED, "rejected (%s)" % type(exc).__name__
    if seconds > DOS_BUDGET:
        return VULNERABLE, "FEATURES regex took %.1fs" % seconds
    return FIXED, "hostile line matched in %.3fs" % seconds
