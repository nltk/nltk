"""GHSA-568f-pv23-39p4 [medium] -- Stable FrameNet and NKJP readers parse outside-root XML in 3.9.4"""

from ._base import guard_rejects, probe


@probe("GHSA-568f-pv23-39p4")
def _framenet_nkjp_outside_root_xml():
    """FrameNet/NKJP entrypoints built parser paths that left the root."""
    from nltk.corpus.reader.framenet import _validate_in_root

    return guard_rejects(lambda path, root: _validate_in_root(path, root, "framenet"))
