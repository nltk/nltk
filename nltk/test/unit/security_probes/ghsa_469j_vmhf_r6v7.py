"""GHSA-469j-vmhf-r6v7 [high] -- Downloader Path Traversal Vulnerability (AFO) - Arbitrary File Overwrite"""

import os
import shutil
import tempfile
import zipfile

from ._base import FIXED, STATIC, VULNERABLE, probe


@probe("GHSA-469j-vmhf-r6v7")
def _downloader_index_traversal():
    """Extract package archives whose members escape the extraction root.

    Several arbitrary-file-write vectors are fired at ``_unzip_iter``: a ``../``
    zip-slip, a deeper traversal, an absolute member, and a member routed through
    a pre-planted symlink. Each must be rejected by the validate-then-extract
    pass, leaving the outside-root canary untouched. Scored on behaviour (the
    canary's bytes), since the rejection wording is not a generic marker.
    """
    from nltk.downloader import ErrorMessage, _unzip_iter

    box = tempfile.mkdtemp()
    try:
        outside = os.path.join(box, "CANARY")
        notes = []
        reached = False
        vectors = (
            ("zip-slip", lambda dest: os.path.relpath(outside, dest)),  # ../CANARY
            ("deep-traversal", lambda dest: "../../../../../../../.." + outside),
            ("absolute", lambda dest: "/" + outside.lstrip("/")),  # /.../CANARY
            ("symlinked-dir", "SYMLINK"),
        )
        for label, make in vectors:
            with open(outside, "w", encoding="utf-8") as fh:
                fh.write("ORIGINAL")
            dest = os.path.join(box, "dest_" + label)
            os.makedirs(dest, exist_ok=True)
            evil = os.path.join(box, label + ".zip")
            if make == "SYMLINK":
                # a pre-planted symlink inside dest pointing at the outside file;
                # a member written "through" it would overwrite the canary.
                link = os.path.join(dest, "CANARY")
                os.symlink(outside, link)
                member = "CANARY"
            else:
                member = make(dest)
            with zipfile.ZipFile(evil, "w") as zf:
                zf.writestr(member, "PWNED")
            messages = list(_unzip_iter(evil, dest, verbose=False))
            if open(outside, encoding="utf-8").read() != "ORIGINAL":
                return VULNERABLE, f"{label} member overwrote the outside-root canary"
            if any(isinstance(m, ErrorMessage) for m in messages):
                reached = True
                notes.append(f"{label}=blocked")
            else:
                notes.append(f"{label}=no-write")
        if reached:
            return FIXED, "; ".join(notes)
        return STATIC, "extraction fizzled without reaching the containment check"
    finally:
        shutil.rmtree(box, ignore_errors=True)
