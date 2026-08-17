"""GHSA-3gqm-fcw5-w839 [high] -- [CWE-918] SSRF Fail-Open in validate_network_url() via DNS Resolution Failure"""

import socket

from ._base import FIXED, VULNERABLE, probe


@probe("GHSA-3gqm-fcw5-w839")
def _ssrf_fail_open():
    # validate_network_url() alone fails open on DNS failure, so probe the
    # reachable urlopen() end-to-end: NXDOMAIN during validation, link-local at
    # connect. urlopen re-resolves and pins the numeric address.
    from nltk import pathsec

    real = socket.getaddrinfo
    calls = []

    def rebinding(host, port, *args, **kwargs):
        if host and "rebind.invalid" in str(host):
            calls.append(1)
            if len(calls) == 1:
                raise socket.gaierror("simulated resolution failure")
            return [
                (
                    socket.AF_INET,
                    socket.SOCK_STREAM,
                    6,
                    "",
                    ("169.254.169.254", port or 80),
                )
            ]
        return real(host, port, *args, **kwargs)

    socket.getaddrinfo = rebinding
    try:
        pathsec.urlopen("http://rebind.invalid/latest/meta-data/", timeout=3)
        return VULNERABLE, "urlopen connected to a rebound link-local address"
    except Exception as exc:
        if "Security Violation" not in str(exc):
            return VULNERABLE, "blocked, but not by an SSRF check: %s" % str(exc)[:60]
        return FIXED, "rebind blocked at connect time by a pinned check"
    finally:
        socket.getaddrinfo = real
