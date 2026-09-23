"""GHSA-7mxv-7h3q-9324 [high]: untrusted external-binary execution plus
loader/JVM env injection when nltk launches java (CWE-426/CWE-427/CWE-88).
"""

import os
import shutil
import stat
import tempfile

from ._base import FIXED, STATIC, VULNERABLE, probe


@probe("GHSA-7mxv-7h3q-9324")
def _java_untrusted_binary_and_loader_env():
    """Drive nltk.internals.java() and _java_child_env() with real attacks.

    (a) Configure an ABSOLUTE java binary planted in a group/world-writable dir
        (a location another local user could swap) and launch it: java() must
        raise pathsec.TrustError before exec. Executing the plant is VULNERABLE.
    (b) Seed LD_PRELOAD / DYLD_INSERT_LIBRARIES / JAVA_TOOL_OPTIONS / GCONV_PATH
        and confirm _java_child_env() drops every one and locks PATH to
        safe_env()["PATH"]. Any survivor is VULNERABLE.
    """
    import nltk.internals as internals
    import nltk.pathsec as pathsec

    # The trust refusal is POSIX-only: the non-POSIX layer degrades to open by
    # design (no DACL check), so it cannot fail closed here.
    if os.name != "posix":
        return STATIC, "untrusted-exec refusal is POSIX-only (non-POSIX degrades open)"

    marker_keys = (
        "LD_PRELOAD",
        "DYLD_INSERT_LIBRARIES",
        "JAVA_TOOL_OPTIONS",
        "GCONV_PATH",
    )
    box = tempfile.mkdtemp()
    saved_bin = internals._java_bin
    saved_env = {k: os.environ.get(k) for k in marker_keys}
    try:
        # A genuinely untrusted directory: group- and world-writable, so a local
        # attacker could plant or swap the binary before it runs.
        writable = os.path.join(box, "writable")
        os.makedirs(writable)
        os.chmod(writable, 0o777)
        if not (os.stat(writable).st_mode & stat.S_IWOTH):
            return STATIC, "filesystem stripped the world-write bit; no untrusted dir"
        plant = os.path.join(writable, "java")
        with open(plant, "w", encoding="utf-8") as fh:
            fh.write("#!/bin/sh\necho planted\n")
        os.chmod(plant, os.stat(plant).st_mode | stat.S_IEXEC)

        # (a) Real sink: config_java stores the absolute plant, java() must refuse.
        # cmd[0] must be a bare main-class token (a leading "-"/"@" is refused
        # earlier, before the trust guard we are exercising).
        internals.config_java(bin=plant, verbose=False)
        try:
            internals.java(["ProbeMain"], stdout="devnull", stderr="devnull")
        except pathsec.TrustError:
            pass
        except Exception as exc:
            return (
                STATIC,
                "planted java failed before the trust guard (%s)" % type(exc).__name__,
            )
        else:
            return VULNERABLE, "java() executed the planted untrusted binary %r" % plant

        # (b) Real sink: seed loader/JVM injectors and scrub the child env.
        for key in marker_keys:
            os.environ[key] = "/tmp/attacker/" + key.lower()
        child = internals._java_child_env()
        survivors = [k for k in marker_keys if k in child]
        if survivors:
            return (
                VULNERABLE,
                "loader/JVM vars survived _java_child_env(): " + ", ".join(survivors),
            )
        if child.get("PATH") != pathsec.safe_env()["PATH"]:
            return VULNERABLE, "child PATH not locked to pathsec.safe_env() PATH"

        return FIXED, (
            "planted absolute java refused (TrustError); loader/JVM env scrubbed "
            "and PATH locked to safe_env()"
        )
    finally:
        internals._java_bin = saved_bin
        for key, val in saved_env.items():
            if val is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = val
        shutil.rmtree(box, ignore_errors=True)
