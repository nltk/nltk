"""GHSA-6hm5-jgcp-p838 [high] -- Path Traversal in NKJPCorpusReader leads to Arbitrary File Read and bypasses the nltk.pathsec sandbox (ENFORCE=True)"""

import os
import shutil
import tempfile
from pathlib import Path

from ._base import FIXED, STATIC, VULNERABLE, is_security_rejection, probe


@probe("GHSA-6hm5-jgcp-p838")
def _nkjp_traversal():
    """NKJP read methods built the file path from a caller fileid.

    Drive add_root() on a real reader: it is the containment guard every public
    read routes through, so this exercises NKJP's own code rather than pathsec in
    isolation. Escapes must be security-refused, and a payload that is merely an
    odd in-root filename must still resolve inside the root.
    """
    from nltk.corpus.reader.nkjp import NKJPCorpusReader

    box = tempfile.mkdtemp()
    try:
        root = os.path.join(box, "nkjp")
        os.makedirs(root)
        reader = NKJPCorpusReader(root=root)
        os.symlink(os.path.dirname(box), os.path.join(root, "linkdir"))

        escapes = {
            "traversal": "../" * 8 + "etc/passwd",
            "absolute": "/etc/passwd",
            "symlinked-dir": "linkdir/passwd",
        }
        refused = []
        for label, fileid in escapes.items():
            try:
                landed = reader.add_root(fileid)
            except Exception as exc:
                if not is_security_rejection(exc):
                    return (
                        STATIC,
                        f"{label} failed before the guard ({type(exc).__name__})",
                    )
                refused.append(label)
                continue
            return VULNERABLE, f"add_root({label}) returned {landed!r}"

        # A backslash payload is a separator on Windows but a literal filename on
        # POSIX; either refuse it or keep it inside the root, never escape.
        try:
            landed = reader.add_root("..\\..\\etc\\passwd")
        except Exception as exc:
            if not is_security_rejection(exc):
                return STATIC, "backslash failed before the guard"
            refused.append("backslash")
        else:
            resolved = Path(landed).resolve()
            root_resolved = Path(root).resolve()
            if resolved != root_resolved and root_resolved not in resolved.parents:
                return VULNERABLE, f"backslash payload escaped to {landed!r}"
            refused.append("backslash=contained")
        return FIXED, "add_root refused: " + ", ".join(refused)
    finally:
        shutil.rmtree(box, ignore_errors=True)
