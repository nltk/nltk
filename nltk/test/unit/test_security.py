import importlib.util
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import mock

import pytest


def test_module_hijacking_prevention():
    """Ensure imports of vulnerable modules from CWD are blocked."""
    parent_paths = [p for p in sys.path if p and p != "."]

    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "joblib.py"), "w") as f:
            f.write("print('HIJACK_SUCCESS')\n")
        with open(os.path.join(d, "victim.py"), "w") as f:
            f.write(
                f"import sys\n"
                f"sys.path = {repr(parent_paths)} + sys.path\n"
                "from nltk.util import parallelize_preprocess\n"
                "list(parallelize_preprocess(str.upper, ['a'], processes=1))\n"
            )
        env = os.environ.copy()
        res = subprocess.run(
            [sys.executable, "victim.py"],
            cwd=d,
            env=env,
            capture_output=True,
            text=True,
        )
        assert "HIJACK_SUCCESS" not in res.stdout


def test_host_imports_of_vulnerable_modules_are_blocked():
    """CWD imports pulled in during `import nltk` are blocked."""
    parent_paths = [p for p in sys.path if p and p != "."]

    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "joblib.py"), "w") as f:
            f.write("print('HOST_HIJACK')\n")
        with open(os.path.join(d, "victim.py"), "w") as f:
            f.write(
                f"import sys\n"
                f"sys.path = {repr(parent_paths)} + sys.path\n"
                "import nltk\n"
                "import joblib\n"
                "print('HOST_SUCCESS')\n"
            )
        env = os.environ.copy()
        res = subprocess.run(
            [sys.executable, "victim.py"],
            cwd=d,
            env=env,
            capture_output=True,
            text=True,
        )
        assert "HOST_HIJACK" not in res.stdout


def test_host_imports_of_non_vulnerable_modules_are_unaffected():
    """Host imports of non‑vulnerable modules from CWD succeed."""
    parent_paths = [p for p in sys.path if p and p != "."]

    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "antigravity.py"), "w") as f:
            f.write("print('ANTIGRAVITY_HIJACK')\n")
        with open(os.path.join(d, "victim.py"), "w") as f:
            f.write(
                f"import sys\n"
                f"sys.path = [''] + {repr(parent_paths)} + sys.path\n"
                "import nltk\n"
                "import antigravity\n"
                "print('HOST_SUCCESS')\n"
            )
        env = os.environ.copy()
        env.pop("PYTHONSAFEPATH", None)  # this test needs the CWD searchable
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
    parent_paths = [p for p in sys.path if p and p != "."]

    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "joblib.py"), "w") as f:
            f.write("print('DISABLED_HIJACK')\n")
        with open(os.path.join(d, "victim.py"), "w") as f:
            f.write(
                f"import os\n"
                f"os.environ['NLTK_DISABLE_IMPORT_SECURITY'] = '1'\n"
                f"import sys\n"
                f"sys.path = [''] + {repr(parent_paths)} + sys.path\n"
                "import nltk\n"
                "import joblib\n"
                "print('SUCCESS')\n"
            )
        env = os.environ.copy()
        env.pop("PYTHONSAFEPATH", None)  # must be able to reach the CWD module
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


def test_pythonsafepath_is_propagated_for_child_interpreters():
    """
    Installing the hook must set PYTHONSAFEPATH=1 so freshly started worker
    interpreters (spawn/forkserver) inherit interpreter-level CWD isolation.
    """
    from nltk import inisec

    with mock.patch.dict(os.environ, {}, clear=False):
        os.environ.pop("PYTHONSAFEPATH", None)
        inisec._install()
        assert os.environ.get("PYTHONSAFEPATH") == "1"


