"""GHSA-vp2x-qp44-57v7 [low] -- Quadratic CPU Exhaustion in `XMLCorpusView._read_xml_fragment()`"""

import os
import tempfile

from ._base import DOS_BUDGET, FIXED, VULNERABLE, probe, timed


@probe("GHSA-vp2x-qp44-57v7")
def _xmlcorpusview_quadratic():
    """Quadratic CPU exhaustion in XMLCorpusView._read_xml_fragment."""
    from nltk.corpus.reader.xmldocs import XMLCorpusView

    def run(size):
        handle, path = tempfile.mkstemp(suffix=".xml")
        os.write(handle, b"<root>" + b"<" * size + b"</root>")
        os.close(handle)
        try:
            list(XMLCorpusView(path, ".*"))
        except Exception:
            pass
        finally:
            os.unlink(path)

    small, large = timed(run, 4000), timed(run, 8000)
    ratio = large / max(small, 1e-4)
    if large > DOS_BUDGET or ratio > 3.0:
        return VULNERABLE, "doubling cost %.1fx" % ratio
    return FIXED, "linear: %.1fx per doubling" % ratio
