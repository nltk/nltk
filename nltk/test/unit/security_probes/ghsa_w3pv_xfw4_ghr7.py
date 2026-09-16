"""GHSA-w3pv-xfw4-ghr7 [moderate] -- Uncontrolled recursion in the
semantic-logic type parser (read_type) causes denial of service via nested
type strings.
"""

from ._base import FIXED, VULNERABLE, probe


@probe("GHSA-w3pv-xfw4-ghr7")
def _logic_read_type_recursion():
    """Uncontrolled recursion in Type.fromstring causes a crash."""
    from nltk.sem.logic import Type

    n = 5000
    # Left-nested complex type: <<<e,e>,e>,e> ...  Each level forces
    # read_type to recurse once on the left half.
    #
    # NOTE: the advisory's suggested payload "<"*n + "e,e" + ">"*n does
    # NOT work: the inner comma sits at paren depth 2, so read_type's
    # top-level-comma scan never breaks and it raises AssertionError
    # instead of recursing.  Shapes B (left-nested) and C (right-nested)
    # both reproduce; we use B.
    payload = "<" * n + "e" + ",e>" * n

    try:
        Type.fromstring(payload)
    except RecursionError:
        return VULNERABLE, "RecursionError escaped from Type.fromstring()"
    except Exception as exc:
        return FIXED, "bounded (%s)" % type(exc).__name__
    return FIXED, "deeply nested type string parsed without crashing"
