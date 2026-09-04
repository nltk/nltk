"""Regression tests for the untrusted-search-path fix in the Boxer wrapper.

``Boxer`` resolves its external ``candc`` / ``boxer`` executables with
``nltk.internals.find_binary`` and then runs them with ``subprocess.Popen``.
``find_binary`` also matches a binary relative to the current working directory:

* a relative ``bin_dir`` (e.g. ".") yields ``./candc`` (a path with a separator),
  and
* even the default ``bin_dir=None`` matches a ``candc/candc`` directory in the
  CWD (``find_file_iter`` joins the name with itself).

Either way the resolved path contains a separator, so ``Popen`` runs it directly
from the CWD without consulting ``$PATH`` -- an attacker who can plant a
``candc``/``boxer`` file there gets code execution (CWE-426/CWE-427).

The wrapper now requires the resolved binary to be an *absolute* path, so a
CWD-relative result is refused. An absolute ``bin_dir`` (or ``CANDC`` env var, or
a ``$PATH`` lookup) keeps working.
"""

import os
import shutil
import subprocess
import tempfile
from types import SimpleNamespace

import pytest

import nltk.data
from nltk import pathsec
from nltk.sem.boxer import Boxer

_BIN_NAMES = ("candc", "boxer")


def _plant_binaries(directory):
    """Create an (executable) file for candc and boxer in *directory*."""
    os.makedirs(directory, exist_ok=True)
    for name in _BIN_NAMES:
        target = os.path.join(directory, name)
        with open(target, "wb"):
            pass
        os.chmod(target, 0o755)
    return directory


def test_relative_bin_dir_is_rejected(tmp_path, monkeypatch):
    """A relative bin_dir resolving the binary in the CWD must be refused."""
    _plant_binaries(str(tmp_path))  # ./candc, ./boxer attacker-planted
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("CANDC", raising=False)

    with pytest.raises(LookupError):
        Boxer(bin_dir=".")


def test_cwd_nested_dir_with_default_bin_dir_is_rejected(tmp_path, monkeypatch):
    """The default bin_dir=None must not pick up a ./<name>/<name> in the CWD."""
    # find_binary("candc", path_to_bin=None) joins the name with itself, so a
    # CWD directory "<name>" containing an executable "<name>" would be run.
    # Plant both so an unfixed wrapper would resolve *both* binaries and succeed.
    for name in _BIN_NAMES:
        nested = os.path.join(str(tmp_path), name, name)
        os.makedirs(os.path.dirname(nested), exist_ok=True)
        with open(nested, "wb"):
            pass
        os.chmod(nested, 0o755)
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("CANDC", raising=False)

    with pytest.raises(LookupError):
        Boxer()


def test_cwd_does_not_override_configured_candc(tmp_path, monkeypatch):
    """A CWD binary must not shadow an absolute CANDC environment variable."""
    _plant_binaries(str(tmp_path / "cwd"))  # attacker-planted in the CWD
    trusted = _plant_binaries(str(tmp_path / "trusted"))  # configured location
    monkeypatch.chdir(tmp_path / "cwd")
    monkeypatch.setenv("CANDC", trusted)

    boxer = Boxer(bin_dir=".")
    assert os.path.realpath(boxer._candc_bin) == os.path.realpath(
        os.path.join(trusted, "candc")
    ), "CWD binary overrode the trusted CANDC location"


def test_absolute_bin_dir_is_accepted(tmp_path, monkeypatch):
    """An explicit absolute bin_dir is still used as-is."""
    abs_dir = _plant_binaries(str(tmp_path / "candc-1.00"))
    monkeypatch.delenv("CANDC", raising=False)

    boxer = Boxer(bin_dir=abs_dir)
    assert os.path.isabs(boxer._candc_bin)
    assert os.path.realpath(boxer._candc_bin) == os.path.realpath(
        os.path.join(abs_dir, "candc")
    )


def test_boxer_call_uses_argv_list_never_shell(monkeypatch):
    """``Boxer._call`` routes through ``pathsec.spawn_trusted`` and builds
    ``[binary] + args`` as an argv list with NO shell, so a metacharacter argument
    reaches the process as a single literal element, never a shell token. Under the
    strict trust policy the binary must be a real file on a trusted path, so it is
    staged under a private data root (not the shared temp, which is refused)."""
    import nltk.data as nltk_data
    import nltk.pathsec as ps

    try:
        base = nltk_data.make_staging_dir(prefix="boxer_test_", cleanup=True)
    except PermissionError as exc:  # pragma: no cover - env-dependent
        pytest.skip(f"no writable in-sandbox NLTK data root: {exc}")
    binary = os.path.join(base, "candc")
    with open(binary, "w") as handle:
        handle.write("#!/bin/sh\nexit 0\n")
    os.chmod(binary, 0o755)

    hostile_args = ["--models", "; touch /tmp/pwned", "$(id)", "a\nb"]
    captured = {}

    class _FakeProc:
        returncode = 0

        def communicate(self, *a, **k):
            return b"", b""

    def _fake_popen(cmd, *a, **k):
        captured["argv"] = list(cmd)
        captured["shell"] = k.get("shell", False)
        return _FakeProc()

    monkeypatch.setattr(ps.subprocess, "Popen", _fake_popen)

    boxer = Boxer.__new__(Boxer)
    boxer._call("some stdin input", binary, args=hostile_args)

    assert captured["shell"] is False
    assert captured["argv"][0] == os.path.realpath(binary)  # resolved trusted path
    for tok in hostile_args:
        assert tok in captured["argv"]  # literal, not shell-interpreted


