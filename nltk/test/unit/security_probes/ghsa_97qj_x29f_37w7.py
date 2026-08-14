"""GHSA-97qj-x29f-37w7 [low] -- Entity-expansion DoS (billion laughs) via remaining raw ElementTree parses (CWE-776)"""
from ._base import FIXED, VULNERABLE, probe


@probe("GHSA-97qj-x29f-37w7")
def _billion_laughs():
    """Entity-expansion DoS via remaining raw ElementTree parses."""
    payload = (
        '<?xml version="1.0"?><!DOCTYPE lolz [<!ENTITY lol "lol">'
        + "".join(
            '<!ENTITY lol%d "&lol%d;&lol%d;">' % (i, i - 1, i - 1) for i in range(1, 10)
        )
        + "]><lolz>&lol9;</lolz>"
    )
    from nltk import xmlsec

    try:
        xmlsec.fromstring(payload)
        return VULNERABLE, "entity expansion was performed"
    except Exception as exc:
        return FIXED, "entity expansion refused (%s)" % type(exc).__name__
