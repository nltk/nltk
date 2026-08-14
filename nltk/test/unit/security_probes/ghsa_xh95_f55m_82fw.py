"""GHSA-xh95-f55m-82fw [high] -- Path traversal in NLTK FramenetCorpusReader.frame() allows arbitrary XML file read, bypa"""
from ._base import escape_probe, probe


@probe("GHSA-xh95-f55m-82fw")
def _framenet_frame_traversal():
    """FramenetCorpusReader.frame(name) interpolated name into a path."""
    from nltk.corpus.reader.framenet import FramenetCorpusReader

    def traverse(box):
        reader = FramenetCorpusReader(box.root, [])
        return reader.frame("../" * 6 + "secret")

    return escape_probe([("frame('../secret')", traverse)])
