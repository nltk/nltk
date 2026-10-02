# Natural Language Toolkit: pathsec sweep attack tests (tbl.demo)
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Path-traversal attack tests for the caller-controlled file sinks hardened in
``nltk.tbl.demo`` (GHSA-8mgp-746c-j5xp).

``nltk.tbl.demo.postag`` pickles a trained Brill/baseline tagger, writes an
error-analysis text file, and plots a learning curve, each to a caller-supplied
path. The hardening routes the pickle and text sinks through ``pathsec.open``
and validates the plot path (which matplotlib writes itself) with
``pathsec.validate_path``. Every one of those destinations must refuse a path
outside the NLTK data sandbox and leave nothing behind, while an in-root
destination must still be accepted.

The generic ``pathsec.open`` negative control and the chat80/agreement sinks this
module once also covered now live in their own suites on ``develop``
(``test_chat80_pathsec.py``, ``test_agreement_pathsec.py`` and the
``test_pathsec_sweep_sem_util.py`` negative control), so they are not repeated
here.
"""

import os

import pytest

import nltk.pathsec as pathsec

# A tiny synthetic tagged corpus so tbl.demo.postag() never needs the treebank
# corpus (postag skips corpus loading when tagged_data is supplied).
TINY_TAGGED = [
    [("the", "AT"), ("dog", "NN"), ("runs", "VBZ")],
    [("a", "AT"), ("cat", "NN"), ("sleeps", "VBZ")],
] * 10


# The pathsec sandbox fixtures (sandbox / pathsec_sandbox) are provided by
# nltk/test/unit/conftest.py.


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


# In-root acceptance (the other half of the teeth): a destination inside the
# sandbox must still be written. These stay corpus-free by supplying
# tagged_data / synthetic stats, so they run on any platform.


def test_tbl_demo_error_output_in_root_accepted(pathsec_sandbox):
    """The error-analysis text sink goes through pathsec.open; an in-root path
    is accepted and written (no pickle round trip is involved)."""
    from nltk.tbl import demo

    target = pathsec_sandbox.root / "errors_ok.txt"
    demo.postag(
        tagged_data=list(TINY_TAGGED),
        num_sents=20,
        trace=0,
        max_rules=5,
        error_output=str(target),
    )
    assert target.exists()
    assert target.stat().st_size > 0


def test_tbl_demo_plot_in_root_accepted(pathsec_sandbox):
    """The learning-curve path is validate_path()-checked, then written by
    matplotlib; an in-root destination is accepted."""
    pytest.importorskip("matplotlib")
    from nltk.tbl import demo

    target = pathsec_sandbox.root / "curve_ok.png"
    stats = {"initialerrors": 2, "rulescores": [1, 1], "tokencount": 10}
    demo._demo_plot(str(target), stats, stats)
    assert target.exists()
    assert target.stat().st_size > 0


# postag()'s caller-supplied output paths, exercised through the real treebank
# corpus. These deliberately do NOT use the pathsec_sandbox fixture: it narrows
# nltk.data.path to one empty temp root, so the treebank corpus cannot load and
# postag raises LookupError long before reaching any write. The real roots stay
# in place and the attack target is staged outside them instead.


@pytest.fixture
def corpus_backed_sandbox(monkeypatch, tmp_path_factory):
    """ENFORCE on, the real data roots intact, plus an out-of-root target."""
    import pathlib as _pathlib
    import shutil as _shutil
    import tempfile as _tempfile

    import nltk.data

    pytest.importorskip("numpy")
    try:
        nltk.data.find("corpora/treebank")
    except LookupError:
        pytest.skip("treebank corpus unavailable")

    outside = _pathlib.Path(
        _tempfile.mkdtemp(prefix=".nltk_tbl_outside_", dir=str(_pathlib.Path.home()))
    )
    monkeypatch.setattr(pathsec, "ENFORCE", True)
    monkeypatch.setattr(pathsec, "_ALLOWED_ROOTS_CACHE", None, raising=False)
    monkeypatch.setattr(pathsec, "_LAST_DATA_PATHS", None, raising=False)
    try:
        yield outside
    finally:
        _shutil.rmtree(outside, ignore_errors=True)


@pytest.mark.parametrize(
    "kwarg",
    [
        "serialize_output",
        "error_output",
        "cache_baseline_tagger",
        "learning_curve_output",
    ],
)
def test_postag_output_paths_refuse_escape(corpus_backed_sandbox, kwarg):
    """Every destination postag() writes is caller-supplied, so none may leave
    the data roots. learning_curve_output reaches savefig, which pathsec.open
    cannot wrap, so it is validated rather than opened through the sentinel."""
    import nltk.tbl.demo as demo

    for target in (str(corpus_backed_sandbox / "pwned.out"), "/etc/nltk_pwned.out"):
        with pytest.raises((PermissionError, ValueError)):
            demo.postag(num_sents=1, max_rules=1, **{kwarg: target})
        assert not os.path.exists(target)


@pytest.mark.parametrize(
    "target", ["../../../tmp/evil.pcl", "ok.pcl\x00.evil", "-Xmx99g", ""]
)
def test_postag_serialize_output_refuses_malformed_paths(corpus_backed_sandbox, target):
    import nltk.tbl.demo as demo

    with pytest.raises((PermissionError, ValueError)):
        demo.postag(num_sents=1, max_rules=1, serialize_output=target)
