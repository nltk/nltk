import importlib.util
import os
import subprocess
import sys
import tempfile

import pytest


def test_module_hijacking_prevention():
    """Ensure imports of vulnerable modules from CWD are blocked."""
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "joblib.py"), "w") as f:
            f.write("print('HIJACK_SUCCESS')\n")
        with open(os.path.join(d, "victim.py"), "w") as f:
            f.write(
                "from nltk.util import parallelize_preprocess\n"
                "list(parallelize_preprocess(str.upper, ['a'], processes=1))\n"
            )
        env = os.environ.copy()
        repo_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..")
        )
        env["PYTHONPATH"] = repo_root + (
            os.pathsep + env["PYTHONPATH"] if "PYTHONPATH" in env else ""
        )
        res = subprocess.run(
            [sys.executable, "victim.py"],
            cwd=d,
            env=env,
            capture_output=True,
            text=True,
        )
        try:
            assert "HIJACK_SUCCESS" not in res.stdout
            assert res.returncode != 0
            assert (
                "Blocked import of joblib from current working directory" in res.stderr
            )
            assert "-P" in res.stderr or "PYTHONSAFEPATH" in res.stderr
        except AssertionError:
            print("--- STDOUT ---\n", res.stdout)
            print("--- STDERR ---\n", res.stderr)
            raise


def test_host_imports_of_vulnerable_modules_are_blocked():
    """Host imports of vulnerable modules from CWD are blocked."""
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "joblib.py"), "w") as f:
            f.write("print('HOST_HIJACK')\n")
        with open(os.path.join(d, "victim.py"), "w") as f:
            f.write("import nltk\n" "import joblib\n" "print('HOST_SUCCESS')\n")
        env = os.environ.copy()
        repo_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..")
        )
        env["PYTHONPATH"] = repo_root + (
            os.pathsep + env["PYTHONPATH"] if "PYTHONPATH" in env else ""
        )
        res = subprocess.run(
            [sys.executable, "victim.py"],
            cwd=d,
            env=env,
            capture_output=True,
            text=True,
        )
        try:
            assert "HOST_HIJACK" not in res.stdout
            assert res.returncode != 0
            assert "Blocked import of joblib" in res.stderr
        except AssertionError:
            print("--- STDOUT ---\n", res.stdout)
            print("--- STDERR ---\n", res.stderr)
            raise


def test_host_imports_of_non_vulnerable_modules_are_unaffected():
    """Host imports of non‑vulnerable modules from CWD succeed."""
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "antigravity.py"), "w") as f:
            f.write("print('ANTIGRAVITY_HIJACK')\n")
        with open(os.path.join(d, "victim.py"), "w") as f:
            f.write("import nltk\n" "import antigravity\n" "print('HOST_SUCCESS')\n")
        env = os.environ.copy()
        repo_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..")
        )
        env["PYTHONPATH"] = repo_root + (
            os.pathsep + env["PYTHONPATH"] if "PYTHONPATH" in env else ""
        )
        res = subprocess.run(
            [sys.executable, "victim.py"],
            cwd=d,
            env=env,
            capture_output=True,
            text=True,
        )
        try:
            assert res.returncode == 0
            assert "ANTIGRAVITY_HIJACK" in res.stdout
            assert "HOST_SUCCESS" in res.stdout
        except AssertionError:
            print("--- STDOUT ---\n", res.stdout)
            print("--- STDERR ---\n", res.stderr)
            raise


def test_disable_flag():
    """Ensure setting NLTK_DISABLE_IMPORT_SECURITY=1 disables the hook."""
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "joblib.py"), "w") as f:
            f.write("print('DISABLED_HIJACK')\n")
        with open(os.path.join(d, "victim.py"), "w") as f:
            f.write(
                "import os\n"
                "os.environ['NLTK_DISABLE_IMPORT_SECURITY'] = '1'\n"
                "import nltk\n"
                "import joblib\n"
                "print('SUCCESS')\n"
            )
        env = os.environ.copy()
        repo_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..")
        )
        env["PYTHONPATH"] = repo_root + (
            os.pathsep + env["PYTHONPATH"] if "PYTHONPATH" in env else ""
        )
        res = subprocess.run(
            [sys.executable, "victim.py"],
            cwd=d,
            env=env,
            capture_output=True,
            text=True,
        )
        try:
            assert (
                "DISABLED_HIJACK" in res.stdout
            ), "Malicious module should be loaded when hook is disabled"
        except AssertionError:
            print("--- STDOUT ---\n", res.stdout)
            print("--- STDERR ---\n", res.stderr)
            raise


@pytest.mark.skipif(
    not importlib.util.find_spec("joblib"), reason="joblib not installed"
)
def test_legitimate_import_from_site_packages():
    import joblib

    assert joblib.__file__ is not None


def test_wordnet_app_reference_decode_rejects_wrong_types():
    """
    nltk.app.wordnet_app.Reference.decode() unpickles attacker-controlled,
    base64-encoded data straight from the wordnet browser's lookup_ URLs via
    RestrictedUnpickler. RestrictedUnpickler blocks class/function
    reconstruction, but it does not guarantee the *type* or *shape* of what
    it returns: pickle's built-in list/dict/int/etc. opcodes never go
    through the blocked path. Without validation, a single crafted
    lookup_<pickle> URL crashed the server, either directly (e.g. decoding
    to an int instead of a str crashed word.split(",") in
    page_from_reference()) or downstream (e.g. a synset_relations dict with
    non-set values crashed toggle_synset_relation()'s .add()/.remove()).
    Every such failure must surface as ValueError, since that's the only
    exception type the lookup_ route in do_GET catches.
    """
    import base64
    import pickle

    from nltk.app.wordnet_app import Reference

    # A legitimate reference still round-trips correctly.
    good = base64.urlsafe_b64encode(pickle.dumps(("dog", {}), -1)).decode()
    ref = Reference.decode(good)
    assert ref.word == "dog"
    assert ref.synset_relations == {}

    # Malformed references must be rejected here, rather than accepted and
    # left to crash downstream code. Covers: wrong type for word; wrong type
    # for synset_relations itself; a synset_relations dict whose keys or
    # values are the wrong type (including frozenset, which looks like a
    # valid set but lacks the .add()/.remove() that toggle_synset_relation()
    # needs, so it must be rejected too, not just non-set types); and
    # payloads that don't even unpack to a (word, synset_relations) pair (a
    # bare int isn't iterable at all; a 1-tuple/3-tuple is the wrong arity).
    bad_payloads = [
        (42, {}),
        ([[[1]]], {}),
        (None, {}),
        ("dog", []),
        ("dog", {"dog.n.01": ["not", "a", "set"]}),
        ("dog", {"dog.n.01": frozenset()}),
        ("dog", {42: {"hypernym"}}),
        42,
        ("dog",),
        ("dog", {}, "extra"),
    ]
    for bad_payload in bad_payloads:
        bad = base64.urlsafe_b64encode(pickle.dumps(bad_payload, -1)).decode()
        try:
            Reference.decode(bad)
            raise AssertionError(f"Reference.decode should reject {bad_payload!r}")
        except ValueError:
            pass

    # Also covers input that isn't valid base64/pickle data at all.
    for bad_string in ["not valid base64!!!", "", "====", "aGVsbG8="]:
        try:
            Reference.decode(bad_string)
            raise AssertionError(f"Reference.decode should reject {bad_string!r}")
        except ValueError:
            pass
