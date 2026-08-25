"""GHSA-m4rf-3fr8-xwx3 [high] -- JVM argument injection bypass via per-call options in the NLTK Stanford wrappers (incomplete fix of CVE-2026-12841)"""

from ._base import FIXED, STATIC, VULNERABLE, probe

#: Every argument class that can change the executed program, run a shell command,
#: load an agent, redirect class loading, crack the module system open or expand an
#: argument file. The per-call ``options=`` channel must refuse all of them.
HOSTILE_OPTIONS = (
    # boot classpath: attacker classes shadow java.* before anything runs
    "-Xbootclasspath/a:/tmp/evil.jar",
    "-Xbootclasspath/p:/tmp/evil.jar",
    "-Xbootclasspath:/tmp/evil.jar",
    # native and Java agents: arbitrary code before main()
    "-agentlib:jdwp=transport=dt_socket,server=y,address=5005",
    "-agentpath:/tmp/evil.so",
    "-javaagent:/tmp/evil.jar",
    "-Xrunjdwp:transport=dt_socket,server=y,address=5005",
    "-Xdebug",
    "-Xnoagent",
    # -XX: flags the JVM hands to a shell, or that unlock the restricted rest
    "-XX:OnError=/bin/sh",
    "-XX:OnOutOfMemoryError=/bin/sh",
    "-XX:+UnlockDiagnosticVMOptions",
    "-XX:+UnlockExperimentalVMOptions",
    "-XX:Flags=/tmp/evil.flags",
    "-XX:CompileCommandFile=/tmp/evil",
    "-XX:SharedArchiveFile=/tmp/evil.jsa",
    "-XX:+HeapDumpOnOutOfMemoryError",
    "-XX:HeapDumpPath=/tmp/steal",
    "-XX:ErrorFile=/tmp/steal",
    # -D properties that redirect code loading or disarm the sandbox
    "-Djava.security.policy=/tmp/all.policy",
    "-Djava.security.manager=allow",
    "-Djava.class.path=/tmp/evil.jar",
    "-Djava.library.path=/tmp/evil",
    "-Djava.ext.dirs=/tmp/evil",
    "-Djava.rmi.server.codebase=http://evil.example/",
    "-Djdk.attach.allowAttachSelf=true",
    "-Dcom.sun.management.jmxremote.port=9999",
    # classpath / module path injected here never reaches _verify_jar_sandbox,
    # which only inspects the classpath= argument
    "-cp",
    "-classpath",
    "--class-path=/tmp/evil.jar",
    "-p",
    "--module-path=/tmp/evil",
    "--upgrade-module-path=/tmp/evil",
    "-Xpatch:java.base=/tmp/evil",
    # module system escapes
    "--patch-module=java.base=/tmp/evil",
    "--add-opens=java.base/java.lang=ALL-UNNAMED",
    "--add-exports=java.base/jdk.internal.misc=ALL-UNNAMED",
    "--add-reads=java.base=ALL-UNNAMED",
    # run something other than the main class the caller named
    "-jar",
    "-m",
    "--module=evil/Main",
    "-Xshare:dump",
    "-Xverify:none",
    "-splash:/tmp/x.png",
    # @argfiles are expanded by the launcher first, smuggling every flag above
    "@/tmp/evil.args",
    "@evil.args",
    # one element carrying two options: a per-element filter must reject the whole
    # token, and a splitting one must validate every piece, not just the first
    "-Xmx1g -javaagent:/tmp/evil.jar",
    "-Xmx1g\t-javaagent:/tmp/evil.jar",
    "-Xmx1g\n-javaagent:/tmp/evil.jar",
    "-Xmx1g\x00-javaagent:/tmp/evil.jar",
    "-Xmx512m;rm -rf /",
    "-Xmx512m`id`",
    "-Xmx512m$(id)",
    # hostile flag hiding behind a legitimate one, and in the value slot of the
    # single multi-token flag the allowlist accepts
    ("-Xmx512m", "-javaagent:/tmp/evil.jar"),
    ("--add-modules", "java.base/tmp"),
    ("--add-modules", "-javaagent:/tmp/evil.jar"),
    # type confusion must never reach argv as a stringified entry
    b"-javaagent:/tmp/evil.jar",
    None,
    "",
)


class _PopenTrap(Exception):
    """Raised instead of launching, carrying the argv java() had assembled."""

    def __init__(self, argv):
        Exception.__init__(self, " ".join(map(str, argv)))
        self.argv = list(argv)


class _NoLaunch:
    """Stands in for ``subprocess`` inside ``nltk.internals``.

    Without it the probe is inconclusive where no JVM exists: an option that got
    past the filter would die in Popen with OSError and the probe would score the
    absence of java as a defence. Trapping at Popen records the argv that was
    about to run, which is the actual proof of injection, and launches nothing.
    """

    PIPE = -1
    DEVNULL = -3

    @staticmethod
    def Popen(argv, **kwargs):
        raise _PopenTrap(argv)


def _refused_by_the_option_filter(exc):
    """True only for _validate_java_options' own rejections.

    java() has three independent guards (options, classpath, cmd); matching a
    loose substring would let the cmd guard's rejection be scored as a defence of
    the options filter, so pin the messages only this filter emits.
    """
    text = str(exc)
    return text.startswith("java_options ") or text.startswith("--add-modules ")


@probe("GHSA-m4rf-3fr8-xwx3")
def _jvm_argument_injection():
    """Per-call options bypassed the CVE-2026-12841 JVM argument filter."""
    from nltk import internals

    # A plausible main class, so the cmd guard can never fire and the only thing
    # that may reject these calls is the filter under test.
    main_class = "edu.stanford.nlp.pipeline.StanfordCoreNLPServer"

    original = internals.subprocess
    internals.subprocess = _NoLaunch
    try:
        leaked, unreached = [], []
        for case in HOSTILE_OPTIONS:
            opts = list(case) if isinstance(case, tuple) else [case]
            label = " ".join(repr(opt) for opt in opts)
            try:
                internals.java([main_class], options=opts)
            except _PopenTrap as trap:
                leaked.append((label, trap.argv))
            except ValueError as exc:
                if not _refused_by_the_option_filter(exc):
                    unreached.append(f"{label}: {type(exc).__name__}")
            except Exception as exc:
                unreached.append(f"{label}: {type(exc).__name__}")
            else:
                leaked.append((label, "no launch attempted"))
    finally:
        internals.subprocess = original

    if leaked:
        label, argv = leaked[0]
        return VULNERABLE, (
            "hostile JVM option reached the launcher: %s (argv=%r); %d of %d leaked"
            % (label, argv, len(leaked), len(HOSTILE_OPTIONS))
        )
    if unreached:
        return STATIC, "not refused by the option filter: " + "; ".join(unreached[:3])
    return FIXED, (
        "all %d hostile per-call JVM options refused by _validate_java_options"
        % len(HOSTILE_OPTIONS)
    )
