"""GHSA-qvv7-cg9c-w4x3 [high] -- DNS-rebinding SSRF filter bypass in nltk.pathsec.urlopen (nltk.download / nltk.data.load) defeats ENFORCE mode"""

from ._base import FIXED, VULNERABLE, is_security_rejection, probe


@probe("GHSA-qvv7-cg9c-w4x3")
def _dns_rebinding():
    """Every internal target must be security-rejected by validate_network_url.

    Covers loopback / unspecified / 127.x, cloud metadata, private, CGNAT and
    benchmarking ranges, plus the IPv6 wrapper forms (mapped, NAT64, 6to4) and a
    name that resolves to loopback. All are literals or resolvable names, so the
    filter classifies them directly rather than failing open on a bad lookup.
    """
    from nltk import pathsec

    targets = [
        "http://127.0.0.1/",
        "http://127.0.0.2/",
        "http://127.1.2.3/",
        "http://0.0.0.0/",
        "http://169.254.169.254/latest/meta-data/",
        "http://10.0.0.1/",
        "http://192.168.1.1/",
        "http://100.64.0.1/",  # CGNAT
        "http://198.18.0.1/",  # benchmarking
        "http://[::1]/",
        "http://[::]/",
        "http://[fe80::1]/",
        "http://[::ffff:127.0.0.1]/",  # IPv4-mapped loopback
        "http://[::ffff:169.254.169.254]/",  # IPv4-mapped metadata
        "http://[64:ff9b::a9fe:a9fe]/",  # NAT64 -> metadata
        "http://[2002:a9fe:a9fe::]/",  # 6to4 -> metadata
        "http://localhost/",
    ]
    passed = []
    for url in targets:
        try:
            pathsec.validate_network_url(url)
            passed.append(url)  # the filter let it through
        except Exception as exc:
            if not is_security_rejection(exc):
                passed.append(url)  # a non-security failure is not a real rejection
    if passed:
        host = passed[0].split("//", 1)[1]
        return (
            VULNERABLE,
            f"{len(passed)}/{len(targets)} SSRF targets not rejected ({host})",
        )
    return FIXED, f"all {len(targets)} internal/mapped SSRF targets rejected"
