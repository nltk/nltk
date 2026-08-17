"""GHSA-p4rw-rvv2-7xwr [medium] -- Corpus readers follow symlinks outside trusted roots despite pathsec enforcement"""

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

    return escape_probe(
        [
            ("open(symlink)", via_symlink),
            ("open(traversal)", via_traversal),
        ]
    )
