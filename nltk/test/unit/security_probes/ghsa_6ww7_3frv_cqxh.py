"""GHSA-6ww7-3frv-cqxh [high] -- pathsec SSRF protection can be bypassed when a proxy is configured"""
from ._base import STATIC, VULNERABLE, probe, read_source


@probe("GHSA-6ww7-3frv-cqxh")
def _proxy_ssrf_bypass():
    """With a proxy configured, the fetch bypassed the validated socket path."""
    source = read_source("nltk.pathsec")
    if "proxy" not in source.lower():
        return VULNERABLE, "pathsec.py does not mention proxies at all"
    return STATIC, "pathsec.py handles proxy configuration explicitly"
