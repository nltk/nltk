"""GHSA-p4gq-832x-fm9v [high] -- URL-Encoded Path Traversal in nltk.data.load() Allows Arbitrary Local File Read"""
from ._base import OUTSIDE_CANARY, OUTSIDE_TARGET, FIXED, STATIC, VULNERABLE, is_security_rejection, probe


@probe("GHSA-p4gq-832x-fm9v")
def _data_load_urlencoded_traversal():
    """Percent-encoded traversal bypassed the literal '../' check."""
    import nltk.data

    if not OUTSIDE_TARGET:
        return STATIC, "no outside-root target on this platform"
    enc = OUTSIDE_TARGET.replace("/", "%2f").lstrip("%2f")
    payloads = [
        "%2e%2e%2f" * 12 + enc,       # encoded ../
        "..%2f" * 12 + enc,           # encoded slash only
        "%252e%252e%252f" * 8 + enc,  # double-encoded
        "..%c0%af" * 8 + enc,         # overlong UTF-8 slash
    ]
    reached = False
    for payload in payloads:
        try:
            data = nltk.data.load(payload, format="raw")
            if OUTSIDE_CANARY in (data if isinstance(data, str) else str(data)):
                return VULNERABLE, "encoded traversal read %s: %s" % (OUTSIDE_TARGET, payload[:24])
        except Exception as exc:
            reached = reached or is_security_rejection(exc)
    if reached:
        return FIXED, "%d encoded traversal payloads rejected" % len(payloads)
    return STATIC, "no security rejection observed"
