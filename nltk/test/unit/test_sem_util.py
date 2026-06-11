import os

import pytest

from nltk.sem.util import demo


def test_demo_model_injection_safeguard(tmp_path, monkeypatch):
    """
    Ensure that passing a malicious payload with newlines to the --model flag
    raises an appropriate import/validation error instead of executing arbitrary code.
    """
    # 1. Setup a dynamic sentinel file that should NEVER be created
    sentinel_file = tmp_path / "vulnerable_trigger.txt"

    # 2. Replicate the exact newline injection payload from the vulnerability report
    # If executed via exec(), this will attempt to write the sentinel file.
    malicious_payload = f"os\nopen(r'{sentinel_file}', 'w').close()\nimport os"

    # 3. Use monkeypatch to simulate the command-line arguments:
    # python -m nltk.sem.util -m <payload> --no-eval
    monkeypatch.setattr("sys.argv", ["test", "-m", malicious_payload, "--no-eval"])

    # 4. Execute the demo entrypoint
    try:
        demo()
    except (SystemExit, ImportError, ValueError):
        # Downstream execution might exit or raise a ModuleNotFoundError/ValueError
        # because the module name is garbage. This is expected and safe.
        pass

    # 5. Assert the exploit failed to execute
    assert not sentinel_file.exists(), (
        "CRITICAL SECURITY REGRESSION: Code injection vulnerability re-introduced via exec() "
        "in nltk.sem.util.demo()"
    )
