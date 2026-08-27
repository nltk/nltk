"""GHSA-pcm8-fqjx-rvx8 [moderate] -- Cyclic collection index causes infinite loop in nltk.downloader"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import nltk

from ._base import FIXED, STATIC, VULNERABLE, probe

_PACKAGE = (
    '<package id="p1" name="Sample" subdir="corpora/p1" '
    'url="http://example.invalid/p1.zip" unzip="0" size="0" unzipped_size="0"/>'
)

#: collection graphs whose references cycle; the traversal must still terminate.
#: "acyclic" is the health control, not an attack.
_GRAPHS = {
    "self": '<collection id="a" name="C"><item ref="a"/><item ref="p1"/></collection>',
    "mutual": (
        '<collection id="a" name="C"><item ref="b"/><item ref="p1"/></collection>'
        '<collection id="b" name="D"><item ref="a"/></collection>'
    ),
    "chain": (
        '<collection id="a" name="C"><item ref="b"/></collection>'
        '<collection id="b" name="D"><item ref="c"/></collection>'
        '<collection id="c" name="E"><item ref="a"/><item ref="p1"/></collection>'
    ),
    "diamond": (
        '<collection id="a" name="C"><item ref="b"/><item ref="c"/></collection>'
        '<collection id="b" name="D"><item ref="d"/></collection>'
        '<collection id="c" name="E"><item ref="d"/></collection>'
        '<collection id="d" name="F"><item ref="p1"/></collection>'
    ),
    "acyclic": '<collection id="a" name="C"><item ref="p1"/></collection>',
}


def _resolve(shape, timeout=30):
    """Resolve an index with the given collection graph in a subprocess.

    Returns ``(kind, detail)`` where *kind* is ``"ok"``, ``"hang"`` (the infinite
    loop symptom) or ``"error"``.
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as fh:
        fh.write(
            '<?xml version="1.0"?><index><packages>'
            + _PACKAGE
            + "</packages><collections>"
            + _GRAPHS[shape]
            + "</collections></index>"
        )
        path = fh.name
    try:
        script = "\n".join(
            [
                "import nltk",
                "from nltk.downloader import Downloader",
                "nltk.pathsec.ENFORCE = False",
                f"dl = Downloader(server_index_url={Path(path).as_uri()!r})",
                "print(','.join(p.id for p in dl.packages()))",
            ]
        )
        env = os.environ.copy()
        root = os.path.dirname(os.path.dirname(os.path.dirname(nltk.__file__)))
        env["PYTHONPATH"] = root + os.pathsep + env.get("PYTHONPATH", "")
        try:
            done = subprocess.run(
                [sys.executable, "-c", script],
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
            )
        except subprocess.TimeoutExpired:
            return "hang", "timed out"
        if done.returncode != 0:
            return "error", done.stderr.strip()[-70:]
        return "ok", done.stdout.strip()
    finally:
        os.unlink(path)


@probe("GHSA-pcm8-fqjx-rvx8")
def _cyclic_collection_index():
    """Resolve indexes whose collection graph cycles in several shapes.

    Self-, mutual-, chain- and diamond-references must each terminate and yield the
    package. A hang IS the advisory's infinite loop, so it is reported VULNERABLE
    rather than inconclusive whenever an acyclic control run shows the host is
    healthy; only a control that also times out downgrades the result to STATIC.
    """
    resolved = []
    for shape in ("self", "mutual", "chain", "diamond"):
        kind, detail = _resolve(shape)
        if kind == "hang":
            control, _ = _resolve("acyclic")
            if control == "ok":
                return VULNERABLE, f"{shape}-referencing index never terminated"
            return STATIC, "cyclic run and the acyclic control both timed out"
        if kind == "error":
            return VULNERABLE, f"{shape} index failed: {detail}"
        if detail != "p1":
            return VULNERABLE, f"{shape} index yielded {detail!r}, expected 'p1'"
        resolved.append(shape)
    return FIXED, "cyclic collection graphs terminate: " + ", ".join(resolved)
