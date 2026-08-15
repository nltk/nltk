"""GHSA-m4rf-3fr8-xwx3 [high] -- JVM argument injection bypass via per-call options in the NLTK Stanford wrappers (incomp"""

from ._base import FIXED, VULNERABLE, probe


@probe("GHSA-m4rf-3fr8-xwx3")
def _jvm_argument_injection():
    """Per-call options bypassed the CVE-2026-12841 JVM argument filter."""
    from nltk.internals import config_java, java

    hostile = ["-Xbootclasspath/a:/tmp/evil.jar", "-agentlib:jdwp=transport=dt_socket"]
    # Require the *specific* rejection. Java is often absent on a dev box, and
    # counting the resulting OSError as "blocked" would let this probe pass for
    # entirely the wrong reason.
    blocked = []
    for option in hostile:
        try:
            java(["-version"], options=[option])
            return VULNERABLE, "hostile JVM option accepted: %s" % option
        except ValueError as exc:
            if "disallow" in str(exc).lower() or "option" in str(exc).lower():
                blocked.append(option)
        except Exception:
            pass
    if len(blocked) < len(hostile):
        return VULNERABLE, "only %d of %d hostile options explicitly refused" % (
            len(blocked),
            len(hostile),
        )
    return FIXED, "all %d hostile per-call JVM options refused by the filter" % len(
        hostile
    )
