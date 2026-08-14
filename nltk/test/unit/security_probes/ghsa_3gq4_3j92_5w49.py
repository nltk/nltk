"""GHSA-3gq4-3j92-5w49 [high] -- Corpus Reader Sandbox Bypass

Probe: run the attack, report what the tree does now. See _base for statuses.
"""
from ._base import escape_probe, probe


@probe("GHSA-3gq4-3j92-5w49")
def _reader_constructor_bypass():
    """Constructors reached outside-root files before the sandbox applied."""
    from nltk.corpus.reader.lin import LinThesaurusCorpusReader

    def lin(box):
        reader = LinThesaurusCorpusReader(box.dir)
        return str(getattr(reader, "_thesaurus", ""))

    return escape_probe([("LinThesaurusCorpusReader(outside root)", lin)])
