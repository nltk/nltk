# Natural Language Toolkit: Stanford wrapper argument-injection regression
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""The Stanford model path and the JVM option list must not be injectable.

Covers CVE-2026-12841 / GHSA-m4rf-3fr8-xwx3 (JVM argument injection via the
per-call options), the cmd[0]/@argfile guard, and the JVM-injecting environment
variables stripped from the child. StanfordTagger bounds its model with
validate_tool_path, which refuses a leading-dash token that would become a tool
flag, plus traversal / out-of-root / NUL.
"""

import os

import pytest

from nltk import internals
from nltk.pathsec import validate_tool_path


@pytest.mark.parametrize(
    "model",
    ["-loadClassifier", "-props", "/etc/passwd", "../../etc/passwd", "ok\x00.tagger"],
)
def test_stanford_model_path_is_bounded(model):
    """The value StanfordTagger hands the JVM as its model argument."""
    with pytest.raises((PermissionError, ValueError)):
        validate_tool_path(model, context="StanfordTagger.tag_sents")


_INJECTION_OPTIONS = [
    ["-jar"],
    ["@/tmp/f"],
    ["-XX:OnError=touch /tmp/x"],
    ["-XX:OnOutOfMemoryError=x"],
    ["-Djava.ext.dirs=/tmp"],
    ["-Djava.rmi.server.codebase=http://x/"],
    ["-javaagent:/tmp/a.jar"],
    ["-agentlib:jdwp=transport=dt_socket"],
    ["--module-path=/tmp/evil"],
    ["-p", "/tmp"],
    ["-Xmx512m ; rm -rf /"],
    ["-Xmx$(id)"],
    ["-verbose:gc\n-XX:OnError=x"],
    ["--add-modules", "a$(id)"],
]


@pytest.mark.parametrize("options", _INJECTION_OPTIONS)
def test_injection_java_options_are_rejected(options):
    with pytest.raises(ValueError):
        internals._validate_java_options(options)


def test_benign_java_options_pass():
    internals._validate_java_options(
        ["-Xmx512m", "-verbose:gc", "-server", "--add-modules", "java.se.ee"]
    )


@pytest.mark.parametrize(
    "var",
    [
        "JAVA_TOOL_OPTIONS",
        "_JAVA_OPTIONS",
        "JDK_JAVA_OPTIONS",
        "IBM_JAVA_OPTIONS",
        "OPENJ9_JAVA_OPTIONS",
        "CLASSPATH",
    ],
)
def test_jvm_injecting_env_vars_are_stripped(monkeypatch, var):
    monkeypatch.setenv(var, "-XX:OnError=touch /tmp/pwned")
    child = internals._java_child_env()
    assert var not in child
    assert "PATH" in child  # ordinary env survives


@pytest.mark.parametrize(
    "cmd", [["-jar"], [" -version"], ["\t@/tmp/f"], ["Main", "@/tmp/f"]]
)
def test_cmd0_and_argfile_are_rejected(cmd):
    with pytest.raises((ValueError, internals.UntrustedJarError, OSError)):
        internals.java(cmd, classpath=None)
