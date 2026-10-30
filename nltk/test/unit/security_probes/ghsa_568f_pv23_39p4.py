"""GHSA-568f-pv23-39p4 [medium] -- Stable FrameNet and NKJP readers parse outside-root XML in 3.9.4"""

from ._base import FIXED, VULNERABLE, guard_rejects, probe


@probe("GHSA-568f-pv23-39p4")
def _framenet_nkjp_outside_root_xml():
    """FrameNet/NKJP entrypoints built parser paths that left the root.

    The advisory covers both readers, so drive both containment guards: a
    regression in either one must fail this probe.
    """
    from nltk.corpus.reader.framenet import _validate_in_root
    from nltk.pathsec import validate_path

    guards = {
        "framenet": lambda path, root: _validate_in_root(path, root, "framenet"),
        "nkjp": lambda path, root: validate_path(
            path, context="NKJPCorpusReader", required_root=root
        ),
    }
    passed = []
    for name, guard in guards.items():
        status, evidence = guard_rejects(guard)
        if status == VULNERABLE:
            return VULNERABLE, f"{name}: {evidence}"
        passed.append(f"{name}={status.lower()}")
    return FIXED, "both reader guards security-reject escapes: " + ", ".join(passed)
