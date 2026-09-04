"""Adversarial coverage for the WekaClassifier JVM-subprocess and ARFF surfaces.

WekaClassifier drives the weka JVM through ``nltk.internals.java`` and writes ARFF
files the JVM reads. Beyond the model-path containment already pinned in
test_weka_model_path_security (GHSA-j456-xh4h-cpf2), a Python wrapper around a JVM
tool is exposed to the vector classes seen across the ecosystem:

- JVM argument injection through the caller option list or the model path
  (``@argfile`` / ``-javaagent``, CVE-2026-12841 / CWE-88);
- an untrusted classpath jar, an out-of-root ``WEKAHOME`` or a current-directory
  ``weka.jar`` (CWE-426 / CWE-427 / CWE-494);
- a decompression bomb in the jar's ``version.txt`` (CWE-409);
- ARFF structural injection through a feature value, a class label, or a feature
  type (CWE-1236);
- classifier-class injection (only the known weka classes may run).

Nothing is mocked at the security boundary: the guards that fire are the real
``internals.java`` / ``pathsec`` / ARFF checks. ``config_weka`` is stubbed only so
the flow can reach ``internals.java`` without a local weka install, and the
classpath is a real file staged inside a trusted data root.

Residual, out of Python's reach: weka's ``-l`` deserializes a Java-serialized
model, so a *malicious model already inside a data root* could still trigger
Java-side deserialization (CWE-502). Containment (the model path must resolve
inside a data root) is the mitigation this layer can provide; it does not make
loading an attacker-authored in-root model safe.
"""

import os

import pytest

import nltk
from nltk.classify import weka
from nltk.classify.weka import ARFF_Formatter, WekaClassifier
from nltk.internals import UntrustedJarError

FEATS = [({"a": 1}, "x"), ({"a": 2}, "y")]


def _staged_root(prefix="weka_sec_"):
    try:
        return nltk.data.make_staging_dir(prefix=prefix, cleanup=True)
    except PermissionError as exc:  # pragma: no cover - env-dependent
        pytest.skip(f"no writable in-sandbox NLTK data root: {exc}")


@pytest.fixture
def trusted_weka(monkeypatch):
    """A trusted-path weka.jar in a data root plus a no-op config_weka, so the
    flow reaches internals.java (which owns the @argfile / classpath guards)."""
    root = _staged_root()
    jar = os.path.join(root, "weka.jar")
    with open(jar, "wb") as handle:
        handle.write(b"PK\x03\x04")  # zip magic; path trust is what is exercised
    monkeypatch.setattr(weka, "config_weka", lambda *a, **k: None)
    monkeypatch.setattr(weka, "_weka_classpath", jar)
    return root, jar


# --- JVM argument injection (CVE-2026-12841 / CWE-88) --------------------------


@pytest.mark.parametrize("evil", ["@/etc/passwd", "@argfile", "\t@sneaky"])
def test_train_option_argfile_is_refused(trusted_weka, evil):
    """A caller weka option that is an @argfile token must be refused: the Java
    launcher expands @argfiles anywhere on the line, injecting JVM arguments."""
    root, _ = trusted_weka
    model = os.path.join(root, "m.model")
    with pytest.raises(ValueError, match="argfile"):
        WekaClassifier.train(model, FEATS, options=[evil])


def test_classify_option_argfile_is_refused(trusted_weka):
    root, _ = trusted_weka
    model = os.path.join(root, "m.model")
    clf = WekaClassifier(ARFF_Formatter.from_train(FEATS), model)
    with pytest.raises(ValueError, match="argfile"):
        clf._classify_many([{"a": 1}], ["-p", "0", "@/etc/passwd"])


# --- untrusted classpath jar (CWE-494) ----------------------------------------


def test_untrusted_classpath_jar_is_refused(monkeypatch):
    """internals.java refuses a classpath jar that resolves outside the trusted
    data roots, so a planted weka.jar cannot load arbitrary Java classes."""
    monkeypatch.setattr(weka, "config_weka", lambda *a, **k: None)
    monkeypatch.setattr(weka, "_weka_classpath", "/tmp/evil-weka.jar")
    root = _staged_root()
    model = os.path.join(root, "m.model")
    with pytest.raises(UntrustedJarError):
        WekaClassifier.train(model, FEATS)


