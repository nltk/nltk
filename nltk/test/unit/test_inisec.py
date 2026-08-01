import importlib.util
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import mock

import pytest

# ---------------------------------------------------------------------------
# Existing coverage (moved from test_security.py)
# ---------------------------------------------------------------------------


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
        res = subprocess.run(
            [sys.executable, "victim.py"],
            cwd=d,
            env=os.environ.copy(),
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
        res = subprocess.run(
            [sys.executable, "victim.py"],
            cwd=d,
            env=os.environ.copy(),
            capture_output=True,
            text=True,
        )
        assert "HOST_HIJACK" not in res.stdout


def test_host_imports_of_non_vulnerable_modules_are_unaffected():
    """Host imports of non-vulnerable modules from CWD succeed."""
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
        env.pop("PYTHONSAFEPATH", None)
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
        env.pop("PYTHONSAFEPATH", None)
        res = subprocess.run(
            [sys.executable, "victim.py"],
            cwd=d,
            env=env,
            capture_output=True,
            text=True,
        )
        try:
            assert "DISABLED_HIJACK" in res.stdout
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
    """Installing the hook sets PYTHONSAFEPATH=1 for child interpreters."""
    from nltk import inisec

    with mock.patch.dict(os.environ, {}, clear=False):
        os.environ.pop("PYTHONSAFEPATH", None)
        inisec._install()
        assert os.environ.get("PYTHONSAFEPATH") == "1"


def test_pythonsafepath_does_not_override_host_choice():
    """NLTK must not override a PYTHONSAFEPATH value the host has already set."""
    from nltk import inisec

    with mock.patch.dict(os.environ, {"PYTHONSAFEPATH": "0"}, clear=False):
        inisec._install()
        assert os.environ.get("PYTHONSAFEPATH") == "0"


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Known residual limitation: fork-based joblib/loky workers inherit the "
        "parent's already-fixed sys.path and run on a fresh stack, so neither "
        "PYTHONSAFEPATH nor caller detection applies. Remedy: launch with -P / "
        "PYTHONSAFEPATH. If this starts passing, the limitation was closed and "
        "the xfail must be removed."
    ),
)
@pytest.mark.skipif(
    not importlib.util.find_spec("joblib"), reason="joblib not installed"
)
def test_worker_process_cwd_import_is_blocked():
    """Documents the fork-worker residual (expected to xfail)."""
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
    reason="PYTHONSAFEPATH was added in Python 3.11.",
)
def test_worker_process_is_protected_with_pythonsafepath():
    """With PYTHONSAFEPATH=1 in the launch env, the worker hijack is prevented."""
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


# ---------------------------------------------------------------------------
# New coverage for the in-project-venv false positive (issue #3730)
# ---------------------------------------------------------------------------


def _make_fake_venv(root: Path) -> Path:
    """Create a site-packages dir nested inside *root*, like an in-project venv."""
    site_packages = (
        root
        / ".venv"
        / "lib"
        / f"python{sys.version_info.major}.{sys.version_info.minor}"
        / "site-packages"
    )
    site_packages.mkdir(parents=True)
    return site_packages


def test_nested_site_packages_is_trusted_fast(tmp_path, monkeypatch):
    """
    Fast (no venv/network) proof of the #3730 fix: a module resolved from a
    site-packages directory nested inside the CWD is trusted, even when NLTK
    initiates the import.
    """
    from nltk import inisec

    d = tmp_path.resolve()
    site_packages = _make_fake_venv(d)
    (site_packages / "installed_dep.py").write_text("VALUE = 'ok'\n")

    monkeypatch.setattr(
        inisec, "_trusted_library_roots", lambda: frozenset({site_packages})
    )
    monkeypatch.chdir(d)
    monkeypatch.syspath_prepend(str(site_packages))
    monkeypatch.syspath_prepend("")

    finder = inisec.NLTKSafeImportFinder()
    monkeypatch.setattr(finder, "_is_import_from_nltk", lambda cwd: True)

    assert finder.find_spec("installed_dep", None) is None


