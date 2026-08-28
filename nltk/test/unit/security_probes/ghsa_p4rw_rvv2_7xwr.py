"""GHSA-p4rw-rvv2-7xwr [medium] -- Corpus readers follow symlinks outside trusted roots despite pathsec enforcement"""

import os

from ._base import escape_probe, probe


@probe("GHSA-p4rw-rvv2-7xwr")
def _readers_follow_symlinks():
    """Readers converted in-root paths to strings and reopened with open()."""
    from nltk.corpus.reader.api import CorpusReader

    def via_symlink(box):
        return CorpusReader(box.root, ["link.xml"]).open("link.xml").read()

    def via_traversal(box):
        payload = "../" * 8 + box.target.lstrip("/")
        return CorpusReader(box.root, [payload]).open(payload).read()

    def via_intermediate_symlink(box):
        # escape through a NON-final path component: <root>/d -> the outside dir
        sub = os.path.join(box.root, "d")
        if not os.path.exists(sub):
            os.symlink(os.path.dirname(box.target), sub)
        name = "d/" + os.path.basename(box.target)
        return CorpusReader(box.root, [name]).open(name).read()

    def via_backslash(box):
        # Windows separator, normalized to '/', so the ".." is still caught
        name = "..\\..\\" + box.target.lstrip("/")
        return CorpusReader(box.root, [name]).open(name).read()

    return escape_probe(
        [
            ("open(symlink)", via_symlink),
            ("open(traversal)", via_traversal),
            ("open(intermediate-symlink)", via_intermediate_symlink),
            ("open(backslash)", via_backslash),
        ]
    )
