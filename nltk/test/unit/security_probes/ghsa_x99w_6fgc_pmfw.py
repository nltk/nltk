"""GHSA-x99w-6fgc-pmfw [critical] -- Allowlisted pickle loaders still permit code execution in current source

Probe: run the attack, report what the tree does now. See _base for statuses.
"""
import io, os
from ._base import FIXED, VULNERABLE, probe


@probe("GHSA-x99w-6fgc-pmfw")
def _pickle_namespace_allowlist():
    """Module-prefix allowlists let REDUCE reach dangerous in-namespace callables."""
    from nltk.picklesec import AllowlistUnpickler

    # os.system is the canonical gadget; nltk.tokenize.repp.ReppTokenizer._execute
    # and numpy.f2py.crackfortran.myeval are the ones the advisory names.
    attempts = [("os", "system"), ("nltk.tokenize.repp", "ReppTokenizer")]
    leaked = []
    for module, name in attempts:
        try:
            AllowlistUnpickler(io.BytesIO(b"")).find_class(module, name)
            leaked.append("%s.%s" % (module, name))
        except Exception:
            pass
    if leaked:
        return VULNERABLE, "find_class resolved: " + ", ".join(leaked)
    return FIXED, "dangerous globals rejected even under an allowlisted parent"
