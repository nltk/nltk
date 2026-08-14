"""GHSA-p3m8-78j2-g5p3 [high] -- [CWE-1188] Default ENFORCE=False Disables All pathsec Security Controls

Probe: run the attack, report what the tree does now. See _base for statuses.
"""
from ._base import FIXED, VULNERABLE, probe


@probe("GHSA-p3m8-78j2-g5p3")
def _pathsec_enforced_by_default():
    """ENFORCE defaulted to False, downgrading every gate to a warning."""
    import nltk.pathsec as pathsec

    if not pathsec.ENFORCE:
        return VULNERABLE, "pathsec.ENFORCE is False: all gates warn only"
    try:
        pathsec.open("/etc/passwd")
        return VULNERABLE, "pathsec.open('/etc/passwd') succeeded"
    except Exception as exc:
        return FIXED, "ENFORCE=True; /etc/passwd -> %s" % type(exc).__name__
