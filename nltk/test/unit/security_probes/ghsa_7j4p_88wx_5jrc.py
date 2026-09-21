"""GHSA-7j4p-88wx-5jrc [high]: chat80 shelve/sqlite persistence follows a symlink or hardlink planted at a derived store backing name (CWE-59)"""

import os
import shutil
import tempfile

from ._base import (
    FIXED,
    OUTSIDE_TARGET,
    STATIC,
    VULNERABLE,
    is_security_rejection,
    probe,
    register_data_root,
)


@probe("GHSA-7j4p-88wx-5jrc")
def _chat80_store_backing_link():
    """Plant a symlink / hardlink at a derived store backing name and open it.

    shelve/dbm and sqlite reopen sidecar names (base + '.db' and friends) by
    path, so a link pre-planted at one redirects the real open outside the
    sandbox even after the base path was validated. Opening the store must
    security-refuse each planted link, never follow it to the outside file.
    """
    import nltk.pathsec as ps
    import nltk.sem.chat80 as chat80

    # The O_NOFOLLOW / st_nlink store guard is POSIX-only and gated on ENFORCE;
    # elsewhere shelve reopens by path with no hardening to exercise.
    if os.name != "posix" or not ps.ENFORCE:
        return STATIC, "store link guard inactive (non-POSIX or ENFORCE off)"
    if not OUTSIDE_TARGET:
        return STATIC, "no readable outside-root target on this platform"

    box = tempfile.mkdtemp()
    # Authorize box as a data root so validate_path passes for names that are not
    # links and the store link guard itself is the check exercised.
    undo = register_data_root(box)
    extra = []
    try:
        notes = []
        for label in ("symlink", "hardlink"):
            base = os.path.join(box, label + "_store")
            planted = base + ".db"
            if label == "symlink":
                os.symlink(OUTSIDE_TARGET, planted)
            else:
                # A hardlink aliases an inode with no symlink to resolve. If the
                # kernel refuses a cross-device or protected link to OUTSIDE_TARGET,
                # alias a secret on the store filesystem instead.
                try:
                    os.link(OUTSIDE_TARGET, planted)
                except OSError:
                    outside = tempfile.mkdtemp()
                    extra.append(outside)
                    secret = os.path.join(outside, "secret")
                    with open(secret, "w", encoding="utf-8") as fh:
                        fh.write("HARDLINK_CANARY")
                    os.link(secret, planted)
            try:
                shelf = chat80._restricted_shelve_open(base)
            except Exception as exc:
                if is_security_rejection(exc):
                    notes.append("%s=blocked" % label)
                    continue
                # The only way past the store guard is for it not to fire; the
                # sink then opened the planted backing name by path and followed
                # the link (dbm failing on outside content is that follow).
                return (
                    VULNERABLE,
                    "%s followed past the store guard (%s)"
                    % (label, type(exc).__name__),
                )
            else:
                try:
                    shelf.close()
                except Exception:
                    pass
                return VULNERABLE, "%s opened the planted store backing name" % label
        return FIXED, "; ".join(notes)
    finally:
        undo()
        shutil.rmtree(box, ignore_errors=True)
        for directory in extra:
            shutil.rmtree(directory, ignore_errors=True)
