"""GHSA-f833-7jw8-xwrv [high] -- Symlink-based sandbox bypass in FramenetCorpusReader (bypasses the fix for CVE-2026-5429

Probe: run the attack, report what the tree does now. See _base for statuses.
"""
from ._base import escape_probe, probe


@probe("GHSA-f833-7jw8-xwrv")
def _framenet_symlink_bypass():
    """Symlink bypass of the GHSA-xh95 fix (lexical check only)."""
    from nltk.corpus.reader.framenet import FramenetCorpusReader

    def via_symlink(box):
        reader = FramenetCorpusReader(box.root, [])
        return reader.frame("link")

    return escape_probe([("frame('link') via symlink", via_symlink)])
