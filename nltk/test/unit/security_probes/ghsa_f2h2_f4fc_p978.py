"""GHSA-f2h2-f4fc-p978 [moderate] -- Uncontrolled recursion in Toolbox
settings helpers causes denial of service via deeply nested input.
"""

from ._base import FIXED, VULNERABLE, probe


@probe("GHSA-f2h2-f4fc-p978")
def _toolbox_recursion():
    """Uncontrolled recursion in the Toolbox settings helpers causes a crash."""
    from nltk.toolbox import (
        ToolboxSettings,
        _to_settings_string,
        add_blank_lines,
        add_default_fields,
        remove_blanks,
        sort_fields,
    )

    n = 2000
    # \\+field starts a nested block; \\-field closes it.  n opens
    # followed by n closes in reverse order gives an n-deep element tree.
    lines = ["\\+field%d" % i for i in range(n)]
    lines += ["\\-field%d" % i for i in range(n - 1, -1, -1)]
    settings_str = "\n".join(lines) + "\n"

    try:
        ts = ToolboxSettings()
        ts.open_string(settings_str)
        tree = ts.parse()  # returns an Element; parse is iterative
    except RecursionError:
        return VULNERABLE, "RecursionError escaped during parse()"
    except Exception as exc:
        return FIXED, "bounded during parse (%s)" % type(exc).__name__

    # NOTE: to_settings_string() takes an ElementTree and calls
    # tree.getroot(); parse() returns an Element, so we call the recursive
    # worker _to_settings_string() directly (as named in the advisory).
    helpers = (
        ("_to_settings_string", lambda: _to_settings_string(tree, [])),
        ("remove_blanks", lambda: remove_blanks(tree)),
        ("add_default_fields", lambda: add_default_fields(tree, {})),
        ("sort_fields", lambda: sort_fields(tree, {})),
        ("add_blank_lines", lambda: add_blank_lines(tree, {}, {})),
    )

    for name, func in helpers:
        try:
            func()
        except RecursionError:
            return VULNERABLE, "RecursionError escaped from %s()" % name
        except Exception as exc:
            return FIXED, f"bounded in {name}() ({type(exc).__name__})"

    return FIXED, "deeply nested settings traversed without crashing"
