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

from ._base import FIXED, QUADRATIC_RATIO, VULNERABLE, probe, register_data_root


class _PathMeter:
    """Stands in for the tagspec: never matches, and adds up the characters of
    every root-to-node path the walk hands it. That sum is the work the per-tag
    rebuild does, so it measures the vector itself rather than wall time."""

    def __init__(self):
        self.chars = 0

    def match(self, path):
        self.chars += len(path)
        return None


def _nested_file(root, depth):
    path = os.path.join(root, "deep.xml")
    pathlib.Path(path).write_text(
        "<a>" * depth + "x" + "</a>" * depth, encoding="utf-8"
    )
    return path


def _read_nested(depth):
    """Iterate the view over ``depth`` nested elements with a tagspec nothing
    matches, which forces the full descent through the public entry point."""
    from nltk.corpus.reader.xmldocs import XMLCorpusView
    from nltk.data import FileSystemPathPointer

    root = tempfile.mkdtemp()
    undo = register_data_root(root)
    try:
        pointer = FileSystemPathPointer(_nested_file(root, depth))
        # iterate rather than list(): len() would walk the file a second time
        return sum(1 for _ in XMLCorpusView(pointer, "zzz"))
    finally:
        undo()
        shutil.rmtree(root, ignore_errors=True)


def _rebuild_work(depth):
    """Characters of path that read_block hands the tagspec over the whole file."""
    from nltk.corpus.reader.xmldocs import XMLCorpusView
    from nltk.data import FileSystemPathPointer

    root = tempfile.mkdtemp()
    undo = register_data_root(root)
    try:
        pointer = FileSystemPathPointer(_nested_file(root, depth))
        meter = _PathMeter()
        stream = pointer.open("utf8")
        try:
            XMLCorpusView(pointer, "zzz").read_block(stream, tagspec=meter)
        finally:
            stream.close()
        return meter.chars
    finally:
        undo()
        shutil.rmtree(root, ignore_errors=True)


@probe("GHSA-cj8f-5fp3-6m88")
def _deep_xml_nesting():
    try:
        _read_nested(16000)
    except ValueError as exc:
        if "MAX_XML_DEPTH" in str(exc):
            return FIXED, "depth 16000 refused: %s" % str(exc)[:70]
        return VULNERABLE, "rejected for another reason, guard not reached: %s" % exc
    # No depth bound: the advisory is only closed if the walk itself is linear.
    # Count the path characters the rebuild hands the tagspec (a load- and
    # platform-invariant measure): the per-tag rebuild gives d**2, so 4x depth
    # is 16x work; a linear walk would give ~4x.
    small, big = 1000, 4000
    ratio = _rebuild_work(big) / max(_rebuild_work(small), 1)
    detail = "path rebuild work scales %.1fx over 4x depth (%d->%d)" % (
        ratio,
        small,
        big,
    )
    if ratio >= QUADRATIC_RATIO:
        return VULNERABLE, "no depth bound and per-tag path rebuild: " + detail
    return FIXED, "no depth bound but the descent is linear: " + detail
