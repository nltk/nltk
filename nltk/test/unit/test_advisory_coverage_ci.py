"""CI-only gate: every advisory published on GitHub must have a probe.

Fetches the live list rather than committing a snapshot (a cache goes stale;
parsing reporter-written advisory text at test time is its own exposure). Runs
only under ``NLTK_ADVISORY_CI`` -- a normal pytest run never hits the network --
and skips, rather than fails, if the fetch itself cannot be made, so it fails
only on a genuine coverage gap.
"""

import json
import os
import subprocess

import pytest

from nltk.test.unit import security_probes as probes

pytestmark = pytest.mark.skipif(
    not os.environ.get("NLTK_ADVISORY_CI"),
    reason="set NLTK_ADVISORY_CI=1 to pull the live advisory list (CI only)",
)


def _fetch_advisories():
    """All advisories from GitHub, or None if the fetch cannot be made."""
    try:
        result = subprocess.run(
            ["gh", "api", "repos/nltk/nltk/security-advisories", "--paginate"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        return json.loads(result.stdout) if result.returncode == 0 else None
    except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return None


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
    # Closed advisories may keep a probe as a regression guard; only flag ids
    # GitHub has never listed.
    known = {a["ghsa_id"] for a in advisories}
    unknown = sorted(set(probes.PROBES) - known)
    assert not unknown, "probes for ids GitHub does not list: %s" % unknown
