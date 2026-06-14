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

import pytest

from nltk.classify.senna import Senna

# Every platform-specific binary name executable() may pick.
_SENNA_BINARIES = (
    "senna-linux64",
    "senna-linux32",
    "senna-win32.exe",
    "senna-osx",
    "senna",
)


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
