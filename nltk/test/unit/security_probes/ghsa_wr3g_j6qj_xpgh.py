"""GHSA-wr3g-j6qj-xpgh [high] Zip extraction follows a pre-planted hardlink and writes through it to an outside-root inode (CWE-59)"""

import os
import shutil
import tempfile
import zipfile

from ._base import (
    FIXED,
    STATIC,
    VULNERABLE,
    is_security_rejection,
    probe,
    register_data_root,
)


@probe("GHSA-wr3g-j6qj-xpgh")
def _zip_hardlink_extract():
    """Extract a benign member onto a pre-planted hardlink aimed outside the root.

    The extraction root holds ``evil.txt`` hardlinked to a secret file that lives
    outside the root. The stdlib extractor's plain ``open(target, "wb")`` follows
    that link and writes the member THROUGH it, clobbering the outside inode. The
    hardened ZipFile._extract_member must security-refuse the multiply-linked
    target and leave the secret's original bytes intact.
    """
    import nltk.pathsec as ps

    # The hardened walk anchors an openat() dir_fd and needs O_NOFOLLOW; without
    # dir_fd support the sink falls back to the stdlib extractor, so gate.
    if (
        os.name != "posix"
        or os.open not in os.supports_dir_fd
        or not getattr(os, "O_NOFOLLOW", 0)
    ):
        return (
            STATIC,
            "hardened extract path inactive (non-POSIX or no dir_fd/O_NOFOLLOW)",
        )

    secret_original = b"ORIGINAL_SECRET_BYTES"
    member_payload = b"EVIL_ZIP_MEMBER_PAYLOAD"

    box = tempfile.mkdtemp()
    # The box must be a legitimate data root: on Linux a raw mkdtemp() lands
    # in world-writable /tmp, which pathsec rightly refuses, and the refusal
    # short-circuits BEFORE the guard under test (vacuous on that platform).
    _undo_root = register_data_root(box)
    try:
        root = os.path.join(box, "corpus")
        os.makedirs(root)

        # The escape target lives outside the extraction root (a sibling of it).
        secret = os.path.join(box, "secret_outside_root")
        with open(secret, "wb") as fh:
            fh.write(secret_original)

        # Pre-plant the hardlink at the member's write path; both inodes are the
        # same file, so a followed write lands in the outside-root secret.
        planted = os.path.join(root, "evil.txt")
        try:
            os.link(secret, planted)
        except OSError as exc:
            return (
                STATIC,
                "cannot hardlink on this filesystem (%s)" % type(exc).__name__,
            )
        if os.stat(planted).st_nlink < 2:
            return STATIC, "hardlink did not raise st_nlink; cannot stage the escape"

        zip_path = os.path.join(box, "payload.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("evil.txt", member_payload)

        try:
            with ps.ZipFile(zip_path) as zf:
                zf.extractall(root)
        except Exception as exc:
            if not is_security_rejection(exc):
                return (
                    STATIC,
                    "extract failed before the guard (%s)" % type(exc).__name__,
                )
            leaked = open(secret, "rb").read()
            if member_payload in leaked:
                return VULNERABLE, "member written through the hardlink despite refusal"
            if leaked != secret_original:
                return (
                    VULNERABLE,
                    "outside secret mutated even though extract was refused",
                )
            return (
                FIXED,
                "hardlinked member target security-refused by %s: %.160s; "
                "secret bytes intact" % (type(exc).__name__, exc),
            )

        # No exception: only FIXED if the write did not reach the outside inode.
        leaked = open(secret, "rb").read()
        if member_payload in leaked or leaked != secret_original:
            return (
                VULNERABLE,
                "extraction wrote through the hardlink to the outside secret",
            )
        return FIXED, "extraction did not follow the hardlink; secret bytes intact"
    finally:
        _undo_root()
        shutil.rmtree(box, ignore_errors=True)
