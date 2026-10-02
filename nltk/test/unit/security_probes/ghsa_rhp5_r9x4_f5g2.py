"""GHSA-rhp5-r9x4-f5g2 [critical] -- [CWE-502] Unsafe Pickle Deserialization in TransitionParser Allows Remote Code Execution"""

from ._base import FIXED, VULNERABLE, probe, read_source


@probe("GHSA-rhp5-r9x4-f5g2")
def _transitionparser_pickle():
    """TransitionParser.parse() used pickle_load() with restricted=False."""
    source = read_source("nltk.parse.transitionparser")
    # The model must be reconstructed through the allowlisting unpickler: either
    # the allowlisted_pickle_load() helper or an AllowlistUnpickler subclass. The
    # hardened loader uses a subclass so it can additionally wrap numpy's object
    # dtype ``scalar`` (a nested unpickle sink) and reject object dtype arrays.
    if "allowlisted_pickle_load" not in source and "AllowlistUnpickler" not in source:
        return VULNERABLE, "transitionparser no longer uses an allowlisting unpickler"
    # No warn-only / unrestricted load may remain: neither the nltk pickle_load()
    # helper (which only warns) nor a bare stdlib pickle.load()/pickle.loads().
    bare = [
        line.strip()
        for line in source.splitlines()
        if ("pickle_load(" in line and "allowlisted_pickle_load" not in line)
        or "pickle.load(" in line
        or "pickle.loads(" in line
    ]
    if bare:
        return VULNERABLE, "unrestricted load remains: %s" % bare[0][:70]
    return FIXED, "loads via an allowlisting unpickler; no unrestricted pickle load"
