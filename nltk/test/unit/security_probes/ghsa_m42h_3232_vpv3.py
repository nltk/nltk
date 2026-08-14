"""GHSA-m42h-3232-vpv3 [high] -- Arbitrary File Read via Path Traversal in nltk.data.load() through Percent-Encoded Seque"""
from ._base import FIXED, VULNERABLE, probe


@probe("GHSA-m42h-3232-vpv3")
def _data_load_traversal():
    """Arbitrary file read via path traversal in nltk.data.load()."""
    import nltk.data

    for payload in ("../" * 12 + "etc/passwd", "/etc/passwd"):
        try:
            nltk.data.load(payload, format="raw")
            return VULNERABLE, "nltk.data.load(%r) succeeded" % payload[:28]
        except Exception:
            pass
    return FIXED, "traversal and absolute paths both rejected"
