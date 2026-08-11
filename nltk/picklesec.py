# Natural Language Toolkit: Safer pickle loading.
#
# Copyright (C) 2001-2026 NLTK Project
# Author: Eric Kafe <kafe.eric@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
#

"""
Helpers for safer and/or more explicit pickle usage in NLTK.

- RestrictedUnpickler: blocks unpickling of *any* globals (classes/functions).
  Intended for loading NLTK data packages where we control the serialization.
- WarningUnpickler: emits a security warning before unpickling (does not make
  unpickling safe).
- AllowlistUnpickler: only reconstructs an explicit, audited allowlist of
  globals. Use it for loading objects whose set of legitimate classes is known
  (e.g. a trained model) so that arbitrary-code gadgets such as ``os.system``
  can never be reconstructed from an untrusted file.
"""

from __future__ import annotations

import pickle
import types
import warnings
from collections.abc import Iterable
from typing import Any, BinaryIO

PICKLE_WARNING = (
    "Security warning: loading pickles can execute arbitrary code. "
    "Only load pickle files from trusted sources and never from untrusted "
    "or unauthenticated locations."
)


class RestrictedUnpickler(pickle.Unpickler):
    """
    Unpickler that prevents any class or function from being used during loading.
    """

    def find_class(self, module: str, name: str) -> Any:
        # Forbid every function/class global.
        raise pickle.UnpicklingError(f"global '{module}.{name}' is forbidden")


class WarningUnpickler(pickle.Unpickler):
    """Unpickler that emits PICKLE_WARNING once per instance."""

    def __init__(self, file: BinaryIO, *, context: str | None = None, **kwargs: Any):
        super().__init__(file, **kwargs)
        self._context = context
        self._warned = False

    def load(self) -> Any:
        if not self._warned:
            msg = (
                PICKLE_WARNING
                if self._context is None
                else f"{PICKLE_WARNING} ({self._context})"
            )
            warnings.warn(msg, RuntimeWarning, stacklevel=3)
            self._warned = True
        return super().load()


def pickle_load(
    file: BinaryIO, *, context: str | None = None, restricted: bool = False
) -> Any:
    """
    Convenience wrapper similar to pickle.load(file).

    - If restricted=True, uses RestrictedUnpickler (no warning by default).
    - If restricted=False, uses WarningUnpickler and emits a warning.
    """
    if restricted:
        return RestrictedUnpickler(file).load()
    return WarningUnpickler(file, context=context).load()


# Modules whose globals are never safe to reconstruct from an untrusted pickle,
# even when a broad parent namespace is allowlisted. This denylist is a
# defense-in-depth backstop: if a caller (now or in the future) allows a wide
# namespace such as ``numpy`` or ``nltk.tokenize``, an in-namespace gadget like
# ``numpy.f2py.crackfortran.myeval`` (eval sink) or
# ``nltk.tokenize.repp.ReppTokenizer._execute`` (subprocess sink) still cannot
# be resolved (GHSA-x99w). Matched by exact module or ``prefix + "."``.
_DENIED_MODULE_PREFIXES = (
    "os",
    "nt",
    "posix",
    "subprocess",
    "sys",
    "socket",
    "shutil",
    "signal",
    "pty",
    "popen2",
    "commands",
    "ctypes",
    "importlib",
    "runpy",
    "builtins",  # builtins.int etc. must be requested via allowed_globals
    "webbrowser",
    "pdb",
    "bdb",
    "code",
    "codeop",
    "multiprocessing",
    "asyncio",
    "threading",
    "pickle",
    "numpy.f2py",
    "numpy.ctypeslib",
    "numpy.distutils",
    "numpy.testing",
    "nltk.tokenize.repp",
    "nltk.internals",
)

