from pathlib import Path

import pytest

import nltk.internals as internals
import nltk.parse.stanford as stanford_parser_mod
import nltk.tag.stanford as stanford_tagger_mod
import nltk.tokenize.stanford as stanford_tokenizer_mod
from nltk.parse.stanford import GenericStanfordParser
from nltk.tag.stanford import StanfordPOSTagger
from nltk.tokenize.stanford import StanfordTokenizer
from nltk.tokenize.stanford_segmenter import StanfordSegmenter


def test_java_call_options_do_not_mutate_global_java_options(monkeypatch):
    captured = {}

    class FakePopen:
        returncode = 0

        def communicate(self):
            return b"", b""

    def fake_popen(cmd, stdin=None, stdout=None, stderr=None):
        captured["cmd"] = cmd
        return FakePopen()

    monkeypatch.setattr(internals, "_java_bin", "java")
    monkeypatch.setattr(internals, "_java_options", ["-XmxGLOBAL"])
    monkeypatch.setattr(internals.subprocess, "Popen", fake_popen)

    internals.java(
        ["Main"],
        classpath=("example.jar",),
        stdout="pipe",
        stderr="pipe",
        options="-XmxLOCAL -Dexample=true",
    )

    assert captured["cmd"] == [
        "java",
        "-XmxLOCAL",
        "-Dexample=true",
        "-cp",
        "example.jar",
        "Main",
    ]
    assert internals._java_options == ["-XmxGLOBAL"]


def test_stanford_tokenizer_cleans_temp_file_when_java_raises(monkeypatch):
    captured = {}

    tokenizer = StanfordTokenizer.__new__(StanfordTokenizer)
    tokenizer._encoding = "utf-8"
    tokenizer._options_cmd = None
    tokenizer.java_options = "-XmxTOKENIZER"
    tokenizer._stanford_jar = "stanford-tokenizer.jar"

    monkeypatch.setattr(internals, "_java_options", ["-XmxGLOBAL"])

    def fake_java(cmd, classpath=None, stdout=None, stderr=None, options=None):
        temp_path = Path(cmd[-1])
        captured["temp_path"] = temp_path
        captured["input_text"] = temp_path.read_text(encoding="utf-8")
        captured["options"] = options
        raise OSError("forced java failure")

    monkeypatch.setattr(stanford_tokenizer_mod, "java", fake_java)

    with pytest.raises(OSError, match="forced java failure"):
        tokenizer._execute(["edu.stanford.nlp.process.PTBTokenizer"], "secret text")

    assert captured["input_text"] == "secret text"
    assert captured["options"] == "-XmxTOKENIZER"
    assert not captured["temp_path"].exists()
    assert internals._java_options == ["-XmxGLOBAL"]


def test_stanford_tokenizer_raises_unlink_error_after_java_success(monkeypatch):
    captured = {}
    original_unlink = stanford_tokenizer_mod.os.unlink

    tokenizer = StanfordTokenizer.__new__(StanfordTokenizer)
    tokenizer._encoding = "utf-8"
    tokenizer._options_cmd = None
    tokenizer.java_options = "-XmxTOKENIZER"
    tokenizer._stanford_jar = "stanford-tokenizer.jar"

    def fake_java(cmd, classpath=None, stdout=None, stderr=None, options=None):
        return b"secret\n", b""

    def fake_unlink(path):
        captured["temp_path"] = Path(path)
        raise PermissionError("cannot remove temp file")

    monkeypatch.setattr(stanford_tokenizer_mod, "java", fake_java)
    monkeypatch.setattr(stanford_tokenizer_mod.os, "unlink", fake_unlink)

    try:
        with pytest.raises(PermissionError, match="cannot remove temp file"):
            tokenizer._execute(["edu.stanford.nlp.process.PTBTokenizer"], "secret text")
    finally:
        if "temp_path" in captured:
            original_unlink(captured["temp_path"])


