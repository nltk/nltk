# Natural Language Toolkit: pathsec tests for the NE chunker model sink
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
#
"""Attack tests for the model-writing sink hardened under GHSA-8mgp-746c-j5xp in
:mod:`nltk.chunk.named_entity`.

``Maxent_NE_Chunker.save_params`` validates its caller-supplied ``tab_dir``
through :func:`nltk.pathsec.validate_tool_dir` before any parameter file is
written. The guard now runs first (before the in-memory classifier is read) and
uses the tool-directory guard, so a destination outside the NLTK data sandbox,
or a malformed / option-shaped / traversal spelling, is refused with
``PermissionError`` and nothing is written.

The ``sandbox`` / ``restricted_sandbox`` fixtures come from
``nltk/test/unit/conftest.py``. The outside target is a fresh directory under the
real home directory, never a temp dir, because a private per-user system temp dir
can itself be an allowed root.
"""

import inspect
import os
import shutil
import types

import pytest

import nltk.pathsec as pathsec


def _stub_chunker():
    """A ``Maxent_NE_Chunker`` built without ``__init__`` (which needs on-disk
    model data), given a stub tagger so the in-memory parameter reads succeed."""
    ne = pytest.importorskip("nltk.chunk.named_entity")
    chunker = object.__new__(ne.Maxent_NE_Chunker)
    chunker._fmt = "multiclass"
    chunker._save_dir = None
    chunker._tagger = types.SimpleNamespace(
        _classifier=types.SimpleNamespace(
            _encoding=types.SimpleNamespace(_mapping={}, _labels=[], _alwayson={}),
            _weights=[],
        )
    )
    return chunker


def test_save_params_refuses_outside_path(sandbox):
    """save_params() must refuse a tab_dir outside the data sandbox before the
    parameter files are written, and write nothing."""
    target_dir = sandbox / "english_ace_multiclass"
    chunker = _stub_chunker()
    with pytest.raises(PermissionError):
        chunker.save_params(tab_dir=str(target_dir))
    assert not target_dir.exists() or not any(target_dir.iterdir())


@pytest.mark.parametrize(
    "bad",
    [
        "-rf",  # option-shaped: argument injection
        "models\x00evil",  # NUL byte truncates the path downstream
        "good/../../../evil",  # a '..' component may not traverse the namespace
        "   ",  # blank but non-empty names a real relative file
    ],
)
def test_save_params_refuses_malformed_dir(bad, enforce_off):
    """The tool-directory guard rejects these string shapes syntactically, so
    they raise even with ENFORCE off. The plain containment check does not (it
    would warn and let the write through), so this pins the switch to
    validate_tool_dir."""
    chunker = _stub_chunker()
    with pytest.raises(PermissionError):
        chunker.save_params(tab_dir=bad)


def test_save_params_validates_before_touching_the_tagger():
    """The guard runs first: with no tagger at all a malformed destination still
    raises PermissionError (from validation), never AttributeError (from reading
    the classifier). This is the ordering the fix moved the guard to."""
    ne = pytest.importorskip("nltk.chunk.named_entity")
    chunker = object.__new__(ne.Maxent_NE_Chunker)
    chunker._fmt = "multiclass"
    chunker._save_dir = None
    chunker._tagger = None
    with pytest.raises(PermissionError):
        chunker.save_params(tab_dir="-rf")


def test_save_params_default_is_private_dir_not_shared_tmp(sandbox, monkeypatch):
    """The default destination must be a fresh *private* (0700),
    unpredictably-named directory that pathsec accepts as a data root; never the
    historical guessable ``/tmp/english_ace_<fmt>/`` in the shared, world
    writable system temp, which another local user could pre-create or symlink
    (CWE-377/378)."""
    ne = pytest.importorskip("nltk.chunk.named_entity")

    captured = {}

    def fake_save(wgt, mpg, lab, aon, tab_dir="."):
        captured["tab_dir"] = tab_dir

    # save_params uses the name imported into named_entity's namespace, so patch
    # it there, not on nltk.classify.maxent.
    monkeypatch.setattr(ne, "save_maxent_params", fake_save)

    chunker = _stub_chunker()
    out = chunker.save_params()
    try:
        assert out == captured["tab_dir"], "save_params must return its dir"
        assert "english_ace" not in out, "must not use the guessable historic name"
        assert os.path.basename(out).startswith("nltk_ne_chunker_")
        assert os.path.isdir(out)
        # A private (0700, user-owned) dir is accepted by pathsec as a data root.
        assert pathsec.is_private_dir(out)
        # The private dir is created once (save_dir) and reused across calls.
        assert chunker.save_dir == out
        assert chunker.save_params() == out, "repeated save must reuse save_dir"
    finally:
        shutil.rmtree(out, ignore_errors=True)


def test_save_params_source_routes_through_validate_tool_dir():
    """Grep-style guard: a future refactor that drops the tool-directory guard,
    or reverts to a bare open(), is caught here."""
    ne = pytest.importorskip("nltk.chunk.named_entity")
    save_params_src = inspect.getsource(ne.Maxent_NE_Chunker.save_params)
    assert "validate_tool_dir(" in save_params_src
