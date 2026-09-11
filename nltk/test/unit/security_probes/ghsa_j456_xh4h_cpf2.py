"""GHSA-j456-xh4h-cpf2 [high] -- WekaClassifier passes an unvalidated caller-controlled model path to the weka JVM, bypassing nltk.pathsec containment (CWE-22, CWE-73)"""

from ._base import FIXED, STATIC, VULNERABLE, is_security_rejection, probe


@probe("GHSA-j456-xh4h-cpf2")
def _weka_model_path_containment():
    """Construct a ``WekaClassifier`` with a model path outside the data roots.

    The model filename is handed to the weka JVM classpath; an unvalidated
    caller path (absolute escape or traversal) could point outside the pathsec
    data roots. ``__init__`` (and ``classify_many`` / ``train``) now route it
    through ``validate_tool_path``, so an out-of-root path is security-rejected
    before it can reach the JVM.
    """
    from nltk.classify.weka import WekaClassifier

    attempts = ("/etc/passwd", "../" * 10 + "etc/passwd")
    for path in attempts:
        try:
            WekaClassifier(None, path)
        except Exception as exc:
            if is_security_rejection(exc):
                continue
            return STATIC, "%s rejected non-securely (%s)" % (path, type(exc).__name__)
        return VULNERABLE, "WekaClassifier accepted out-of-root model %r" % path
    return FIXED, "out-of-root weka model path refused by validate_tool_path"
