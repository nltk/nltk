"""GHSA-97qj-x29f-37w7 [low] -- Entity-expansion DoS (billion laughs) via remaining raw ElementTree parses (CWE-776)"""

from ._base import FIXED, VULNERABLE, probe


@probe("GHSA-97qj-x29f-37w7")
def _billion_laughs():
    """Entity-expansion DoS via remaining raw ElementTree parses."""
    # A FLAT entity (unlike a nested billion-laughs) IS expanded by stock
    # ElementTree, so the probe flips to VULNERABLE if the entity guard is removed.
    payload = (
        '<?xml version="1.0"?><!DOCTYPE d [<!ENTITY a "'
        + "A" * 10000
        + '">]><d>'
        + "&a;" * 100
        + "</d>"
    )
    from nltk import xmlsec

    try:
        xmlsec.fromstring(payload)
        return VULNERABLE, "entity expansion was performed"
    except Exception as exc:
        return FIXED, "entity expansion refused (%s)" % type(exc).__name__
