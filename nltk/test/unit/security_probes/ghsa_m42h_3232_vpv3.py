"""GHSA-m42h-3232-vpv3 [high] -- Arbitrary File Read via Path Traversal in nltk.data.load()"""
from ._base import OUTSIDE_CANARY, OUTSIDE_TARGET, FIXED, STATIC, VULNERABLE, is_security_rejection, probe


@probe("GHSA-m42h-3232-vpv3")
def _data_load_traversal():
    """nltk.data.load() built a path from its argument with no containment."""
    import nltk.data

    if not OUTSIDE_TARGET:
        return STATIC, "no outside-root target on this platform"
    rel = OUTSIDE_TARGET.lstrip("/")
    payloads = ["../" * 12 + rel, OUTSIDE_TARGET, "..\\" * 12 + rel, "....//" * 12 + rel]
    reached = False
    for payload in payloads:
        try:
            data = nltk.data.load(payload, format="raw")
            if OUTSIDE_CANARY in (data if isinstance(data, str) else str(data)):
                return VULNERABLE, "nltk.data.load(%r) read %s" % (payload[:24], OUTSIDE_TARGET)
        except Exception as exc:
            reached = reached or is_security_rejection(exc)
    if reached:
        return FIXED, "%d traversal payloads rejected" % len(payloads)
    return STATIC, "no security rejection observed"
