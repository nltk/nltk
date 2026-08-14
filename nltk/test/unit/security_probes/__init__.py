"""Live probes for every published NLTK security advisory.

One ``ghsa_*.py`` module per advisory, each running the attack the advisory
describes and reporting what the tree does now -- an advisory says a version
*was* vulnerable; a probe checks the tree *is* fixed. Importing this package
imports every probe module, populating :data:`PROBES`.

    python -m nltk.test.unit.security_probes    # print the report

``test_advisory_probes`` runs the probes offline; ``test_advisory_coverage_ci``
pulls the live list from GitHub (CI only) to catch a newly published advisory
with no probe.
"""

import importlib
import pkgutil

from ._base import BENIGN, FIXED, PROBES, STATIC, VULNERABLE, probe  # noqa: F401

# Import every ghsa_* sibling so its @probe registration runs. __path__ is this
# package's own, so nothing outside the test tree is imported.
for _module in pkgutil.iter_modules(__path__):
    if _module.name.startswith("ghsa_"):
        importlib.import_module("%s.%s" % (__name__, _module.name))

__all__ = ["PROBES", "FIXED", "VULNERABLE", "STATIC", "BENIGN", "run"]


def run():
    """Print one line per advisory; return the number VULNERABLE."""
    counts = {}
    for ghsa in sorted(PROBES):
        try:
            status, evidence = PROBES[ghsa]()
        except Exception as exc:
            status, evidence = "ERROR", "%s: %s" % (type(exc).__name__, str(exc)[:70])
        counts[status] = counts.get(status, 0) + 1
        print("%-22s %-10s %s" % (ghsa, status, evidence[:70]))
    print("\nprobes: %d" % len(PROBES))
    for status in (FIXED, STATIC, BENIGN, VULNERABLE, "ERROR"):
        if counts.get(status):
            print("  %-10s %d" % (status, counts[status]))
    return counts.get(VULNERABLE, 0)