def test_current_directory_is_not_a_weka_search_path():
    """A weka.jar in the CWD must never be picked up (CWE-426/427/494)."""
    assert "." not in weka._weka_search
    assert os.curdir not in weka._weka_search
    assert not any(os.path.abspath(p) == os.getcwd() for p in weka._weka_search)


# --- WEKAHOME containment (CWE-426) -------------------------------------------


def test_wekahome_outside_roots_is_ignored(monkeypatch):
    """An attacker-influenceable WEKAHOME pointing outside the trusted roots is
    dropped with a warning, not added to the classpath search."""
    monkeypatch.setattr(weka, "_weka_classpath", None)
    monkeypatch.setattr(weka, "config_java", lambda *a, **k: None)
    monkeypatch.setenv("WEKAHOME", "/tmp/evil-weka")
    with pytest.warns(UserWarning, match="outside the trusted"):
        with pytest.raises(LookupError):  # nothing found in the trusted dirs
            weka.config_weka()


# --- classifier-class allowlist ------------------------------------------------


def test_unknown_classifier_class_is_refused(trusted_weka):
    root, _ = trusted_weka
    model = os.path.join(root, "m.model")
    with pytest.raises(ValueError, match="Unknown classifier"):
        WekaClassifier.train(model, FEATS, classifier="weka.evil.RuntimeExec")


# --- ARFF structural injection (CWE-1236) -------------------------------------


@pytest.mark.parametrize(
    "hostile",
    ["x\n@ATTRIBUTE evil NUMERIC", "a\r\n@DATA", "lbl,inject", "a'b", "%comment"],
)
def test_arff_label_injection_is_sanitized(hostile):
    """A class label cannot introduce a newline, an ARFF separator, or an
    unescaped quote into the header or data section."""
    out = ARFF_Formatter._sanitize_arff_label(hostile)
    assert "\n" not in out and "\r" not in out and "\t" not in out
    assert "," not in out
    assert out.count("'") % 2 == 0  # quotes are doubled, never left dangling


def test_arff_feature_value_injection_is_escaped():
    """A string feature value carrying a newline and ARFF directives must not
    inject a new @ATTRIBUTE/@DATA line; repr escapes the newline to a literal."""
    fmt = ARFF_Formatter(["x", "y"], [("f", "STRING")])
    payload = "v\n@ATTRIBUTE evil NUMERIC\n@DATA\n0"
    data = fmt.data_section([({"f": payload}, "x")])
    body = data.split("@DATA", 1)[1]
    assert "\n@ATTRIBUTE" not in body
    assert "\n@DATA" not in body


@pytest.mark.parametrize(
    "bad", ["STRING\n@ATTRIBUTE evil NUMERIC", "NUMERIC\t}", "a\r"]
)
def test_arff_feature_type_control_char_is_refused(bad):
    """A caller-supplied feature TYPE with a control character would break out of
    the @ATTRIBUTE line, so building the header refuses it."""
    fmt = ARFF_Formatter(["x"], [("f", bad)])
    with pytest.raises(ValueError, match="control characters"):
        fmt.header_section()


# --- functionality: a legitimate corpus still formats and round-trips ----------


def test_legit_arff_still_formats():
    """The guards must not disturb ordinary ARFF generation."""
    toks = [({"a": 1, "s": "hi"}, "pos"), ({"a": 2, "s": "bye"}, "neg")]
    fmt = ARFF_Formatter.from_train(toks)
    text = fmt.format(toks)
    assert "@RELATION" in text and "@DATA" in text
    assert sorted(fmt.labels()) == ["neg", "pos"]
    assert [t for _, t in fmt._features] == ["NUMERIC", "STRING"]


def test_legit_model_path_write_roundtrips(tmp_path):
    """A legitimate in-root model path and ARFF file still work end to end at the
    boundary (up to the point weka itself would be invoked)."""
    root = _staged_root()
    fmt = ARFF_Formatter.from_train(FEATS)
    arff = os.path.join(root, "train.arff")
    fmt.write(arff, FEATS)
    with open(arff) as handle:
        assert "@DATA" in handle.read()
