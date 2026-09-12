#!/usr/bin/env python3
# Natural Language Toolkit: bare-execution CI guard
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""Fail if a bare builtin ``eval(``, ``exec(`` or ``compile(`` is used.

These builtins turn a string into running code, so interpolating any
attacker-influenced fragment into one is a code-injection primitive (CWE-94 /
CWE-95). NLTK needs exactly one of them: ``nltk.decorators`` builds a
signature-preserving wrapper with ``eval``, and that call is fenced by
``_assert_safe_signature`` first (CVE-2026-14727). Every such reviewed use is
annotated with a trailing ``# bare-exec ok: <reason>`` on the same line; this
guard fails on any un-annotated one so a new bare ``eval``/``exec``/``compile``
cannot slip in.

An AST check is used, not a regex, so only the *builtin* is flagged: an
``ast.Attribute`` call such as ``re.compile(...)`` or ``self.eval(...)`` is
ignored, and a module that defines its own ``def compile`` (``nltk.redos``, whose
``compile`` is the ReDoS-safe regex compiler) shadows the builtin, so its own
``compile(...)`` calls are ignored too.

Usage: ``python tools/check_no_bare_execution.py`` (exit 1 on any violation).
"""

import ast
import os
import sys

TARGETS = {"eval", "exec", "compile"}
SUPPRESS_MARKER = "# bare-exec ok"
SCAN_ROOTS = ["nltk"]
# Test trees legitimately construct hostile code strings to prove the guards
# reject them; those are not shipped execution sites.
EXCLUDE_DIRS = {"test", "tests"}


def _iter_py_files(path):
    if os.path.isfile(path):
        yield path
        return
    for dirpath, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for name in files:
            if name.endswith(".py"):
                yield os.path.join(dirpath, name)


def _shadowed_builtins(tree):
    """Names rebound at module scope, so a call to them is not the builtin."""
    shadowed = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.name in TARGETS:
                shadowed.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in TARGETS:
                    shadowed.add(target.id)
    return shadowed


def find_violations(paths):
    violations = []
    for base in paths:
        for py in _iter_py_files(base):
            with open(py, encoding="utf-8") as fh:  # sandboxed-open ok: the guard
                source = fh.read()
            try:
                tree = ast.parse(source, py)
            except SyntaxError:
                continue
            shadowed = _shadowed_builtins(tree)
            lines = source.splitlines()
            for node in ast.walk(tree):
                if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)):
                    continue
                name = node.func.id
                if name not in TARGETS or name in shadowed:
                    continue
                end = getattr(node, "end_lineno", node.lineno) or node.lineno
                span = lines[node.lineno - 1 : end]
                if any(SUPPRESS_MARKER in ln for ln in span):
                    continue
                text = span[0].strip() if span else ""
                violations.append((py, node.lineno, name, text))
    return violations


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(root)
    violations = find_violations(SCAN_ROOTS)
    if not violations:
        print("bare-execution guard: OK (no un-annotated eval/exec/compile)")
        return 0
    print("bare-execution guard: FAILED -- bare eval/exec/compile of a code string.")
    print("Interpolating untrusted text into one is a code-injection primitive.")
    print(f"Fence and annotate a reviewed use with `{SUPPRESS_MARKER}: <reason>`.\n")
    for path, lineno, name, text in violations:
        print(f"  {path}:{lineno}: {name}(...) -> {text}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
