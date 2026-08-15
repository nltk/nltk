"""GHSA-6ww7-3frv-cqxh [high] -- pathsec SSRF protection can be bypassed when a proxy is configured"""

import urllib.request

from ._base import FIXED, VULNERABLE, probe


@probe("GHSA-6ww7-3frv-cqxh")
def _proxy_ssrf_bypass():
    """A configured proxy is the egress, so NLTK cannot pin the validated IP.

    Under ENFORCE the proxied fetch must fail closed *before any egress*
    (CWE-918). FIXED only on that specific refusal -- a later connection error
    (e.g. the fake proxy being unreachable) means the guard did NOT fire, which
    is the bypassed state, so it is VULNERABLE, not a pass.
    """
    from nltk import pathsec

    saved = (
        urllib.request.getproxies,
        urllib.request.proxy_bypass,
        urllib.request._opener,
        pathsec.ENFORCE,
        pathsec.ALLOW_PROXIED_FETCH,
        getattr(pathsec, "_resolve_hostname", None),
    )
    try:
        urllib.request.getproxies = lambda: {"http": "http://attacker-proxy:8080"}
        # Pin proxy_bypass: pathsec asks it whether the configured proxy actually
        # carries this host. The real macOS impl (proxy_bypass_macosx_sysconf)
        # reads system config and bypasses link-local hosts on some runners, which
        # would make the simulated proxy inert and the probe misreport VULNERABLE.
        # False = "the proxy carries every host", the scenario under test, on all
        # platforms.
        urllib.request.proxy_bypass = lambda host: False
        urllib.request._opener = None
        pathsec.ENFORCE = True
        pathsec.ALLOW_PROXIED_FETCH = False
        pathsec._resolve_hostname = lambda host: []
        try:
            pathsec.urlopen("http://169.254.169.254/latest/meta-data/", timeout=2)
        except PermissionError as exc:
            if "proxied fetch" in str(exc):
                return FIXED, "proxied fetch fails closed before egress"
            return (
                VULNERABLE,
                "PermissionError, but not the proxy guard: %s" % str(exc)[:50],
            )
        except Exception as exc:
            # Guard did not fire; the request proceeded and failed downstream.
            return (
                VULNERABLE,
                "guard bypassed; reached egress (%s)" % type(exc).__name__,
            )
        return VULNERABLE, "proxied fetch of a link-local host was not refused"
    finally:
        (
            urllib.request.getproxies,
            urllib.request.proxy_bypass,
            urllib.request._opener,
            pathsec.ENFORCE,
            pathsec.ALLOW_PROXIED_FETCH,
            pathsec._resolve_hostname,
        ) = saved
