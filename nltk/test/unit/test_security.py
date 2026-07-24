"""
Unit tests for security-related patches and vulnerability regressions.
"""

import importlib
import os
import sys
import tempfile


def test_module_hijacking_prevention():
    """
    Simulate a search path attack by dropping a malicious module in the CWD,
    and ensure the system loads the safe installed module instead.
    """
    # Import nltk to ensure the sys.path mitigation is active
    import nltk

    with tempfile.TemporaryDirectory() as temp_dir:
        # 1. Setup the attacker payload
        malicious_module = os.path.join(temp_dir, "joblib.py")
        with open(malicious_module, "w") as f:
            f.write("hijacked = True\n")

        # 2. Simulate an application changing to the attacker's directory
        original_cwd = os.getcwd()
        os.chdir(temp_dir)

        try:
            # Clear joblib from the cache if it was already loaded by other tests,
            # forcing Python to search sys.path again.
            if "joblib" in sys.modules:
                del sys.modules["joblib"]

            # 3. Trigger the import (simulating parallelize_preprocess behavior)
            import joblib

            # 4. Verify the exploit failed
            assert (
                getattr(joblib, "hijacked", False) is False
            ), "Vulnerability: Loaded attacker module from CWD!"

        finally:
            # Restore the environment so we don't break subsequent tests
            os.chdir(original_cwd)
            if "joblib" in sys.modules:
                del sys.modules["joblib"]
