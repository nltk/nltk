"""GHSA-ww6m-cw3f-q94g [medium] -- Quadratic-time DoS in PorterStemmer via long runs of 'y'"""

from ._base import FIXED, VULNERABLE, probe, within_budget


@probe("GHSA-ww6m-cw3f-q94g")
def _porter_stemmer_quadratic():
    """_measure called an O(run) _is_consonant per position: 'y'*20000 was >20s."""
    from nltk.stem.porter import PorterStemmer

    ok, seconds = within_budget(lambda: PorterStemmer().stem("y" * 40000 + "ness"))
    if ok:
        return FIXED, "stem('y'*40000) in %.3fs" % seconds
    return VULNERABLE, "stem('y'*40000) took %.1fs" % seconds
