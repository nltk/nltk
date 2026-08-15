"""GHSA-8mpw-7fpc-4gqj [low] -- Pl196xCorpusReader has quadratic ReDoS on malformed TEI blocks"""

import os
import tempfile

from ._base import DOS_BUDGET, FIXED, VULNERABLE, probe, timed


@probe("GHSA-8mpw-7fpc-4gqj")
def _pl196x_quadratic():
    """Pl196xCorpusReader rescanned malformed TEI blocks quadratically."""
    from nltk.corpus.reader.xmldocs import XMLCorpusView

    def run(size):
        handle, path = tempfile.mkstemp(suffix=".xml")
        os.write(handle, b"<TEI>" + b"<div " * size + b"</TEI>")
        os.close(handle)
        try:
            list(XMLCorpusView(path, ".*"))
        except Exception:
            pass
        finally:
            os.unlink(path)

    small, large = timed(run, 3000), timed(run, 6000)
    ratio = large / max(small, 1e-4)
    if large > DOS_BUDGET or ratio > 3.0:
        return VULNERABLE, "doubling cost %.1fx" % ratio
    return FIXED, "linear: %.1fx per doubling" % ratio
