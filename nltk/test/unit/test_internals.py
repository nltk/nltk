"""Tests for nltk.internals binary discovery (untrusted-search-path hardening).

``find_binary`` must not return a current-working-directory-relative executable
when the caller did not supply an explicit ``path_to_bin``: such a path would be
run relative to the CWD, so a planted ``./<name>/<name>`` could hijack the tool
(CWE-426 / CWE-427). A trusted absolute match (env var / searchpath / ``which``)
or an explicit ``path_to_bin`` is still honored.
"""

import os
import stat

import pytest

from nltk.internals import find_binary

_NAME = "nltktestbin"  # unlikely to exist on PATH


def _make_exec(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/sh\ntrue\n")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


def test_find_binary_ignores_cwd_relative_when_no_path_to_bin(tmp_path, monkeypatch):
    """A planted ``./<name>/<name>`` must be ignored in favour of a trusted
    (absolute) searchpath match when no ``path_to_bin`` is given."""
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    _make_exec(cwd / _NAME / _NAME)  # attacker-planted ./<name>/<name>
    realdir = tmp_path / "realbin"
    _make_exec(realdir / _NAME)  # trusted, absolute location
    monkeypatch.chdir(cwd)

    result = find_binary(_NAME, searchpath=[str(realdir)], binary_names=[_NAME])
    assert os.path.isabs(result)
    assert os.path.realpath(result) == os.path.realpath(str(realdir / _NAME))


def test_find_binary_empty_path_to_bin_treated_as_none(tmp_path, monkeypatch):
    """An empty-string ``path_to_bin`` must not bypass the CWD-relative refusal."""
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    _make_exec(cwd / _NAME / _NAME)
    realdir = tmp_path / "realbin"
    _make_exec(realdir / _NAME)
    monkeypatch.chdir(cwd)

    result = find_binary(
        _NAME, path_to_bin="", searchpath=[str(realdir)], binary_names=[_NAME]
    )
    assert os.path.isabs(result)
    assert os.path.realpath(result) == os.path.realpath(str(realdir / _NAME))


def test_find_binary_refuses_cwd_only_executable(tmp_path, monkeypatch):
    """If the only match is a CWD-relative executable, the tool is reported as
    not found rather than executed."""
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    _make_exec(cwd / _NAME / _NAME)
    monkeypatch.chdir(cwd)

    with pytest.raises(LookupError):
        find_binary(
            _NAME, searchpath=[str(tmp_path / "nonexistent")], binary_names=[_NAME]
        )


def test_find_binary_honors_explicit_relative_path_to_bin(tmp_path, monkeypatch):
    """An explicit ``path_to_bin`` (even relative) is the caller's own choice and
    is still honored."""
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    _make_exec(cwd / "tools" / _NAME)
    monkeypatch.chdir(cwd)

    result = find_binary(
        _NAME, path_to_bin=os.path.join("tools", _NAME), binary_names=[_NAME]
    )
    assert os.path.basename(result) == _NAME


def test_find_binary_honors_explicit_relative_path_via_name(tmp_path, monkeypatch):
    """A relative path with a directory component passed via ``name`` (the
    documented "name or path" usage) is an explicit choice and is honored; only
    a *bare* name triggers the CWD-relative refusal."""
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    _make_exec(cwd / "tools" / _NAME)
    monkeypatch.chdir(cwd)

    result = find_binary(os.path.join("tools", _NAME), binary_names=[_NAME])
    assert os.path.basename(result) == _NAME
