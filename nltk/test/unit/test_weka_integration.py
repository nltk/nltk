"""End-to-end integration test for the Weka wrapper with the real weka.jar + JVM.

Skipped unless a Java runtime and a ``weka.jar`` are actually available (set
``WEKA_JAR`` or install under ``~/nltk_data/weka/weka.jar``), so it exercises the
real train/classify round trip -- proving the ``config_weka`` sandbox-bounding
change does not break legitimate use -- without ever mocking the JVM.
"""

import os
import shutil

import pytest


def _weka_jar():
    for cand in (
        os.environ.get("WEKA_JAR"),
        os.path.join(os.path.expanduser("~/nltk_data/weka"), "weka.jar"),
        "/usr/share/weka/weka.jar",
        "/usr/local/share/weka/weka.jar",
    ):
        if cand and os.path.exists(cand):
            return cand
    return None


@pytest.mark.skipif(shutil.which("java") is None, reason="no Java runtime on PATH")
def test_real_weka_train_and_classify(tmp_path):
    """Train a NaiveBayes model with the real jar and classify two instances."""
    jar = _weka_jar()
    if jar is None:
        pytest.skip("weka.jar not available")

    import nltk.classify.weka as wk
    from nltk.classify.weka import WekaClassifier

    wk._weka_classpath = None
    train = [
        ({"a": 1, "b": 0}, "pos"),
        ({"a": 1, "b": 0}, "pos"),
        ({"a": 1, "b": 1}, "pos"),
        ({"a": 0, "b": 1}, "neg"),
        ({"a": 0, "b": 1}, "neg"),
        ({"a": 0, "b": 0}, "neg"),
    ]
    model = str(tmp_path / "weka.model")
    try:
        wk.config_weka(classpath=jar)
        clf = WekaClassifier.train(model, train, classifier="naivebayes")
        preds = clf.classify_many([{"a": 1, "b": 0}, {"a": 0, "b": 1}])
    except (LookupError, OSError) as exc:
        # a JDK-less runtime (e.g. the macOS /usr/bin/java stub) cannot execute
        pytest.skip(f"weka/java not runnable here: {str(exc)[:60]}")
    assert preds == ["pos", "neg"]


@pytest.mark.skipif(shutil.which("java") is None, reason="no Java runtime on PATH")
def test_real_weka_version_read_through_secure_zip(tmp_path):
    """_check_weka_version reads weka/core/version.txt from the real jar."""
    jar = _weka_jar()
    if jar is None:
        pytest.skip("weka.jar not available")
    from nltk.classify.weka import _check_weka_version

    version = _check_weka_version(jar)
    assert version and version.strip()
