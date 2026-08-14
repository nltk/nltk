"""GHSA-p4rw-rvv2-7xwr [medium] -- Corpus readers follow symlinks outside trusted roots despite pathsec enforcement

Probe: run the attack, report what the tree does now. See _base for statuses.
"""
from ._base import escape_probe, probe


@probe("GHSA-p4rw-rvv2-7xwr")
def _readers_reopen_with_builtin_open():
    """Readers converted in-root paths to strings and reopened with open()."""
    from nltk.corpus.reader.api import CorpusReader

    def absolute(box):
        reader = CorpusReader(box.root, [".*"])
        with reader.open(box.secret) as handle:
            return handle.read()

    return escape_probe([("open(absolute outside path)", absolute)])
