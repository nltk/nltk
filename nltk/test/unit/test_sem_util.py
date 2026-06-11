from nltk.sem.util import demo


def test_demo_model_injection_safeguard(tmp_path, monkeypatch):
    """
    Ensure that passing a malicious payload with newlines to the --model flag
    raises an appropriate error instead of executing arbitrary code.
    """
    sentinel_file = tmp_path / "vulnerable_trigger.txt"
    malicious_payload = f"os\nopen(r'{sentinel_file}', 'w').close()\nimport os"

    monkeypatch.setattr("sys.argv", ["test", "-m", malicious_payload, "--no-eval"])

    try:
        demo()
    except SystemExit:
        pass

    assert not sentinel_file.exists(), (
        "CRITICAL SECURITY REGRESSION: Code injection vulnerability re-introduced "
        "in nltk.sem.util.demo()"
    )
