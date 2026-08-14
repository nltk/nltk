"""GHSA-3gqm-fcw5-w839 [high] -- [CWE-918] SSRF Fail-Open in validate_network_url() via DNS Resolution Failure

Probe: run the attack, report what the tree does now. See _base for statuses.
"""
import socket
from ._base import FIXED, VULNERABLE, probe


@probe("GHSA-3gqm-fcw5-w839")
def _ssrf_fail_open():
    """validate_network_url() failed open when DNS resolution failed.

    Probed end-to-end, deliberately. ``_resolve_hostname`` returns ``[]`` on
    OSError, so the validation loop in ``validate_network_url`` iterates zero
    times and the function returns clean -- the fail-open the advisory
    describes is real *as a property of that function*. But it is not the
    reachable boundary: ``pathsec.urlopen`` re-resolves through
    ``_resolve_and_validate_host``, which pins the numeric address and
    validates every record, so the rebind is caught at connect time.

    An earlier version of this probe called ``validate_network_url`` alone and
    reported VULNERABLE. That measured a helper, not an attack. What decides
    whether a user is exposed is whether the *reachable* API can be made to
    connect to a forbidden address, so that is what is simulated here: DNS
    fails during validation, then answers with a link-local address at connect
    time -- the classic rebind.
    """
    import socket

    from nltk import pathsec

    real_getaddrinfo = socket.getaddrinfo
    calls = {"n": 0}

    def rebinding(host, port, *args, **kwargs):
        if host and "rebind.invalid" in str(host):
            calls["n"] += 1
            if calls["n"] == 1:  # validation sees NXDOMAIN
                raise socket.gaierror("simulated resolution failure")
            return [  # connection sees the link-local metadata address
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("169.254.169.254", port or 80))
            ]
        return real_getaddrinfo(host, port, *args, **kwargs)

    socket.getaddrinfo = rebinding
    try:
        try:
            pathsec.validate_network_url("http://rebind.invalid/latest/meta-data/")
            helper_open = True
        except Exception:
            helper_open = False
        try:
            pathsec.urlopen("http://rebind.invalid/latest/meta-data/", timeout=3)
            return VULNERABLE, "urlopen connected to a rebound link-local address"
        except Exception as exc:
            if "Security Violation" not in str(exc):
                return VULNERABLE, "blocked, but not by an SSRF check: %s" % (
                    str(exc)[:60],
                )
            note = " (validate_network_url alone still fails open)" if helper_open else ""
            return FIXED, "rebind blocked at connect time by a pinned check%s" % note
    finally:
        socket.getaddrinfo = real_getaddrinfo
