"""GHSA-3hhw-38pf-pxj6 [medium] -- Symlink-based arbitrary file read in IPIPANCorpusReader, bypasses nltk.pathsec entirely

Probe: run the attack, report what the tree does now. See _base for statuses.
"""
from ._base import escape_probe, probe


@probe("GHSA-3hhw-38pf-pxj6")
def _ipipan_symlink():
    """IPIPANCorpusReader read a caller-supplied fileid with builtin open()."""
    from nltk.corpus.reader.ipipan import IPIPANCorpusReader

    def via_channels(box):
        reader = IPIPANCorpusReader(box.root, ["link.xml"])
        return reader.channels(fileids=["link.xml"])

    def via_categories(box):
        reader = IPIPANCorpusReader(box.root, ["link.xml"])
        return reader.categories(fileids=["link.xml"])

    return escape_probe(
        [("channels()", via_channels), ("categories()", via_categories)]
    )
