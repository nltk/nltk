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

import pytest

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
