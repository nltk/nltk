# Natural Language Toolkit: Java source-file-mode command injection tests
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""Regression tests for the JEP 330 source-file-mode execution channel in java().

nltk.internals.java() validates its JVM ``options`` and screens ``classpath=``
through ``_verify_jar_sandbox``, and it rejects a ``cmd[0]`` that is a launcher
switch (-jar, @argfile). It did NOT reject a ``cmd[0]`` that names a ``.java``
source file. On JDK 11 and later the launcher compiles and runs such a file in
source-file mode (JEP 330) when it is the first non-option argument, so a
caller-influenced ``cmd[0]`` of ``/path/Evil.java`` (or a relative ``Evil.java``
resolved against the untrusted working directory) executes arbitrary code with
no -jar / @argfile token and without ``NLTK_ALLOW_UNSAFE_JARS`` (CWE-94). The
jar sandbox never sees it: it inspects ``classpath=`` only, never ``cmd``.

The fix requires ``cmd[0]`` to have the shape of a Java main class (a dotted run
of Java identifiers) and refuses the launcher's source and archive suffixes.
These tests assert the guard refuses every attack form before any spawn (so no
JVM is needed to run them) and still accepts every real NLTK main-class name.
"""

import os
import re
import subprocess

import pytest

from nltk import internals
from nltk.internals import _is_java_main_class, _reject_non_main_class, java

# Tokens the Java launcher would compile or run, or that are filesystem paths.
# A main class is never any of these.
ATTACK_FIRST_TOKENS = [
    "/abs/Evil.java",
    "Evil.java",
    "./evil.java",
    "com.example.Main.java",
    "Main.JAVA",
    "  /tmp/Evil.java  ",
    "C:\\Evil.java",
    "/tmp/payload.jar",
    "payload.jar",
    "evil.jmod",
    "Main.class",
    "a/b/Main",
    "..\\Main",
    "pkg/Main",
]

# Every main-class token NLTK's own Java wrappers pass, plus simple and inner
# class names a caller may legitimately use.
BENIGN_MAIN_CLASSES = [
    "edu.stanford.nlp.process.PTBTokenizer",
    "edu.stanford.nlp.pipeline.StanfordCoreNLPServer",
    "edu.stanford.nlp.tagger.maxent.MaxentTagger",
    "edu.stanford.nlp.ie.crf.CRFClassifier",
    "edu.stanford.nlp.international.arabic.process.ArabicSegmenter",
    "org.maltparser.Malt",
    "Main",
    "com.foo.Bar$Inner",
    "my_pkg.Main2",
]


@pytest.mark.parametrize("token", ATTACK_FIRST_TOKENS)
def test_reject_non_main_class_refuses_attack_tokens(token):
    """A source file, archive or path as cmd[0] is refused by the shape guard."""
    with pytest.raises(ValueError, match="main class"):
        _reject_non_main_class(token)


@pytest.mark.parametrize("token", BENIGN_MAIN_CLASSES)
def test_reject_non_main_class_accepts_real_main_classes(token):
    """Every real NLTK main-class name passes the shape guard (no over-block)."""
    _reject_non_main_class(token)
    assert _is_java_main_class(token)


def test_dotted_java_suffix_is_refused_even_though_identifier_shaped():
    """``com.example.Main.java`` is identifier-shaped but a source file to the
    launcher, so the suffix check must refuse it before the shape check accepts it.
    """
    with pytest.raises(ValueError, match="source or archive"):
        _reject_non_main_class("com.example.Main.java")


def test_java_refuses_source_file_cmd0_before_spawning(tmp_path):
    """java() refuses a .java source-file cmd[0] and never reaches the JVM.

    The end-to-end teeth: a real source file is planted and passed as the first
    command token exactly as the exploit does. The guard raises ValueError
    before the JVM is resolved or spawned (so this needs no JDK), and the
    program the source file would write is never created. Without the fix java()
    runs the source file in JEP 330 mode and the marker appears.
    """
    src = tmp_path / "Evil.java"
    marker = tmp_path / "pwned.txt"
    src.write_text(
        "import java.io.FileWriter;\n"
        "public class Evil {\n"
        "  public static void main(String[] a) throws Exception {\n"
        '    try (FileWriter w = new FileWriter(a[0])) { w.write("x"); }\n'
        "  }\n}\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="source or archive|main class"):
        java([os.fspath(src), os.fspath(marker)], stdout="pipe", stderr="pipe")
    assert not marker.exists()


def test_java_still_rejects_launcher_switches():
    """The pre-existing -jar / @argfile refusals are unchanged by the new guard."""
    with pytest.raises(ValueError, match="launcher switch|@argfile"):
        java(["-jar", "/tmp/x.jar"], stdout="pipe", stderr="pipe")
    with pytest.raises(ValueError, match="@argfile|launcher switch|main class"):
        java(["@/tmp/argfile"], stdout="pipe", stderr="pipe")


def _jdk_major(java_bin):
    """Major version of the launcher at *java_bin* (8 for the 1.8 line), or
    None when the binary prints no version banner: macOS ships a
    ``/usr/bin/java`` stub that exists but has no runtime behind it."""
    banner = subprocess.run(
        [java_bin, "-version"], capture_output=True, text=True, timeout=60, check=False
    ).stderr
    match = re.search(r'version "(\d+)(?:\.(\d+))?', banner)
    if match is None:
        return None
    major = int(match.group(1))
    return int(match.group(2)) if major == 1 else major


@pytest.mark.parametrize(
    "filename", ["Evil.java", "EVIL2.JAVA", "com.example.Evil.java"]
)
def test_source_file_mode_is_real_on_this_jdk(tmp_path, monkeypatch, filename):
    """With the guard bypassed, the real launcher on this machine runs a planted
    source file passed as cmd[0] on JDK 11 and later, in every spelling the
    guard refuses (plain, upper-case suffix, dotted), and cannot on JDK 8. This
    pins the guard to the launcher's actual behaviour rather than to a belief
    about it: the suffix match must be case-insensitive because the launcher's
    is, and the dotted form must be caught by the suffix check first.
    """
    monkeypatch.setattr(internals, "_java_bin", None)
    monkeypatch.setattr(internals, "_java_options", [])
    try:
        internals.config_java()
    except LookupError:
        pytest.skip("no Java binary found on this machine")
    major = _jdk_major(internals._java_bin)
    if major is None:
        pytest.skip(f"{internals._java_bin} is a launcher stub with no runtime")
    src = tmp_path / filename
    marker = tmp_path / "pwned.txt"
    src.write_text(
        "public class Evil {\n"
        "  public static void main(String[] a) throws Exception {\n"
        '    try (java.io.FileWriter w = new java.io.FileWriter(a[0])) { w.write("x"); }\n'
        "  }\n}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(internals, "_reject_non_main_class", lambda first: None)
    if major >= 11:
        java([os.fspath(src), os.fspath(marker)], stdout="pipe", stderr="pipe")
        assert marker.exists(), "JEP 330 did not run the planted source"
    else:
        with pytest.raises(OSError):
            java([os.fspath(src), os.fspath(marker)], stdout="pipe", stderr="pipe")
        assert not marker.exists()
