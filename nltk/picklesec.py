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


class AllowlistUnpickler(pickle.Unpickler):
    """
    Unpickler that only reconstructs an explicit, audited allowlist of globals.

    Two complementary allowlists are supported:

    - ``allowed_globals``: a set of exact ``(module, qualname)`` pairs.
    - ``allowed_modules``: a set of module names; a global is permitted when its
      module equals an allowed name or is a submodule of one (i.e. ``module``
      equals ``name`` or starts with ``name + "."``).

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

    def _module_allowed(self, module: str) -> bool:
        return any(
            module == name or module.startswith(name + ".")
            for name in self._allowed_modules
        )

    def find_class(self, module: str, name: str) -> Any:
        if (module, name) in self._allowed_globals or self._module_allowed(module):
            return super().find_class(module, name)
        raise pickle.UnpicklingError(
            f"global '{module}.{name}' is not in the pickle allowlist"
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
