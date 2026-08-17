# Natural Language Toolkit: pathsec sweep tests (nltk.tag sinks)
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
#
"""Attack tests for the caller-controlled model-path sinks hardened under
GHSA-8mgp-746c-j5xp in :mod:`nltk.tag`.

The taggers here hand a model path to a native extension or an external
process that ``pathsec.open`` cannot wrap:

* ``CRFTagger.set_model_file`` / ``CRFTagger.train`` -> pycrfsuite C-extension
  (``Tagger.open`` / ``Trainer.train``).
* ``StanfordTagger.tag_sents`` -> a Java subprocess (``-model`` /
  ``-loadClassifier``).
* ``HunposTagger.__init__`` -> the ``hunpos-tag`` subprocess argv.

Each patched API now calls ``pathsec.validate_path`` immediately before the
hand-off, so a model path *outside* the NLTK data sandbox is refused. The
outside target is a fresh directory under the real home directory; never a
temp dir, because the system temp dir can itself be an allowed root (and on
Linux ``tempfile.mkdtemp()`` lives under the shared ``/tmp``).
"""

import inspect
import os
import shutil
import tempfile
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


def test_crf_set_model_file_refuses_outside_path(sandbox):
    """CRFTagger.set_model_file() must refuse an outside model path before the
    pycrfsuite native loader touches it.

    Reached without pycrfsuite installed: ``validate_path`` runs before
    ``self._tagger.open``, so ``object.__new__`` (no ``__init__``, which needs
    pycrfsuite) suffices to drive the sink.
    """
    from nltk.tag.crf import CRFTagger

    target = sandbox / "model.crf.tagger"
    ct = object.__new__(CRFTagger)
    with pytest.raises(PermissionError):
        ct.set_model_file(str(target))


def test_crf_train_refuses_outside_path(sandbox):
    """CRFTagger.train() must refuse an outside destination before the pycrfsuite
    Trainer writes the model."""
    pytest.importorskip("pycrfsuite")
    from nltk.tag.crf import CRFTagger

    target = sandbox / "trained.crf.tagger"
    ct = CRFTagger()
    with pytest.raises(PermissionError):
        ct.train([[("dog", "Noun"), ("runs", "Verb")]], str(target))
    assert not target.exists()


def test_stanford_tag_sents_refuses_outside_model(sandbox):
    """StanfordTagger.tag_sents() must refuse an outside model path before the
    JVM subprocess is spawned.

    Driven via ``object.__new__`` so no Stanford jar / JVM is required:
    ``validate_path`` raises before the ``java()`` hand-off.
    """
    from nltk.tag.stanford import StanfordPOSTagger

    target = sandbox / "english-bidirectional-distsim.tagger"
    tagger = object.__new__(StanfordPOSTagger)
    tagger._stanford_model = str(target)
    tagger._stanford_jar = "unused.jar"
    tagger._encoding = "utf8"
    tagger.java_options = "-mx1000m"

    with pytest.raises(PermissionError):
        tagger.tag_sents([["What", "is", "the", "airspeed"]])


def test_hunpos_init_refuses_outside_model(sandbox):
    """HunposTagger.__init__() must refuse an outside model path before the
    hunpos-tag subprocess is spawned.

    ``find_file`` returns the outside model only if it exists on disk, so the
    model file is created under ``~``; a dummy binary satisfies ``find_binary``
    without being executed (validation raises before ``Popen``).
    """
    from nltk.tag.hunpos import HunposTagger

    dummy_bin = sandbox / "hunpos-tag"
    dummy_bin.write_text("#!/bin/sh\n")
    model = sandbox / "en_wsj.model"
    model.write_text("stub")

    with pytest.raises(PermissionError):
        HunposTagger(str(model), path_to_bin=str(dummy_bin))


def test_sources_route_through_pathsec():
    """Grep-style guard: the patched sinks must reference the pathsec sentinel,
    so a future refactor that drops the check is caught here."""
    from nltk.tag import crf, hunpos, stanford

    crf_set_src = inspect.getsource(crf.CRFTagger.set_model_file)
    assert (
        'validate_path(model_file, context="CRFTagger.set_model_file")' in crf_set_src
    )

    crf_train_src = inspect.getsource(crf.CRFTagger.train)
    assert 'validate_path(model_file, context="CRFTagger.train")' in crf_train_src

    stanford_src = inspect.getsource(stanford.StanfordTagger.tag_sents)
    assert "validate_path(self._stanford_model" in stanford_src

    hunpos_src = inspect.getsource(hunpos.HunposTagger.__init__)
    assert "validate_path(self._hunpos_model" in hunpos_src
