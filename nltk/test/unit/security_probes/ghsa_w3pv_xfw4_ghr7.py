"""GHSA-w3pv-xfw4-ghr7 [medium] -- Uncontrolled recursion in semantic-logic type parser causes denial of service via nested type strings (CWE-674)"""

from ._base import FIXED, VULNERABLE, probe


@probe("GHSA-w3pv-xfw4-ghr7")
def _logic_read_type_recursion():
    """Parse a deeply nested type string with ``read_type``.

    ``read_type`` recursed once per ``<`` level with no bound, so a type like
    ``<<<...,e>,e>,e>`` crashed with an uncaught ``RecursionError`` (a DoS). It
    must now reject the input with a bounded ``LogicalExpressionException``.
    """
    from nltk.sem.logic import MAX_TYPE_DEPTH, LogicalExpressionException, read_type

    payload = "e"
    for _ in range(MAX_TYPE_DEPTH + 200):
        payload = "<%s,e>" % payload
    try:
        read_type(payload)
    except RecursionError:
        return VULNERABLE, "read_type recursed to RecursionError (uncontrolled)"
    except LogicalExpressionException as exc:
        return FIXED, "deep type string rejected: %s" % str(exc)[:56]
    return VULNERABLE, "read_type accepted an adversarially deep type string"
