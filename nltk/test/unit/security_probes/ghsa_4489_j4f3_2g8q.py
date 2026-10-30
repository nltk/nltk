"""GHSA-4489-j4f3-2g8q [high] -- nltk ≤ 3.10.2: unpickler dotted-name RCE bypass"""

import io
import pickle

from ._base import FIXED, VULNERABLE, probe


def _dotted_global(module, name):
    """A protocol-4 pickle whose STACK_GLOBAL carries a dotted attribute chain."""
    su = lambda s: pickle.SHORT_BINUNICODE + bytes([len(s.encode())]) + s.encode()
    return (
        pickle.PROTO + bytes([4]) + su(module) + su(name) + pickle.STACK_GLOBAL + b"."
    )


@probe("GHSA-4489-j4f3-2g8q")
def _unpickler_dotted_name():
    """A real proto-4 load whose global rides a dotted attribute chain must be
    refused before the chain is walked (the getattr-traversal RCE, not a poke at
    find_class at proto 0 where stock pickle already errors for the wrong reason).
    """
    from nltk.picklesec import allowlisted_pickle_load

    gadgets = [
        ("collections", "OrderedDict.fromkeys"),  # resolvable dotted chain
        ("sklearn", "os.system"),
        ("nltk.tokenize", "repp.ReppTokenizer._execute"),
    ]
    for module, name in gadgets:
        try:
            allowlisted_pickle_load(
                io.BytesIO(_dotted_global(module, name)),
                allowed_modules=(module.split(".")[0],),
            )
            return VULNERABLE, f"dotted name {module}.{name} resolved"
        except pickle.UnpicklingError as exc:
            if "dotted name" not in str(exc):
                return VULNERABLE, f"{module}.{name} blocked but not as a dotted name"
        except Exception:
            return VULNERABLE, f"{module}.{name} failed before the dotted-name guard"
    return FIXED, "proto-4 dotted-name globals rejected before traversal"
