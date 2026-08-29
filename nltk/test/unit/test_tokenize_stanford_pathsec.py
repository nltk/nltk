# Natural Language Toolkit: pathsec guards for the Stanford tokenizer wrappers
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Security guards for ``nltk.tokenize.stanford`` and
``nltk.tokenize.stanford_segmenter``.

Both wrappers hand caller-supplied model, dictionary, corpus and input-file
paths straight into a child JVM's argv (``-loadClassifier`` /
``-serDictionary`` / ``-sighanCorporaDict`` / ``-textFile``), which
``pathsec.open`` cannot wrap. An unbounded value there is an arbitrary file read
(GHSA-8mgp-746c-j5xp). These tests drive the real code path with only the
``java`` hand-off replaced, so a probe cannot pass merely because the test
assembled the argv itself. Each guard assertion runs WITHOUT the real Stanford
jars: the crafted attack is refused before the JVM is reached, and the benign
control stops at a trapped ``java`` rather than launching one.

SSRF is not in scope here: these wrappers invoke a local Java jar, they never
fetch a URL.
"""

import hashlib
import os

import pytest

import nltk.data
from nltk import pathsec


class _ReachedJVM(Exception):
    """Raised by the trapped ``java`` so a test can tell "the argv was built and
    handed off" apart from "a guard refused first"."""


class _MutatingPath:
    """A ``PathLike`` that answers one path the first time and another after.

    Models the ``__fspath__`` TOCTOU: a guard that validates the object and then
    lets the caller re-read it would check one file and hand a different one to
    the JVM. The wrapper must freeze the value the guard returned.
    """

    def __init__(self, first, rest):
        self._calls = 0
        self._first = first
        self._rest = rest

    def __fspath__(self):
        self._calls += 1
        return self._first if self._calls == 1 else self._rest


def _trap_java(monkeypatch, module, sink):
    """Replace ``module.java`` with a trap that records argv and stops before
    launching a JVM."""

    def fake_java(cmd, *args, **kwargs):
        sink["cmd"] = list(cmd)
        raise _ReachedJVM

    monkeypatch.setattr(module, "java", fake_java)
    return sink


def _segmenter(monkeypatch, root, model=None, dictionary=None, sihan=None):
    """A StanfordSegmenter whose jar passes the sha256 allowlist, so a benign
    call reaches the model-path handling rather than stopping at the jar check."""
    import nltk.tokenize.stanford_segmenter as seg

    jar = os.path.join(root, "seg.jar")
    with pathsec.open(jar, "wb") as handle:
        handle.write(b"PK\x05\x06" + b"\0" * 18)
    with pathsec.open(jar, "rb") as handle:
        digest = hashlib.sha256(handle.read()).hexdigest()
    monkeypatch.setenv("NLTK_SEGMENTER_ALLOW_SHA256", digest)

    tool = object.__new__(seg.StanfordSegmenter)
    tool._stanford_jar = jar
    tool._encoding = "utf8"
    tool.java_options = "-mx1g"
    tool._jar_sha256_cache = {}
    tool._java_class = "edu.stanford.nlp.ie.crf.CRFClassifier"
    tool._model = model
    tool._dict = dictionary
    tool._sihan_corpora_dict = sihan
    tool._sihan_post_processing = "true"
    tool._keep_whitespaces = "false"
    tool._options_cmd = ""
    return tool


# ---------------------------------------------------------------------------
# StanfordSegmenter: model / dictionary / sihan / input-file argv paths
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("slot", ["model", "dictionary", "sihan"])
def test_segmenter_model_paths_refuse_escape(pathsec_sandbox, monkeypatch, slot):
    """A model, dictionary or Sihan corpus dir outside the roots is refused
    before the JVM sees it."""
    import nltk.tokenize.stanford_segmenter as seg

    root, outside = pathsec_sandbox
    _trap_java(monkeypatch, seg, {})
    evil = outside / "evil.ser.gz"
    evil.write_text("payload", encoding="utf-8")
    inside = str(root / "in.txt")
    with pathsec.open(inside, "w", encoding="utf-8") as handle:
        handle.write("中文")

    tool = _segmenter(monkeypatch, str(root), **{slot: str(evil)})
    with pytest.raises((PermissionError, ValueError)):
        tool.segment_file(inside)


def test_segmenter_input_file_refuses_escape(pathsec_sandbox, monkeypatch):
    """``segment_file`` is an arbitrary-file-read primitive without a guard on
    its own argument."""
    import nltk.tokenize.stanford_segmenter as seg

    root, outside = pathsec_sandbox
    _trap_java(monkeypatch, seg, {})
    tool = _segmenter(monkeypatch, str(root))
    with pytest.raises((PermissionError, ValueError)):
        tool.segment_file(str(outside / "passwd"))


