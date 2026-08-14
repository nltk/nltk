"""GHSA-f833-7jw8-xwrv [high] -- Symlink-based sandbox bypass in FramenetCorpusReader (bypasses the fix for CVE-2026-54292)"""
from ._base import guard_rejects, probe


@probe("GHSA-f833-7jw8-xwrv")
def _framenet_symlink_bypass():
    """A symlink inside frame/ pointed outside the root; the guard now resolves it."""
    from nltk.corpus.reader.framenet import _validate_in_root

    return guard_rejects(lambda path, root: _validate_in_root(path, root, "framenet"))
