"""GHSA-f833-7jw8-xwrv [high] -- Symlink-based sandbox bypass in FramenetCorpusReader (bypasses the fix for CVE-2026-54292)"""

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
from .ghsa_xh95_f55m_82fw import CANARY, seeded_reader

_FRAME_XML = (
    '<?xml version="1.0"?><frame xmlns="http://framenet.icsi.berkeley.edu" '
    'ID="1" name="%s"><definition>x</definition></frame>' % CANARY
)


@probe("GHSA-f833-7jw8-xwrv")
def _framenet_symlink_bypass():
    """A symlink inside frame/ pointed outside the root; the guard now resolves it.

    Two shapes the plain name check cannot see, driven through the real reader: a
    multi-hop symlink chain, and a symlinked corpus *directory* (so every frame in
    it resolves outside). Both must be refused by the resolving containment guard.
    """
    import nltk.data
    from nltk.corpus.reader.framenet import _validate_in_root

    _saved_path = list(nltk.data.path)
    box = tempfile.mkdtemp()
    try:
        outside_dir = os.path.join(box, "outside")
        os.makedirs(outside_dir)
        outside = os.path.join(outside_dir, "outside.xml")
        with open(outside, "w", encoding="utf-8") as fh:
            fh.write(_FRAME_XML)

        cases = []
        # 1. multi-hop chain: frame/chain.xml -> hop.xml -> outside.xml
        chain_root = os.path.join(box, "fn_chain")
        chain_reader = seeded_reader(chain_root)
        hop = os.path.join(box, "hop.xml")
        os.symlink(outside, hop)
        os.symlink(hop, os.path.join(chain_root, "frame", "chain.xml"))
        cases.append(("symlink-chain", chain_reader, "chain"))

        # 2. the frame/ directory itself is a symlink out of the root
        dir_root = os.path.join(box, "fn_dir")
        os.makedirs(dir_root)
        os.symlink(outside_dir, os.path.join(dir_root, "frame"))
        dir_reader = seeded_reader(dir_root)
        cases.append(("symlinked-dir", dir_reader, "outside"))

        reached = []
        for label, reader, name in cases:
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
                return VULNERABLE, f"{label} read a frame outside the corpus root"
            reached.append(label + "=no-leak")

        status, evidence = guard_rejects(
            lambda path, root_: _validate_in_root(path, root_, "framenet")
        )
        if status == VULNERABLE:
            return VULNERABLE, evidence
        return FIXED, "symlink escapes refused: " + ", ".join(reached)
    finally:
        _restore_data_path(_saved_path)
        shutil.rmtree(box, ignore_errors=True)
