"""GHSA-4489-j4f3-2g8q [high] -- nltk ≤ 3.10.2: unpickler dotted-name RCE bypass"""

import io

from ._base import FIXED, VULNERABLE, probe


@probe("GHSA-4489-j4f3-2g8q")
def _unpickler_dotted_name():
    """Dotted `name` resolved through find_class reached a command sink."""
    from nltk.picklesec import AllowlistUnpickler

    try:
        AllowlistUnpickler(io.BytesIO(b"")).find_class(
            "nltk.tokenize", "repp.ReppTokenizer._execute"
        )
        return VULNERABLE, "dotted name resolved through find_class"
    except Exception as exc:
        return FIXED, "dotted name rejected (%s)" % type(exc).__name__
