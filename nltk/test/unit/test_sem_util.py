import pytest

from nltk.grammar import FeatStructNonterminal
from nltk.sem.util import demo, root_semrep
from nltk.tree import Tree


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


def test_root_semrep_missing_feature_raises_keyerror():
    """A tree whose root has no semantics feature should raise KeyError,
    not ``RuntimeError: No active exception to reraise``."""
    tree = Tree(FeatStructNonterminal("S[NUM='sg']"), ["John"])
    with pytest.raises(KeyError):
        root_semrep(tree)
