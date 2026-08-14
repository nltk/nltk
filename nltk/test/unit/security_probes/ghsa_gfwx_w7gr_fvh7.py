"""GHSA-gfwx-w7gr-fvh7 [medium] -- Improper Neutralization of Input During Web Page Generation ('Cross-site Scripting') in 

Probe: run the attack, report what the tree does now. See _base for statuses.
"""
from ._base import STATIC, VULNERABLE, probe, read_source


@probe("GHSA-gfwx-w7gr-fvh7")
def _wordnet_app_xss():
    """Reflected XSS in the wordnet_app lookup_ route."""
    source = read_source("nltk.app.wordnet_app")
    if "escape" in source or "quote(" in source or "html.escape" in source:
        return STATIC, "response path escapes reflected input"
    return VULNERABLE, "no escaping found on the reflected lookup_ route"
