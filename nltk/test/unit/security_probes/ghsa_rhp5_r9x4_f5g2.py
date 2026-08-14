"""GHSA-rhp5-r9x4-f5g2 [critical] -- [CWE-502] Unsafe Pickle Deserialization in TransitionParser Allows Remote Code Execution

Probe: run the attack, report what the tree does now. See _base for statuses.
"""
from ._base import FIXED, VULNERABLE, probe, read_source


@probe("GHSA-rhp5-r9x4-f5g2")
def _transitionparser_pickle():
    """TransitionParser.parse() used pickle_load() with restricted=False."""
    source = read_source("nltk.parse.transitionparser")
    if "allowlisted_pickle_load" not in source:
        return VULNERABLE, "transitionparser no longer uses allowlisted_pickle_load"
    bare = [
        line.strip()
        for line in source.splitlines()
        if "pickle_load(" in line and "allowlisted_pickle_load" not in line
    ]
    if bare:
        return VULNERABLE, "unrestricted load remains: %s" % bare[0][:70]
    return FIXED, "loads via allowlisted_pickle_load; no unrestricted pickle_load"
