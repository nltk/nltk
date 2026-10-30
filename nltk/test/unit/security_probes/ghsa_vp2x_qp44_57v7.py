"""GHSA-vp2x-qp44-57v7 [low] -- Quadratic CPU Exhaustion in `XMLCorpusView._read_xml_fragment()`"""

import io

from ._base import FIXED, VULNERABLE, probe, within_budget


@probe("GHSA-vp2x-qp44-57v7")
def _xmlcorpusview_quadratic():
    """_VALID_XML_RE re-scanned the whole growing buffer per 1 KiB block: O(n^2)."""
    from nltk.corpus.reader.xmldocs import XMLCorpusView

    view = XMLCorpusView.__new__(XMLCorpusView)
    # 4M chars: at 2M the pre-fix quadratic scan was ~15.6s, right at the budget, so
    # the min-of-3 sampling could dip under and false-pass; 4M is comfortably >30s.
    payload = "<a " + "x" * 4_000_000 + ">"
    ok, seconds = within_budget(lambda: view._read_xml_fragment(io.StringIO(payload)))
    if ok:
        return FIXED, "2M-char unterminated tag in %.3fs" % seconds
    return VULNERABLE, "unterminated tag took %.1fs" % seconds
