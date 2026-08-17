# Natural Language Toolkit: pathsec sweep attack tests (tbl.demo)
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Path-traversal attack tests for the caller-controlled file sinks hardened in
``nltk.tbl.demo`` (GHSA-8mgp-746c-j5xp).

Each patched API must refuse to write to a path outside the NLTK data sandbox and
must leave nothing behind. The chat80 and agreement sinks this file used to also
cover now live in test_chat80_pathsec.py and test_agreement_pathsec.py.
"""

import pytest

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
