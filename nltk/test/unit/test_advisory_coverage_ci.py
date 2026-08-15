"""CI-only gate: every advisory published on GitHub must have a probe.

Fetches the live list rather than committing a snapshot (a cache goes stale;
parsing reporter-written advisory text at test time is its own exposure).

No credentials by design. Published advisories on a public repo are readable
unauthenticated, so this uses no GITHUB_TOKEN and touches no secret -- there is
nothing here for a malicious PR to exfiltrate. The response is parsed as JSON
and only GHSA ids are compared; the reporter-controlled text is never executed.

Runs only under ``NLTK_ADVISORY_CI`` (a normal pytest run never hits the
network) and skips, rather than fails, if the fetch cannot be made -- so a rate
limit or an outage can never turn this red. It fails only on a real coverage
gap.
"""

import json
import os
import urllib.request

import pytest

from nltk.test.unit import security_probes as probes

pytestmark = pytest.mark.skipif(
    not os.environ.get("NLTK_ADVISORY_CI"),
    reason="set NLTK_ADVISORY_CI=1 to pull the live advisory list (CI only)",
)

_API = "https://api.github.com/repos/nltk/nltk/security-advisories?per_page=100"

#: Closed/withdrawn advisories deliberately kept as regression probes. The
#: public API lists only published advisories, so these must be named here or
#: the reverse check would flag them as unknown.
_CLOSED_WITH_PROBE = {"GHSA-4489-j4f3-2g8q"}


def _fetch_advisories():
    """All advisories from the public API, or None if the fetch cannot be made.

    Unauthenticated on purpose: no token is read, so none can leak. Only the
    ``ghsa_id`` and ``state`` fields are used.
    """
    request = urllib.request.Request(
        _API,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "nltk-advisory-coverage",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.load(response)
    except Exception:
        return None
    if not isinstance(data, list):
        return None
    return data


def test_every_published_advisory_has_a_probe():
    advisories = _fetch_advisories()
    if advisories is None:
        pytest.skip("could not fetch advisories from GitHub")
    published = {a["ghsa_id"] for a in advisories if a.get("state") == "published"}
    missing = sorted(published - set(probes.PROBES))
    assert not missing, "published advisories with no probe:\n  " + "\n  ".join(missing)


def test_no_probe_targets_an_unknown_advisory():
    advisories = _fetch_advisories()
    if advisories is None:
        pytest.skip("could not fetch advisories from GitHub")
    known = {a["ghsa_id"] for a in advisories} | _CLOSED_WITH_PROBE
    unknown = sorted(set(probes.PROBES) - known)
    assert not unknown, "probes for ids GitHub does not list: %s" % unknown
