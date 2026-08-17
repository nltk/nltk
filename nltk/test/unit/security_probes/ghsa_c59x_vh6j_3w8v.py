"""GHSA-c59x-vh6j-3w8v [moderate] -- nltk >= 3.10.3: AllowlistUnpickler numpy submodule bypass"""

import io
import pickle

from ._base import FIXED, VULNERABLE, probe


def _global_pickle(module, name, *args):
    """
    Build a protocol‑4 pickle that calls <module>.<name>(*args)
    using STACK_GLOBAL + REDUCE.
    """

    def _string(s):
        # SHORT_BINUNICODE: opcode 0x8c, 1‑byte length, UTF‑8 bytes
        enc = s.encode()
        return bytes([0x8C, len(enc)]) + enc

    buf = bytearray()
    # PROTO 4
    buf.append(pickle.PROTO[0])  # 0x80
    buf.append(4)  # protocol number
    # STACK_GLOBAL: module name, then object name, then opcode 0x93
    buf.extend(_string(module))
    buf.extend(_string(name))
    buf.append(pickle.STACK_GLOBAL[0])  # 0x93
    # MARK (0x28) to start tuple of arguments
    buf.append(pickle.MARK[0])  # 0x28
    for a in args:
        buf.extend(_string(a))
    # TUPLE (0x74), REDUCE (0x52), STOP (0x2e)
    buf.append(pickle.TUPLE[0])  # 0x74
    buf.append(pickle.REDUCE[0])  # 0x52
    buf.append(pickle.STOP[0])  # 0x2e
    return bytes(buf)


@probe("GHSA-c59x-vh6j-3w8v")
def _numpy_submodule_bypass():
    """
    Attempt to load a pickle that calls numpy.lib.npyio.recfromtxt on a dummy path.
    The fix adds numpy.lib.npyio, numpy.lib.format, and numpy.lib._npyio_impl to
    _DENIED_MODULE_PREFIXES, so the call should be rejected.
    """
    # Find which module hosts recfromtxt (numpy 1.x vs 2.x)
    import numpy

    from nltk.picklesec import AllowlistUnpickler

    mod_name = None
    for candidate in ("numpy.lib.npyio", "numpy.lib._npyio_impl"):
        try:
            mod = __import__(candidate, fromlist=["recfromtxt"])
            if hasattr(mod, "recfromtxt"):
                mod_name = candidate
                break
        except ImportError:
            continue

    if mod_name is None:
        return FIXED, "numpy.recfromtxt not found (numpy not installed?)"

    # Build a pickle that calls recfromtxt("/dummy/path")
    payload = _global_pickle(mod_name, "recfromtxt", "/dummy/path")

    try:
        AllowlistUnpickler(
            io.BytesIO(payload),
            allowed_modules=("numpy", "scipy", "sklearn"),
        ).load()
        return VULNERABLE, "recfromtxt executed (bypass succeeded)"
    except Exception as exc:
        # If the fix is in place, the global lookup should be denied,
        # and the exception will mention the module or function name.
        if "recfromtxt" in str(exc) or "numpy.lib" in str(exc):
            return FIXED, f"recfromtxt rejected: {type(exc).__name__}"
        return VULNERABLE, f"unexpected exception: {type(exc).__name__}"
