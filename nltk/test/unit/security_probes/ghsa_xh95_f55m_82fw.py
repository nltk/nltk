"""GHSA-xh95-f55m-82fw [high] -- Path traversal in NLTK FramenetCorpusReader.frame() allows arbitrary XML file read, bypassing the nltk.pathsec sandbox (ENFORCE=True)"""

import os
import shutil
import tempfile

from ._base import (
    FIXED,
    STATIC,
    VULNERABLE,
    _restore_data_path,
    guard_rejects,
    is_security_rejection,
    probe,
    register_data_root,
)

CANARY = "PWNED-CANARY"

_FRAME_XML = (
    '<?xml version="1.0"?><frame xmlns="http://framenet.icsi.berkeley.edu" '
    'ID="1" name="%s"><definition>x</definition></frame>' % CANARY
)


def seeded_reader(root):
    """A FramenetCorpusReader whose frame index is pre-seeded.

    frame_by_name() builds the whole frame index first, which needs a real corpus;
    seeding it lets the probe reach the containment guard the advisory added.
    """
    from nltk.corpus.reader.framenet import FramenetCorpusReader

    os.makedirs(os.path.join(root, "frame"), exist_ok=True)
    # Register the corpus root as a data root so the reader constructs on Linux,
    # where mkdtemp lands in /tmp (not a pathsec root). The "outside" targets are
    # siblings under box, NOT under root, so they stay out of the sandbox.
    register_data_root(root)
    reader = FramenetCorpusReader(root, [])
    reader._frame_idx = {"seed": 1}
    return reader


@probe("GHSA-xh95-f55m-82fw")
def _framenet_frame_traversal():
    """frame() interpolated a caller name into a path opened with builtin open().

    Drive the real public reader with names crafted to escape the corpus root; a
    returned frame carrying the canary is a leak, and only a security-marked
    refusal counts as a defence (an incidental error means the guard was never hit).
    """
    import nltk.data
    from nltk.corpus.reader.framenet import _validate_in_root

    # the symlink attempt below needs os.symlink, which is POSIX-only
    if os.name != "posix":
        return STATIC, "symlink escape is POSIX-only"

    _saved_path = list(nltk.data.path)
    box = tempfile.mkdtemp()
    try:
        root = os.path.join(box, "fn")
        reader = seeded_reader(root)
        # a parseable frame XML outside the root: if containment is ever removed,
        # the read succeeds and the canary surfaces instead of an opaque error.
        outside = os.path.join(box, "outside.xml")
        with open(outside, "w", encoding="utf-8") as fh:
            fh.write(_FRAME_XML)
        os.symlink(outside, os.path.join(root, "frame", "evil.xml"))

        attempts = {
            "traversal": "../" * 6 + outside.lstrip("/"),
            "absolute": outside,
            "symlink": "evil",  # no separators: only the resolve guard can catch it
        }
        reached = []
        for label, name in attempts.items():
            try:
                result = reader.frame_by_name(name)
            except Exception as exc:
                if not is_security_rejection(exc):
                    return (
                        STATIC,
                        f"{label} failed before the guard ({type(exc).__name__})",
                    )
                reached.append(label)
                continue
            if CANARY in str(result):
                return VULNERABLE, f"frame_by_name({label}) read outside the root"
            reached.append(label + "=no-leak")
        # the guard itself must also refuse raw outside-root paths
        status, evidence = guard_rejects(
            lambda path, root_: _validate_in_root(path, root_, "framenet")
        )
        if status == VULNERABLE:
            return VULNERABLE, evidence
        return FIXED, "frame_by_name refused: " + ", ".join(reached)
    finally:
        _restore_data_path(_saved_path)
        shutil.rmtree(box, ignore_errors=True)
