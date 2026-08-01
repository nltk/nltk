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

This mitigation is **best-effort and fails open**: whenever it cannot be certain
that an import is a CWD hijack, it allows the import. It never breaks a legitimate
import, but it is defense-in-depth rather than an absolute guarantee.

Scope of protection
--------------------
* **Main process (synchronous imports).** The meta-path finder inspects the call
  stack whenever a module is resolved as a *loose* file in the current working
  directory (CWD). If any ancestor frame belongs to ``nltk``, the import is
  blocked. This covers both direct imports and indirect ones initiated by NLTK
  through a dependency (e.g. ``nltk -> sklearn -> joblib``). The host application's
  own CWD imports are left untouched.

* **Freshly started worker interpreters (``spawn`` / ``forkserver``).** These read
  ``PYTHONSAFEPATH`` during interpreter startup and therefore omit the CWD from
  ``sys.path`` natively. NLTK propagates ``PYTHONSAFEPATH=1`` into the environment
  at install time so such workers inherit interpreter-level isolation.

What is *not* blocked
---------------------
Only modules that live *loose* in the current working directory are candidates for
blocking. Modules resolved from a trusted library location -- the interpreter
prefix(es), the ``sysconfig`` install paths, or ``site-packages`` -- are always
allowed, even when that location happens to sit *inside* the CWD. This is the
standard layout for in-project virtual environments (``uv``, Poetry in-project
venvs, ``python -m venv .venv``), and importing an installed dependency from such
an environment is never treated as hijacking (see issue #3730).

Additionally, if the current working directory is not actually present on
``sys.path``, no implicit-CWD hijack vector exists, so the hook does not engage
at all.

Known residual limitations
--------------------------
* **Fork-based workers** (the default for some parallel backends, e.g. joblib/loky
  on Linux) inherit the parent's already-fixed ``sys.path`` and run on a fresh call
  stack with no ``nltk`` frame, so caller detection cannot fire.
* **Editable installs** (``pip install -e``) whose source tree lives under the CWD
  but outside a standard ``site-packages`` may not be recognised as a trusted root.

For complete, deterministic protection, start Python with the ``-P`` flag or set
``PYTHONSAFEPATH=1`` in the environment **before** launching the process.

Note: ``-P`` and ``PYTHONSAFEPATH`` require **Python 3.11+**. On Python 3.10 they
are silently ignored. (Python 3.10 is expected to be dropped in an upcoming
release.)

The hook can be disabled entirely by setting ``NLTK_DISABLE_IMPORT_SECURITY=1``.
"""

import importlib.abc
import importlib.machinery
import os
import site
import sys
import sysconfig
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def _trusted_library_roots():
    """
    Return a frozenset of resolved directories that hold legitimately installed
    code (interpreter prefixes, ``sysconfig`` install paths, and ``site-packages``).

    A module resolved from any of these locations is never considered a CWD
    hijack, even when the location is nested inside the current working directory
    (the common in-project ``.venv`` layout).

    The result is cached: these paths are fixed for the life of the interpreter.
    """
    roots = set()

    for prefix in (
        sys.prefix,
        sys.exec_prefix,
        getattr(sys, "base_prefix", None),
        getattr(sys, "base_exec_prefix", None),
    ):
        if prefix:
            try:
                roots.add(Path(prefix).resolve())
            except (OSError, ValueError):
                pass

    try:
        for key in ("purelib", "platlib", "stdlib", "platstdlib", "data", "scripts"):
            path = sysconfig.get_paths().get(key)
            if path:
                try:
                    roots.add(Path(path).resolve())
                except (OSError, ValueError):
                    pass
    except Exception:
        pass

    try:
        for path in site.getsitepackages():
            try:
                roots.add(Path(path).resolve())
            except (OSError, ValueError):
                pass
    except Exception:
        # site.getsitepackages() can be missing in some embedded/virtual setups.
        pass

    try:
        user_site = site.getusersitepackages()
        if user_site:
            roots.add(Path(user_site).resolve())
    except Exception:
        pass

    return frozenset(roots)


def _is_under_any(path, roots):
    """Return True if *path* is equal to or nested under any directory in *roots*."""
    for root in roots:
        try:
            path.relative_to(root)
            return True
        except ValueError:
            continue
    return False


def _cwd_on_sys_path(cwd):
    """
    Return True if the current working directory is actually reachable via
    ``sys.path``. If it is not, there is no implicit-CWD hijack vector and no
    reason to block anything.
    """
    for entry in sys.path:
        if entry == "":
            return True
        try:
            if Path(entry).resolve() == cwd:
                return True
        except (OSError, ValueError):
            continue
    return False


class NLTKSafeImportFinder(importlib.abc.MetaPathFinder):
    """
    Custom finder that dynamically blocks NLTK and its dependencies from
    importing modules that live loose in the current working directory.
    """

    def _is_import_from_nltk(self, cwd):
        """
        Walk the *entire* call stack to determine if NLTK is an ancestor.
        This correctly catches indirect imports (e.g., NLTK -> sklearn -> joblib)
        that occur synchronously in the current process.

        Frames whose source file lives inside the CWD are ignored, so a malicious
        ``nltk``-named module dropped in the CWD cannot masquerade as the real
        NLTK to authorize a sibling hijack.
        """
        try:
            frame = sys._getframe(2)
            while frame:
                module_name = frame.f_globals.get("__name__")
                if (
                    module_name
                    and module_name.startswith("nltk")
                    and module_name != "nltk.inisec"
                ):
                    filename = frame.f_globals.get("__file__")
                    trustworthy = True
                    if filename:
                        try:
                            Path(filename).resolve().relative_to(cwd)
                            trustworthy = False
                        except (ValueError, OSError):
                            trustworthy = True
                    if trustworthy:
                        return True
                frame = frame.f_back
        except Exception:
            pass
        return False

    def find_spec(self, fullname, path, target=None):
        # 1. Exempt NLTK itself so local development from the repo root works.
        top_level = fullname.split(".")[0]
        if top_level == "nltk":
            return None

        # 2. Resolve the CWD (respects process chdir). If it is gone, bail out.
        try:
            cwd = Path.cwd().resolve()
        except (FileNotFoundError, OSError):
            return None

        # 3. If the CWD is not even on sys.path, there is nothing to hijack.
        if not _cwd_on_sys_path(cwd):
            return None

        # 4. Ask the default PathFinder where this module lives.
        spec = importlib.machinery.PathFinder.find_spec(fullname, path, target)
        if spec is None:
            return None

        # 5. Collect the candidate filesystem locations for this spec.
        candidates = []
        if spec.origin and spec.origin not in ("built-in", "frozen"):
            candidates.append(spec.origin)
        if spec.submodule_search_locations:
            candidates.extend(spec.submodule_search_locations)
        if not candidates:
            # Builtin/frozen: no loose file to hijack.
            return None

        trusted_roots = _trusted_library_roots()

        # 6. Loose CWD module: inside the CWD but NOT under any trusted root.
        is_loose_cwd = False
        for candidate in candidates:
            try:
                resolved = Path(candidate).resolve()
            except (OSError, ValueError):
                continue
            try:
                resolved.relative_to(cwd)
            except ValueError:
                continue  # Not inside the CWD.
            if _is_under_any(resolved, trusted_roots):
                continue  # Inside the CWD but installed -> trusted.
            is_loose_cwd = True
            break

        # 7. FAST EXIT: not a loose CWD module -> let it load normally.
        if not is_loose_cwd:
            return None

        # 8. It IS a loose CWD module. Block only if NLTK initiated this import.
        if self._is_import_from_nltk(cwd):
            raise ImportError(
                f"Blocked import of {fullname} from current working directory "
                "for security reasons. Use '-P' or set PYTHONSAFEPATH to prevent "
                "Python from searching the current working directory."
            )

        # 9. Loose CWD import requested by the host application (not NLTK), allow it.
        return None


def _install():
    """
    Install the finder once and propagate interpreter-level CWD isolation to
    freshly started worker interpreters (``spawn`` / ``forkserver``) via
    ``PYTHONSAFEPATH``.

    ``setdefault`` is used so NLTK never overrides a value the host has already
    chosen; it only supplies a default for child interpreters to inherit.
    """
    os.environ.setdefault("PYTHONSAFEPATH", "1")

    if not any(isinstance(f, NLTKSafeImportFinder) for f in sys.meta_path):
        sys.meta_path.insert(0, NLTKSafeImportFinder())


# Install the finder only once, unless explicitly disabled via environment variable
if os.environ.get("NLTK_DISABLE_IMPORT_SECURITY") != "1":
    _install()
