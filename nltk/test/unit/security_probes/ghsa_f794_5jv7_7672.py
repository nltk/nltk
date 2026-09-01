"""GHSA-f794-5jv7-7672 [high] -- Downloader.download follows hardlinks and overwrites outside-root files"""

import os
import shutil
import tempfile

from ._base import FIXED, STATIC, VULNERABLE, is_security_rejection, probe


@probe("GHSA-f794-5jv7-7672")
def _downloader_hardlink():
    """Write through a symlink / hardlink / absolute path that escapes the root.

    pathsec.open (the downloader's write sink) must security-refuse each. The
    hardlink is the advisory's own vector: a refused hardlink (or absolute)
    target must also keep its original bytes, because truncation is deferred
    until after the containment checks -- a refused write never zeroes the file.
    """
    import nltk.pathsec as ps

    # The hardlink/symlink write guard (_hardened_open) is POSIX-only and gated on
    # ENFORCE; elsewhere the sink falls back to builtins.open.
    if os.name != "posix" or not ps.ENFORCE:
        return STATIC, "hardened write path inactive (non-POSIX or ENFORCE off)"

    import nltk.data

    box = tempfile.mkdtemp()
    # Authorize box as a data root so the sandbox layer passes and _hardened_open
    # itself is the guard exercised (on a world-writable /tmp it blocks too early).
    nltk.data.path.insert(0, box)
    try:
        root = os.path.join(box, "corpus")
        os.makedirs(root)
        notes = []
        for label in ("symlink", "hardlink", "absolute"):
            outside = os.path.join(box, label + "_secret")
            with open(outside, "w", encoding="utf-8") as fh:
                fh.write("ORIGINAL")
            if label == "symlink":
                target = os.path.join(root, "s.tmp")
                os.symlink(outside, target)
            elif label == "hardlink":
                target = os.path.join(root, "h.tmp")
                os.link(outside, target)
            else:
                target = outside
            try:
                with ps.open(target, "wb", required_root=root) as fh:
                    fh.write(b"PWNED")
            except Exception as exc:
                if not is_security_rejection(exc):
                    return (
                        STATIC,
                        f"{label} failed before the guard ({type(exc).__name__})",
                    )
                notes.append(f"{label}=blocked")
            else:
                if "PWNED" in open(outside, encoding="utf-8").read():
                    return VULNERABLE, f"{label} write escaped to the outside file"
                notes.append(f"{label}=no-leak")
            if open(outside, encoding="utf-8").read() != "ORIGINAL":
                return (
                    VULNERABLE,
                    f"{label} zeroed the outside file (truncate before guard)",
                )
        return FIXED, "; ".join(notes)
    finally:
        if box in nltk.data.path:
            nltk.data.path.remove(box)
        shutil.rmtree(box, ignore_errors=True)
