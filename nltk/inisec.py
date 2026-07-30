# Natural Language Toolkit: Security – early import hook
#
# Copyright (C) 2026 NLTK Project
# Author: Eric Kafe <kafe.eric@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Early security module to prevent module hijacking from the current working directory.

This module installs a custom `MetaPathFinder` to mitigate Untrusted Search Path
vulnerabilities (CWE-426/CWE-427). By default, Python prepends the current working
directory (CWD) to `sys.path`, allowing attackers to drop malicious scripts that
shadow standard library or third-party modules.

To protect NLTK without disrupting the host application's legitimate local imports,
this hook operates dynamically:
1. It intercepts module resolution and checks if the target module resides inside
   the current working directory.
2. If it does not, the import proceeds instantly via standard Python resolution.
3. If it does resolve to the CWD, the hook inspects the call stack to determine
   if the import was triggered by NLTK internals.
4. If NLTK initiated the import, it is blocked for security reasons.
5. If the host application initiated the import, it is allowed to proceed normally.

This approach is future-proof (it protects all standard library and third-party
dependencies without a hardcoded list) and highly performant (the expensive call
stack inspection only occurs for modules actually located in the CWD).

The hook is installed at the very top of `nltk/__init__.py` to ensure it is active
before any other NLTK code executes.
"""

import importlib.abc
import importlib.machinery
import os
import sys
from pathlib import Path


class NLTKSafeImportFinder(importlib.abc.MetaPathFinder):
    """
    Custom finder that blocks NLTK from importing modules from the CWD.
    """

    def __init__(self):
        pass

    def _is_import_from_nltk(self):
        """Walk the call stack to determine if the import originated from NLTK code."""
        frame = sys._getframe(1)
        while frame:
            module_name = frame.f_globals.get("__name__")
            if (
                module_name
                and not module_name.startswith(("importlib.", "_frozen_importlib"))
                and module_name != "nltk.inisec"
            ):
                return module_name.startswith("nltk")
            frame = frame.f_back
        return False

    def find_spec(self, fullname, path, target=None):
        # 1. Exempt NLTK itself to prevent breaking local development.
        # (If an attacker drops a malicious nltk.py in the CWD, it executes before
        # this hook is even installed anyway, so exempting it here is secure).
        top_level = fullname.split(".")[0]
        if top_level == "nltk":
            return None

        # 2. Ask the default PathFinder where this module lives
        spec = importlib.machinery.PathFinder.find_spec(fullname, path, target)
        if spec is None:
            return None

        # 3. Resolve CWD dynamically
        try:
            cwd = Path.cwd().resolve()
        except FileNotFoundError:
            return None

        # 4. Check if the module resolves to the CWD
        is_cwd = False
        try:
            if spec.origin:
                if Path(spec.origin).resolve().parent == cwd:
                    is_cwd = True
            elif spec.submodule_search_locations:
                for loc in spec.submodule_search_locations:
                    if Path(loc).resolve().parent == cwd:
                        is_cwd = True
                        break
        except FileNotFoundError:
            pass

        # 5. FAST EXIT: If it's not in the CWD, we don't care. Let it load instantly.
        if not is_cwd:
            return None

        # 6. SLOW PATH: It is in the CWD. We only walk the stack for this rare case.
        if self._is_import_from_nltk():
            raise ImportError(
                f"Blocked import of {fullname} from current working directory "
                "for security reasons. Use '-P' or set PYTHONSAFEPATH."
            )

        # 7. It's in the CWD, but requested by the host application (not NLTK).
        # Allow the user's code to import their local module normally.
        return None


# Install the finder only once, unless explicitly disabled by setting the environment
# variable to "1" (strict check, not just any value).
if os.environ.get("NLTK_DISABLE_IMPORT_SECURITY") != "1":
    if not any(isinstance(f, NLTKSafeImportFinder) for f in sys.meta_path):
        sys.meta_path.insert(0, NLTKSafeImportFinder())
