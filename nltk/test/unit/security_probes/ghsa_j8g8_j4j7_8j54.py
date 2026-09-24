"""GHSA-j8g8-j4j7-8j54 [moderate]: Algorithmic DoS (CWE-407) via grow-and-reparse.

A fixed-size read block re-scanned over the whole growing buffer is O(n**2).
"""

import io

from ._base import FIXED, QUADRATIC_RATIO, VULNERABLE, probe, scaling_ratio


@probe("GHSA-j8g8-j4j7-8j54")
def _readline_grow_and_reparse():
    """Read one enormous unterminated line through SeekableUnicodeStreamReader.

    The fixed reader scans only the freshly read span for a line boundary, so a
    single unterminated line stays near linear. The pre-fix reader re-split the
    whole growing buffer on every block, which is quadratic. VULNERABLE when the
    big/small timing ratio reads super-linear.
    """
    from nltk.data import SeekableUnicodeStreamReader

    def op(n):
        # One line of n bytes with no line boundary anywhere, so the reader keeps
        # growing its window to the end without ever finding a break.
        reader = SeekableUnicodeStreamReader(io.BytesIO(b"a" * n), "utf-8")
        reader.readline()

    # 2 MB and 8 MB rather than 1 and 4: the fixed reader is linear and still
    # takes about 0.1 s, while the pre-fix re-parse has four times the work,
    # so its t_small clears scaling_ratio's 0.1 s noise floor with margin on a
    # fast interpreter (at 1 MB the CPython 3.14.7 runners read it as FIXED).
    # The larger sizes also exposed a residual in-place str growth that copied
    # on every pass on Windows (9.6x there); readline now joins spans once.
    small, big = 2_000_000, 8_000_000
    ratio = scaling_ratio(op, small, big)
    if ratio >= QUADRATIC_RATIO:
        return (
            VULNERABLE,
            "readline scales %.1fx over a 4x input (quadratic re-parse)" % ratio,
        )
    return FIXED, "readline scales %.1fx over a 4x input (near-linear)" % ratio
