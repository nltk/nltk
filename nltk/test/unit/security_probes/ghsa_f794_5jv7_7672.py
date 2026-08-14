"""GHSA-f794-5jv7-7672 [high] -- Downloader.download follows hardlinks and overwrites outside-root files

Probe: run the attack, report what the tree does now. See _base for statuses.
"""
from ._base import STATIC, VULNERABLE, probe, read_source


@probe("GHSA-f794-5jv7-7672")
def _downloader_hardlink():
    """Pre-existing hardlinks inside the install tree were followed."""
    source = read_source("nltk.downloader")
    if "st_nlink" in source or "nlink" in source:
        return STATIC, "downloader inspects link counts before writing"
    if "O_NOFOLLOW" in source or "pathsec" in source:
        return STATIC, "writes go through guarded open helpers"
    return VULNERABLE, "no hardlink guard found in downloader.py"
