"""Regression tests for the unverified-jar / search-path fix in the Weka wrapper.

``config_weka`` searched for ``weka.jar`` with the current working directory (".")
listed first in ``_weka_search``. A ``./weka.jar`` planted in the CWD by an
attacker would be selected over a system install and run via
``java -cp ./weka.jar weka.classifiers.bayes.NaiveBayes ...`` with no integrity
check -- arbitrary code execution (CWE-494, reachable via an untrusted search
path, CWE-426). The CWD is no longer searched; ``WEKAHOME`` or an explicit
``config_weka(classpath=...)`` must be used.
"""

import os

import pytest

import nltk.classify.weka as weka

# Capture the real default search path at import time, before the autouse
# fixture neutralises it, so the regression assertion below can check it.
_DEFAULT_WEKA_SEARCH = list(weka._weka_search)


@pytest.fixture(autouse=True)
def _isolate(monkeypatch):
    # config_weka() calls config_java() first; stub it so the search logic runs
    # without a JVM, and reset the cached classpath around each test.
    monkeypatch.setattr(weka, "config_java", lambda *a, **k: None)
    monkeypatch.setattr(weka, "_weka_classpath", None)
    # Neutralise the system search path so the outcome can't depend on a
    # host-installed weka.jar (e.g. /usr/share/weka) on the test runner.
    monkeypatch.setattr(weka, "_weka_search", [])
    monkeypatch.delenv("WEKAHOME", raising=False)


def test_cwd_not_in_default_search_path():
    """The CWD must not be part of the default weka.jar search path."""
    assert "." not in _DEFAULT_WEKA_SEARCH
    assert "" not in _DEFAULT_WEKA_SEARCH


def test_cwd_weka_jar_is_not_picked_up(tmp_path, monkeypatch):
    """A ./weka.jar in the CWD must not be auto-selected."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "weka.jar").write_bytes(b"")  # attacker-planted in the CWD

    with pytest.raises(LookupError):
        weka.config_weka()
    assert weka._weka_classpath is None


def test_explicit_classpath_still_used(tmp_path):
    """An explicit classpath argument is still honoured."""
    jar = tmp_path / "weka.jar"
    jar.write_bytes(b"")
    weka.config_weka(classpath=str(jar))
    assert weka._weka_classpath == str(jar)


def test_wekahome_outside_sandbox_is_ignored(pathsec_sandbox, monkeypatch):
    """A WEKAHOME outside the pathsec-allowed roots must not be trusted: an
    attacker-controlled env var cannot add a weka.jar from an untrusted dir
    (CWE-426/CWE-427). The pathsec_sandbox fixture enforces a single data root,
    so ``outside`` is guaranteed to be outside it on every platform."""
    outside = pathsec_sandbox.outside
    (outside / "weka.jar").write_bytes(b"")  # attacker-planted jar
    monkeypatch.setenv("WEKAHOME", str(outside))
    with pytest.warns(UserWarning, match="outside the trusted"):
        with pytest.raises(LookupError):
            weka.config_weka()
    assert weka._weka_classpath is None


def test_wekahome_inside_sandbox_is_used(pathsec_sandbox, monkeypatch):
    """A WEKAHOME within the authorized data roots is honoured, so a legitimate
    install still auto-resolves. The fixture makes ``root`` the one allowed
    data root on every platform, so this does not depend on a host temp dir
    happening to be trusted."""
    root = pathsec_sandbox.root
    (root / "weka.jar").write_bytes(b"")
    monkeypatch.setenv("WEKAHOME", str(root))
    weka.config_weka()
    assert weka._weka_classpath == os.path.join(str(root), "weka.jar")


def test_train_scratch_arff_staged_inside_data_root(restricted_sandbox, monkeypatch):
    """The scratch ARFF that train() feeds to weka must be staged INSIDE an
    NLTK data root, not the shared system temp dir (CWE-377). The external java
    call is mocked, so this needs neither a JVM nor a real weka.jar; the mock
    captures the ``-t <train.arff>`` path and confirms it exists at call time."""
    data_root = restricted_sandbox
    captured = {}

    def fake_java(cmd, **kwargs):
        train_file = cmd[cmd.index("-t") + 1]
        captured["train"] = train_file
        assert os.path.exists(train_file)  # staged before weka is invoked
        return ("", "")

    monkeypatch.setattr(weka, "config_weka", lambda *a, **k: None)
    monkeypatch.setattr(weka, "java", fake_java)

    model = os.path.join(data_root, "name.model")
    featuresets = [({"a": 1, "b": 0}, "pos"), ({"a": 0, "b": 1}, "neg")]
    weka.WekaClassifier.train(model, featuresets)

    staged = os.path.realpath(captured["train"])
    root = os.path.realpath(data_root)
    # Inside-root via commonpath (Windows-drive-safe); un-hardened develop staged
    # under tempfile.gettempdir() instead, so this assertion fails against it.
    assert os.path.commonpath([staged, root]) == root


def test_arff_formatter_escapes_directive_injection():
    """A newline in a feature name or value must not inject a new ARFF directive:
    the formatter writes names/values via repr()/%r, which escapes newlines, so a
    crafted feature cannot smuggle an @ATTRIBUTE/@DATA line into the file."""
    evil = "x\n@ATTRIBUTE injected NUMERIC"
    tokens = [({evil: "v\n@DATA\n9,pwn"}, "A"), ({evil: "w"}, "B")]
    arff = weka.ARFF_Formatter.from_train(tokens).format(tokens)
    assert "\n@ATTRIBUTE injected NUMERIC\n" not in arff  # no injected header line
    assert "\n@DATA\n9,pwn" not in arff  # no injected data line
    assert "\\n@ATTRIBUTE" in arff  # the newline was escaped by repr instead
