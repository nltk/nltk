# Natural Language Toolkit: pathsec sweep tests (chunk / sentiment sinks)
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
#
"""Attack tests for the bare-``open()`` sinks hardened under GHSA-8mgp-746c-j5xp
in :mod:`nltk.chunk.named_entity` and :mod:`nltk.sentiment.sentiment_analyzer`.

Each patched file-write API is driven with a path *outside* the NLTK data
sandbox and must raise ``PermissionError`` and write nothing outside. The
outside target is a fresh directory under the real home directory; never a
temp dir, because the system temp dir can itself be an allowed root (and on
Linux ``tempfile.mkdtemp()`` lives under the shared ``/tmp``).
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

# The pathsec sandbox fixtures (sandbox / restricted_sandbox / enforce_off)
# are provided by nltk/test/unit/conftest.py.


def test_negative_control_pathsec_open_refuses_outside(sandbox):
    """Baseline: pathsec.open() itself refuses a write outside the sandbox."""
    target = sandbox / "pwned.txt"
    with pytest.raises(PermissionError):
        pathsec.open(str(target), "w")
    assert not target.exists()


def test_sentiment_save_file_refuses_outside_path(sandbox):
    """SentimentAnalyzer.save_file() must not pickle to an outside path."""
    sa = pytest.importorskip("nltk.sentiment.sentiment_analyzer")
    target = sandbox / "clf.pickle"
    analyzer = sa.SentimentAnalyzer()
    with pytest.raises(PermissionError):
        analyzer.save_file({"weights": [1, 2, 3]}, str(target))
    assert not target.exists()


def test_ne_chunker_save_params_refuses_outside_path(sandbox):
    """Maxent_NE_Chunker.save_params() must refuse an outside tab_dir before the
    parameter files are written."""
    ne = pytest.importorskip("nltk.chunk.named_entity")
    target_dir = sandbox / "english_ace_multiclass"

    # Build the object without __init__ (which needs on-disk model data) and give
    # it a stub tagger so the in-memory param reads succeed; validate_path then
    # refuses the outside tab_dir before save_maxent_params writes anything.
    chunker = object.__new__(ne.Maxent_NE_Chunker)
    chunker._fmt = "multiclass"
    chunker._tagger = types.SimpleNamespace(
        _classifier=types.SimpleNamespace(
            _encoding=types.SimpleNamespace(_mapping={}, _labels=[], _alwayson={}),
            _weights=[],
        )
    )
    with pytest.raises(PermissionError):
        chunker.save_params(tab_dir=str(target_dir))
    assert not target_dir.exists() or not any(target_dir.iterdir())


def test_ne_chunker_save_params_default_is_private_dir_not_shared_tmp(
    sandbox, monkeypatch
):
    """The default destination must be a fresh *private* (0700),
    unpredictably-named directory; never the historical guessable
    ``/tmp/english_ace_<fmt>/`` in the shared, world-writable system temp, which
    another local user could pre-create or symlink (CWE-377/378)."""
    import nltk.pathsec as pathsec

    ne = pytest.importorskip("nltk.chunk.named_entity")

    captured = {}

    def fake_save(wgt, mpg, lab, aon, tab_dir="/tmp"):
        captured["tab_dir"] = tab_dir

    # save_params uses the name imported into named_entity's namespace, so patch
    # it there (not on nltk.classify.maxent).
    monkeypatch.setattr(ne, "save_maxent_params", fake_save)

    chunker = object.__new__(ne.Maxent_NE_Chunker)
    chunker._fmt = "multiclass"
    chunker._save_dir = None
    chunker._tagger = types.SimpleNamespace(
        _classifier=types.SimpleNamespace(
            _encoding=types.SimpleNamespace(_mapping={}, _labels=[], _alwayson={}),
            _weights=[],
        )
    )
    out = chunker.save_params()
    try:
        assert out == captured["tab_dir"], "save_params must return its dir"
        assert "english_ace" not in out, "must not use the guessable historic name"
        assert os.path.basename(out).startswith("nltk_ne_chunker_")
        assert os.path.isdir(out)
        # Private (0700, user-owned) -> pathsec accepts it as a data root.
        assert pathsec.is_private_dir(out)
        # The private dir is created once (save_dir) and reused across calls.
        assert chunker.save_dir == out
        assert chunker.save_params() == out, "repeated save must reuse save_dir"
    finally:
        shutil.rmtree(out, ignore_errors=True)


def test_sources_route_through_pathsec():
    """Grep-style guard: the patched sinks must reference the pathsec sentinel,
    so a future refactor that reverts to a bare open() is caught here."""
    ne = pytest.importorskip("nltk.chunk.named_entity")
    sa = pytest.importorskip("nltk.sentiment.sentiment_analyzer")

    save_file_src = inspect.getsource(sa.SentimentAnalyzer.save_file)
    assert "pathsec_open(" in save_file_src
    assert "with open(" not in save_file_src

    save_params_src = inspect.getsource(ne.Maxent_NE_Chunker.save_params)
    assert "validate_path(" in save_params_src
