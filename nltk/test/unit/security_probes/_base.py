"""Shared machinery for the per-advisory security probes.

Each ``ghsa_*`` module registers one probe with ``@probe("GHSA-...")``. A probe
runs the attack the advisory describes and returns ``(status, evidence)``:

    FIXED       attack ran, tree defended
    VULNERABLE  attack ran and worked -- a regression
    STATIC      guard confirmed in source, attack not executed (needs a
                network peer / real download / running JVM)
    BENIGN      audited, never exploitable here, pinned so it stays that way

This package lives inside ``nltk/test/unit`` so the coverage test imports it as
a normal sibling -- it never computes an outside path or touches ``sys.path``,
which in an installed tree would reach ``site-packages``. ``read_source`` uses a
module's own ``__file__`` for the same reason.
"""

import importlib
import io  # noqa: F401  (re-exported for probe bodies)
import os
import shutil
import socket  # noqa: F401
import tempfile
import time

FIXED = "FIXED"
VULNERABLE = "VULNERABLE"
STATIC = "STATIC"
BENIGN = "BENIGN"

#: Hostile payloads must not finish inside this. Generous so a loaded CI runner
#: does not flake to a false VULNERABLE.
DOS_BUDGET = 15.0

#: GHSA id -> probe callable, populated as each module is imported.
PROBES = {}


def probe(ghsa):
    """Register a probe returning (status, evidence)."""

    def register(func):
        if ghsa in PROBES:
            raise RuntimeError("duplicate probe for %s" % ghsa)
        PROBES[ghsa] = func
        return func

    return register


def timed(func, *args):
    start = time.perf_counter()
    func(*args)
    return time.perf_counter() - start


def read_source(dotted_module):
    """Source of an importable NLTK module, via its own ``__file__``."""
    module = importlib.import_module(dotted_module)
    return open(module.__file__, encoding="utf-8").read()


SECRET = "OUTSIDE-ROOT-SECRET"


class Sandbox:
    """A corpus root with a symlink and an outside-root secret to try to read."""

    def __init__(self):
        self.dir = tempfile.mkdtemp()
        self.root = os.path.join(self.dir, "corpus")
        os.makedirs(self.root, exist_ok=True)
        self.secret = os.path.join(self.dir, "secret.txt")
        with open(self.secret, "w", encoding="utf-8") as handle:
            handle.write(SECRET)
        self.link = os.path.join(self.root, "link.xml")
        try:
            os.symlink(self.secret, self.link)
        except OSError:
            self.link = None

    def cleanup(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def leaked(self, value):
        return SECRET in (value if isinstance(value, str) else str(value))


def escape_probe(attempts):
    """VULNERABLE if any ``(label, fn)`` returns the outside-root secret.

    A callable that raises is a defended path; one that returns the secret is
    an escape.
    """
    box = Sandbox()
    try:
        tried = []
        for label, run in attempts:
            try:
                result = run(box)
            except Exception as exc:
                tried.append("%s=%s" % (label, type(exc).__name__))
                continue
            if box.leaked(result):
                return VULNERABLE, "%s read the outside-root file" % label
            tried.append("%s=no-leak" % label)
        return FIXED, "; ".join(tried)
    finally:
        box.cleanup()