def test_loose_cwd_module_still_blocked(tmp_path, monkeypatch):
    """A module loose in the CWD is still blocked when NLTK initiates it."""
    from nltk import inisec

    d = tmp_path.resolve()
    (d / "joblib.py").write_text("print('LOOSE')\n")

    monkeypatch.setattr(inisec, "_trusted_library_roots", lambda: frozenset())
    monkeypatch.chdir(d)
    monkeypatch.syspath_prepend(str(d))
    monkeypatch.syspath_prepend("")

    finder = inisec.NLTKSafeImportFinder()
    monkeypatch.setattr(finder, "_is_import_from_nltk", lambda cwd: True)

    with pytest.raises(ImportError):
        finder.find_spec("joblib", None)


def test_no_block_when_cwd_not_on_sys_path(tmp_path, monkeypatch):
    """No blocking when the CWD is not on sys.path, even for a loose module."""
    from nltk import inisec

    d = tmp_path.resolve()
    (d / "joblib.py").write_text("print('LOOSE')\n")

    monkeypatch.setattr(inisec, "_trusted_library_roots", lambda: frozenset())
    monkeypatch.chdir(d)
    monkeypatch.setattr(sys, "path", [p for p in sys.path if p not in ("", ".")])

    finder = inisec.NLTKSafeImportFinder()
    monkeypatch.setattr(finder, "_is_import_from_nltk", lambda cwd: True)

    assert finder.find_spec("joblib", None) is None


def test_namespace_package_in_cwd_is_blocked(tmp_path, monkeypatch):
    """
    A PEP-420 namespace package directory in the CWD resolves with origin=None but
    submodule_search_locations in the CWD, so it is a valid hijack vector and is
    blocked when NLTK initiates the import.
    """
    from nltk import inisec

    d = tmp_path.resolve()
    (d / "ns_pkg").mkdir()  # no __init__.py -> namespace package

    monkeypatch.setattr(inisec, "_trusted_library_roots", lambda: frozenset())
    monkeypatch.chdir(d)
    monkeypatch.syspath_prepend(str(d))
    monkeypatch.syspath_prepend("")

    finder = inisec.NLTKSafeImportFinder()
    monkeypatch.setattr(finder, "_is_import_from_nltk", lambda cwd: True)

    with pytest.raises(ImportError):
        finder.find_spec("ns_pkg", None)


def test_trusted_library_roots_contains_prefix():
    """The interpreter prefix must be reported as a trusted root."""
    from nltk import inisec

    inisec._trusted_library_roots.cache_clear()
    roots = inisec._trusted_library_roots()
    assert Path(sys.prefix).resolve() in roots
    inisec._trusted_library_roots.cache_clear()


@pytest.mark.skipif(
    os.environ.get("NLTK_RUN_VENV_E2E") != "1",
    reason="Slow/network end-to-end venv test; set NLTK_RUN_VENV_E2E=1 to run.",
)
def test_in_project_venv_end_to_end(tmp_path):
    """
    Full subprocess reproducer for #3730: installs NLTK into a real venv nested in
    the CWD, then runs a plain `import nltk` from the project root.
    """
    project = tmp_path / "demo"
    project.mkdir()
    venv = project / ".venv"

    if (
        subprocess.run(
            [sys.executable, "-m", "venv", str(venv)], capture_output=True, text=True
        ).returncode
        != 0
    ):
        pytest.skip("could not create venv")

    bin_dir = "Scripts" if os.name == "nt" else "bin"
    py = venv / bin_dir / ("python.exe" if os.name == "nt" else "python")

    nltk_root = str(Path(__file__).resolve().parents[3])
    install = subprocess.run(
        [str(py), "-m", "pip", "install", nltk_root],
        capture_output=True,
        text=True,
    )
    if install.returncode != 0:
        pytest.skip(f"could not install nltk into venv: {install.stderr[-500:]}")

    res = subprocess.run(
        [str(py), "-c", "import nltk; print('OK', nltk.__version__)"],
        cwd=project,
        capture_output=True,
        text=True,
    )
    try:
        assert res.returncode == 0
        assert "OK" in res.stdout
    except AssertionError:
        print("--- STDOUT ---\n", res.stdout)
        print("--- STDERR ---\n", res.stderr)
        raise
