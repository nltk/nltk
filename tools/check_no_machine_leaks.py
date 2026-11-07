#!/usr/bin/env python3
# Natural Language Toolkit: machine-leak CI guard
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""Fail if a tracked file names a developer's home directory or carries a
credential-shaped token.

A test that falls back to ``/Users/<dev>/...`` when an environment variable is
unset works on one laptop and silently skips everywhere else, and the path
itself ends up in the public tree, the tag and the sdist: the 3.10.4 release
shipped a JDK path under a developer's home directory in two harnesses and
real users' home directories in two examples. A pasted API token or private
key is worse, and a release can never be un-published (CWE-200, CWE-540,
CWE-798).

The guard scans every git-tracked text file. A home directory is flagged by
name: ``/Users/<name>``, ``/home/<name>`` or ``<drive>:\\Users\\<name>`` where
``<name>`` is not a documented placeholder (``user``, ``runner``, ``victim``
and the other entries of :data:`PLACEHOLDERS`). Tokens are flagged by the
well-known prefixes of PyPI, GitHub, AWS, Hugging Face, Anthropic, Google and
Slack credentials and by PEM private-key headers. A reviewed exception may be
annotated with a trailing ``# machine-leak ok: <reason>`` on the same line.

Usage: ``python tools/check_no_machine_leaks.py [path ...]`` (exit 1 on any
violation; with no path, every git-tracked file). The functions are reused by
``tools/check_sdist_hygiene.py`` to scan built distributions.
"""

import os
import re
import subprocess
import sys

SUPPRESS_MARKER = "# machine-leak ok"

# Names that stand for "some user" in documentation, fixtures and containers.
PLACEHOLDERS = frozenset(
    {
        "user",
        "username",
        "users",
        "you",
        "yourname",
        "your_name",
        "me",
        "appuser",
        "runner",
        "victim",
        "attacker",
        "someone",
        "example",
        "nobody",
        "nltk",
        "x",
    }
)

_NAME = r"[A-Za-z0-9_.-]+"
HOME_PATTERNS = (
    re.compile(rb"(?<![\w/])/Users/(" + _NAME.encode() + rb")"),
    re.compile(rb"(?<![\w/])/home/(" + _NAME.encode() + rb")"),
    re.compile(rb"[A-Za-z]:\\\\?Users\\\\?(" + _NAME.encode() + rb")"),
)

# Credential shapes: issuer prefixes that never occur in prose or code.
TOKEN_PATTERNS = (
    ("PyPI API token", re.compile(rb"pypi-AgE[A-Za-z0-9_-]{40,}")),
    ("GitHub token", re.compile(rb"\bgh[pousr]_[A-Za-z0-9]{36,}")),
    ("GitHub fine-grained token", re.compile(rb"github_pat_[A-Za-z0-9_]{40,}")),
    ("AWS access key id", re.compile(rb"\bAKIA[0-9A-Z]{16}\b")),
    ("Hugging Face token", re.compile(rb"\bhf_[A-Za-z0-9]{30,}")),
    ("Anthropic API key", re.compile(rb"\bsk-ant-[A-Za-z0-9_-]{40,}")),
    ("Google API key", re.compile(rb"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("Slack token", re.compile(rb"\bxox[abprs]-[A-Za-z0-9-]{20,}")),
    ("OpenAI-style key", re.compile(rb"\bsk-[A-Za-z0-9]{40,}\b")),
    ("private key", re.compile(rb"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
)

# Formats whose bytes are not text; their names are still checked by callers.
BINARY_SUFFIXES = (
    ".png",
    ".gif",
    ".jpg",
    ".jpeg",
    ".tiff",
    ".ico",
    ".pickle",
    ".pkl",
    ".zip",
    ".gz",
    ".whl",
)


def check_bytes(data):
    """Yield ``(lineno, kind, excerpt)`` for every leak in ``data``."""
    for lineno, line in enumerate(data.split(b"\n"), 1):
        if SUPPRESS_MARKER.encode() in line:
            continue
        for pattern in HOME_PATTERNS:
            for match in pattern.finditer(line):
                name = match.group(1).decode("utf-8", "replace")
                if name.lower() in PLACEHOLDERS:
                    continue
                yield lineno, "home directory of " + name, _excerpt(line)
        for kind, pattern in TOKEN_PATTERNS:
            if pattern.search(line):
                yield lineno, kind, _excerpt(line, 32)


def check_text(text):
    """Convenience for callers holding ``str``; same tuples as check_bytes."""
    return list(check_bytes(text.encode("utf-8", "surrogateescape")))


def _excerpt(line, width=100):
    text = line.decode("utf-8", "replace").strip()
    return text if len(text) <= width else text[:width] + "..."


def is_binary_name(path):
    return path.lower().endswith(BINARY_SUFFIXES)


def tracked_files(root):
    out = subprocess.run(
        ["git", "-C", root, "ls-files", "-z"],
        check=True,
        capture_output=True,
    ).stdout
    return [p.decode("utf-8", "surrogateescape") for p in out.split(b"\0") if p]


def find_violations(root, paths):
    """``(path, lineno, kind, excerpt)`` for every leak in ``paths``."""
    violations = []
    for rel in paths:
        if is_binary_name(rel):
            continue
        full = os.path.join(root, rel)
        if not os.path.isfile(full):
            continue
        with open(full, "rb") as fh:  # sandboxed-open ok: the guard
            data = fh.read()
        for lineno, kind, excerpt in check_bytes(data):
            violations.append((rel, lineno, kind, excerpt))
    return violations


def main(argv=None):
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    paths = (argv if argv is not None else sys.argv[1:]) or tracked_files(root)
    violations = find_violations(root, paths)
    if not violations:
        print("machine-leak guard: OK (no home directories or credential tokens)")
        return 0
    print("machine-leak guard: FAILED, a tracked file leaks machine-local state.")
    print("A home directory path belongs in an environment variable; a token")
    print("never belongs in the tree. Annotate a reviewed example with")
    print(f"`{SUPPRESS_MARKER}: <reason>`. Offenders:\n")
    for path, lineno, kind, excerpt in violations:
        print(f"  {path}:{lineno}: {kind} -> {excerpt}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
