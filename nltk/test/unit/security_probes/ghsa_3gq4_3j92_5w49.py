"""GHSA-3gq4-3j92-5w49 [high] -- Corpus Reader Sandbox Bypass"""

import os

from ._base import escape_probe, probe


@probe("GHSA-3gq4-3j92-5w49")
def _lin_constructor_bypass():
    """LinThesaurusCorpusReader reached files before the sandbox applied.

    Point it at a root whose only entry is a symlink to the outside target and
    read it back; a leak is the outside file surfacing in the thesaurus.
    """
    from nltk.corpus.reader.lin import LinThesaurusCorpusReader

    def load(box):
        # The reader eagerly opens files matching sim[A-Z].lsp; the symlink must
        # match that pattern or the constructor never reaches the guard.
        simlink = os.path.join(box.root, "simA.lsp")
        if not os.path.exists(simlink):
            os.symlink(box.target or "/nonexistent", simlink)
        reader = LinThesaurusCorpusReader(box.root)
        return "".join(str(v) for v in getattr(reader, "_thesaurus", {}).values())

    return escape_probe([("LinThesaurus(simA.lsp symlink)", load)])
