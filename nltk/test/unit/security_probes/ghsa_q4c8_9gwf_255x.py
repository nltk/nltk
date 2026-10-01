"""GHSA-q4c8-9gwf-255x [draft] : Quadratic-time DoS (CWE-400 / CWE-407) in
``SeekableUnicodeStreamReader.readline``. Every block read re-ran
``str.splitlines`` over the whole growing buffer, so a single unterminated
corpus line of N characters cost O(N**2) (an 8 MB line took 14 s).

The fix looks for a line break only in the freshly read block (plus the
previous block's last character) and grows the buffer through a list of parts,
so the read is linear. The same sink is probed as GHSA-j8g8-j4j7-8j54, and this
probe is that one measurement (an unterminated line timed over a 4x input
through the suite's scaling rule), so the two advisories cannot drift apart.
"""

from ._base import probe
from .ghsa_j8g8_j4j7_8j54 import _readline_grow_and_reparse


@probe("GHSA-q4c8-9gwf-255x")
def _readline_unterminated_line():
    """The GHSA-j8g8 readline measurement, registered for this advisory too."""
    return _readline_grow_and_reparse()
