"""GHSA-32p6-cwhc-8r78 [draft] : Compile-time regex DoS (CWE-1333). The regex
engine's compile cost is quadratic in the number of capturing groups and the
redos match timeout only starts after compile, so a capturing-group bomb well
under MAX_PATTERN_LENGTH burned tens of seconds before any match was attempted.

The fix makes ``redos.check_pattern`` refuse more than ``MAX_GROUP_COUNT``
capturing groups up front; non-capturing groups are not counted.
"""

import time

from ._base import FIXED, VULNERABLE, probe


@probe("GHSA-32p6-cwhc-8r78")
def _capturing_group_compile_bomb():
    """Compile a 6000-group bomb (12 KB, far under the length cap) through redos.

    The guard refuses it with a ValueError naming the group bound before the
    engine ever sees it; without the guard the engine compiles it, quadratically.
    """
    from nltk import redos

    bomb = "()" * 6000
    start = time.perf_counter()
    try:
        redos.compile(bomb)
    except ValueError as exc:
        if "capturing groups" in str(exc):
            return FIXED, "group bomb refused before compile: %s" % str(exc)[:70]
        return VULNERABLE, "refused for another reason, guard not reached: %s" % exc
    elapsed = time.perf_counter() - start
    return VULNERABLE, "6000-group bomb compiled in %.2fs; no group bound" % elapsed
