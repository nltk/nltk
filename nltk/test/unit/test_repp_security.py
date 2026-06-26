"""Regression tests for the untrusted-search-path fix in ReppTokenizer (CWE-426).

``find_repptokenizer`` used ``os.path.exists(repp_dirname)`` to accept a directory
as-is. For a *relative* ``repp_dirname`` that resolves against the current working
directory and is checked *before* the ``REPP_TOKENIZER`` environment variable, so
an attacker who can write a ``./<name>/src/repp`` executable into the CWD could
have it run (the command path contains a separator, so ``subprocess`` executes it
directly) -- overriding a trusted ``REPP_TOKENIZER``.

Only an explicit *absolute* directory is now taken as-is; a relative name is
resolved through ``REPP_TOKENIZER``.
"""

import os
import pathlib

import pytest

from nltk.tokenize.repp import ReppTokenizer


def _make_repp_dir(path):
    (path / "src").mkdir(parents=True, exist_ok=True)
    (path / "erg").mkdir(parents=True, exist_ok=True)
    (path / "src" / "repp").write_bytes(b"")
    (path / "erg" / "repp.set").write_bytes(b"")
    return path


def test_relative_dirname_not_resolved_against_cwd(tmp_path, monkeypatch):
    """A relative repp_dirname matching a CWD directory must NOT be used."""
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    _make_repp_dir(cwd / "reppdir")  # attacker-planted in the CWD
    monkeypatch.chdir(cwd)
    monkeypatch.delenv("REPP_TOKENIZER", raising=False)

    with pytest.raises(LookupError):
        ReppTokenizer("reppdir")


def test_cwd_does_not_override_configured_repp_tokenizer(tmp_path, monkeypatch):
    """A CWD directory must not shadow a configured REPP_TOKENIZER."""
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    _make_repp_dir(cwd / "reppdir")  # attacker-planted in the CWD
    trusted = _make_repp_dir(tmp_path / "trusted")  # the configured location
    monkeypatch.chdir(cwd)
    monkeypatch.setenv("REPP_TOKENIZER", str(trusted))

    tok = ReppTokenizer("reppdir")
    assert os.path.realpath(tok.repp_dir) == os.path.realpath(
        str(trusted)
    ), "CWD directory overrode the trusted REPP_TOKENIZER"


def test_absolute_path_still_accepted(tmp_path, monkeypatch):
    """An explicit absolute directory is still used as-is, incl. as a Path."""
    abs_dir = _make_repp_dir(tmp_path / "absrepp")
    monkeypatch.delenv("REPP_TOKENIZER", raising=False)

    assert os.path.realpath(ReppTokenizer(str(abs_dir)).repp_dir) == os.path.realpath(
        str(abs_dir)
    )
    # a pathlib.Path is accepted too (normalised via os.fspath) and resolves to
    # the same directory.
    assert os.path.realpath(
        ReppTokenizer(pathlib.Path(abs_dir)).repp_dir
    ) == os.path.realpath(str(abs_dir))
