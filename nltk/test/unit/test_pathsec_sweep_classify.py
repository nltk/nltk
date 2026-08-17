"""
Attack regression tests for the bare-``open()`` path-traversal sweep of
``nltk.classify.maxent`` and ``nltk.classify.weka`` (GHSA-8mgp-746c-j5xp).

Each caller-controlled / hardcoded-``/tmp`` file-write sink in those modules is
now routed through the ``nltk.pathsec`` sandbox.  These tests prove containment:
with the sandbox restricted to a single throwaway data root, a caller-supplied
path that points OUTSIDE every allowed root is refused with ``PermissionError``
and nothing is written there.

The "outside" target is a fresh directory under the real ``$HOME``; **never** a
temp dir, because the private system temp directory is itself an allowed pathsec
root on macOS, which would make a temp target a false "outside".
"""

import os
import shutil
import tempfile
from pathlib import Path

import pytest

import nltk.data
import nltk.pathsec as pathsec

# The pathsec sandbox fixtures (sandbox / restricted_sandbox / enforce_off)
# are provided by nltk/test/unit/conftest.py.


def _outside_dir():
    """A fresh directory path under the real ``$HOME``; guaranteed outside
    every allowed pathsec root.  Deliberately NOT a temp dir: the private system
    temp is itself an allowed root, so a temp target would be a false "outside".
    """
    return Path.home() / f".nltk_sweep_classify_{os.getpid()}"


def test_save_maxent_params_refuses_outside_tab_dir(restricted_sandbox):
    """maxent.save_maxent_params: a caller-controlled ``tab_dir`` must not let
    the 4 ``{tab_dir}/*.txt`` writes land outside the sandbox."""
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
        # The write actually landed inside the returned private dir.
        assert (Path(out) / "weights.txt").exists()
    finally:
        shutil.rmtree(out, ignore_errors=True)


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
