"""GHSA-469j-vmhf-r6v7 [high] -- Downloader Path Traversal Vulnerability (AFO) - Arbitrary File Overwrite"""

import os
import shutil
import tempfile
import zipfile

from ._base import FIXED, STATIC, VULNERABLE, probe


@probe("GHSA-469j-vmhf-r6v7")
def _downloader_index_traversal():
    """Extract a package archive whose member escapes the extraction root.

    A zip-slip member (``../CANARY``) must be rejected by the validate-then-
    extract pass, leaving the outside-root canary untouched. Scored on behaviour
    (the canary's bytes), since the rejection wording is not a generic marker.
    """
    from nltk.downloader import ErrorMessage, _unzip_iter

    box = tempfile.mkdtemp()
    try:
        outside = os.path.join(box, "CANARY")
        with open(outside, "w", encoding="utf-8") as fh:
            fh.write("ORIGINAL")
        dest = os.path.join(box, "dest")
        member = os.path.relpath(outside, dest)  # ../CANARY, escapes dest
        evil = os.path.join(box, "evil.zip")
        with zipfile.ZipFile(evil, "w") as zf:
            zf.writestr(member, "PWNED")
        messages = list(_unzip_iter(evil, dest, verbose=False))
        if open(outside, encoding="utf-8").read() != "ORIGINAL":
            return VULNERABLE, "zip-slip member overwrote the outside-root canary"
        if any(isinstance(m, ErrorMessage) for m in messages):
            return FIXED, "zip-slip member rejected; outside canary intact"
        return STATIC, "extraction fizzled without reaching the containment check"
    finally:
        shutil.rmtree(box, ignore_errors=True)
