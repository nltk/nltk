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

#: The advisories endpoint. GitHub caps per_page at 100 and paginates the rest
#: via the Link header, so a single request silently drops advisories past 100.
_API_ORIGIN = "https://api.github.com/repos/nltk/nltk/security-advisories"
_API = _API_ORIGIN + "?per_page=100"

#: Hard bound on pages followed. 50 * 100 = 5000 advisories -- never reached in
#: practice; a cap only guards against a pathological/looping Link header.
_MAX_PAGES = 50

#: Per-page read ceiling. The advisory list is tens of KB; anything past this is
#: implausible, so cap the read rather than let json buffer an unbounded body.
_MAX_BYTES = 5 * 1024 * 1024

_HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "nltk-advisory-coverage",
}

#: Closed/withdrawn advisories deliberately kept as regression probes. The
#: public API lists only published advisories, so these must be named here or
#: the reverse check would flag them as unknown.
_CLOSED_WITH_PROBE = {"GHSA-4489-j4f3-2g8q"}


def _next_url(link_header):
    """The *on-origin* rel="next" URL from a GitHub ``Link`` header, else None.

    Folding the origin check in here keeps the fetch loop branch-free: absent,
    malformed, or off-origin next links all simply stop pagination, so the loop
    never follows a link that leaves the advisories endpoint.
    """
    for part in (link_header or "").split(","):
        segments = part.split(";")
        url = segments[0].strip().lstrip("<").rstrip(">")
        if url.startswith(_API_ORIGIN) and any(
            seg.strip() == 'rel="next"' for seg in segments[1:]
        ):
            return url
    return None


def _fetch_advisories():
    """All advisories from the public API, or None if the fetch cannot be made.

    Follows GitHub's Link-header pagination so advisories past the first 100 are
    not silently dropped (which would let a real coverage gap pass unnoticed).
    The body is read with a byte cap and parsed with ``json.loads`` -- never
    ``json.load`` straight off the socket, which would buffer an unbounded
    response. Anything that cannot be fetched, bounded, or proven complete
    returns None so the test skips rather than asserting on a partial list.

    Unauthenticated on purpose: no token is read, so none can leak. Only the
    ``ghsa_id`` and ``state`` fields are used.
    """
    advisories, url = [], _API
    for _ in range(_MAX_PAGES):
        try:
            request = urllib.request.Request(url, headers=_HEADERS)
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read(_MAX_BYTES + 1)
                url = _next_url(response.headers.get("Link"))
            page = json.loads(raw)
        except Exception:
            return None
        if len(raw) > _MAX_BYTES or not isinstance(page, list):
            return None
        advisories.extend(page)
        if not url:
            return advisories
    return None  # page cap hit -- list not provably complete, skip not assert


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
