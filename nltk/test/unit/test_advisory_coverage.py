"""Every published security advisory must stay fixed, and stay probed.

``audit/advisories.py`` holds a live probe per published advisory: it runs the
attack the advisory describes and reports what the tree does now. This file is
the CI gate over it, so a regression fails a test rather than waiting for
someone to re-read 37 advisories by hand.

Two things are enforced:

* no advisory reports VULNERABLE;
* no *newly published* advisory is left without a probe.

The second matters more than it looks. Advisories are filed continuously, and
the failure mode is silent: an advisory lands, nobody writes a probe, and the
suite stays green while coverage quietly drops. Failing on an unprobed
advisory turns that into a visible task.

Probe results are cached from ``audit/advisories.json`` so this runs offline.
"""

import pathlib
import sys

import pytest

AUDIT = pathlib.Path(__file__).resolve().parents[3] / "audit"

pytestmark = pytest.mark.skipif(
    not (AUDIT / "advisories.py").exists(),
    reason="audit/advisories.py not present in this checkout",
)


def _load():
    if str(AUDIT) not in sys.path:
        sys.path.insert(0, str(AUDIT))
    import advisories

    return advisories


def _published(advisories):
    return [a for a in advisories.load_advisories() if a["state"] == "published"]


def test_no_published_advisory_is_vulnerable():
    """Run every probe; none may report VULNERABLE."""
    advisories = _load()
    regressions = []
    for advisory in _published(advisories):
        func = advisories.PROBES.get(advisory["ghsa_id"])
        if func is None:
            continue
        try:
            status, evidence = func()
        except Exception as exc:  # a probe that crashes is not a pass
            regressions.append(
                "%s probe error: %s: %s"
                % (advisory["ghsa_id"], type(exc).__name__, str(exc)[:80])
            )
            continue
        if status == advisories.VULNERABLE:
            regressions.append("%s: %s" % (advisory["ghsa_id"], evidence))
    assert not regressions, "advisories regressed:\n  " + "\n  ".join(regressions)


def test_every_published_advisory_has_a_probe():
    """A newly published advisory must not silently go unverified."""
    advisories = _load()
    missing = [
        "%s [%s] %s" % (a["ghsa_id"], a["severity"], a["summary"][:60])
        for a in _published(advisories)
        if a["ghsa_id"] not in advisories.PROBES
    ]
    assert not missing, (
        "published advisories with no probe in audit/advisories.py:\n  "
        + "\n  ".join(missing)
        + "\n\nAdd a probe, or refresh the cache with "
        "`python3 audit/advisories.py --refresh`."
    )


def test_probe_registry_matches_known_advisories():
    """A probe keyed to an unknown GHSA id is a typo, not coverage."""
    advisories = _load()
    known = {a["ghsa_id"] for a in advisories.load_advisories()}
    unknown = sorted(set(advisories.PROBES) - known)
    assert not unknown, "probes registered for unknown advisory ids: %s" % unknown
