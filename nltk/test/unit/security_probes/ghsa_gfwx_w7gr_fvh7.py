"""GHSA-gfwx-w7gr-fvh7 [medium] -- Improper Neutralization of Input During Web Page Generation ('Cross-site Scripting') in nltk"""

import io

from ._base import FIXED, STATIC, VULNERABLE, probe


@probe("GHSA-gfwx-w7gr-fvh7")
def _wordnet_app_xss():
    """Drive the lookup_ handler in-process with a hostile word.

    A socket-free ``do_GET`` against ``/lookup_<script>`` builds the real
    response; the reflected word must come back HTML-escaped, never as a live
    ``<script>`` tag.
    """
    from nltk.data import find

    try:
        find("corpora/wordnet.zip")
    except LookupError:
        return STATIC, "wordnet corpus unavailable; handler not exercised"

    import nltk.app.wordnet_app as wa

    payload = "<script>alert(1)</script>"
    handler = wa.MyServerHandler.__new__(wa.MyServerHandler)
    handler.wfile = io.BytesIO()
    handler.path = "/lookup_" + wa.Reference(payload).encode()
    handler.send_response = lambda *a, **k: None
    handler.send_header = lambda *a, **k: None
    handler.end_headers = lambda: None
    handler.do_GET()
    out = handler.wfile.getvalue().decode("utf-8", "replace")
    if payload in out:
        return VULNERABLE, "raw <script> reflected on the lookup_ route"
    if "&lt;script&gt;" in out:
        return FIXED, "hostile word reflected only HTML-escaped"
    return STATIC, "reflection not observed in the response"
