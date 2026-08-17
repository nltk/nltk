# Natural Language Toolkit: pathsec sweep attack tests (agreement / chat80)
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Path-traversal attack tests for the caller-controlled file sinks hardened in
``nltk.metrics.agreement`` and ``nltk.sem.chat80`` (GHSA-8mgp-746c-j5xp).

Each patched API must refuse to read from / write to a path outside the NLTK
data sandbox and must leave nothing behind.
"""

import os
import pathlib
import runpy
import shutil
import sys
import tempfile

import pytest

import nltk.data
import nltk.pathsec as pathsec


@pytest.fixture
def sandbox():
    """Enforce pathsec with a single throwaway data root and yield an *outside*
    target directory the sandbox must refuse.

    The outside directory is a fresh dir under the real home directory; NOT a
    temp dir, because on macOS the private per-user system temp dir *is* an
    allowed root (``pathsec._get_allowed_roots``), which would make a temp-dir
    "attack" spuriously succeed.
    """
    saved_enforce = pathsec.ENFORCE
    saved_paths = list(nltk.data.path)
    saved_cwd = os.getcwd()

    data_root = tempfile.mkdtemp(prefix="nltk_sweep_sandbox_")
    outside = pathlib.Path.home() / f".nltk_sweep_agreement_chat80_{os.getpid()}"
    outside.mkdir(parents=True, exist_ok=True)

    pathsec.ENFORCE = True
    nltk.data.path[:] = [data_root]
    pathsec._ALLOWED_ROOTS_CACHE = None
    pathsec._LAST_DATA_PATHS = None

    try:
        yield outside
    finally:
        pathsec.ENFORCE = saved_enforce
        nltk.data.path[:] = saved_paths
        pathsec._ALLOWED_ROOTS_CACHE = None
        pathsec._LAST_DATA_PATHS = None
        os.chdir(saved_cwd)
        shutil.rmtree(outside, ignore_errors=True)
        shutil.rmtree(data_root, ignore_errors=True)


def test_negative_control_open_outside_raises(sandbox):
    """The sandbox is wired correctly: a plain pathsec.open() of the outside
    target must be refused and write nothing."""
    target = sandbox / "neg_control.txt"
    with pytest.raises(PermissionError):
        pathsec.open(str(target), "w")
    assert not target.exists()


# --------------------------------------------------------------------------- #
# nltk.sem.chat80
# --------------------------------------------------------------------------- #
def test_chat80_val_dump_refuses_outside(sandbox):
    from nltk.sem import chat80

    target = sandbox / "evil_valuation"
    with pytest.raises(PermissionError):
        chat80.val_dump([], str(target))
    # shelve may append backend suffixes (.db/.dir/.dat/.bak); none may appear.
    assert not list(sandbox.glob("evil_valuation*"))


def test_chat80_val_load_refuses_outside(sandbox):
    from nltk.sem import chat80

    target = sandbox / "evil_db"
    with pytest.raises(PermissionError):
        chat80.val_load(str(target))


def test_chat80_cities2table_refuses_outside(sandbox):
    from nltk.sem import chat80

    target = sandbox / "evil_city.db"
    with pytest.raises(PermissionError):
        chat80.cities2table("cities.pl", "city", str(target))
    assert not target.exists()


def test_chat80_label_indivs_refuses_outside_cwd(sandbox):
    from nltk.sem import chat80
    from nltk.sem.evaluate import Valuation

    # label_indivs writes the fixed name "chat_pnames.cfg" relative to CWD; make
    # CWD the outside dir so the write would land outside the sandbox.
    os.chdir(sandbox)
    with pytest.raises(PermissionError):
        chat80.label_indivs(Valuation([]), lexicon=True)
    assert not (sandbox / "chat_pnames.cfg").exists()


# --------------------------------------------------------------------------- #
# nltk.metrics.agreement (__main__ -f caller-file read)
# --------------------------------------------------------------------------- #
def test_agreement_main_file_read_refuses_outside(sandbox):
    target = sandbox / "evil_annotations.txt"
    target.write_text("a 1 x\n")  # content is irrelevant; read must be refused

    saved_argv = list(sys.argv)
    sys.argv = ["agreement", "-f", str(target)]
    try:
        with pytest.raises(PermissionError):
            # Runs the module's __main__ block in-process so the fixture's
            # ENFORCE / nltk.data.path settings apply to the patched open.
            runpy.run_module("nltk.metrics.agreement", run_name="__main__")
    finally:
        sys.argv = saved_argv
