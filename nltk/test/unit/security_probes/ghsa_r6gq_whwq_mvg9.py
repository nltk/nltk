"""GHSA-r6gq-whwq-mvg9 [medium] -- Symlink escape in CorpusReader allows arbitrary local file read outside the corpus root"""
from ._base import escape_probe, probe


@probe("GHSA-r6gq-whwq-mvg9")
def _corpusreader_open_symlink():
    """CorpusReader.open() containment check was lexical; a symlink escaped it."""
    from nltk.corpus.reader.api import CorpusReader

    def via_symlink(box):
        return CorpusReader(box.root, ["link.xml"]).open("link.xml").read()

    return escape_probe([("CorpusReader.open(symlink)", via_symlink)])
