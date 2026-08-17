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

import pytest

import nltk.data
from nltk import pathsec


def _make_outside_dir():
    """A fresh directory under the real ``$HOME`` that is guaranteed OUTSIDE
    every allowed pathsec root.

    Deliberately NOT a temp dir: a *private* per-user system temp dir is itself
    an allowed root on macOS (``/var/folders/...`` is mode 0700), so an attack
    target staged there would be (correctly) permitted and the test would not
    exercise the guard.
    """
    return pathlib.Path(
        tempfile.mkdtemp(prefix=".nltk_sandbox_outside_", dir=str(pathlib.Path.home()))
    )


def _enforce_single_root(monkeypatch):
    """Turn ENFORCE on, restrict the allowed roots to one fresh data root, and
    invalidate the cached roots. Returns the data-root path. monkeypatch restores
    every mutated global at teardown."""
    data_root = tempfile.mkdtemp(prefix="nltk_sandbox_root_")
    monkeypatch.setattr(pathsec, "ENFORCE", True)
    monkeypatch.setattr(nltk.data, "path", [data_root])
    monkeypatch.setattr(pathsec, "_ALLOWED_ROOTS_CACHE", None, raising=False)
    monkeypatch.setattr(pathsec, "_LAST_DATA_PATHS", None, raising=False)
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
