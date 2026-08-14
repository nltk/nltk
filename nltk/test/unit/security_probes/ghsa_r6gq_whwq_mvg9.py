"""GHSA-r6gq-whwq-mvg9 [medium] -- Symlink escape in CorpusReader allows arbitrary local file read outside the corpus root"""
from ._base import escape_probe, probe


@probe("GHSA-r6gq-whwq-mvg9")
def _corpusreader_open_symlink():
    """CorpusReader.open() boundary check was lexical, so symlinks escaped."""
    from nltk.corpus.reader.api import CorpusReader

    def via_open(box):
        reader = CorpusReader(box.root, ["link.xml"])
        with reader.open("link.xml") as handle:
            return handle.read()

    return escape_probe([("CorpusReader.open('link.xml')", via_open)])
