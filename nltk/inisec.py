# Natural Language Toolkit: Security – early import hook
#
# Copyright (C) 2026 NLTK Project
# Author: Eric Kafe <kafe.eric@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Early security module to prevent module hijacking from the current working directory.

This module installs a custom `MetaPathFinder` to mitigate Uncontrolled Search Path
vulnerabilities (CWE-427). It uses a dynamic, full-stack inspection architecture
to protect NLTK and its entire dependency tree without relying on a hardcoded list
of vulnerable modules, and without globally mutating the host application's
``sys.path``.

The hook is installed at the very top of `nltk/__init__.py` to ensure it is active
before any NLTK code executes.

Scope of protection
--------------------
* **Main process (synchronous imports).** The meta-path finder inspects the call
  stack whenever a module is resolved from the current working directory (CWD). If
  any ancestor frame belongs to ``nltk``, the import is blocked. This covers both
  direct imports and indirect ones initiated by NLTK through a dependency
  (e.g. ``nltk -> sklearn -> joblib``). The host application's own CWD imports are
  left untouched.

* **Freshly started worker interpreters (``spawn`` / ``forkserver``).** These read
  ``PYTHONSAFEPATH`` during interpreter startup and therefore omit the CWD from
  ``sys.path`` natively. NLTK propagates ``PYTHONSAFEPATH=1`` into the environment
  at install time so such workers inherit interpreter-level isolation.

Known residual limitation
-------------------------
Imports executed inside a **``fork``-based worker** (the default for some parallel
backends, e.g. joblib/loky on Linux) are *not* fully covered. A forked worker
inherits the parent's already-fixed ``sys.path`` (so ``PYTHONSAFEPATH`` is never
re-evaluated) and runs on a fresh call stack with no ``nltk`` frame (so caller
detection cannot fire). Closing this in-library would require stripping the CWD
from the *parent's* ``sys.path`` — a global mutation this module deliberately
avoids because it can break a host application's legitimate local imports.

To obtain complete protection across fork-based workers, start Python with the
``-P`` flag or set ``PYTHONSAFEPATH=1`` in the environment **before** launching the
process.

Note: ``-P`` and ``PYTHONSAFEPATH`` require **Python 3.11+**. On Python 3.10 they
are silently ignored, so this launch-time remedy is unavailable and fork-based
worker imports cannot be isolated this way. (Python 3.10 is expected to be dropped
in an upcoming release.)

The hook can be disabled entirely by setting ``NLTK_DISABLE_IMPORT_SECURITY=1``.
"""

import importlib.abc
import importlib.machinery
import os
import sys
from pathlib import Path


class NLTKSafeImportFinder(importlib.abc.MetaPathFinder):
    """
    Custom finder that dynamically blocks NLTK and its dependencies from
    importing modules from the current working directory.
    """

    def _is_import_from_nltk(self):
        """
        Walk the *entire* call stack to determine if NLTK is an ancestor.
        This correctly catches indirect imports (e.g., NLTK -> sklearn -> joblib)
        that occur synchronously in the current process.
        """
        try:
            frame = sys._getframe(2)
            while frame:
                module_name = frame.f_globals.get("__name__")
                if module_name:
                    if module_name.startswith("nltk") and module_name != "nltk.inisec":
                        return True
                frame = frame.f_back
        except Exception:
            pass
        return False

    def find_spec(self, fullname, path, target=None):
        # 1. Exempt NLTK itself to ensure local development from repo root works.
        top_level = fullname.split(".")[0]
        if top_level == "nltk":
            return None

        # 2. Ask default PathFinder where this module lives
        spec = importlib.machinery.PathFinder.find_spec(fullname, path, target)
        if spec is None:
            return None

        # 3. Resolve CWD dynamically (respects process chdir)
        try:
            cwd = Path.cwd().resolve()
        except FileNotFoundError:
            return None

        # 4. Check if the module or package resolves to the CWD (or any subdirectory within it)
        is_cwd = False
        try:
            if spec.origin:
                resolved_origin = Path(spec.origin).resolve()
                resolved_origin.relative_to(cwd)
                is_cwd = True
            elif spec.submodule_search_locations:
                for loc in spec.submodule_search_locations:
                    resolved_loc = Path(loc).resolve()
                    resolved_loc.relative_to(cwd)
                    is_cwd = True
                    break
        except (ValueError, FileNotFoundError):
            # ValueError means the path is NOT inside cwd; FileNotFoundError means it doesn't exist
            pass

        # 5. FAST EXIT: If the module is NOT in the CWD, let it load instantly.
        if not is_cwd:
            return None

        # 6. It is in the CWD. Block only if NLTK initiated this import
        #    (directly or indirectly) in the current process.
        if self._is_import_from_nltk():
            raise ImportError(
                f"Blocked import of {fullname} from current working directory "
                "for security reasons. Use '-P' or set PYTHONSAFEPATH to prevent "
                "Python from searching the current working directory."
            )

        # 7. CWD import requested by the host application (not NLTK), allow it.
        return None


def _install():
    """
    Install the finder once and propagate interpreter-level CWD isolation to
    freshly started worker interpreters (``spawn`` / ``forkserver``) via
    ``PYTHONSAFEPATH``.

    ``setdefault`` is used so NLTK never overrides a value the host has already
    chosen; it only supplies a default for child interpreters to inherit. Note
    that setting this has no effect on the *current* interpreter (the flag is
    read only at startup) — it exists purely for inheritance by children.
    """
    os.environ.setdefault("PYTHONSAFEPATH", "1")

    if not any(isinstance(f, NLTKSafeImportFinder) for f in sys.meta_path):
        sys.meta_path.insert(0, NLTKSafeImportFinder())


# Install the finder only once, unless explicitly disabled via environment variable
if os.environ.get("NLTK_DISABLE_IMPORT_SECURITY") != "1":
    _install()