# Individual dangerous globals that live in an *allowed* namespace and so are
# not caught by :data:`_DENIED_MODULE_PREFIXES`. ``numpy.load`` (and friends)
# have ``__module__ == "numpy"`` yet perform file / nested-pickle I/O, so a
# broad ``numpy`` allow (needed for genuine array unpickling) would otherwise
# expose them. Matched both on the requested ``(module, name)`` and on the
# resolved object's ``(__module__, __qualname__)``.
_DENIED_GLOBALS = frozenset(
    {
        ("numpy", "load"),
        ("numpy", "loadtxt"),
        ("numpy", "fromfile"),
        ("numpy", "fromregex"),
        ("numpy", "genfromtxt"),
        ("numpy", "save"),
        ("numpy", "savez"),
        ("numpy", "savez_compressed"),
        ("numpy", "savetxt"),
        ("numpy", "memmap"),
        ("numpy", "DataSource"),
        ("numpy", "vectorize"),
        ("pandas", "read_pickle"),
    }
)


class AllowlistUnpickler(pickle.Unpickler):
    """
    Unpickler that only reconstructs an explicit, audited allowlist of globals.

    Two complementary allowlists are supported:

    - ``allowed_globals``: a set of exact ``(module, qualname)`` pairs. Use this
      for individual safe globals from an otherwise-dangerous module, e.g.
      ``("builtins", "int")``.
    - ``allowed_modules``: a set of module names; a global is permitted when its
      module equals an allowed name or is a submodule of one (i.e. ``module``
      equals ``name`` or starts with ``name + "."``).

    Three hard guards apply *before* the allowlists and cannot be opted out of:

    1. A dotted ``name`` is rejected. For pickle protocol >= 4,
       ``pickle.Unpickler.find_class`` resolves a dotted ``name`` through
       :func:`getattr` chaining, so an attacker who is allowed the module
       ``sklearn`` could otherwise request ``sklearn.os.system`` and reach a
       command-execution sink the module allowlist never intended (GHSA-4489).
       Legitimate model globals are always a single qualname.
    2. Globals from a denied module (:data:`_DENIED_MODULE_PREFIXES`) are
       rejected even if a parent namespace is allowlisted, so an in-namespace
       gadget cannot ride a broad ``allowed_modules`` entry (GHSA-x99w).
    3. ``builtins`` is denied wholesale; individual safe builtins must be named
       explicitly via ``allowed_globals``.

    Anything not covered by either allowlist raises ``UnpicklingError`` before
    the global is resolved, so dangerous callables such as ``os.system`` or
    ``builtins.eval`` can never be reconstructed from an untrusted pickle. This
    is stricter than :func:`pickle_load` (which only warns and then executes)
    but, unlike :class:`RestrictedUnpickler` (which blocks *all* globals), it
    still allows the known-good classes a saved object legitimately needs.
    """

    def __init__(
        self,
        file: BinaryIO,
        *,
        allowed_globals: Iterable[tuple[str, str]] = (),
        allowed_modules: Iterable[str] = (),
        **kwargs: Any,
    ):
        super().__init__(file, **kwargs)
        if isinstance(allowed_modules, str):
            allowed_modules = (allowed_modules,)
        self._allowed_globals = set(allowed_globals)
        self._allowed_modules = tuple(allowed_modules)

    @staticmethod
    def _module_denied(module: str) -> bool:
        return any(
            module == deny or module.startswith(deny + ".")
            for deny in _DENIED_MODULE_PREFIXES
        )

    def _module_allowed(self, module: str) -> bool:
        return any(
            module == name or module.startswith(name + ".")
            for name in self._allowed_modules
        )

    def _resolve(self, module: str, name: str) -> Any:
        # Resolve, then apply post-resolution defense in depth. A prefix
        # ``allowed_modules`` entry (needed for e.g. numpy array unpickling)
        # otherwise exposes *every* attribute of every module in the namespace:
        # bare module objects, re-exports whose real home is a dangerous module,
        # and dangerous same-module callables such as ``numpy.load`` (a nested
        # unpickle sink). Reject those even though the requested module string
        # itself is allowlisted.
        obj = super().find_class(module, name)
        if isinstance(obj, types.ModuleType):
            raise pickle.UnpicklingError(
                f"global '{module}.{name}' resolves to a module object, which is "
                "not a reconstructable class/function"
            )
        true_module = getattr(obj, "__module__", None)
        true_qualname = getattr(obj, "__qualname__", name)
        # An audited safe primitive keeps its exemption even though its real home
        # (e.g. ``builtins``) is a denied module.
        if (true_module, true_qualname) not in _SAFE_DENIED_GLOBALS:
            if true_module and self._module_denied(true_module):
                raise pickle.UnpicklingError(
                    f"global '{module}.{name}' re-exports {true_module}."
                    f"{true_qualname} from a denied module"
                )
        if (true_module, true_qualname) in _DENIED_GLOBALS:
            raise pickle.UnpicklingError(
                f"global '{module}.{name}' ({true_module}.{true_qualname}) is a "
                "denied callable and cannot be reconstructed from an untrusted "
                "pickle"
            )
        return obj

    def find_class(self, module: str, name: str) -> Any:
        # Guard 1: reject dotted names -- find_class would getattr-chain them
        # (proto >= 4), reaching e.g. `<allowed_module>.os.system` (GHSA-4489).
        if "." in name:
            raise pickle.UnpicklingError(
                f"global '{module}.{name}' has a dotted name, which is forbidden "
                "(attribute-traversal pickle RCE, GHSA-4489)"
            )
        # Guard 2: reject dunder names -- a prefix allow otherwise reaches module
        # internals like ``__builtins__`` / ``__loader__`` / ``__class__``.
        # Legitimate pickled globals are never dunders.
        if name.startswith("__") and name.endswith("__"):
            raise pickle.UnpicklingError(
                f"global '{module}.{name}' has a dunder name, which is forbidden"
            )
        # Guard 3: an exact denied global (e.g. ``numpy.load``) is rejected even
        # under an allowed namespace, before resolution.
        if (module, name) in _DENIED_GLOBALS:
            raise pickle.UnpicklingError(
                f"global '{module}.{name}' is a denied callable and cannot be "
                "reconstructed from an untrusted pickle"
            )
        # Guard 4: an exact allowlisted global is honored, unless it is from a
        # denied module and not one of the audited safe primitives (GHSA-x99w).
        if (module, name) in self._allowed_globals:
            if (
                self._module_denied(module)
                and (module, name) not in _SAFE_DENIED_GLOBALS
            ):
                raise pickle.UnpicklingError(
                    f"global '{module}.{name}' is from a denied module and cannot "
                    "be reconstructed from an untrusted pickle"
                )
            return self._resolve(module, name)
        if self._module_denied(module):
            raise pickle.UnpicklingError(
                f"global '{module}.{name}' is from a denied module "
                "(defense-in-depth backstop, GHSA-x99w)"
            )
        if self._module_allowed(module):
            return self._resolve(module, name)
        raise pickle.UnpicklingError(
            f"global '{module}.{name}' is not in the pickle allowlist"
        )


