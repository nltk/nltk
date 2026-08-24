"""Regression tests: nltk.internals.java() returns text (universal_newlines=True),
so the Java wrappers must not call ``.decode()`` on its (already-str) output. A
bytes-era ``stdout.decode(...)`` raised AttributeError and broke Stanford tagging,
tokenizing, parsing and Weka classification whenever a real JVM ran.
"""

import pytest


def test_stanford_pos_tagger_handles_str_output(monkeypatch, tmp_path):
    from nltk.tag import stanford as st

    jar = tmp_path / "stanford-postagger.jar"
    jar.write_bytes(b"PK\x03\x04")
    model = tmp_path / "m.tagger"
    model.write_text("x")
    monkeypatch.setattr(st, "find_jar", lambda *a, **k: str(jar))
    monkeypatch.setattr(st, "find_file", lambda *a, **k: str(model))
    tagger = st.StanfordPOSTagger(model_filename=str(model), path_to_jar=str(jar))

    # java() returns str (universal_newlines); tagging must not .decode() it.
    monkeypatch.setattr(st, "java", lambda *a, **k: ("The_DT fox_NN ._.\n", ""))
    result = tagger.tag(["The", "fox", "."])
    assert result == [("The", "DT"), ("fox", "NN"), (".", ".")]


def test_stanford_tokenizer_handles_str_output(monkeypatch, tmp_path):
    from nltk.tokenize import stanford as st

    jar = tmp_path / "stanford-postagger.jar"
    jar.write_bytes(b"PK\x03\x04")
    monkeypatch.setattr(st, "find_jar", lambda *a, **k: str(jar))
    tok = st.StanfordTokenizer(path_to_jar=str(jar))

    monkeypatch.setattr(st, "java", lambda *a, **k: ("Hello\n,\nworld\n!\n", ""))
    assert tok.tokenize("Hello, world!") == ["Hello", ",", "world", "!"]


def test_weka_classifier_handles_str_output(monkeypatch, tmp_path):
    from nltk.classify import weka as wk

    # bypass jar discovery / java, feed a str weka report through the parser path
    monkeypatch.setattr(wk, "config_weka", lambda *a, **k: None)
    monkeypatch.setattr(
        wk, "_weka_classpath", str(tmp_path / "weka.jar"), raising=False
    )

    class _Fmt:
        def write(self, *a, **k):
            pass

        def labels(self):
            return ["yes", "no"]

    report = "inst# actual predicted error prediction\n1 1:? 2:no 0.9\n"
    monkeypatch.setattr(wk, "java", lambda *a, **k: (report, ""))
    clf = wk.WekaClassifier(_Fmt(), str(tmp_path / "model"))
    # must not raise AttributeError on str .decode(); returns parsed predictions
    out = clf.classify_many([{"a": 1}])
    assert out == ["no"]


@pytest.mark.parametrize(
    "modname",
    [
        "nltk.tag.stanford",
        "nltk.tokenize.stanford",
        "nltk.parse.stanford",
        "nltk.tokenize.stanford_segmenter",
        "nltk.classify.weka",
    ],
)
def test_wrapper_guards_decode_with_isinstance(modname):
    """Every wrapper that decodes java() output must guard it with isinstance(...,
    bytes) so it is safe on the str java() now returns."""
    import importlib
    import inspect

    src = inspect.getsource(importlib.import_module(modname))
    if ".decode(" in src:
        assert (
            "isinstance(" in src and "bytes" in src
        ), f"{modname} calls .decode() without an isinstance(..., bytes) guard"