def test_segmenter_segment_sents_model_refuses_escape(pathsec_sandbox, monkeypatch):
    """The second argv-building path (``segment_sents``) stages its input under a
    data root and must reject an out-of-sandbox model just the same."""
    import nltk.tokenize.stanford_segmenter as seg

    root, outside = pathsec_sandbox
    monkeypatch.setattr(nltk.data, "_STAGING_TEMPDIR", None, raising=False)
    _trap_java(monkeypatch, seg, {})
    evil = outside / "evil.ser.gz"
    evil.write_text("payload", encoding="utf-8")

    tool = _segmenter(monkeypatch, str(root), model=str(evil))
    with pytest.raises((PermissionError, ValueError)):
        tool.segment_sents([["中文"]])


def test_segmenter_in_sandbox_paths_reach_jvm(pathsec_sandbox, monkeypatch):
    """Over-block control: legitimate in-sandbox paths must still be handed to
    the JVM, otherwise the guard has broken the feature."""
    import nltk.tokenize.stanford_segmenter as seg

    root, _outside = pathsec_sandbox
    sink = _trap_java(monkeypatch, seg, {})
    model = str(root / "model.ser.gz")
    with pathsec.open(model, "w", encoding="utf-8") as handle:
        handle.write("m")
    inside = str(root / "in.txt")
    with pathsec.open(inside, "w", encoding="utf-8") as handle:
        handle.write("中文")

    tool = _segmenter(monkeypatch, str(root), model=model)
    with pytest.raises(_ReachedJVM):
        tool.segment_file(inside)
    assert model in sink["cmd"]


def test_segmenter_model_fspath_frozen_once(pathsec_sandbox, monkeypatch):
    """A mutating ``__fspath__`` must not swap the model between the check and
    the argv: the JVM sees the validated string, coerced to a real ``str``."""
    import nltk.tokenize.stanford_segmenter as seg

    root, outside = pathsec_sandbox
    sink = _trap_java(monkeypatch, seg, {})
    good = str(root / "model.ser.gz")
    with pathsec.open(good, "w", encoding="utf-8") as handle:
        handle.write("m")
    evil = outside / "evil.ser.gz"
    evil.write_text("payload", encoding="utf-8")
    inside = str(root / "in.txt")
    with pathsec.open(inside, "w", encoding="utf-8") as handle:
        handle.write("中文")

    tool = _segmenter(monkeypatch, str(root), model=_MutatingPath(good, str(evil)))
    with pytest.raises(_ReachedJVM):
        tool.segment_file(inside)
    idx = sink["cmd"].index("-loadClassifier") + 1
    assert sink["cmd"][idx] == good
    assert type(sink["cmd"][idx]) is str
    assert str(evil) not in sink["cmd"]


# ---------------------------------------------------------------------------
# StanfordSegmenter: -options is one comma-joined argv element
# ---------------------------------------------------------------------------


def test_segmenter_options_reject_separator_injection():
    """An option NAME holding a separator would inject extra option pairs into
    the single comma-joined ``-options`` element."""
    from nltk.tokenize.stanford_segmenter import _validated_options

    with pytest.raises(ValueError):
        _validated_options({"normalize=true,serDictionary": "value"})


def test_segmenter_options_reject_empty_name():
    from nltk.tokenize.stanford_segmenter import _validated_options

    with pytest.raises(ValueError):
        _validated_options({"   ": "value"})


def test_segmenter_options_path_value_bounded(pathsec_sandbox):
    """An option VALUE that names a file is bounded to the data roots."""
    from nltk.tokenize.stanford_segmenter import _validated_options

    _root, outside = pathsec_sandbox
    with pytest.raises((PermissionError, ValueError)):
        _validated_options({"serDictionary": str(outside / "passwd")})


def test_segmenter_options_benign_pass():
    """Over-block control: ordinary options pass through unchanged."""
    from nltk.tokenize.stanford_segmenter import _validated_options

    out = _validated_options({"normalizeSpace": True, "americanize": "false"})
    assert out == {"normalizeSpace": True, "americanize": "false"}


# ---------------------------------------------------------------------------
# StanfordTokenizer: the staged input file must land inside a data root
# ---------------------------------------------------------------------------


def test_stanford_tokenizer_input_file_staged_in_data_root(
    pathsec_sandbox, monkeypatch
):
    """The temp input file is created with ``dir=staging_tempdir()``, so it lands
    inside a data root rather than the shared system temp dir."""
    import nltk.tokenize.stanford as st

    root, _outside = pathsec_sandbox
    monkeypatch.setattr(nltk.data, "_STAGING_TEMPDIR", None, raising=False)
    sink = _trap_java(monkeypatch, st, {})
    tool = object.__new__(st.StanfordTokenizer)
    tool._stanford_jar = str(root / "postagger.jar")
    tool._encoding = "utf8"
    tool.java_options = "-mx1g"
    tool._options_cmd = ""

    with pytest.raises(_ReachedJVM):
        tool._execute(["edu.stanford.nlp.process.PTBTokenizer"], "hello world")

    staged = os.path.realpath(sink["cmd"][-1])
    assert staged.startswith(os.path.realpath(str(root)) + os.sep)
