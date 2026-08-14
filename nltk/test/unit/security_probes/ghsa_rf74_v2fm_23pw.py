"""GHSA-rf74-v2fm-23pw [low] -- Unbounded recursion in JSONTaggedDecoder.decode_obj() may cause DoS

Probe: run the attack, report what the tree does now. See _base for statuses.
"""
from ._base import FIXED, VULNERABLE, probe


@probe("GHSA-rf74-v2fm-23pw")
def _jsontagged_recursion():
    """Unbounded recursion in JSONTaggedDecoder.decode_obj()."""
    from nltk.jsontags import JSONTaggedDecoder

    payload = "[" * 5000 + "]" * 5000
    try:
        JSONTaggedDecoder().decode(payload)
    except RecursionError:
        return VULNERABLE, "RecursionError escaped to the caller"
    except Exception as exc:
        return FIXED, "bounded (%s)" % type(exc).__name__
    return FIXED, "deep nesting handled"
