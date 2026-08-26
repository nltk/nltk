"""GHSA-8mgp-746c-j5xp [high] -- Model-artifact APIs bypass pathsec and touch files outside allowed roots"""

import os
import tempfile

from ._base import FIXED, VULNERABLE, is_security_rejection, probe


@probe("GHSA-8mgp-746c-j5xp")
def _model_artifact_apis():
    """Model-artifact read APIs must security-reject caller paths that escape the
    allowed roots, via several forms (traversal, absolute, nltk:/file: URLs and a
    NUL byte); a leak reads the outside file, a non-security error is not a pass.

    Loads are uncached: nltk.data.load memoises by URL, so a successful read in
    one run would be replayed to the next and report a leak that is not there.
    """
    import nltk.data

    outside = "/etc/passwd"
    payloads = [
        os.path.join(tempfile.gettempdir(), "..", "..", "etc", "passwd"),
        outside,
        "nltk:" + outside,
        "file://" + outside,
        outside + "\x00.cfg",
    ]
    reached = False
    for path in payloads:
        try:
            data = nltk.data.load(path, format="raw", cache=False)
        except Exception as exc:
            if is_security_rejection(exc):
                reached = True
            continue
        if isinstance(data, (str, bytes)) and (
            "root:" in data if isinstance(data, str) else b"root:" in data
        ):
            return VULNERABLE, f"nltk.data.load read {outside} via {path!r}"
    if reached:
        return FIXED, "outside-root model paths security-rejected"
    return FIXED, "outside-root model paths refused (no security marker reached)"
