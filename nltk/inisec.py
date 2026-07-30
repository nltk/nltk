# Natural Language Toolkit: Initial security
#
# Copyright (C) 2001-2026 NLTK Project
# Author: Eric Kafe <kafe.eric@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
#
"""Initial security for NLTK."""


import importlib.abc
import importlib.machinery
import sys
from pathlib import Path


class NLTKSafeImportFinder(importlib.abc.MetaPathFinder):
    """
    Prevents module hijacking by blocking imports that originate from
    within the NLTK package or involve known vulnerable dependencies.
    """

    _vulnerable_modules = (
        "numpy",
        "numpypy",
        "joblib",
        "tqdm",
        "scipy",
        "sklearn",
        "matplotlib",
        "pandas",
        "nltk",  # Protect NLTK itself from CWD hijacking
    )

    def find_spec(self, fullname, path, target=None):
        # Check if this import was triggered by NLTK code
        frame = sys._getframe(1)
        caller_module = frame.f_globals.get("__name__")
        is_from_nltk = caller_module and caller_module.startswith("nltk")

        # Check if this is a known vulnerable dependency (including nltk itself)
        is_vulnerable = fullname.split(".")[0] in self._vulnerable_modules

        # Only intercept if imported by NLTK OR is a known vulnerable dependency
        if not (is_from_nltk or is_vulnerable):
            return None

        # Use PathFinder directly to avoid recursion
        spec = importlib.machinery.PathFinder.find_spec(fullname, path, target)
        if spec is None or not spec.origin:
            return None

        # Block only if module is a direct child of the CWD
        try:
            cwd = Path.cwd().resolve()
            module_path = Path(spec.origin).resolve()
            if module_path.parent == cwd:
                raise ImportError(
                    f"Blocked import of {fullname} from current working directory "
                    "for security reasons. Use '-P' or set PYTHONSAFEPATH to prevent "
                    "Python from searching the current working directory."
                )
        except FileNotFoundError:
            # CWD was deleted; cannot determine safety, allow import
            pass

        return spec


# Install the finder only once
if not any(isinstance(f, NLTKSafeImportFinder) for f in sys.meta_path):
    sys.meta_path.insert(0, NLTKSafeImportFinder())

# Make the finder class available for testing
__all__ = ["NLTKSafeImportFinder"]
