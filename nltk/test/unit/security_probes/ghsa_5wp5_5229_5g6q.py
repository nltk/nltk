"""GHSA-5wp5-5229-5g6q [high] -- Missing Post-Download Integrity Verification Allows Malicious Package Injection"""
from ._base import STATIC, VULNERABLE, probe, read_source


@probe("GHSA-5wp5-5229-5g6q")
def _downloader_integrity():
    """No integrity verification between download and extraction."""
    source = read_source("nltk.downloader")
    markers = ("checksum", "sha256", "hashlib", "digest")
    hits = [m for m in markers if m in source]
    if not hits:
        return VULNERABLE, "downloader.py performs no post-download verification"
    return STATIC, "integrity check present (%s)" % ", ".join(hits[:3])
