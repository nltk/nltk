"""GHSA-3hhw-38pf-pxj6 [medium] -- Symlink-based arbitrary file read in IPIPANCorpusReader, bypasses nltk.pathsec entirely"""

from ._base import escape_probe, probe


@probe("GHSA-3hhw-38pf-pxj6")
def _ipipan_symlink():
    """IPIPAN channels()/categories() read a caller fileid with builtin open()."""
    from nltk.corpus.reader.ipipan import IPIPANCorpusReader

    def channels(box):
        return IPIPANCorpusReader(box.root, ["link.xml"]).channels(fileids=["link.xml"])

    def categories(box):
        return IPIPANCorpusReader(box.root, ["link.xml"]).categories(
            fileids=["link.xml"]
        )

    return escape_probe([("channels()", channels), ("categories()", categories)])
