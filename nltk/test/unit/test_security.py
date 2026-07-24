"""
Unit tests for security-related patches and vulnerability regressions.
"""

import os
import sys
import tempfile


def test_sys_path_restrictive_posture():
    """
    Verify CWE-427 mitigation: dynamic CWD ('') and explicit CWD should be deprioritized
    to the end of sys.path to enforce a restrictive module search policy.
    """
    # Import nltk to ensure __init__.py logic has run
    import nltk

    cwd = os.getcwd()

    # If the dynamic CWD is in the path, it must not be the first element
    if "" in sys.path:
        assert (
            sys.path.index("") > 0
        ), "Security Failure: Dynamic CWD ('') is at the front of sys.path"

    # If the explicit CWD is in the path, it must not be the first element
    if cwd in sys.path:
        assert (
            sys.path.index(cwd) > 0
        ), f"Security Failure: Explicit CWD ({cwd}) is at the front of sys.path"


def test_module_hijacking_prevention():
    """
    Simulate a CWE-427 attack by dropping a malicious module in the CWD,
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
            ), "CWE-427 Vulnerability: Loaded attacker module from CWD!"

        finally:
            # Restore the environment so we don't break subsequent tests
            os.chdir(original_cwd)
            if "joblib" in sys.modules:
                del sys.modules["joblib"]
