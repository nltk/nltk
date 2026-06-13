"""Regression tests for the untrusted-search-path fix in MaltParser (CWE-426).

``find_maltparser`` used ``os.path.exists(parser_dirname)`` to accept a directory
as-is. For a *relative* ``parser_dirname`` (as NLTK's docs use) that resolves
against the current working directory and is checked *before* the ``MALT_PARSER``
environment variable, so an attacker who can write a ``maltparser-*/`` directory
into the CWD could place its jars on the Java classpath -- overriding a trusted
``MALT_PARSER`` -- and have ``org.maltparser.Malt`` executed (RCE).

Only an explicit *absolute* directory is now taken as-is; a relative name is
resolved through ``MALT_PARSER``.
"""

import os
import pathlib

import pytest

from nltk.parse.malt import find_maltparser

# The names find_maltparser asserts must be present in the directory.
_MALT_JARS = ["log4j.jar", "libsvm.jar", "liblinear-1.8.jar", "maltparser-1.9.2.jar"]


def _make_malt_dir(path):
    path.mkdir(parents=True, exist_ok=True)
    for jar in _MALT_JARS:
        (path / jar).write_bytes(b"")
    return path


def test_relative_dirname_not_resolved_against_cwd(tmp_path, monkeypatch):
    """A relative parser_dirname matching a CWD directory must NOT be used."""
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    _make_malt_dir(cwd / "maltparser-1.9.2")  # attacker-planted in the CWD
    monkeypatch.chdir(cwd)
    monkeypatch.delenv("MALT_PARSER", raising=False)

    # With no MALT_PARSER configured, the relative name must not fall back to the
    # current working directory; discovery fails instead of silently using it.
    with pytest.raises(LookupError):
        find_maltparser("maltparser-1.9.2")


def test_cwd_does_not_override_configured_malt_parser(tmp_path, monkeypatch):
    """A CWD directory must not shadow a configured MALT_PARSER."""
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    _make_malt_dir(cwd / "maltparser-1.9.2")  # attacker-planted in the CWD
    trusted = _make_malt_dir(tmp_path / "trusted")  # the configured location
    monkeypatch.chdir(cwd)
    monkeypatch.setenv("MALT_PARSER", str(trusted))

    jars = find_maltparser("maltparser-1.9.2")
    chosen = os.path.realpath(os.path.dirname(jars[0]))
    assert chosen == os.path.realpath(
        str(trusted)
    ), "CWD directory overrode the trusted MALT_PARSER"


def test_absolute_path_still_accepted(tmp_path, monkeypatch):
    """An explicit absolute directory is still used as-is."""
    abs_dir = _make_malt_dir(tmp_path / "absmalt")
    monkeypatch.delenv("MALT_PARSER", raising=False)

    jars = find_maltparser(str(abs_dir))
    chosen = os.path.realpath(os.path.dirname(jars[0]))
    assert chosen == os.path.realpath(str(abs_dir))


def test_pathlike_argument_is_handled(tmp_path, monkeypatch):
    """A pathlib.Path argument is accepted; a relative one fails cleanly."""
    abs_dir = _make_malt_dir(tmp_path / "absmalt")
    monkeypatch.delenv("MALT_PARSER", raising=False)
    # An absolute Path is accepted (normalised via os.fspath).
    assert find_maltparser(pathlib.Path(abs_dir))
    # A relative Path with no MALT_PARSER raises a clean LookupError -- not an
    # AssertionError from find_dir()'s str check, and not a CWD pickup.
    monkeypatch.chdir(tmp_path)
    with pytest.raises(LookupError):
        find_maltparser(pathlib.Path("not-a-configured-malt-dir"))
