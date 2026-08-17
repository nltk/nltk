# Natural Language Toolkit: pathsec sweep attack tests (misc modules)
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Path-traversal attack tests for the caller-controlled file sinks hardened in
``nltk.tbl.demo``, ``nltk.sem.chat80`` and ``nltk.metrics.agreement``.

Each patched API must refuse to read from / write to a path outside the NLTK
data sandbox and must leave nothing behind (GHSA-8mgp-746c-j5xp).
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


# A tiny synthetic tagged corpus so tbl.demo.postag() never needs the treebank
# corpus (postag skips corpus loading when tagged_data is supplied).
TINY_TAGGED = [
    [("the", "AT"), ("dog", "NN"), ("runs", "VBZ")],
    [("a", "AT"), ("cat", "NN"), ("sleeps", "VBZ")],
] * 10


# The pathsec sandbox fixtures (sandbox / restricted_sandbox / enforce_off)
# are provided by nltk/test/unit/conftest.py.


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
# nltk.tbl.demo
# --------------------------------------------------------------------------- #
def test_tbl_demo_cache_baseline_refuses_outside(sandbox):
    from nltk.tbl import demo

    target = sandbox / "evil_baseline.pcl"
    with pytest.raises(PermissionError):
        demo.postag(
            tagged_data=list(TINY_TAGGED),
            num_sents=20,
            trace=0,
            cache_baseline_tagger=str(target),
        )
    assert not target.exists()


def test_tbl_demo_serialize_output_refuses_outside(sandbox):
    from nltk.tbl import demo

    target = sandbox / "evil_tagger.pcl"
    with pytest.raises(PermissionError):
        demo.postag(
            tagged_data=list(TINY_TAGGED),
            num_sents=20,
            trace=0,
            max_rules=5,
            serialize_output=str(target),
        )
    assert not target.exists()


def test_tbl_demo_error_output_refuses_outside(sandbox):
    from nltk.tbl import demo

    target = sandbox / "evil_errors.txt"
    with pytest.raises(PermissionError):
        demo.postag(
            tagged_data=list(TINY_TAGGED),
            num_sents=20,
            trace=0,
            max_rules=5,
            error_output=str(target),
        )
    assert not target.exists()


def test_tbl_demo_plot_refuses_outside(sandbox):
    from nltk.tbl import demo

    target = sandbox / "evil_curve.png"
    stats = {"initialerrors": 0, "rulescores": [], "tokencount": 1}
    with pytest.raises(PermissionError):
        demo._demo_plot(str(target), stats, stats)
    assert not target.exists()


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
