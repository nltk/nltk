"""GHSA-ww6m-cw3f-q94g [medium] -- Quadratic-time DoS in PorterStemmer via long runs of 'y'"""

from ._base import DOS_BUDGET, FIXED, VULNERABLE, probe, timed


@probe("GHSA-ww6m-cw3f-q94g")
def _porter_stemmer_quadratic():
    """Quadratic-time DoS in PorterStemmer via long runs of 'y'."""
    from nltk.stem.porter import PorterStemmer

    stemmer = PorterStemmer()
    small = timed(stemmer.stem, "y" * 4000)
    large = timed(stemmer.stem, "y" * 8000)
    ratio = large / max(small, 1e-4)
    if large > DOS_BUDGET or ratio > 3.0:
        return VULNERABLE, "doubling cost {:.1f}x ({:.2f}s -> {:.2f}s)".format(
            ratio, small, large
        )
    return FIXED, "linear: {:.1f}x per doubling ({:.3f}s at n=8000)".format(
        ratio, large
    )
