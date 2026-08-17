"""Path-traversal containment tests for the parse-package bare-``open`` sweep.

``TransitionParser.train`` and ``TransitionParser.parse`` both take a
*caller-supplied* model path (``modelfile`` / ``modelFile``). Before the sweep
they reached the filesystem through a bare ``open()``; ``train`` wrote the
fitted model with ``pickle.dump(model, open(modelfile, "wb"))`` and ``parse``
read it back with ``open(modelFile, "rb")``; so a path outside NLTK's data
sandbox was written to (arbitrary-path pickle write) or read from without any
containment (GHSA-8mgp-746c-j5xp). Both sinks now route through
``nltk.pathsec.open``, which refuses a path outside the allowed data roots
before any bytes move.

Each test enforces the pathsec sandbox with a single fresh allowed root and
attacks with a path under ``$HOME``; never a temp dir, because a *private*
system temp dir is itself an allowed root on macOS, which would mask the block.
"""

import os
import pickle
import shutil
import tempfile
from pathlib import Path

import pytest

import nltk.data
import nltk.pathsec as pathsec
from nltk.parse import DependencyGraph, transitionparser
from nltk.parse.transitionparser import TransitionParser

# A small projective gold sentence (same shape used by the transitionparser
# doctests / existing security tests).
GOLD = """
Economic  JJ     2      ATT
news  NN     3       SBJ
has       VBD       0       ROOT
little      JJ      5       ATT
effect   NN     3       OBJ
on     IN      5       ATT
financial       JJ       8       ATT
markets    NNS      6       PC
.    .      3       PU
"""


# Lightweight fakes so ``train`` reaches its model-save open without the
# heavy numpy/scipy/sklearn fit pipeline. Defined at module level so a fake
# model is picklable (needed by the in-sandbox positive control).
# The pathsec sandbox fixtures (sandbox / restricted_sandbox / enforce_off)
# are provided by nltk/test/unit/conftest.py.


class _Arr:
    def astype(self, *args, **kwargs):
        return self


class _FakeX(_Arr):
    def __init__(self):
        self.indices = _Arr()
        self.indptr = _Arr()


class _FakeModel:
    def fit(self, *args, **kwargs):
        return self


class _FakeSVM:
    @staticmethod
    def SVC(*args, **kwargs):
        return _FakeModel()


def test_negative_control_outside_refused_inside_allowed(pathsec_sandbox):
    """Baseline: pathsec refuses an outside path but permits an in-sandbox one."""
    allowed_root, home_target = pathsec_sandbox
    outside = home_target / "canary.txt"
    with pytest.raises(PermissionError):
        pathsec.open(str(outside), "w")
    assert not outside.exists(), "negative control wrote outside the sandbox"

    inside = allowed_root / "ok.txt"
    with pathsec.open(str(inside), "w") as fh:
        fh.write("ok")
    assert inside.exists()


def test_train_refuses_outside_model(pathsec_sandbox, monkeypatch):
    """TransitionParser.train must refuse to write a model outside the sandbox."""
    _, home_target = pathsec_sandbox
    outside_model = home_target / "tp.model"

    monkeypatch.setattr(
        transitionparser,
        "load_svmlight_file",
        lambda name: (_FakeX(), None),
        raising=False,
    )
    monkeypatch.setattr(transitionparser, "svm", _FakeSVM(), raising=False)

    parser = TransitionParser(TransitionParser.ARC_STANDARD)
    gold = DependencyGraph(GOLD)
    with pytest.raises(PermissionError):
        parser.train([gold], str(outside_model), verbose=False)
    assert not outside_model.exists(), "train wrote a model outside the sandbox"


def test_train_permits_inside_model(pathsec_sandbox, monkeypatch):
    """Positive control: an in-sandbox model path still trains/saves fine."""
    allowed_root, _ = pathsec_sandbox
    inside_model = allowed_root / "tp.model"

    monkeypatch.setattr(
        transitionparser,
        "load_svmlight_file",
        lambda name: (_FakeX(), None),
        raising=False,
    )
    monkeypatch.setattr(transitionparser, "svm", _FakeSVM(), raising=False)

    parser = TransitionParser(TransitionParser.ARC_STANDARD)
    gold = DependencyGraph(GOLD)
    parser.train([gold], str(inside_model), verbose=False)
    assert inside_model.exists(), "train failed to save inside the sandbox"


def test_parse_refuses_outside_model(pathsec_sandbox):
    """TransitionParser.parse must refuse to read a model from outside the sandbox.

    The model file genuinely exists outside the sandbox, so the refusal is the
    pathsec block (PermissionError), not a FileNotFoundError.
    """
    _, home_target = pathsec_sandbox
    outside_model = home_target / "evil.model"
    import builtins

    with builtins.open(outside_model, "wb") as fh:
        pickle.dump({}, fh)

    parser = TransitionParser(TransitionParser.ARC_STANDARD)
    gold = DependencyGraph(GOLD)
    with pytest.raises(PermissionError):
        parser.parse([gold], str(outside_model))


def test_parse_permits_inside_model(pathsec_sandbox):
    """Positive control: an in-sandbox model path gets past the pathsec open.

    A plain (non-model) pickle then fails downstream, but crucially NOT with a
    PermissionError; proving the sink blocks only outside paths.
    """
    allowed_root, _ = pathsec_sandbox
    inside_model = allowed_root / "model.pickle"
    import builtins

    with builtins.open(inside_model, "wb") as fh:
        pickle.dump({}, fh)

    parser = TransitionParser(TransitionParser.ARC_STANDARD)
    gold = DependencyGraph(GOLD)
    with pytest.raises(Exception) as excinfo:
        parser.parse([gold], str(inside_model))
    assert not isinstance(
        excinfo.value, PermissionError
    ), "in-sandbox model read was wrongly refused by pathsec"
