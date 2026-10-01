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


def test_stanford_parser_handles_str_output(monkeypatch, tmp_path):
    from nltk.parse import stanford as sp

    jar = tmp_path / "stanford-parser.jar"
    jar.write_bytes(b"PK\x03\x04")
    models = tmp_path / "stanford-parser-4.2.0-models.jar"
    models.write_bytes(b"PK\x03\x04")
    monkeypatch.setattr(sp, "find_jar_iter", lambda *a, **k: iter([str(jar)]))
    monkeypatch.setattr(sp, "find_jars_within_path", lambda d: [str(jar), str(models)])
    parser = sp.StanfordParser(path_to_jar=str(jar), path_to_models_jar=str(models))

    # java() returns str; the parser must not b"...".replace()/decode() it.
    tree_out = "(ROOT (S (NP (DT the) (NN fox)) (VP (VBZ runs))))\n\n"
    monkeypatch.setattr(sp, "java", lambda *a, **k: (tree_out, ""))
    tree = list(parser.raw_parse("the fox runs"))[0]
    assert tree.label() == "ROOT"
    assert "VP" in [t.label() for t in tree.subtrees()]


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


def test_corenlp_server_start_error_handles_str_stderr(monkeypatch):
    """CoreNLPServer.start() reads the server's stderr via popen.communicate();
    java()'s Popen is text-mode, so that is a str and must not be .decode()d."""
    from nltk.parse import corenlp

    monkeypatch.setattr(
        corenlp,
        "find_jar_iter",
        lambda *a, **k: iter(["/x/stanford-corenlp-4.0.0.jar"]),
    )
    monkeypatch.setattr(corenlp, "try_port", lambda *a, **k: 9000)
    monkeypatch.setattr(corenlp, "config_java", lambda *a, **k: None)

    class _DeadPopen:
        def poll(self):
            return 1  # server exited immediately

        def communicate(self):
            return ("", "boom: CoreNLP failed to start")  # str, like text-mode Popen

    monkeypatch.setattr(corenlp, "java", lambda *a, **k: _DeadPopen())
    server = corenlp.CoreNLPServer(
        path_to_jar="/x/stanford-corenlp-4.0.0.jar",
        path_to_models_jar="/x/stanford-corenlp-4.0.0-models.jar",
    )
    with pytest.raises(corenlp.CoreNLPServerError) as exc:
        server.start()
    assert "boom" in str(exc.value)  # str stderr surfaced, no AttributeError


@pytest.mark.parametrize(
    "modname",
    [
        "nltk.tag.stanford",
        "nltk.tokenize.stanford",
        "nltk.parse.stanford",
        "nltk.tokenize.stanford_segmenter",
        "nltk.classify.weka",
        "nltk.parse.corenlp",
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
