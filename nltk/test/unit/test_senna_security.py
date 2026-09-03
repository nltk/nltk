"""Regression tests for the untrusted-search-path fix in the Senna wrapper.

``Senna.__init__`` accepted a *relative* ``senna_path`` (e.g. ".") and resolved
the executable against the current working directory. Because ``executable()``
returns a path that contains a separator (e.g. ``./senna-osx``),
``subprocess.Popen`` runs it directly from the CWD without consulting ``$PATH``,
so an attacker who can write a ``senna-<platform>`` file there would have it
executed -- running code from an untrusted location (CWE-829, an untrusted
search path, CWE-426/CWE-427).

Only an explicit *absolute* directory (or an absolute ``SENNA`` environment
variable) is now used; a relative ``senna_path`` no longer falls back to the CWD.
"""

import os
from platform import architecture, system
from types import SimpleNamespace

import pytest

import nltk.classify.senna as senna_mod
from nltk.classify.senna import Senna

# Every platform-specific binary name executable() may pick.
_SENNA_BINARIES = (
    "senna-linux64",
    "senna-linux32",
    "senna-win32.exe",
    "senna-osx",
    "senna",
)


def _this_platforms_binary():
    """The exact binary name ``Senna.executable`` selects on THIS platform, so a
    reassignment test plants the file the wrapper will actually look for."""
    os_name = system()
    if os_name == "Linux":
        return "senna-linux64" if architecture()[0] == "64bit" else "senna-linux32"
    if os_name == "Windows":
        return "senna-win32.exe"
    if os_name == "Darwin":
        return "senna-osx"
    return "senna"


def _plant_senna_binaries(directory):
    """Create an (executable) file for every candidate senna binary name."""
    os.makedirs(directory, exist_ok=True)
    for name in _SENNA_BINARIES:
        target = os.path.join(directory, name)
        with open(target, "wb"):
            pass
        os.chmod(target, 0o755)
    return directory


def test_cwd_senna_binary_is_not_picked_up(tmp_path, monkeypatch):
    """A senna-<platform> planted in the CWD must not be auto-selected."""
    _plant_senna_binaries(str(tmp_path))  # attacker-planted in the CWD
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SENNA", raising=False)

    with pytest.raises(LookupError):
        Senna(".", ["pos"])


def test_cwd_does_not_override_configured_senna(tmp_path, monkeypatch):
    """A CWD directory must not shadow an absolute SENNA environment variable."""
    cwd = tmp_path / "cwd"
    _plant_senna_binaries(str(cwd))  # attacker-planted in the CWD
    trusted = tmp_path / "trusted"
    _plant_senna_binaries(str(trusted))  # the configured (trusted) location
    monkeypatch.chdir(cwd)
    monkeypatch.setenv("SENNA", str(trusted))

    senna = Senna(".", ["pos"])
    assert os.path.realpath(senna._path) == os.path.realpath(
        str(trusted)
    ), "CWD directory overrode the trusted SENNA location"


def test_relative_senna_env_is_rejected(tmp_path, monkeypatch):
    """A relative SENNA environment variable must not be resolved against CWD."""
    _plant_senna_binaries(str(tmp_path))  # attacker-planted in the CWD
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SENNA", ".")

    with pytest.raises(LookupError):
        Senna(".", ["pos"])


def test_absolute_path_still_accepted(tmp_path, monkeypatch):
    """An explicit absolute directory is still used as-is."""
    abs_dir = _plant_senna_binaries(str(tmp_path / "senna"))
    monkeypatch.delenv("SENNA", raising=False)

    senna = Senna(abs_dir, ["pos"])
    assert os.path.realpath(senna._path) == os.path.realpath(abs_dir)


def test_absolute_path_without_executable_raises(tmp_path, monkeypatch):
    """An absolute senna_path with no senna binary fails fast (not deferred)."""
    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.delenv("SENNA", raising=False)

    with pytest.raises(LookupError):
        Senna(str(empty), ["pos"])


