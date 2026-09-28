"""GHSA-cj8f-5fp3-6m88 [draft] : Quadratic CPU exhaustion (CWE-400 / CWE-407)
in ``XMLCorpusView.read_block``. The root-to-node path is rebuilt with
``"/".join(context)`` at every start tag, O(depth) each, so a deeply nested
crafted corpus file cost O(n**2) (depth 32000 ran past 45 s).

The fix refuses nesting deeper than ``MAX_XML_DEPTH`` with a ValueError.
"""

import os
import pathlib
import shutil
import tempfile

from ._base import (
    FIXED,
    QUADRATIC_RATIO,
    VULNERABLE,
    probe,
    register_data_root,
    scaling_ratio,
)


def _read_nested(depth):
    """Drive read_block over ``depth`` nested elements with a tagspec nothing
    matches, which forces the full descent."""
    from nltk.corpus.reader.xmldocs import XMLCorpusView
    from nltk.data import FileSystemPathPointer

    root = tempfile.mkdtemp()
    undo = register_data_root(root)
    try:
        path = os.path.join(root, "deep.xml")
        pathlib.Path(path).write_text(
            "<a>" * depth + "x" + "</a>" * depth, encoding="utf-8"
        )
        # iterate rather than list(): len() would walk the file a second time
        return sum(1 for _ in XMLCorpusView(FileSystemPathPointer(path), "zzz"))
    finally:
        undo()
        shutil.rmtree(root, ignore_errors=True)


@probe("GHSA-cj8f-5fp3-6m88")
def _deep_xml_nesting():
    try:
        _read_nested(12000)
    except ValueError as exc:
        if "MAX_XML_DEPTH" in str(exc):
            return FIXED, "depth 12000 refused: %s" % str(exc)[:70]
        return VULNERABLE, "rejected for another reason, guard not reached: %s" % exc
    # No depth bound: the advisory is only closed if the walk itself is linear.
    # The per-tag regex match is a linear floor under the quadratic path
    # rebuild, so the sizes are large enough for the rebuild to dominate.
    ratio = scaling_ratio(_read_nested, 3000, 12000, reps=2)
    detail = "read_block scales %.1fx over 4x depth (3000->12000)" % ratio
    if ratio >= QUADRATIC_RATIO:
        return VULNERABLE, "no depth bound and per-tag path rebuild: " + detail
    return FIXED, "no depth bound but the descent is linear: " + detail
