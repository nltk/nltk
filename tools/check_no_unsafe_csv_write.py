#!/usr/bin/env python3
# Natural Language Toolkit: CSV-write CI guard
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""Fail if a sandbox-sensitive module writes untrusted data to a CSV cell raw.

A CSV/TSV file is often opened later in a spreadsheet, where a cell that begins
with ``= + - @`` is executed as a formula (CWE-1236), and if it is displayed in a
terminal an embedded control sequence fires (CWE-150). Modules that export
externally sourced rows (tweets in nltk.twitter.common / nltk.sentiment.util)
must route every cell through ``nltk.termsec.sanitize_csv_field`` first.

In the guarded modules a ``writer.writerow(...)`` / ``writerows(...)`` argument is
accepted only when every cell is sanitised -- a ``[sanitize_csv_field(c) for c in
...]`` comprehension -- or the row is a literal list/tuple of constants (a static
header). Anything else is flagged; annotate a reviewed exception with a trailing
``# unsafe-csv ok: <reason>``.

Usage: ``python tools/check_no_unsafe_csv_write.py`` (exit 1 on any violation).
"""

import ast
import os
import sys

GUARDED_PATHS = [
    "nltk/twitter/common.py",
    "nltk/sentiment/util.py",
]

SUPPRESS_MARKER = "# unsafe-csv ok"
_SANITIZER = "sanitize_csv_field"


def _is_sanitizer_call(node):
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if isinstance(func, ast.Name):
        return func.id == _SANITIZER
    if isinstance(func, ast.Attribute):
        return func.attr == _SANITIZER
    return False


def _is_literal_seq(node):
    return isinstance(node, (ast.List, ast.Tuple)) and all(
        isinstance(e, ast.Constant) for e in node.elts
    )


def _is_sanitized_row(node):
    # [sanitize_csv_field(c) for c in <row>]  ->  every cell neutralised.
    if isinstance(node, (ast.ListComp, ast.GeneratorExp)):
        return _is_sanitizer_call(node.elt)
    # A static header of literal column names.
    return _is_literal_seq(node)


def _is_safe_write(call):
    if not call.args:
        return True
    arg = call.args[0]
    if call.func.attr == "writerow":
        return _is_sanitized_row(arg)
    # writerows: a comprehension/sequence of sanitised rows.
    if isinstance(arg, (ast.ListComp, ast.GeneratorExp)):
        return _is_sanitized_row(arg.elt)
    if isinstance(arg, (ast.List, ast.Tuple)):
        return all(_is_sanitized_row(e) for e in arg.elts)
    return False


def find_violations(paths):
    violations = []
    for py in paths:
        with open(py, encoding="utf-8") as fh:  # sandboxed-open ok: the guard
            source = fh.read()
        try:
            tree = ast.parse(source, py)
        except SyntaxError:
            continue
        lines = source.splitlines()
        for node in ast.walk(tree):
            if not (
                isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            ):
                continue
            if node.func.attr not in ("writerow", "writerows"):
                continue
            if _is_safe_write(node):
                continue
            end = getattr(node, "end_lineno", node.lineno) or node.lineno
            span = lines[node.lineno - 1 : end]
            if any(SUPPRESS_MARKER in ln for ln in span):
                continue
            text = span[0].strip() if span else ""
            violations.append((py, node.lineno, text))
    return violations


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(root)
    violations = find_violations(GUARDED_PATHS)
    if not violations:
        print("unsafe-csv guard: OK (every CSV cell routes through sanitize_csv_field)")
        return 0
    print("unsafe-csv guard: FAILED -- untrusted data written to a CSV cell raw.")
    print("Route each cell through nltk.termsec.sanitize_csv_field, e.g.")
    print("writer.writerow([sanitize_csv_field(c) for c in row]), or annotate a")
    print(f"reviewed exception with `{SUPPRESS_MARKER}: <reason>`. Offenders:\n")
    for path, lineno, text in violations:
        print(f"  {path}:{lineno}: {text}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
