"""
Regression tests for the model-artifact save hardening in
``nltk.classify.maxent`` and ``nltk.chunk.named_entity`` (GHSA-8mgp-746c-j5xp,
CWE-377/378).

``save_maxent_params`` and ``Maxent_NE_Chunker.save_params`` used to write to a
guessable path in the shared, world-writable system temp
(``/tmp/english_ace_<fmt>/`` / ``/tmp``): on a multi-user host another local user
could pre-create or symlink that exact path to redirect or read the write. They
now default to a fresh private (mode 0700), unpredictably-named staging directory
under an allowed data root, validate any caller-supplied destination against the
pathsec sandbox before writing, and emit LF line endings so the tab files reload
cleanly on Windows.

The "outside" target is a fresh directory under the real ``$HOME``; never a temp
dir, because the private system temp directory is itself an allowed pathsec root
on macOS, which would make a temp target a false "outside".
"""

import inspect
import os
import shutil
import tempfile
import types
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
    return Path.home() / f".nltk_maxent_ne_{os.getpid()}"


# --- nltk.classify.maxent.save_maxent_params --------------------------------


def test_save_maxent_params_refuses_outside_tab_dir(restricted_sandbox):
    """maxent.save_maxent_params: a caller-controlled ``tab_dir`` must not let the
    4 ``{tab_dir}/*`` writes land outside the sandbox."""
    numpy = pytest.importorskip("numpy")
    from nltk.classify.maxent import save_maxent_params

    outside = _outside_dir()
    param_files = ("weights.txt", "mapping.tab", "labels.txt", "alwayson.tab")
    try:
        # NEGATIVE CONTROL: prove the target is genuinely outside every root.
        with pytest.raises(PermissionError):
            pathsec.open(str(outside / "weights.txt"), "w")

        # ATTACK: point tab_dir at the outside directory.
        wgt = numpy.array([0.1, 0.2])
        with pytest.raises(PermissionError):
            save_maxent_params(wgt, {}, [], {}, tab_dir=str(outside))

        # Containment: no parameter file was written outside the sandbox.
        for name in param_files:
            assert not (outside / name).exists()
    finally:
        shutil.rmtree(outside, ignore_errors=True)


def test_save_maxent_params_default_is_private_dir_not_shared_tmp(restricted_sandbox):
    """The default destination must be a fresh *private* (0700),
    unpredictably-named directory (returned by the call); never the historical
    guessable shared ``/tmp`` (CWE-377/378)."""
    numpy = pytest.importorskip("numpy")
    from nltk.classify.maxent import save_maxent_params

    out = save_maxent_params(numpy.array([0.1, 0.2]), {}, [], {})
    try:
        # is_private_dir (0700, user-owned) is the real "not shared /tmp" check;
        # a fresh mkdtemp lives under /tmp on Linux, so assert privacy plus the
        # unpredictable mkdtemp name, not that the path avoids /tmp.
        assert pathsec.is_private_dir(out), "default dir must be private (0700)"
        assert os.path.basename(out).startswith("nltk_maxent_params_")
        assert (Path(out) / "weights.txt").exists()
    finally:
        shutil.rmtree(out, ignore_errors=True)


def test_save_maxent_params_round_trip(restricted_sandbox):
    """Functional check: params written by save_maxent_params reload identically
    via load_maxent_params (given a PathPointer, as the loaders use), and the tab
    files are LF-only so a reload cannot pick up a stray CR on Windows."""
    numpy = pytest.importorskip("numpy")
    from nltk.classify.maxent import load_maxent_params, save_maxent_params
    from nltk.data import FileSystemPathPointer

    wgt = numpy.array([0.5, -1.25, 3.0])
    mpg = {("word", "cat", "L1"): 5, ("shape", "upcase", "L2"): 7}
    lab = ["L1", "L2"]
    aon = {}
    out = save_maxent_params(wgt, mpg, lab, aon)
    try:
        for name in ("weights.txt", "mapping.tab", "labels.txt", "alwayson.tab"):
            assert b"\r" not in Path(out, name).read_bytes(), f"{name} has CR"
        w2, m2, l2, a2 = load_maxent_params(FileSystemPathPointer(out))
        assert numpy.allclose(w2, wgt)
        assert l2 == lab
        assert m2 == mpg
        assert a2 == aon
    finally:
        shutil.rmtree(out, ignore_errors=True)


# --- nltk.chunk.named_entity.Maxent_NE_Chunker.save_params -------------------


def _stub_chunker(ne, fmt="multiclass"):
    """A Maxent_NE_Chunker built without __init__ (which needs on-disk model
    data) plus a stub tagger, so the in-memory parameter reads in save_params
    succeed and the path guard is what decides the outcome."""
    chunker = object.__new__(ne.Maxent_NE_Chunker)
    chunker._fmt = fmt
    chunker._save_dir = None
    chunker._tagger = types.SimpleNamespace(
        _classifier=types.SimpleNamespace(
            _encoding=types.SimpleNamespace(_mapping={}, _labels=[], _alwayson={}),
            _weights=[],
        )
    )
    return chunker


def test_ne_chunker_save_params_refuses_outside_path(restricted_sandbox):
    """Maxent_NE_Chunker.save_params() must refuse an outside tab_dir before the
    parameter files are written."""
    ne = pytest.importorskip("nltk.chunk.named_entity")
    target_dir = _outside_dir() / "english_ace_multiclass"
    chunker = _stub_chunker(ne)
    try:
        with pytest.raises((PermissionError, ValueError)):
            chunker.save_params(tab_dir=str(target_dir))
        assert not target_dir.exists() or not any(target_dir.iterdir())
    finally:
        shutil.rmtree(_outside_dir(), ignore_errors=True)


def test_ne_chunker_save_params_default_is_private_dir(restricted_sandbox, monkeypatch):
    """The default destination must be a fresh *private* (0700),
    unpredictably-named directory, reused across calls; never the historical
    guessable ``/tmp/english_ace_<fmt>/`` (CWE-377/378)."""
    ne = pytest.importorskip("nltk.chunk.named_entity")

    captured = {}

    def fake_save(wgt, mpg, lab, aon, tab_dir="/tmp"):
        captured["tab_dir"] = tab_dir

    # save_params uses the name imported into named_entity's namespace, so patch
    # it there (not on nltk.classify.maxent).
    monkeypatch.setattr(ne, "save_maxent_params", fake_save)

    chunker = _stub_chunker(ne)
    out = chunker.save_params()
    try:
        assert out == captured["tab_dir"], "save_params must return its dir"
        assert "english_ace" not in out, "must not use the guessable historic name"
        assert os.path.basename(out).startswith("nltk_ne_chunker_")
        assert pathsec.is_private_dir(out), "default dir must be private (0700)"
        assert chunker.save_dir == out
        assert chunker.save_params() == out, "repeated save must reuse save_dir"
    finally:
        shutil.rmtree(out, ignore_errors=True)


def test_maxent_and_ne_sinks_route_through_pathsec():
    """Grep-style guard: the patched sinks must reference the pathsec sentinels,
    so a future refactor that reverts to a bare open()/``/tmp`` is caught here."""
    ne = pytest.importorskip("nltk.chunk.named_entity")
    from nltk.classify import maxent

    ne_src = inspect.getsource(ne.Maxent_NE_Chunker.save_params)
    assert "validate_path(" in ne_src

    mx_src = inspect.getsource(maxent.save_maxent_params)
    assert "pathsec_open(" in mx_src
    assert "validate_path(" in mx_src
    assert '"/tmp' not in mx_src and "'/tmp" not in mx_src