def test_pythonsafepath_does_not_override_host_choice():
    """
    NLTK must not override a PYTHONSAFEPATH value the host has already set.
    """
    from nltk import inisec

    with mock.patch.dict(os.environ, {"PYTHONSAFEPATH": "0"}, clear=False):
        inisec._install()
        assert os.environ.get("PYTHONSAFEPATH") == "0"


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Known residual limitation: fork-based joblib/loky workers inherit the "
        "parent's already-fixed sys.path and run on a fresh stack, so neither "
        "PYTHONSAFEPATH nor caller detection applies. Closing this in-library "
        "would require globally mutating the parent's sys.path, which this "
        "design deliberately avoids. Remedy: launch with -P / PYTHONSAFEPATH. "
        "If this test starts passing, the limitation was closed and the xfail "
        "must be removed."
    ),
)
@pytest.mark.skipif(
    not importlib.util.find_spec("joblib"), reason="joblib not installed"
)
def test_worker_process_cwd_import_is_blocked():
    """
    Documents the fork-worker residual: a module dropped in the CWD is imported
    by a joblib/loky worker because the worker's fresh stack has no NLTK frame
    and its inherited sys.path still contains the CWD. Expected to xfail under
    the current in-library-only design.
    """
    parent_paths = [p for p in sys.path if p and p != "."]

    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "joblib_victim.py"), "w") as f:
            f.write("print('WORKER_HIJACK')\n")
        with open(os.path.join(d, "victim.py"), "w") as f:
            f.write(
                f"import sys\n"
                f"sys.path = {repr(parent_paths)} + sys.path\n"
                "import nltk\n"
                "from joblib import Parallel, delayed\n"
                "\n"
                "def work(_):\n"
                "    try:\n"
                "        import joblib_victim\n"
                "        return 'IMPORTED'\n"
                "    except ImportError:\n"
                "        return 'BLOCKED'\n"
                "\n"
                "if __name__ == '__main__':\n"
                "    out = Parallel(n_jobs=2)(delayed(work)(i) for i in range(2))\n"
                "    print('RESULTS', out)\n"
            )
        env = os.environ.copy()
        # Deliberately do NOT set PYTHONSAFEPATH here: this test characterises
        # the residual that exists WITHOUT the recommended launch-time remedy.
        env.pop("PYTHONSAFEPATH", None)
        res = subprocess.run(
            [sys.executable, "victim.py"],
            cwd=d,
            env=env,
            capture_output=True,
            text=True,
        )
        assert "WORKER_HIJACK" not in res.stdout
        assert "IMPORTED" not in res.stdout


@pytest.mark.skipif(
    sys.version_info < (3, 11),
    reason="PYTHONSAFEPATH was added in Python 3.11; on earlier versions it is "
    "silently ignored, so this launch-time remedy does not apply.",
)
def test_worker_process_is_protected_with_pythonsafepath():
    """
    Confirms the recommended remedy works: with PYTHONSAFEPATH=1 in the launch
    environment, worker interpreters omit the CWD and the hijack is prevented.
    Requires Python 3.11+, where PYTHONSAFEPATH exists.
    """
    if not importlib.util.find_spec("joblib"):
        pytest.skip("joblib not installed")

    parent_paths = [p for p in sys.path if p and p != "."]

    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "joblib_victim.py"), "w") as f:
            f.write("print('WORKER_HIJACK')\n")
        with open(os.path.join(d, "victim.py"), "w") as f:
            f.write(
                f"import sys\n"
                f"sys.path = {repr(parent_paths)} + sys.path\n"
                "import nltk\n"
                "from joblib import Parallel, delayed\n"
                "\n"
                "def work(_):\n"
                "    try:\n"
                "        import joblib_victim\n"
                "        return 'IMPORTED'\n"
                "    except ImportError:\n"
                "        return 'BLOCKED'\n"
                "\n"
                "if __name__ == '__main__':\n"
                "    out = Parallel(n_jobs=2)(delayed(work)(i) for i in range(2))\n"
                "    print('RESULTS', out)\n"
            )
        env = os.environ.copy()
        env["PYTHONSAFEPATH"] = "1"
        res = subprocess.run(
            [sys.executable, "victim.py"],
            cwd=d,
            env=env,
            capture_output=True,
            text=True,
        )
        assert "WORKER_HIJACK" not in res.stdout


def test_wordnet_app_reference_decode_rejects_wrong_types():
    """
    nltk.app.wordnet_app.Reference.decode() unpickles attacker-controlled,
    base64-encoded data straight from the wordnet browser's lookup_ URLs via
    RestrictedUnpickler. Every malformed input must surface as ValueError,
    since that's the only exception type the lookup_ route in do_GET catches.
    """
    import base64
    import pickle

    from nltk.app.wordnet_app import Reference

    good = base64.urlsafe_b64encode(pickle.dumps(("dog", {}), -1)).decode()
    ref = Reference.decode(good)
    assert ref.word == "dog"
    assert ref.synset_relations == {}

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

    for bad_string in ["not valid base64!!!", "", "====", "aGVsbG8="]:
        try:
            Reference.decode(bad_string)
            raise AssertionError(f"Reference.decode should reject {bad_string!r}")
        except ValueError:
            pass
