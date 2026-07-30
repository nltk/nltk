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
of vulnerable modules.

The hook is installed at the very top of `nltk/__init__.py` to ensure it is active
before any NLTK code executes.
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
        This correctly catches indirect imports (e.g., NLTK -> sklearn -> joblib).
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

        # 6. FUTURE-PROOF CHECK: It is in the CWD. Was it triggered by NLTK?
        if self._is_import_from_nltk():
            raise ImportError(
                f"Blocked import of {fullname} from current working directory "
                "for security reasons. Use '-P' or set PYTHONSAFEPATH to prevent "
                "Python from searching the current working directory."
            )

        # 7. CWD import requested by the host application (not NLTK), allow it.
        return None


# Install the finder only once, unless explicitly disabled via environment variable
if os.environ.get("NLTK_DISABLE_IMPORT_SECURITY") != "1":
    if not any(isinstance(f, NLTKSafeImportFinder) for f in sys.meta_path):
        sys.meta_path.insert(0, NLTKSafeImportFinder())