# A tiny set of individually-safe globals that live in an otherwise-denied
# module. ``builtins`` is denied wholesale (Guard 3), but a few immutable
# builtin types are needed by legitimate model pickles (e.g. defaultdict's
# default_factory is ``int``). These are non-callable-as-a-sink primitives.
_SAFE_DENIED_GLOBALS = frozenset(
    {
        ("builtins", "int"),
        ("builtins", "float"),
        ("builtins", "complex"),
        ("builtins", "bool"),
        ("builtins", "str"),
        ("builtins", "bytes"),
        ("builtins", "list"),
        ("builtins", "tuple"),
        ("builtins", "dict"),
        ("builtins", "set"),
        ("builtins", "frozenset"),
    }
)


def allowlisted_pickle_load(
    file: BinaryIO,
    *,
    allowed_globals: Iterable[tuple[str, str]] = (),
    allowed_modules: Iterable[str] = (),
) -> Any:
    """
    Load a pickle while only permitting an explicit allowlist of globals.

    See :class:`AllowlistUnpickler` for the meaning of ``allowed_globals`` and
    ``allowed_modules``. Prefer this over the warn-only :func:`pickle_load` when
    the set of legitimate classes in the file is known (e.g. a trained model),
    because :func:`pickle_load` still executes arbitrary code.
    """
    return AllowlistUnpickler(
        file, allowed_globals=allowed_globals, allowed_modules=allowed_modules
    ).load()
