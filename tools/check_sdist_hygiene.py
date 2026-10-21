#!/usr/bin/env python3
# Natural Language Toolkit: distribution hygiene CI guard
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""Fail if a built sdist or wheel carries anything but the tracked tree.

``MANIFEST.in`` grafts ``nltk/`` and ``web/`` wholesale, so whatever sits in
the working tree at build time ships: the 3.10.3 sdist on PyPI contains 293
stale bytecode files, and the first 3.10.4 build held 57 of them (``make
clean`` re-imports nltk to read the version, planting them again after it
cleared them). A release can never be re-uploaded, so the check runs on the
archives themselves, in CI on every code change and in ``release.yml`` on the
artifacts it is about to publish.

For each archive the guard checks that

* every member is a git-tracked file with identical bytes, or one of the
  generated files setuptools writes (``PKG-INFO``, ``setup.cfg``,
  ``nltk.egg-info/*`` in the sdist; ``*.dist-info/*`` in the wheel);
* no member is compiled bytecode, a cache directory, an editor or OS leftover,
  a log, a credential file or a hidden file other than a ``.gitkeep``;
* the sdist carries every tracked file under ``nltk/`` and ``web/``, and the
  wheel carries nothing under ``nltk/test/unit/`` (the wheel is the library
  plus doctests; the unit tests are for the repository and CI);
* no member names a developer's home directory or holds a credential-shaped
  token (``tools/check_no_machine_leaks.py`` does the scanning).

Usage: ``python tools/check_sdist_hygiene.py dist/*`` (exit 1 on any finding).
Archives are read in memory and never extracted.
"""

import fnmatch
import importlib.util
import os
import posixpath
import sys
import tarfile
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

JUNK_PATTERNS = (
    "*.pyc",
    "*.pyo",
    "*.pyd",
    "*~",
    "*.orig",
    "*.rej",
    "*.swp",
    "*.swo",
    "*.bak",
    "*.log",
    "*.tmp",
    "*.pem",
    "*.key",
    "*.p12",
    "*.pfx",
    ".DS_Store",
    "Thumbs.db",
    ".pypirc",
    ".netrc",
    ".env",
    ".env.*",
    "MANIFEST",
)
JUNK_DIRS = frozenset({"__pycache__", ".git", ".idea", ".vscode", ".pytest_cache"})
HIDDEN_OK = frozenset({".gitkeep"})

SDIST_GENERATED = ("PKG-INFO", "setup.cfg")
SDIST_GENERATED_DIRS = ("nltk.egg-info/",)
# These tracked files legitimately ship with bytes setuptools rewrote.
SDIST_REWRITTEN = frozenset({"setup.cfg"})
SDIST_MUST_CARRY = ("nltk/", "web/")
WHEEL_PACKAGE = "nltk/"
WHEEL_EXCLUDED = ("nltk/test/unit/",)


def _load_leak_guard():
    path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "check_no_machine_leaks.py"
    )
    spec = importlib.util.spec_from_file_location("check_no_machine_leaks", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _tracked_bytes(root, rel):
    with open(os.path.join(root, rel), "rb") as fh:  # sandboxed-open ok: the guard
        return fh.read()


def _junk_reason(member):
    parts = member.split("/")
    for part in parts[:-1]:
        if part in JUNK_DIRS:
            return "cache or tool directory " + part
    name = parts[-1]
    for pattern in JUNK_PATTERNS:
        if fnmatch.fnmatch(name, pattern):
            return "junk file " + pattern
    if name.startswith(".") and name not in HIDDEN_OK:
        return "hidden file"
    return None


def _sdist_members(path):
    """``(relative name, bytes)`` for each file member, plus the top directory."""
    members = []
    top = None
    with tarfile.open(path, "r:gz") as tar:
        for info in tar:
            if info.isdir():
                continue
            name = posixpath.normpath(info.name)
            first, _, rest = name.partition("/")
            if top is None:
                top = first
            if not info.isfile() or first != top or not rest:
                members.append((name, None))
                continue
            members.append((rest, tar.extractfile(info).read()))
    return top, members


def check_sdist(path, tracked, root=ROOT, leaks=None):
    """Findings for one sdist as ``(member, kind, detail)`` tuples."""
    leaks = leaks or _load_leak_guard()
    findings = []
    top, members = _sdist_members(path)
    seen = set()
    for member, data in members:
        if data is None:
            findings.append((member, "outside the release directory", top))
            continue
        seen.add(member)
        reason = _junk_reason(member)
        if reason:
            findings.append((member, reason, ""))
            continue
        generated = member in SDIST_GENERATED or member.startswith(SDIST_GENERATED_DIRS)
        if member in tracked:
            if member not in SDIST_REWRITTEN and data != _tracked_bytes(root, member):
                findings.append((member, "bytes differ from the tracked file", ""))
        elif not generated:
            findings.append((member, "not a git-tracked file", ""))
        if not leaks.is_binary_name(member):
            for lineno, kind, excerpt in leaks.check_bytes(data):
                findings.append((f"{member}:{lineno}", kind, excerpt))
    for rel in sorted(tracked):
        if rel.startswith(SDIST_MUST_CARRY) and rel not in seen:
            findings.append((rel, "tracked file missing from the sdist", ""))
    return findings


def check_wheel(path, tracked, root=ROOT, leaks=None):
    """Findings for one wheel as ``(member, kind, detail)`` tuples."""
    leaks = leaks or _load_leak_guard()
    findings = []
    with zipfile.ZipFile(path) as whl:
        for info in whl.infolist():
            member = posixpath.normpath(info.filename)
            if info.is_dir():
                continue
            reason = _junk_reason(member)
            if reason:
                findings.append((member, reason, ""))
                continue
            data = whl.read(info)
            first = member.partition("/")[0]
            if first.endswith(".dist-info"):
                pass
            elif member.startswith(WHEEL_PACKAGE):
                if member.startswith(WHEEL_EXCLUDED):
                    findings.append((member, "unit test shipped in the wheel", ""))
                elif member not in tracked:
                    findings.append((member, "not a git-tracked file", ""))
                elif data != _tracked_bytes(root, member):
                    findings.append((member, "bytes differ from the tracked file", ""))
            else:
                findings.append((member, "outside the package", ""))
            if not leaks.is_binary_name(member):
                for lineno, kind, excerpt in leaks.check_bytes(data):
                    findings.append((f"{member}:{lineno}", kind, excerpt))
    return findings


def check_archive(path, tracked, root=ROOT, leaks=None):
    if path.endswith(".tar.gz"):
        return check_sdist(path, tracked, root, leaks)
    if path.endswith(".whl"):
        return check_wheel(path, tracked, root, leaks)
    return [(path, "not an sdist (.tar.gz) or a wheel (.whl)", "")]


def main(argv=None):
    paths = argv if argv is not None else sys.argv[1:]
    if not paths:
        print("usage: check_sdist_hygiene.py dist/*.tar.gz dist/*.whl")
        return 2
    leaks = _load_leak_guard()
    tracked = set(leaks.tracked_files(ROOT))
    status = 0
    for path in paths:
        findings = check_archive(path, tracked, ROOT, leaks)
        if not findings:
            print(f"distribution hygiene: OK {path}")
            continue
        status = 1
        print(f"distribution hygiene: FAILED {path}")
        for member, kind, detail in findings:
            print(f"  {member}: {kind}" + (f" -> {detail}" if detail else ""))
    if status:
        print("\nA release can never be re-uploaded: rebuild from a clean checkout")
        print(
            "(no __pycache__, nothing untracked under nltk/ or web/) and fix the tree."
        )
    return status


if __name__ == "__main__":
    sys.exit(main())
