"""GHSA-x5ph-mj9p-rfr8 [high] -- Security Report: StreamBackedCorpusView Bypasses pathsec.ENFORCE - Arbitrary Local File"""
from ._base import escape_probe, probe


@probe("GHSA-x5ph-mj9p-rfr8")
def _streambacked_view_enforce():
    """StreamBackedCorpusView read outside roots even with ENFORCE=True."""
    from nltk.corpus.reader.util import StreamBackedCorpusView
    from nltk.tokenize import wordpunct_tokenize

    def read_outside(box):
        view = StreamBackedCorpusView(
            box.secret, lambda stream: wordpunct_tokenize(stream.read())
        )
        return " ".join(list(view))

    return escape_probe([("StreamBackedCorpusView(outside)", read_outside)])