# --- Re-validation at invocation (path reassigned after construction) ---------
#
# ``__init__`` enforces an absolute senna_path, but ``self._path`` is a plain
# attribute; if it is reassigned to a relative value afterwards, ``executable()``
# returns a path with a separator (e.g. ``./senna-osx``) that ``subprocess.Popen``
# runs directly from the current working directory, so an attacker who can plant a
# ``senna-<platform>`` file there gets code execution (CWE-426/CWE-427). Weka
# re-validates its model path at ``_classify_many`` for exactly this reassignment
# case; ``tag_sents`` now re-asserts the absolute-path invariant the same way,
# refusing a CWD-relative executable BEFORE any process spawns.


@pytest.fixture
def _senna_popen_spy(monkeypatch):
    """Record argv without launching senna. ``senna.py`` does
    ``from subprocess import Popen``, so the name is patched on the module."""
    calls = []

    class _FakeProc:
        returncode = 0

        def communicate(self, *a, **k):
            return b"", b""

    def _fake_popen(cmd, *a, **k):
        calls.append(SimpleNamespace(argv=list(cmd), shell=k.get("shell", False)))
        return _FakeProc()

    monkeypatch.setattr(senna_mod, "Popen", _fake_popen)
    return calls


def _make_abs_senna(tmp_path, monkeypatch):
    """Construct a Senna pointed at a valid absolute install directory."""
    absdir = tmp_path / "senna-install"
    absdir.mkdir()
    binpath = absdir / _this_platforms_binary()
    binpath.write_bytes(b"")
    os.chmod(binpath, 0o755)
    monkeypatch.delenv("SENNA", raising=False)
    return Senna(str(absdir), ["pos"]), str(absdir)


@pytest.mark.parametrize("relative_path", [".", "." + os.sep, "senna-cwd", ""])
def test_relative_path_reassigned_after_construction_is_refused(
    tmp_path, monkeypatch, _senna_popen_spy, relative_path
):
    """Reassigning ``_path`` to a relative value must be refused at ``tag_sents``,
    before any spawn, even though a matching binary sits in the CWD."""
    senna, _absdir = _make_abs_senna(tmp_path, monkeypatch)

    # Attacker plants the platform binary in the CWD and reassigns the path.
    cwd = tmp_path / "attacker_cwd"
    cwd.mkdir()
    binname = _this_platforms_binary()
    (cwd / binname).write_bytes(b"")
    os.chmod(cwd / binname, 0o755)
    monkeypatch.chdir(cwd)

    senna._path = relative_path
    with pytest.raises(LookupError):
        senna.tag_sents([["hello", "world"]])
    assert _senna_popen_spy == [], "a CWD-relative senna binary reached the spawn"


def test_absolute_path_still_reaches_the_spawn_after_revalidation(
    tmp_path, monkeypatch, _senna_popen_spy
):
    """Benign control: a valid absolute install still reaches the (trapped) spawn
    with an ABSOLUTE argv[0] and no shell, so the re-validation is not over-broad."""
    senna, absdir = _make_abs_senna(tmp_path, monkeypatch)
    senna.tag_sents([["hi", "there"]])
    assert len(_senna_popen_spy) == 1
    argv = _senna_popen_spy[0].argv
    assert os.path.isabs(argv[0])
    assert argv[0] == os.path.join(senna._path.rstrip(os.sep), _this_platforms_binary())
    assert _senna_popen_spy[0].shell is False
    # The -path argument (senna's data dir) is the absolute install directory.
    assert argv[argv.index("-path") + 1] == senna._path
    assert os.path.isabs(argv[argv.index("-path") + 1])


