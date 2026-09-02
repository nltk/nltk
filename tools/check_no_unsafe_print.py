#!/usr/bin/env python3
# Natural Language Toolkit: terminal-output CI guard
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""Fail if a sandbox-sensitive module ``print(...)``s untrusted data unescaped.

Modules that echo *externally sourced* text -- a package id/name from a
downloaded server index, a tweet body, an error carrying a server message --
must neutralise terminal control sequences first, or the value can drive the
user's terminal when it is printed (CWE-150). The chokepoint is
``nltk.termsec.sanitize_terminal`` (the same idea as ``pathsec`` for paths and
``jsontags`` for JSON).

In the guarded modules a ``print(...)`` argument is accepted only when it cannot
carry a live control sequence:

* a string/number literal (``ast.Constant``);
* ``sanitize_terminal(...)`` (or ``safe_print(...)``);
* an f-string whose every interpolation is a literal, a ``sanitize_terminal(...)``
  call, or uses the ``!r`` conversion (``repr`` escapes control bytes);
* a ``%``-format whose format string is a literal that uses no ``%s``/``%a``
  (``%r`` and numeric conversions are already escaped/safe).

Anything else -- a raw name/attribute, a ``.format(...)``, a ``%s`` of data, an
f-string interpolation printed with no conversion -- is flagged. A reviewed
exception may be annotated with a trailing ``# unsafe-print ok: <reason>``.

Usage: ``python tools/check_no_unsafe_print.py`` (exit 1 on any violation).
"""

import ast
import os
import sys

# Modules that echo untrusted external content to the terminal. Scoped, like the
# open guard's GUARDED_PATHS: extend it as more echoers are hardened.
GUARDED_PATHS = [
    "nltk/downloader.py",
    "nltk/twitter/twitterclient.py",
]

SUPPRESS_MARKER = "# unsafe-print ok"
_SANITIZERS = {"sanitize_terminal", "safe_print"}


def _is_sanitizer_call(node):
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if isinstance(func, ast.Name):
        return func.id in _SANITIZERS
    if isinstance(func, ast.Attribute):
        return func.attr in _SANITIZERS
    return False


def _is_safe_formatted_value(node):
    # A {..} slot inside an f-string.
    if isinstance(node, ast.Constant):
        return True
    if isinstance(node, ast.FormattedValue):
        if node.conversion == ord("r"):  # {x!r} -> repr escapes control bytes
            return True
        return _safe_expr(node.value)
    return False


def _percent_format_is_safe(node):
    # "<literal>" % (...) is safe when the literal uses no %s/%a of raw data.
    if not (isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod)):
        return False
    left = node.left
    if not (isinstance(left, ast.Constant) and isinstance(left.value, str)):
        return False
    fmt = left.value
    i = 0
    while i < len(fmt):
        if fmt[i] == "%":
            j = i + 1
            while j < len(fmt) and fmt[j] not in "sraidiouxXeEfFgGc%":
                j += 1
            if j < len(fmt) and fmt[j] in "sa":
                return False  # %s / %a can emit raw control bytes
            i = j + 1
        else:
            i += 1
    return True


# Builtins that return a number, never a string carrying control bytes.
_NUMERIC_BUILTINS = {"len", "int", "ord", "id", "hash", "abs", "round"}


def _is_str_constant(node):
    return isinstance(node, ast.Constant) and isinstance(node.value, str)


def _safe_expr(node):
    """Recursively decide an expression cannot carry a live control sequence."""
    if isinstance(node, ast.Constant):
        return True
    if _is_sanitizer_call(node):
        return True
    if _percent_format_is_safe(node):
        return True
    if isinstance(node, ast.JoinedStr):
        return all(_is_safe_formatted_value(v) for v in node.values)
    if isinstance(node, ast.BinOp):
        # A repeated literal ("=" * n): the literal operand fixes the content, so
        # the count operand is irrelevant to control-byte safety.
        if isinstance(node.op, ast.Mult):
            if _is_str_constant(node.left) or _is_str_constant(node.right):
                return True
            return _safe_expr(node.left) and _safe_expr(node.right)
        # A concatenation of safe parts.
        if isinstance(node.op, ast.Add):
            return _safe_expr(node.left) and _safe_expr(node.right)
    if isinstance(node, ast.Call):
        # A numeric builtin returns a number, not a control-bearing string.
        if isinstance(node.func, ast.Name) and node.func.id in _NUMERIC_BUILTINS:
            return True
        # A string method on an already-safe receiver: sanitized.ljust(...).
        if isinstance(node.func, ast.Attribute):
            recv_safe = _safe_expr(node.func.value)
            args_safe = all(_safe_expr(a) for a in node.args)
            return recv_safe and args_safe
    return False


def _is_safe_arg(node):
    return _safe_expr(node)


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
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)):
                continue
            if node.func.id != "print":
                continue
            if all(_is_safe_arg(a) for a in node.args):
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
        print(
            "unsafe-print guard: OK (no unescaped untrusted print in guarded modules)"
        )
        return 0
    print("unsafe-print guard: FAILED -- untrusted data printed without escaping.")
    print("Wrap the value in nltk.termsec.sanitize_terminal(...), use !r, or annotate")
    print(f"a reviewed exception with `{SUPPRESS_MARKER}: <reason>`. Offenders:\n")
    for path, lineno, text in violations:
        print(f"  {path}:{lineno}: {text}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
