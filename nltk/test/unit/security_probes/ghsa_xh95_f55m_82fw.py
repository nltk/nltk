"""GHSA-xh95-f55m-82fw [high] -- Path traversal in NLTK FramenetCorpusReader.frame() allows arbitrary XML file read, bypassing the nltk.pathsec sandbox (ENFORCE=True)"""

from ._base import guard_rejects, probe


@probe("GHSA-xh95-f55m-82fw")
def _framenet_frame_traversal():
    """frame() interpolated a caller name into a path opened with builtin open().

    frame() needs a populated index to reach the file open, so drive the guard
    the fix added -- _validate_in_root -- directly with outside-root paths.
    """
    from nltk.corpus.reader.framenet import _validate_in_root

    return guard_rejects(lambda path, root: _validate_in_root(path, root, "framenet"))