# --- End-to-end with a REAL, executable senna-contract binary -----------------
#
# The upstream senna-<platform> binaries are 2011-era 32-bit executables that do
# not run on a current arm64 macOS, so a downloaded senna-osx could never prove
# the benign path actually executes here. Instead these tests drop a real,
# executable program that honours SENNA's stdin/stdout contract (one sentence per
# stdin line; one tab-separated ``word<TAB>tag`` line per token; a blank line
# between sentences) at a genuine absolute path and drive the WHOLE real code
# path: real ``subprocess.Popen``, real process, real output parsing. Nothing is
# mocked. The attacker copy additionally touches a marker file when executed, so
# the refusal test proves, with a genuinely runnable binary, that the CWD
# binary never ran.

POSIX_ONLY = pytest.mark.skipif(
    os.name != "posix",
    reason="the executable senna stub is a POSIX shell script",
)


def _write_real_senna(dirpath, marker=None):
    """Write a real, executable senna-contract program named for THIS platform.

    If *marker* is given, the program touches that path on execution, so a test
    can prove from its (non-)existence whether the binary actually ran.
    """
    os.makedirs(dirpath, exist_ok=True)
    lines = ["#!/bin/sh"]
    if marker is not None:
        # Quote to tolerate spaces; this fires only if the process is spawned.
        lines.append(': > "%s"' % marker)
    lines += [
        "while IFS= read -r line; do",
        '  [ -z "$line" ] && continue',
        "  for w in $line; do printf '%s\\tNNP\\n' \"$w\"; done",
        "  printf '\\n'",
        "done",
    ]
    binpath = os.path.join(dirpath, _this_platforms_binary())
    with open(binpath, "w") as fh:
        fh.write("\n".join(lines) + "\n")
    os.chmod(binpath, 0o755)
    return binpath


@POSIX_ONLY
def test_real_senna_binary_tags_end_to_end(tmp_path, monkeypatch):
    """Benign, fully real: an absolute install with a runnable senna-contract
    binary tags a sentence through the real subprocess and parser."""
    from nltk.tag import SennaTagger

    absdir = str(tmp_path / "senna-v3.0")
    _write_real_senna(absdir)
    monkeypatch.delenv("SENNA", raising=False)

    tagger = SennaTagger(absdir)
    tagged = tagger.tag("What is the airspeed ?".split())
    assert [w for w, _ in tagged] == ["What", "is", "the", "airspeed", "?"]
    assert all(tag == "NNP" for _, tag in tagged)  # the real binary's output


@POSIX_ONLY
def test_real_cwd_senna_binary_never_executes_when_path_reassigned(
    tmp_path, monkeypatch
):
    """Teeth with a REAL binary: a runnable senna-<platform> is planted in the CWD
    and ``_path`` is reassigned to ``.`` after construction. The planted binary is
    demonstrably executable (running it directly touches the marker), yet
    ``tag_sents`` raises before spawning, so the marker the binary would create
    never appears; the guard stops code execution, not just a missing file."""
    import subprocess

    from nltk.tag import SennaTagger

    # A valid absolute install so construction succeeds.
    absdir = str(tmp_path / "trusted")
    _write_real_senna(absdir)
    monkeypatch.delenv("SENNA", raising=False)
    tagger = SennaTagger(absdir)

    # Attacker plants a genuinely-runnable senna in the CWD that touches a marker.
    cwd = tmp_path / "attacker_cwd"
    marker = tmp_path / "senna_executed.marker"
    attacker_bin = _write_real_senna(str(cwd), marker=str(marker))
    monkeypatch.chdir(cwd)

    # Prove the planted binary really runs (would tag + create the marker).
    proof_marker = tmp_path / "proof.marker"
    proof_bin = _write_real_senna(str(tmp_path / "proof"), marker=str(proof_marker))
    subprocess.run([proof_bin], input=b"hello world\n", capture_output=True, check=True)
    assert proof_marker.exists(), "sanity: the stub is genuinely executable"

    # Now reassign to a relative path and confirm tag_sents refuses BEFORE exec.
    tagger._path = "." + os.sep
    assert os.path.isfile(attacker_bin)  # the CWD binary the guard must not run
    with pytest.raises(LookupError):
        tagger.tag_sents([["hello", "world"]])
    assert not marker.exists(), "the CWD senna binary was executed despite the guard"
