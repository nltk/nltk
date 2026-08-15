"""GHSA-x99w-6fgc-pmfw [critical] -- Allowlisted pickle loaders still permit code execution in current source"""

import io

from ._base import FIXED, VULNERABLE, probe


@probe("GHSA-x99w-6fgc-pmfw")
def _pickle_namespace_allowlist():
    """Module-prefix allowlists let REDUCE reach dangerous in-namespace callables."""
    from nltk.picklesec import AllowlistUnpickler

    # Canonical RCE gadgets plus the ones the advisory names. find_class
    # returning any of these is code execution waiting for REDUCE.
    gadgets = [
        ("os", "system"),
        ("posix", "system"),
        ("nt", "system"),
        ("subprocess", "Popen"),
        ("subprocess", "call"),
        ("builtins", "eval"),
        ("builtins", "exec"),
        ("builtins", "__import__"),
        ("numpy.f2py.crackfortran", "myeval"),
        ("nltk.tokenize.repp", "ReppTokenizer"),
    ]
    leaked = []
    for module, name in gadgets:
        try:
            AllowlistUnpickler(io.BytesIO(b"")).find_class(module, name)
            leaked.append(f"{module}.{name}")
        except Exception:
            pass
    if leaked:
        return VULNERABLE, "find_class resolved: " + ", ".join(leaked[:4])
    return FIXED, "%d dangerous globals all rejected under allowlisted parents" % len(
        gadgets
    )
