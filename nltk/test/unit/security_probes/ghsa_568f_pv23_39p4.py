"""GHSA-568f-pv23-39p4 [medium] -- Stable FrameNet and NKJP readers parse outside-root XML in 3.9.4

Probe: run the attack, report what the tree does now. See _base for statuses.
"""
from ._base import escape_probe, probe


@probe("GHSA-568f-pv23-39p4")
def _framenet_nkjp_outside_root_xml():
    """FrameNet/NKJP entrypoints built parser paths that left the root."""
    from nltk.corpus.reader.framenet import FramenetCorpusReader

    def absolute_frame(box):
        reader = FramenetCorpusReader(box.root, [])
        return reader.frame(box.secret)

    return escape_probe([("frame(absolute path)", absolute_frame)])
