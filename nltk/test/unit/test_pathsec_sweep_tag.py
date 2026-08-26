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


def test_tagger_sources_route_through_pathsec():
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


# --- the full escape matrix, fired at every guarded model-path sink -----------
def _escape_vectors(root, outside):
    """Every shape a caller-supplied model path can take to leave the sandbox.

    A plain outside path is only the simplest one; the guard must also resolve
    symlinks (final and intermediate), reject traversal and absolute paths, and
    refuse URL schemes, which are not filesystem paths at all (GHSA-8mgp).
    """
    secret = outside / "secret"
    secret.write_text("SECRET", encoding="utf-8")
    link = root / "link.model"
    if not link.exists():
        os.symlink(str(secret), str(link))
    linkdir = root / "linkdir"
    if not linkdir.exists():
        os.symlink(str(outside), str(linkdir))
    return {
        "plain-outside": str(outside / "m.model"),
        "traversal": os.path.join(str(root), "..", "..", "etc", "passwd"),
        "absolute": "/etc/passwd",
        "symlink-in-root": str(link),
        "intermediate-symlink": str(linkdir / "secret"),
        "file-url": "file:///etc/passwd",
        "http-url": "http://evil.example/m.model",
        "nul-byte": "/etc/passwd\x00.model",
    }


def _drive_crf(path):
    from nltk.tag.crf import CRFTagger

    object.__new__(CRFTagger).set_model_file(path)


def _drive_stanford(path):
    from nltk.tag.stanford import StanfordPOSTagger

    tagger = object.__new__(StanfordPOSTagger)
    tagger._stanford_model = path
    tagger._stanford_jar = "unused.jar"
    tagger._encoding = "utf8"
    tagger.java_options = "-mx1000m"
    tagger.tag_sents([["What", "is", "the", "airspeed"]])


def _drive_perceptron_save(path):
    from nltk.tag.perceptron import AveragedPerceptron

    AveragedPerceptron().save(path)


def _drive_perceptron_load(path):
    from nltk.tag.perceptron import AveragedPerceptron

    AveragedPerceptron().load(path)


_SINKS = {
    "CRFTagger.set_model_file": _drive_crf,
    "StanfordTagger.tag_sents": _drive_stanford,
    "AveragedPerceptron.save": _drive_perceptron_save,
    "AveragedPerceptron.load": _drive_perceptron_load,
}


@pytest.mark.parametrize("sink", sorted(_SINKS))
@pytest.mark.parametrize(
    "vector",
    [
        "plain-outside",
        "traversal",
        "absolute",
        "symlink-in-root",
        "intermediate-symlink",
        "file-url",
        "http-url",
        "nul-byte",
    ],
)
def test_every_sink_refuses_every_escape_vector(pathsec_sandbox, sink, vector):
    """No model-path sink may accept any escape form."""
    root, outside = pathsec_sandbox
    path = _escape_vectors(root, outside)[vector]
    with pytest.raises((PermissionError, ValueError)):
        _SINKS[sink](path)


@pytest.mark.parametrize("sink", sorted(_SINKS))
def test_sinks_do_not_over_block_an_in_root_path(pathsec_sandbox, sink):
    """The guard must let a legitimate in-sandbox model path through.

    Each sink then fails for its own unrelated reason (no native tagger, a stub
    jar, a missing file); what matters is that the failure is NOT a containment
    refusal, which would mean the guard rejects valid models.
    """
    root, _ = pathsec_sandbox
    legit = root / "legit.model"
    legit.write_text("{}", encoding="utf-8")
    try:
        _SINKS[sink](str(legit))
    except (PermissionError, ValueError) as exc:  # pragma: no cover - failure path
        pytest.fail(f"{sink} refused an in-sandbox path: {exc}")
    except Exception:
        pass  # reached the sink; the guard allowed it


def test_model_path_guard_is_load_bearing(pathsec_sandbox, monkeypatch):
    """Negative control: neuter validate_path and the outside path reaches the
    sink, proving the guard (not an incidental error) is what refuses it."""
    import nltk.tag.crf as crf_module

    root, outside = pathsec_sandbox
    target = str(outside / "m.model")
    with pytest.raises((PermissionError, ValueError)):
        _drive_crf(target)

    monkeypatch.setattr(crf_module, "validate_path", lambda *a, **k: None)
    with pytest.raises(AttributeError):
        # past the guard, the native tagger attribute is what is missing now
        _drive_crf(target)


def test_setting_model_file_attribute_directly_reaches_no_loader():
    """Documented negative result: assigning _model_file bypasses the guard but
    reaches nothing. The only native open() is inside the guarded setter, so a
    raw attribute write leaves an inert string rather than loading a model."""
    import inspect

    import nltk.tag.crf as crf_module

    source = inspect.getsource(crf_module)
    opens = [ln.strip() for ln in source.splitlines() if "_tagger.open(" in ln]
    assert opens, "expected a native open() call in crf.py"
    for line in opens:
        assert "self._model_file" in line
    setter = inspect.getsource(crf_module.CRFTagger.set_model_file)
    assert "validate_path" in setter
    assert setter.index("validate_path") < setter.index("_tagger.open")
