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
"""

from __future__ import annotations

import pickle
import warnings
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
