# Natural Language Toolkit: shared pytest fixtures for the pathsec sandbox tests
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Shared fixtures for the ``nltk.pathsec`` sandbox test suites.

Many security tests need the same setup: enforce pathsec against a single
throwaway data root, then either write inside it (which must succeed) or aim at a
path outside it (which must be refused). These fixtures centralize that setup so
each test file no longer repeats it.

``pytest`` discovers a ``conftest.py`` automatically, so any test module under
``nltk/test/unit`` can request these fixtures by name without importing anything.
"""

import os
import pathlib
import shutil
import tempfile
from collections import namedtuple

import pytest

import nltk.data
from nltk import pathsec


def make_home_dir(prefix):
    """A fresh directory under the real ``$HOME``, the one directory chain that
    is private on every CI runner, for a fixture the trust chain must be able
    to accept. The caller removes it.

    Deliberately NOT a temp dir, in both directions: on Linux the shared
    ``/tmp`` is world-writable, so nothing staged under it can ever clear the
    private-chain rule (a "clean" install there is refused before the planted
    weakness is even looked at); on macOS the per-user temp dir is private and
    is itself an allowed root (``/var/folders/...`` is mode 0700), so an attack
    target staged there would be (correctly) permitted and the test would not
    exercise the guard. ``$HOME`` behaves the same on both.
    """
    return tempfile.mkdtemp(prefix=prefix, dir=os.path.expanduser("~"))


def _make_outside_dir():
    """A fresh directory under the real ``$HOME`` that is guaranteed OUTSIDE
    every allowed pathsec root (see :func:`make_home_dir` for why not a temp
    dir)."""
    return pathlib.Path(make_home_dir(".nltk_sandbox_outside_"))


def _enforce_single_root(monkeypatch):
    """Turn ENFORCE on, restrict the allowed roots to one fresh data root, and
    invalidate the cached roots. Returns the data-root path. monkeypatch restores
    every mutated global at teardown."""
    # The root lives under $HOME, not the system temp dir: on a Linux runner
    # the temp dir is world-writable /tmp, so a tool install or model tree
    # staged inside a temp root could never pass the private-chain checks
    # (validate_tool_data_dir, resolve_trusted_executable) and every such
    # fixture had to escape to $HOME by hand. Under $HOME the root is a
    # private chain on every runner, and make_staging_dir() allocates the
    # fixtures inside it through pathsec. realpath folds an 8.3 short
    # component (a Windows runner's profile under RUNNER~1) to long form, so
    # an in-root path clears the short-name guard.
    data_root = os.path.realpath(make_home_dir(".nltk_sandbox_root_"))
    monkeypatch.setattr(pathsec, "ENFORCE", True)
    monkeypatch.setattr(nltk.data, "path", [data_root])
    monkeypatch.setattr(pathsec, "_ALLOWED_ROOTS_CACHE", None, raising=False)
    monkeypatch.setattr(pathsec, "_LAST_DATA_PATHS", None, raising=False)
    # staging_tempdir() memoises a process-global scratch dir; clear it so a dir
    # an earlier test allocated under the ambient root (still "valid" there) does
    # not leak in, and it is re-allocated under this enforced single root.
    monkeypatch.setattr(nltk.data, "_STAGING_TEMPDIR", None, raising=False)
    return data_root


@pytest.fixture
def sandbox(monkeypatch):
    """Enforce pathsec against a single throwaway data root and yield a fresh
    directory that is OUTSIDE every allowed root, which any patched file sink
    must refuse to read from / write to. The allowed data root and the outside
    dir are removed, and the working directory and every mutated pathsec global
    are restored, at teardown.
    """
    saved_cwd = os.getcwd()
    data_root = _enforce_single_root(monkeypatch)
    outside = _make_outside_dir()
    try:
        yield outside
    finally:
        os.chdir(saved_cwd)
        shutil.rmtree(outside, ignore_errors=True)
        # data_root also holds any staging dirs make_staging_dir created under it.
        shutil.rmtree(data_root, ignore_errors=True)


@pytest.fixture
def restricted_sandbox(monkeypatch):
    """Enforce pathsec against a single throwaway data root and yield that root
    (a path string). A write inside it succeeds; a caller-supplied path outside
    it must be refused. Use :func:`_make_outside_dir` (or the ``sandbox``
    fixture) for an out-of-root target.
    """
    data_root = _enforce_single_root(monkeypatch)
    try:
        yield data_root
    finally:
        shutil.rmtree(data_root, ignore_errors=True)


@pytest.fixture
def enforce_off(monkeypatch):
    """Force pathsec.ENFORCE off and invalidate the roots cache, so a functional
    read/write test on a temp-dir target is isolated from ambient or leaked
    ENFORCE state (a full test run may leave ENFORCE on, and on Linux a temp dir
    lives under world-writable /tmp, which is not an allowed root)."""
    monkeypatch.setattr(pathsec, "ENFORCE", False)
    monkeypatch.setattr(pathsec, "_ALLOWED_ROOTS_CACHE", None, raising=False)
    monkeypatch.setattr(pathsec, "_LAST_DATA_PATHS", None, raising=False)


# A namedtuple so a test can either unpack ``root, outside = pathsec_sandbox`` or
# read ``pathsec_sandbox.root`` / ``.outside``.
PathsecSandbox = namedtuple("PathsecSandbox", ["root", "outside"])


@pytest.fixture
def pathsec_sandbox(monkeypatch):
    """Enforce pathsec against a single throwaway data root and yield BOTH the
    trusted ``root`` (a ``pathlib.Path``; writes inside it succeed) and an
    out-of-sandbox ``outside`` dir (a ``pathlib.Path`` that must be refused), for
    a test that needs both at once. Use ``sandbox`` / ``restricted_sandbox`` when
    only one is needed. The result unpacks as ``root, outside`` too.
    """
    saved_cwd = os.getcwd()
    data_root = _enforce_single_root(monkeypatch)
    outside = _make_outside_dir()
    try:
        yield PathsecSandbox(root=pathlib.Path(data_root), outside=outside)
    finally:
        os.chdir(saved_cwd)
        shutil.rmtree(outside, ignore_errors=True)
        shutil.rmtree(data_root, ignore_errors=True)


@pytest.fixture
def trusted_java_stub():
    """A stub 'java' under $HOME, a private directory chain on every CI runner
    (a shared temp dir is not), so the trusted spawn accepts it as the JVM and a
    Popen spy can see what java() would have launched."""
    root = pathlib.Path(make_home_dir(".nltk_java_stub_"))
    stub = root / ("java.exe" if os.name == "nt" else "java")
    stub.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    stub.chmod(0o755)
    try:
        yield str(stub)
    finally:
        shutil.rmtree(root, ignore_errors=True)
