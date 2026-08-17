"""GHSA-8mpw-7fpc-4gqj [low] -- Pl196xCorpusReader has quadratic ReDoS on malformed TEI blocks"""

import io

from ._base import FIXED, VULNERABLE, probe, within_budget


@probe("GHSA-8mpw-7fpc-4gqj")
def _tei_read_block_quadratic():
    """read_block did block.count() over the whole growing block per line: 80k lines=43s."""
    from nltk.corpus.reader.pl196x import TEICorpusView

    view = TEICorpusView.__new__(TEICorpusView)
    view._pagesize = 4096
    view._textids = None
    view._tagged = False
    view._group_by_sent = False
    payload = "x\n" * 80000  # no </text>: pre-patch swallowed it all at O(n^2)
    ok, seconds = within_budget(lambda: view.read_block(io.StringIO(payload)))
    if ok:
        return FIXED, "80k-line unterminated TEI in %.3fs" % seconds
    return VULNERABLE, "unterminated TEI took %.1fs" % seconds
