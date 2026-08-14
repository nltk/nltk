"""Shared machinery for the per-advisory security probes.

Each advisory in this package registers one probe with ``@probe("GHSA-...")``.
A probe runs the attack the advisory describes and returns ``(status,
evidence)``:

    FIXED       the probe ran the attack and the tree defended
    VULNERABLE  the probe ran the attack and it worked -- a real regression
    STATIC      the guard is present in the source, but the attack was not
                executed (a network peer / real download / running JVM is
                needed). Weaker evidence than FIXED, and labelled so a source
                inspection is never passed off as an exploit attempt.
    BENIGN      audited, never exploitable here, pinned so it stays that way

Design note -- this package lives *inside* ``nltk/test/unit`` on purpose. The
coverage test imports it as a normal sibling package. It never reaches outside
the test tree with computed ``parents[...]`` paths and never injects onto
``sys.path`` -- in an installed environment that reaches ``site-packages`` and
would import whatever ``advisories`` module happens to be first on the path,
which is the very path-confusion class these advisories are about.

Locating NLTK source for the STATIC probes uses the imported module's own
``__file__``, not path arithmetic, for the same reason.
"""

import importlib
import io  # noqa: F401  (used by probe bodies via `from ._base import *`)
import os
import shutil
import socket  # noqa: F401
import tempfile
import time

FIXED = "FIXED"
VULNERABLE = "VULNERABLE"
STATIC = "STATIC"
BENIGN = "BENIGN"

#: A hostile payload that a vulnerable build cannot finish inside. Generous so
#: a loaded CI runner does not flake to a false VULNERABLE.
DOS_BUDGET = 15.0

#: Registry of GHSA id -> probe callable, populated as each module is imported.
PROBES = {}


def probe(ghsa):
    """Register a probe for an advisory. The function returns (status, evidence)."""

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
    """Return the source of an importable NLTK module, via its own __file__.

    Deliberately not ``repo_root / "nltk" / ...``: the module's ``__file__`` is
    wherever it is actually installed, so this cannot be pointed at an
    attacker-planted tree by path arithmetic.
    """
    module = importlib.import_module(dotted_module)
    return open(module.__file__, encoding="utf-8").read()


# ---------------------------------------------------------------------------
# Corpus-reader sandbox escapes share one setup: a corpus root that contains a
# symlink pointing outside it, plus an outside-root secret to try to read.
# ---------------------------------------------------------------------------

SECRET = "OUTSIDE-ROOT-SECRET"


class Sandbox:
    """A corpus root with a symlink and an outside-root traversal target."""

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
        try:
            return SECRET in (value if isinstance(value, str) else str(value))
        except Exception:
            return False


def escape_probe(attempts):
    """Run ``attempts`` against a sandbox; VULNERABLE if any returns the secret.

    ``attempts`` is a list of ``(label, callable(sandbox))``. A callable that
    raises is a defended path; one that returns the outside-root secret is an
    escape.
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
