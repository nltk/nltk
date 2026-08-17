"""
Regression tests for the file-write hardening in ``nltk.classify.weka``
(GHSA-8mgp-746c-j5xp).

``ARFF_Formatter.write`` opened a caller-supplied ``outfile`` path with a bare
``open()``, so ARFF data could be written to any path outside the allowed NLTK
data roots. The write is now routed through the ``nltk.pathsec`` sandbox, which
refuses an out-of-sandbox destination before any bytes are written.

The "outside" target is a fresh directory under the real ``$HOME``; never a temp
dir, because the private system temp directory is itself an allowed pathsec root
on macOS, which would make a temp target a false "outside".
"""

import inspect
import os
import shutil
import tempfile
from pathlib import Path

import pytest

import nltk.data
import nltk.pathsec as pathsec


@pytest.fixture
def restricted_sandbox():
    """Restrict pathsec's allowed roots to one throwaway data dir with
    ``ENFORCE`` on, restoring every mutated global afterwards."""
    saved_enforce = pathsec.ENFORCE
    saved_path = list(nltk.data.path)
    saved_cache = pathsec._ALLOWED_ROOTS_CACHE
    saved_last = pathsec._LAST_DATA_PATHS
    data_root = tempfile.mkdtemp()
    try:
        pathsec.ENFORCE = True
        nltk.data.path[:] = [data_root]
        pathsec._ALLOWED_ROOTS_CACHE = None
        pathsec._LAST_DATA_PATHS = None
        yield data_root
    finally:
        pathsec.ENFORCE = saved_enforce
        nltk.data.path[:] = saved_path
        pathsec._ALLOWED_ROOTS_CACHE = saved_cache
        pathsec._LAST_DATA_PATHS = saved_last
        shutil.rmtree(data_root, ignore_errors=True)


def _outside_dir():
    """A fresh directory path under the real ``$HOME``; guaranteed outside every
    allowed pathsec root. Deliberately NOT a temp dir: the private system temp is
    itself an allowed root, so a temp target would be a false "outside"."""
    return Path.home() / f".nltk_weka_{os.getpid()}"


def test_arff_formatter_write_refuses_outside_path(restricted_sandbox):
    """weka.ARFF_Formatter.write: a caller-supplied ``outfile`` path outside the
    sandbox must be refused before any data is written."""
    from nltk.classify.weka import ARFF_Formatter

    outside = _outside_dir()
    target_file = outside / "attack.arff"
    try:
        # NEGATIVE CONTROL: prove the target is genuinely outside every root.
        with pytest.raises(PermissionError):
            pathsec.open(str(target_file), "w")

        # ATTACK: write() to an outside path string.
        formatter = ARFF_Formatter(["yes", "no"], [("f1", "NUMERIC")])
        with pytest.raises(PermissionError):
            formatter.write(str(target_file), [])

        # Containment: nothing was written outside the sandbox.
        assert not target_file.exists()
    finally:
        shutil.rmtree(outside, ignore_errors=True)


def test_arff_formatter_write_accepts_in_sandbox_path(restricted_sandbox):
    """A destination inside an allowed data root is written normally (so the guard
    does not break the legitimate path), with LF line endings so the ARFF file is
    byte-identical across platforms."""
    from nltk.classify.weka import ARFF_Formatter

    target = os.path.join(restricted_sandbox, "ok.arff")
    formatter = ARFF_Formatter(["yes", "no"], [("f1", "NUMERIC")])
    formatter.write(target, [])
    assert os.path.exists(target)
    assert b"\r" not in Path(target).read_bytes(), "ARFF write must be LF-only"


def test_arff_write_routes_through_pathsec():
    """Grep-style guard: the write sink must reference the pathsec sentinel, so a
    future refactor that reverts to a bare open() is caught here."""
    from nltk.classify.weka import ARFF_Formatter

    src = inspect.getsource(ARFF_Formatter.write)
    assert "pathsec_open(" in src
    assert "= open(" not in src
