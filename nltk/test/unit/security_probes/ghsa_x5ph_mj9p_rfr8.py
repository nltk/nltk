"""GHSA-x5ph-mj9p-rfr8 [high] -- Security Report: StreamBackedCorpusView Bypasses pathsec.ENFORCE - Arbitrary Local File Read"""

from ._base import escape_probe, probe


@probe("GHSA-x5ph-mj9p-rfr8")
def _streambacked_view():
    """StreamBackedCorpusView opened its fileid with builtin open(), no pathsec."""
    from nltk.corpus.reader.util import StreamBackedCorpusView

    read = lambda path: "".join(
        list(StreamBackedCorpusView(path, lambda s: [s.read()]))
    )
    return escape_probe(
        [
            ("direct outside path", lambda box: read(box.target)),
            ("symlink in root", lambda box: read(box.link)),
        ]
    )
