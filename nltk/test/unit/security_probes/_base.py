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


def within_budget(func, budget=DOS_BUDGET, repeats=3):
    """Fastest of ``repeats`` runs of ``func``; ``(ok, seconds)``, ok if under budget.

    Absolute wall-clock, not a doubling ratio: a pre-patch quadratic ran for
    tens of seconds on these payloads while the fixed code is milliseconds, so a
    generous budget separates them cleanly. Min-of-k because one sample on a
    loaded CI runner is noise -- a tight ratio there produced a false
    VULNERABLE. Contention only adds time, so the minimum is closest to truth.
    """
    best = min(timed(func) for _ in range(repeats))
    return best < budget, best


def read_source(dotted_module):
    """Source of an importable NLTK module, via its own ``__file__``."""
    module = importlib.import_module(dotted_module)
    return open(module.__file__, encoding="utf-8").read()


def _outside_root_target():
    """A real file outside every pathsec-allowed root, plus a canary in it.

    Must be genuinely outside the allowed roots: on macOS the private system
    temp dir *is* an allowed root, so a temp file is not an escape target. A
    system file is. The canary must survive tokenisation/parsing, so it is a
    substring that appears verbatim in the file, not a word a reader would
    split.
    """
    for path, canary in (("/etc/passwd", "root:"), ("/etc/hosts", "localhost")):
        try:
            if canary in open(path, encoding="utf-8", errors="ignore").read():
                return path, canary
        except OSError:
            continue
    return None, None


OUTSIDE_TARGET, OUTSIDE_CANARY = _outside_root_target()

#: Substrings that mark a rejection as a *security* decision rather than an
#: incidental failure (a missing file, a parse error). A probe may only report
#: FIXED when the attack was refused by one of these -- proving it reached the
#: guard -- or when the guard is disabled and it leaks.
_SECURITY_MARKERS = (
    "security",
    "violation",
    "pathsec",
    "unauthorized",
    "outside",
    "traversal",
    "must be relative",
    "unsafe",
)


def is_security_rejection(exc):
    return any(marker in str(exc).lower() for marker in _SECURITY_MARKERS)


class Sandbox:
    """A corpus root holding a symlink to a real outside-root file."""

    def __init__(self):
        self.dir = tempfile.mkdtemp()
        self.root = os.path.join(self.dir, "corpus")
        os.makedirs(self.root, exist_ok=True)
        self.target = OUTSIDE_TARGET
        self.canary = OUTSIDE_CANARY
        self.link = os.path.join(self.root, "link.xml")
        try:
            os.symlink(OUTSIDE_TARGET or "/nonexistent", self.link)
        except OSError:
            self.link = None

    def cleanup(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def leaked(self, value):
        text = value if isinstance(value, str) else str(value)
        return bool(self.canary) and self.canary in text


def guard_rejects(guard):
    """Probe a containment guard directly with real outside-root paths.

    For readers whose public read needs a fully populated corpus, drive the
    guard function the advisory added instead: it must security-reject a
    symlink, an absolute path and a traversal that resolve outside the root.
    ``guard`` is ``fn(path, root)``; VULNERABLE if any passes, FIXED if all are
    security-rejected.
    """
    if not OUTSIDE_TARGET:
        return STATIC, "no readable outside-root target on this platform"
    box = Sandbox()
    try:
        cases = {
            "symlink": box.link,
            "absolute": OUTSIDE_TARGET,
            "traversal": os.path.join(box.root, "../" * 8 + OUTSIDE_TARGET.lstrip("/")),
        }
        notes = []
        for label, path in cases.items():
            if path is None:
                continue
            try:
                guard(path, box.root)
                return VULNERABLE, "%s path passed the guard" % label
            except Exception as exc:
                if not is_security_rejection(exc):
                    return STATIC, "{} rejected non-securely ({})".format(
                        label, type(exc).__name__
                    )
                notes.append(label)
        return FIXED, "guard security-rejects: " + ", ".join(notes)
    finally:
        box.cleanup()


def escape_probe(attempts):
    """Drive outside-root read attempts against a sandbox.

    ``attempts`` is a list of ``(label, fn(sandbox))``. Each fn tries to make a
    reader return the contents of a real outside-root file.

    * any fn returns the canary -> VULNERABLE (a genuine escape).
    * a fn refused by a security check -> that attempt reached the guard.
    * a fn that fails incidentally (missing file, parse error) never reached
      the sink; it is reported as such, not counted as a defence.

    FIXED requires at least one attempt to have been security-refused, so a
    probe cannot pass merely because every attack fizzled before the guard.
    """
    if not OUTSIDE_TARGET:
        return STATIC, "no readable outside-root target on this platform"
    box = Sandbox()
    try:
        reached, notes = False, []
        for label, run in attempts:
            try:
                result = run(box)
            except Exception as exc:
                if is_security_rejection(exc):
                    reached = True
                    notes.append(f"{label}=blocked({type(exc).__name__})")
                else:
                    notes.append(f"{label}=unreached({type(exc).__name__})")
                continue
            if box.leaked(result):
                return VULNERABLE, f"{label} read {box.target}"
            notes.append("%s=no-leak" % label)
        detail = "; ".join(notes)
        if reached:
            return FIXED, detail
        return STATIC, "attack never reached a security check: " + detail
    finally:
        box.cleanup()
