"""GHSA-q4c8-9gwf-255x [draft] : Quadratic-time DoS (CWE-400 / CWE-407) in
``SeekableUnicodeStreamReader.readline``. Every block read re-ran
``str.splitlines`` over the whole growing buffer, so a single unterminated
corpus line of N characters cost O(N**2) (an 8 MB line took 14 s).

The fix re-splits only when the new block (or the buffered prefix) carries a
line break and grows the buffer through a list of parts, so the read is linear.
"""

import io

from ._base import FIXED, QUADRATIC_RATIO, VULNERABLE, probe, scaling_ratio


@probe("GHSA-q4c8-9gwf-255x")
def _readline_unterminated_line():
    """Read one unterminated line and measure how the time scales with its length.

    A linear read scales ~4x for 4x input; the pre-fix whole-buffer re-split per
    block scales ~16x and trips the quadratic ratio.
    """
    from nltk.data import SeekableUnicodeStreamReader

    def op(n):
        SeekableUnicodeStreamReader(io.BytesIO(b"a" * n), "utf-8").readline()

    small, big = 500_000, 2_000_000  # big == 4 * small
    ratio = scaling_ratio(op, small, big)
    detail = "readline scales %.1fx over 4x input (%d->%d chars)" % (ratio, small, big)
    if ratio >= QUADRATIC_RATIO:
        return VULNERABLE, "whole-buffer re-split per block: " + detail
    return FIXED, "linear read: " + detail
