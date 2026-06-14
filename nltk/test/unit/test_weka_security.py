"""Regression tests for the unverified-jar / search-path fix in the Weka wrapper.

``config_weka`` searched for ``weka.jar`` with the current working directory (".")
listed first in ``_weka_search``. A ``./weka.jar`` planted in the CWD by an
attacker would be selected over a system install and run via
``java -cp ./weka.jar weka.classifiers.bayes.NaiveBayes ...`` with no integrity
check -- arbitrary code execution (CWE-494, reachable via an untrusted search
path, CWE-426). The CWD is no longer searched; ``WEKAHOME`` or an explicit
``config_weka(classpath=...)`` must be used.
"""

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
