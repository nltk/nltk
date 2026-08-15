"""GHSA-6hm5-jgcp-p838 [high] -- Path Traversal in NKJPCorpusReader leads to Arbitrary File Read and bypasses the nltk.pathsec sandbox"""

from ._base import guard_rejects, probe


@probe("GHSA-6hm5-jgcp-p838")
def _nkjp_traversal():
    """NKJP read methods built the file path from a caller fileid.

    add_root() is the containment guard the fix routes through; drive it with
    outside-root paths.
    """
    from nltk.pathsec import validate_path

    return guard_rejects(
        lambda path, root: validate_path(
            path, context="NKJPCorpusReader", required_root=root
        )
    )
