"""Live probes for every published NLTK security advisory.

One ``ghsa_*.py`` module per advisory, each registering a probe that runs the
attack the advisory describes and reports what the tree does now. An advisory
records that a version *was* vulnerable; a probe checks the tree *is* fixed,
and a fix that silently regresses looks exactly like one that shipped.

Importing this package imports every probe module, which populates
:data:`PROBES`. Discovery is over this package's own ``__path__`` only -- a
fixed, in-tree location -- never a computed path that could reach outside the
test tree.

Run the report::

    python -m nltk.test.unit.security_probes

The offline test (:mod:`nltk.test.unit.test_advisory_probes`) runs every probe
and fails on any VULNERABLE. The CI-only test
(:mod:`nltk.test.unit.test_advisory_coverage_ci`) pulls the live published
list from GitHub and fails if a newly published advisory has no probe here.
"""

import importlib
import pkgutil

from ._base import BENIGN, FIXED, PROBES, STATIC, VULNERABLE, probe  # noqa: F401

# Import every ghsa_* sibling so its @probe registration runs. __path__ and the
# package name come from this package itself, so nothing outside the test tree
# is ever imported.
for _module in pkgutil.iter_modules(__path__):
    if _module.name.startswith("ghsa_"):
        importlib.import_module("%s.%s" % (__name__, _module.name))

__all__ = ["PROBES", "FIXED", "VULNERABLE", "STATIC", "BENIGN", "run"]


def run():
    """Print a one-line-per-advisory report. Returns the number VULNERABLE."""
    vulnerable = 0
    counts = {}
    for ghsa in sorted(PROBES):
        try:
            status, evidence = PROBES[ghsa]()
        except Exception as exc:
            status, evidence = "ERROR", "%s: %s" % (type(exc).__name__, str(exc)[:70])
        counts[status] = counts.get(status, 0) + 1
        if status == VULNERABLE:
            vulnerable += 1
        print("%-22s %-10s %s" % (ghsa, status, evidence[:70]))
    print()
    print("probes: %d" % len(PROBES))
    for status in (FIXED, STATIC, BENIGN, VULNERABLE, "ERROR"):
        if counts.get(status):
            print("  %-10s %d" % (status, counts[status]))
    return vulnerable