def test_stanford_tokenizer_preserves_java_error_when_cleanup_also_fails(
    monkeypatch,
):
    captured = {}
    original_unlink = stanford_tokenizer_mod.os.unlink

    tokenizer = StanfordTokenizer.__new__(StanfordTokenizer)
    tokenizer._encoding = "utf-8"
    tokenizer._options_cmd = None
    tokenizer.java_options = "-XmxTOKENIZER"
    tokenizer._stanford_jar = "stanford-tokenizer.jar"

    def fake_java(cmd, classpath=None, stdout=None, stderr=None, options=None):
        raise OSError("forced java failure")

    def fake_unlink(path):
        captured["temp_path"] = Path(path)
        raise PermissionError("cannot remove temp file")

    monkeypatch.setattr(stanford_tokenizer_mod, "java", fake_java)
    monkeypatch.setattr(stanford_tokenizer_mod.os, "unlink", fake_unlink)

    try:
        with pytest.raises(OSError, match="forced java failure"):
            tokenizer._execute(["edu.stanford.nlp.process.PTBTokenizer"], "secret text")
    finally:
        if "temp_path" in captured:
            original_unlink(captured["temp_path"])


def test_stanford_parser_cleans_temp_file_when_java_raises(monkeypatch):
    captured = {}

    parser = GenericStanfordParser.__new__(GenericStanfordParser)
    parser._encoding = "utf-8"
    parser.corenlp_options = ""
    parser._classpath = ("stanford-parser.jar",)
    parser.java_options = ["-XmxPARSER"]
    parser._USE_STDIN = False

    monkeypatch.setattr(internals, "_java_options", ["-XmxGLOBAL"])

    def fake_java(cmd, classpath=None, stdout=None, stderr=None, options=None):
        temp_path = Path(cmd[-1])
        captured["temp_path"] = temp_path
        captured["input_text"] = temp_path.read_text(encoding="utf-8")
        captured["options"] = options
        raise OSError("forced parser failure")

    monkeypatch.setattr(stanford_parser_mod, "java", fake_java)

    with pytest.raises(OSError, match="forced parser failure"):
        parser._execute(
            ["edu.stanford.nlp.parser.lexparser.LexicalizedParser"], "parse me"
        )

    assert captured["input_text"] == "parse me"
    assert captured["options"] == ["-XmxPARSER"]
    assert not captured["temp_path"].exists()
    assert internals._java_options == ["-XmxGLOBAL"]


def test_stanford_tagger_cleans_temp_file_when_java_raises(monkeypatch):
    captured = {}

    tagger = StanfordPOSTagger.__new__(StanfordPOSTagger)
    tagger._encoding = "utf-8"
    tagger._stanford_jar = "stanford-postagger.jar"
    tagger._stanford_model = "english.tagger"
    tagger.java_options = ["-XmxTAGGER"]

    monkeypatch.setattr(internals, "_java_options", ["-XmxGLOBAL"])

    def fake_java(cmd, classpath=None, stdout=None, stderr=None, options=None):
        temp_path = Path(cmd[cmd.index("-textFile") + 1])
        captured["temp_path"] = temp_path
        captured["input_text"] = temp_path.read_text(encoding="utf-8")
        captured["options"] = options
        raise OSError("forced tagger failure")

    monkeypatch.setattr(stanford_tagger_mod, "java", fake_java)

    with pytest.raises(OSError, match="forced tagger failure"):
        tagger.tag_sents([["secret", "tokens"]])

    assert captured["input_text"] == "secret tokens"
    assert captured["options"] == ["-XmxTAGGER"]
    assert not captured["temp_path"].exists()
    assert internals._java_options == ["-XmxGLOBAL"]


def test_stanford_segmenter_cleans_temp_file_when_execute_raises():
    captured = {}

    segmenter = StanfordSegmenter.__new__(StanfordSegmenter)
    segmenter._encoding = "UTF-8"
    segmenter._java_class = "edu.stanford.nlp.ie.crf.CRFClassifier"
    segmenter._model = "segmenter-model.ser.gz"
    segmenter._keep_whitespaces = "false"
    segmenter._sihan_corpora_dict = None

    def fake_execute(cmd):
        temp_path = Path(cmd[cmd.index("-textFile") + 1])
        captured["temp_path"] = temp_path
        captured["input_text"] = temp_path.read_text(encoding="utf-8")
        raise RuntimeError("forced segmenter failure")

    segmenter._execute = fake_execute

    with pytest.raises(RuntimeError, match="forced segmenter failure"):
        segmenter.segment_sents([["secret", "tokens"]])

    assert captured["input_text"] == "secret tokens"
    assert not captured["temp_path"].exists()
