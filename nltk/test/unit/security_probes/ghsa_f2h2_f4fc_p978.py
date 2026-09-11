"""GHSA-f2h2-f4fc-p978 [medium] -- Uncontrolled recursion in Toolbox settings helpers causes denial of service via deeply nested input (CWE-674)"""

from ._base import FIXED, VULNERABLE, probe


@probe("GHSA-f2h2-f4fc-p978")
def _toolbox_settings_recursion():
    """Parse a settings string whose ``\\+field`` markers nest without closing.

    Each ``\\+`` opens an element-tree level walked later by recursive helpers
    (``remove_blanks``, ``add_default_fields``, ``_sort_fields``,
    ``add_blank_lines``, ``_to_settings_string``), so a string with thousands of
    open markers built an arbitrarily deep tree and crashed those walks with an
    uncaught ``RecursionError`` (a DoS). ``parse`` must now bound the nesting
    with a ``ValueError`` at read time.
    """
    from nltk.toolbox import MAX_TOOLBOX_DEPTH, ToolboxSettings

    n = MAX_TOOLBOX_DEPTH + 200
    data = "".join("\\+f%d val\n" % i for i in range(n))
    ts = ToolboxSettings()
    ts.open_string(data)
    try:
        ts.parse()
    except RecursionError:
        return VULNERABLE, "toolbox parse recursed to RecursionError (uncontrolled)"
    except ValueError as exc:
        return FIXED, "deeply nested settings rejected: %s" % str(exc)[:48]
    return VULNERABLE, "ToolboxSettings.parse accepted adversarially deep nesting"
