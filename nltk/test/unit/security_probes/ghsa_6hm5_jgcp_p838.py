"""GHSA-6hm5-jgcp-p838 [high] -- Path Traversal in NKJPCorpusReader leads to Arbitrary File Read and bypasses the nltk.pa

Probe: run the attack, report what the tree does now. See _base for statuses.
"""
from ._base import escape_probe, probe


@probe("GHSA-6hm5-jgcp-p838")
def _nkjp_traversal():
    """NKJPCorpusReader read methods built paths from caller fileids."""
    from nltk.corpus.reader.nkjp import NKJPCorpusReader

    def traverse(box):
        reader = NKJPCorpusReader(root=box.root, fileids=[".*"])
        return reader.raw(fileids="../" * 6 + "secret.txt")

    return escape_probe([("NKJP raw(../secret)", traverse)])
