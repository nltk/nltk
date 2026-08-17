"""GHSA-3gq4-3j92-5w49 [high] -- Corpus Reader Sandbox Bypass"""

from ._base import escape_probe, probe


@probe("GHSA-3gq4-3j92-5w49")
def _lin_constructor_bypass():
    """LinThesaurusCorpusReader reached files before the sandbox applied.

    Point it at a root whose only entry is a symlink to the outside target and
    read it back; a leak is the outside file surfacing in the thesaurus.
    """
    from nltk.corpus.reader.lin import LinThesaurusCorpusReader

    def load(box):
        reader = LinThesaurusCorpusReader(box.root, ["link.xml"])
        return "".join(str(v) for v in getattr(reader, "_thesaurus", {}).values())

    return escape_probe([("LinThesaurus(symlink root)", load)])
