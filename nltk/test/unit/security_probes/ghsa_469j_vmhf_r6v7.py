"""GHSA-469j-vmhf-r6v7 [high] -- Downloader Path Traversal Vulnerability (AFO) - Arbitrary File Overwrite"""
from ._base import STATIC, VULNERABLE, probe, read_source


@probe("GHSA-469j-vmhf-r6v7")
def _downloader_index_traversal():
    """subdir/id from a remote XML index were not validated (AFO)."""
    source = read_source("nltk.downloader")
    guards = ("validate_path", "pathsec", "_safe_join", "commonpath", "resolve()")
    if not any(g in source for g in guards):
        return VULNERABLE, "downloader.py contains no path-containment guard"
    hits = [g for g in guards if g in source]
    return STATIC, "downloader guards present: %s" % ", ".join(hits[:3])