def test_boxer_scratch_file_staged_in_data_root(monkeypatch):
    """The scratch input handed to boxer must be staged inside an allowed
    nltk.data root, never the shared system temp dir (world writable and not a
    pathsec root; CWE-377/CWE-378).

    Teeth: an unhardened wrapper calls ``tempfile.mkstemp`` with no ``dir=``, so
    the file lands in the system temp dir and the containment check below fails.
    This needs neither the ``boxer`` nor the ``candc`` binary: ``_call`` is faked.
    """
    # Stage the data root under $HOME so it is inside the pathsec sandbox on
    # every OS; the system temp dir is deliberately not an allowed data root.
    home = os.path.expanduser("~")
    root = tempfile.mkdtemp(prefix="nltk_boxer_test_", dir=home)
    monkeypatch.setattr(nltk.data, "path", [root, *nltk.data.path])

    boxer = Boxer.__new__(Boxer)
    boxer._resolve = True
    boxer._elimeq = False
    boxer._boxer_bin = os.path.join(root, "boxer")  # never executed; _call is faked

    captured = {}

    def fake_call(input_str, binary, args=(), verbose=False):
        temp_path = args[args.index("--input") + 1]
        captured["path"] = temp_path
        with open(temp_path, encoding="utf-8") as handle:
            captured["contents"] = handle.read()
        return b""

    monkeypatch.setattr(boxer, "_call", fake_call)
    try:
        boxer._call_boxer(b"ccg(1, t).")

        staged = os.path.realpath(captured["path"])
        assert staged.startswith(
            os.path.realpath(root) + os.sep
        ), "boxer scratch file was staged outside the nltk.data root"
        # Exercise the guard itself: the staged path validates as in-sandbox.
        pathsec.validate_path(captured["path"], required_root=root)
        assert captured["contents"] == "ccg(1, t)."
    finally:
        shutil.rmtree(root, ignore_errors=True)


# --- candc structured-input injection guard (integrated from #3850) ------------
# ``Boxer._call_candc`` builds a line-oriented candc input where ``<META>'id'``
# marks a discourse boundary. A control character or quote in a discourse id, or
# an input line that itself starts with ``<META>``, would inject or misroute those
# boundaries. The guard runs BEFORE the spawn.


def _candc_boxer(spy):
    boxer = Boxer.__new__(Boxer)
    boxer._candc_models_path = "/models"
    boxer._candc_bin = "/nonexistent/candc"  # never reached for a refused input
    boxer._call = spy
    return boxer


@pytest.mark.parametrize(
    "discourse_id",
    ["a\nb", "a\rb", "a\x00b", "id'quote", 'id"dquote', "a\x0bb", "tab\tid"],
)
def test_candc_rejects_hostile_discourse_id(discourse_id):
    called = []
    boxer = _candc_boxer(lambda *a, **k: called.append(a) or ("", 0))
    with pytest.raises(ValueError):
        boxer._call_candc([["hello"]], [discourse_id], question=False)
    assert called == [], "a hostile discourse id reached the candc spawn"


@pytest.mark.parametrize(
    "line",
    [
        "line\nwith newline",
        "line\rwith cr",
        "line\x00nul",
        "ctrl\x0bchar",
        "<META>'injected-boundary'",  # a line masquerading as a discourse marker
    ],
)
def test_candc_rejects_hostile_input_line(line):
    called = []
    boxer = _candc_boxer(lambda *a, **k: called.append(a) or ("", 0))
    with pytest.raises(ValueError):
        boxer._call_candc([["ok first line", line]], ["0"], question=False)
    assert called == [], "a hostile candc input line reached the spawn"


def test_candc_benign_input_reaches_call_with_meta_boundary():
    """Benign control: a normal discourse reaches the (trapped) spawn, with the
    ``<META>'id'`` boundary and the input lines present and unmodified."""
    captured = {}

    def spy(input_str, binary, args, verbose):
        captured["input"] = input_str
        return ""

    boxer = _candc_boxer(spy)
    boxer._call_candc([["hello world", "second line"]], ["disc1"], question=False)
    assert "<META>'disc1'" in captured["input"]
    assert "hello world" in captured["input"]
    assert "second line" in captured["input"]
    # A tab is ordinary whitespace, allowed inside an input line.
    boxer._call_candc([["a\ttabbed\tline"]], ["0"], question=False)
    assert "a\ttabbed\tline" in captured["input"]
