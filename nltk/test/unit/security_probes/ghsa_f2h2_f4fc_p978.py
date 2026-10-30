"""GHSA-f2h2-f4fc-p978 [moderate] Uncontrolled recursion in Toolbox
settings helpers causes denial of service via deeply nested input.
"""

from ._base import FIXED, VULNERABLE, probe

#: Four times MAX_TOOLBOX_DEPTH and twice the default recursion limit.
DEPTH = 2000


@probe("GHSA-f2h2-f4fc-p978")
def _toolbox_recursion():
    """Both choke points are bounded, and the fix left the helpers working.

    A settings file ``DEPTH`` blocks deep must be refused by ``parse`` with the
    bound's ValueError; a tree that deep built in code must be refused the
    same way by every recursive helper; and an ordinary settings tree must be
    walked by every helper, with what ``to_settings_string`` writes reading
    back as the same tree. Any other outcome is reported, including another
    exception, which is how the regression of the first fix went unseen.
    """
    from xml.etree.ElementTree import Element, ElementTree, SubElement, tostring

    from nltk.toolbox import (
        ToolboxSettings,
        add_blank_lines,
        add_default_fields,
        remove_blanks,
        sort_fields,
        to_settings_string,
    )

    def settings(text):
        ts = ToolboxSettings()
        ts.open_string(text)
        try:
            return ts.parse(unwrap=False)
        finally:
            ts.close()

    def chain(n):
        root = node = Element("grp")
        for _ in range(n - 1):
            node = SubElement(node, "grp")
        node.text = "x"
        return root

    def bounded(exc):
        return isinstance(exc, ValueError) and "MAX_TOOLBOX_DEPTH" in str(exc)

    rules = {"grp": ("grp",), "set": ("mkr",)}
    helpers = (
        ("to_settings_string", lambda t: to_settings_string(ElementTree(t))),
        ("remove_blanks", remove_blanks),
        ("add_default_fields", lambda t: add_default_fields(t, {"grp": ("x",)})),
        ("sort_fields", lambda t: sort_fields(t, rules)),
        ("add_blank_lines", lambda t: add_blank_lines(t, {}, {})),
        ("add_blank_lines(listed)", lambda t: add_blank_lines(t, rules, rules)),
    )
    failures = []

    # \+field opens a nested block and \-field closes it.
    lines = ["\\+field%d" % i for i in range(DEPTH)]
    lines += ["\\-field%d" % i for i in range(DEPTH - 1, -1, -1)]
    try:
        settings("\n".join(lines) + "\n")
        failures.append("parse() accepted a %d deep settings file" % DEPTH)
    except Exception as exc:
        if not bounded(exc):
            failures.append("parse() raised %s, not the bound" % type(exc).__name__)

    for name, walk in helpers:
        try:
            walk(chain(DEPTH))
            failures.append("%s walked a %d deep tree" % (name, DEPTH))
        except RecursionError:
            failures.append("RecursionError escaped from %s" % name)
        except Exception as exc:
            if not bounded(exc):
                failures.append(f"{name} raised {type(exc).__name__}, not the bound")

    ordinary = "\\+set top\n\\nam a\n\\+mkr lx\n\\lng v\n\\-mkr\n\\mkr ps\n\\-set\n"
    for name, walk in helpers:
        try:
            walk(settings(ordinary))
        except Exception as exc:
            failures.append(f"{name} fails on an ordinary tree ({type(exc).__name__})")
    try:
        tree = settings(ordinary)
        if tostring(settings(to_settings_string(ElementTree(tree)))) != tostring(tree):
            failures.append("to_settings_string output reads back as another tree")
    except Exception as exc:
        failures.append(
            "to_settings_string output does not read back (%s)" % type(exc).__name__
        )

    if failures:
        return VULNERABLE, "; ".join(failures)
    return FIXED, (
        "a %d deep settings file is refused at parse, a %d deep tree by all %d "
        "helper walks, and an ordinary tree is walked" % (DEPTH, DEPTH, len(helpers))
    )
