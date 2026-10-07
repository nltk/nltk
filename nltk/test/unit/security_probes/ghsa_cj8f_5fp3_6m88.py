"""GHSA-cj8f-5fp3-6m88 [draft] : Quadratic CPU exhaustion (CWE-400 / CWE-407)
in ``XMLCorpusView.read_block``. The root-to-node path is handed to the tagspec
at every tag; rebuilt with ``"/".join(context)`` it cost O(depth) each, so a
deeply nested crafted corpus file cost O(n**2) (depth 32000 ran past 45 s), and
a wide path (long tag names under a prefix nested within the depth cap) made
every sibling cost the path's length, O(n**2) in the file (962 KB took 9.9 s).

The fix refuses nesting deeper than ``MAX_XML_DEPTH`` and a joined path longer
than ``MAX_XML_PATH_LENGTH`` with a ValueError, and extends the path per tag
instead of re-joining it.
"""

import os
import pathlib
import shutil
import tempfile

from ._base import FIXED, QUADRATIC_RATIO, VULNERABLE, probe, register_data_root

_BOUNDS = ("MAX_XML_DEPTH", "MAX_XML_PATH_LENGTH")


class _PathMeter:
    """Stands in for the tagspec: never matches, and adds up the characters of
    every root-to-node path the walk hands it. That sum is the work the per-tag
    path costs, so it measures the vector itself rather than wall time."""

    def __init__(self):
        self.chars = 0

    def match(self, path):
        self.chars += len(path)
        return None


def _nested(depth):
    return "<a>" * depth + "x" + "</a>" * depth


def _wide(depth, name_len, siblings):
    """``depth`` nested elements with ``name_len``-char names, then ``siblings``
    empty elements under the innermost one: a path of depth * name_len chars
    handed to the tagspec once per sibling."""
    name = "n" * name_len
    return (
        "".join("<%s%d>" % (name, i) for i in range(depth))
        + "<x/>" * siblings
        + "".join("</%s%d>" % (name, i) for i in reversed(range(depth)))
    )


def _write_doc(root, text):
    path = os.path.join(root, "doc.xml")
    pathlib.Path(path).write_text(text, encoding="utf-8")
    return path


def _read(text):
    """Iterate the view over ``text`` with a tagspec nothing matches, which
    forces the full walk through the public entry point."""
    from nltk.corpus.reader.xmldocs import XMLCorpusView
    from nltk.data import FileSystemPathPointer

    root = tempfile.mkdtemp()
    undo = register_data_root(root)
    try:
        pointer = FileSystemPathPointer(_write_doc(root, text))
        # iterate rather than list(): len() would walk the file a second time
        return sum(1 for _ in XMLCorpusView(pointer, "zzz"))
    finally:
        undo()
        shutil.rmtree(root, ignore_errors=True)


def _path_work(text):
    """Characters of path that read_block hands the tagspec over the whole file."""
    from nltk.corpus.reader.xmldocs import XMLCorpusView
    from nltk.data import FileSystemPathPointer

    root = tempfile.mkdtemp()
    undo = register_data_root(root)
    try:
        pointer = FileSystemPathPointer(_write_doc(root, text))
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


def _bound_named_in(exc):
    """The bound a refusal names, or None when it was refused for another reason."""
    for bound in _BOUNDS:
        if bound in str(exc):
            return bound
    return None


@probe("GHSA-cj8f-5fp3-6m88")
def _deep_or_wide_xml_path():
    # Deep and narrow: a bound refuses it, else the per-tag path work must be
    # linear in depth (the rebuild gave d**2, so 4x depth is 16x; linear ~4x).
    try:
        _read(_nested(16000))
    except ValueError as exc:
        if _bound_named_in(exc) is None:
            return (
                VULNERABLE,
                "deep: rejected for another reason, bound not reached: %s" % exc,
            )
        deep = "depth 16000 refused by %s" % _bound_named_in(exc)
    else:
        ratio = _path_work(_nested(4000)) / max(_path_work(_nested(1000)), 1)
        deep = "path work scales %.1fx over 4x depth (1000->4000)" % ratio
        if ratio >= QUADRATIC_RATIO:
            return VULNERABLE, "no depth bound and per-tag path rebuild: " + deep
        deep = "no depth bound but the descent is linear: " + deep
    # Shallow and wide: 400 deep (under the depth cap) with 1000-char names is a
    # 400 KB path. A bound refuses it, else the path work over a budget split 4x
    # between name length and sibling count must be linear (~4x; per-sibling ~16x).
    try:
        _read(_wide(400, 1000, 2000))
    except ValueError as exc:
        if _bound_named_in(exc) is None:
            return (
                VULNERABLE,
                "wide: rejected for another reason, bound not reached: %s" % exc,
            )
        wide = "a 400 KB path refused by %s" % _bound_named_in(exc)
    else:
        ratio = _path_work(_wide(400, 400, 4000)) / max(
            _path_work(_wide(400, 100, 1000)), 1
        )
        wide = "sibling path work scales %.1fx over a 4x budget" % ratio
        if ratio >= QUADRATIC_RATIO:
            return VULNERABLE, "no path width bound and per-sibling path cost: " + wide
        wide = "no path width bound but the walk is linear: " + wide
    return FIXED, deep + "; " + wide
