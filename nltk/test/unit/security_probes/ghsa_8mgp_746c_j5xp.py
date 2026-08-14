"""GHSA-8mgp-746c-j5xp [high] -- Model-artifact APIs bypass pathsec and touch files outside allowed roots

Probe: run the attack, report what the tree does now. See _base for statuses.
"""
import os, tempfile
from ._base import FIXED, VULNERABLE, probe


@probe("GHSA-8mgp-746c-j5xp")
def _model_artifact_apis():
    """Model-artifact read/write APIs treated caller paths as plain filenames."""
    import nltk.data

    try:
        nltk.data.load(os.path.join(tempfile.gettempdir(), "..", "..", "etc", "passwd"),
                       format="raw")
        return VULNERABLE, "nltk.data.load reached outside an allowed root"
    except Exception as exc:
        return FIXED, "outside-root model path rejected (%s)" % type(exc).__name__
