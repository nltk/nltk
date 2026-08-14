"""GHSA-qvv7-cg9c-w4x3 [high] -- DNS-rebinding SSRF filter bypass in nltk.pathsec.urlopen (nltk.download / nltk.data.load"""
from ._base import FIXED, VULNERABLE, probe


@probe("GHSA-qvv7-cg9c-w4x3")
def _dns_rebinding():
    """DNS-rebinding SSRF filter bypass in nltk.pathsec.urlopen."""
    from nltk import pathsec

    blocked = 0
    targets = [
        "http://169.254.169.254/latest/meta-data/",
        "http://127.0.0.1/",
        "http://[::1]/",
        "http://0.0.0.0/",
    ]
    for url in targets:
        try:
            pathsec.validate_network_url(url)
        except Exception:
            blocked += 1
    if blocked < len(targets):
        return VULNERABLE, "%d of %d SSRF targets allowed" % (
            len(targets) - blocked,
            len(targets),
        )
    return FIXED, "all %d loopback/link-local targets rejected" % len(targets)
