"""GHSA-p4gq-832x-fm9v [high] -- URL-Encoded Path Traversal in nltk.data.load() Allows Arbitrary Local File Read

Probe: run the attack, report what the tree does now. See _base for statuses.
"""
from ._base import FIXED, VULNERABLE, probe


@probe("GHSA-p4gq-832x-fm9v")
def _data_load_urlencoded_traversal():
    """URL-encoded traversal (%2e%2e%2f) bypassed the literal '../' check."""
    import nltk.data

    for payload in ("%2e%2e%2f" * 12 + "etc%2fpasswd", "..%2f" * 12 + "etc/passwd"):
        try:
            nltk.data.load(payload, format="raw")
            return VULNERABLE, "url-encoded traversal succeeded: %s" % payload[:28]
        except Exception:
            pass
    return FIXED, "url-encoded traversal rejected"
