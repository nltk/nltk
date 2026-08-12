#!/usr/bin/env python3
# Natural Language Toolkit: sandboxed-open CI guard
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""Fail if a bare builtin ``open(`` is used in a sandbox-sensitive module.

Modules that resolve *untrusted* paths (corpus readers reading corpus files,
``nltk.data`` resolving resource names) must open files through the pathsec
sandbox -- ``from nltk.pathsec import open as pathsec_open`` -- so path
traversal / symlink-TOCTOU protections apply (CWE-22/59). The two historical
aliases (``pathsec_open`` / ``_secure_open``) both point at ``nltk.pathsec.open``;
this guard makes the *policy* enforceable regardless of the alias, which is the
security intent behind issue #3740 (superseding a one-off alias rename that could
silently drift again).

An AST check is used rather than a regex so that only the *builtin* ``open(...)``
(``ast.Name`` ``open``) is flagged -- ``pathsec_open(...)``, ``self.open(...)``,
``fp.open()``, ``os.open(...)``, ``gzip.open(...)`` etc. (all ``ast.Attribute``
or differently-named) are correctly ignored.

A deliberate, reviewed exception may be annotated with a trailing
``# sandboxed-open ok: <reason>`` comment on the same line.

Usage: ``python tools/check_no_unsandboxed_open.py`` (exit 1 on any violation).
"""

import ast
import os
import sys

# Sandbox-sensitive modules that must never open a file with the builtin. These
# are currently clean; the guard keeps them that way.
GUARDED_PATHS = [
    "nltk/corpus/reader",
    "nltk/corpus/util.py",
    "nltk/data.py",
]

SUPPRESS_MARKER = "# sandboxed-open ok"


def _iter_py_files(path):
    if os.path.isfile(path):
        yield path
        return
    for dirpath, _dirs, files in os.walk(path):
        for name in files:
            if name.endswith(".py"):
                yield os.path.join(dirpath, name)


def find_violations(paths):
    violations = []
    for base in paths:
        for py in _iter_py_files(base):
            with open(
                py, encoding="utf-8"
            ) as fh:  # sandboxed-open ok: the guard itself
                source = fh.read()
            try:
                tree = ast.parse(source, py)
            except SyntaxError:
                continue
            lines = source.splitlines()
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id == "open"
                ):
                    # Scan every physical line of the call so a suppression
                    # marker still counts if the formatter wrapped the call.
                    end = getattr(node, "end_lineno", node.lineno) or node.lineno
                    span = lines[node.lineno - 1 : end]
                    if any(SUPPRESS_MARKER in ln for ln in span):
                        continue
                    line = span[0].strip() if span else ""
                    violations.append((py, node.lineno, line.strip()))
    return violations


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(root)
    violations = find_violations(GUARDED_PATHS)
    if not violations:
        print("sandboxed-open guard: OK (no un-sandboxed open() in guarded modules)")
        return 0
    print(
        "sandboxed-open guard: FAILED -- builtin open() in a sandbox-sensitive module."
    )
    print("Use `from nltk.pathsec import open as pathsec_open` (or annotate a reviewed")
    print(f"exception with `{SUPPRESS_MARKER}: <reason>`). Offenders:\n")
    for path, lineno, text in violations:
        print(f"  {path}:{lineno}: {text}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
