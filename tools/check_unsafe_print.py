#!/usr/bin/env python3
# Natural Language Toolkit: unsafe-print CI guard
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""Fail if a ``print()`` / ``sys.std*.write()`` can emit an unsanitised value.

A value an attacker can influence (a corpus token, a tool subprocess line, a
tweet, a user expression) printed raw to a terminal can carry ANSI/OSC escape
sequences or Unicode bidi/invisibles that hijack or spoof the terminal
(CWE-150 / 1007 / 1236). ``nltk.termsec.safe_print`` / ``sanitize_terminal`` is
the choke point that neutralises them.

This guard makes the policy structural, like ``no-unsandboxed-open`` for pathsec:
EVERY ``print`` in the shipped tree must be one of --

  * ``safe_print(...)`` (sanitises every argument), or
  * a print whose arguments are ALL provably harmless: string/number literals,
    or interpolations that are entirely ``repr``-escaped (``!r`` / ``%r`` / ``%a``)
    or numeric-formatted (``%d`` / ``%.3f`` / ``{n:d}`` ...), which cannot carry a
    control byte, or an argument already wrapped in ``sanitize_terminal`` /
    ``sanitize_csv_field``, or
  * a print explicitly reviewed benign with a trailing ``# unsafe-print ok: <why>``
    marker on the statement's first or last line.

Anything else -- a bare ``print(value)``, ``print(f"{value}")``, ``print("%s" % v)``
-- is a violation: route it through ``safe_print`` or justify it with the marker.

Usage: ``python tools/check_unsafe_print.py`` (exit 1 on any violation).
"""

import ast
import os
import re
import sys

GUARDED_PATHS = ["nltk"]
_EXEMPT_PREFIXES = (os.path.join("nltk", "test"),)
_EXEMPT_FILES = (os.path.join("nltk", "termsec.py"),)
_MARKER = "unsafe-print ok"
_SANITIZERS = {"safe_print", "sanitize_terminal", "sanitize_csv_field"}

# %-format conversion chars that cannot carry a control byte: repr/ascii-repr,
# every integer/float base, and the literal percent. 's' (str) and 'c' (chr of an
# int -> could be ESC) are deliberately excluded.
_SAFE_PERCENT = set("radiouxXeEfFgGn%")
_PERCENT_CONV = re.compile(r"%[-+ #0-9.*]*([a-zA-Z%])")
# f-string numeric type chars (the last char of a format spec like ``.3f``/``d``).
_NUMERIC_SPEC_END = set("bcdoxXneEfFgG%")


def _spec_is_numeric(fmtspec):
    if not isinstance(fmtspec, ast.JoinedStr):
        return False
    text = "".join(v.value for v in fmtspec.values if isinstance(v, ast.Constant))
    return bool(text) and text[-1] in _NUMERIC_SPEC_END and "s" not in text[-1]


def _fvalue_is_safe(node):
    # An f-string ``{expr}`` field is harmless iff repr-converted or numeric-spec'd.
    if node.conversion in (114, 97):  # !r , !a
        return True
    return _spec_is_numeric(node.format_spec)


def _percent_is_safe(fmt):
    convs = _PERCENT_CONV.findall(fmt)
    return bool(convs) and all(c in _SAFE_PERCENT for c in convs)


def _is_safe_arg(arg):
    if isinstance(arg, ast.Constant):
        return True
    if isinstance(arg, ast.JoinedStr):  # f-string
        return all(
            isinstance(v, ast.Constant) or _fvalue_is_safe(v) for v in arg.values
        )
    if isinstance(arg, ast.BinOp):
        if isinstance(arg.op, ast.Mod):
            # "...%r..." % value -> safe iff the format conversions are all safe
            if isinstance(arg.left, ast.Constant) and isinstance(arg.left.value, str):
                return _percent_is_safe(arg.left.value)
            return False
        if isinstance(arg.op, ast.Add):  # concatenation: safe iff both sides are
            return _is_safe_arg(arg.left) and _is_safe_arg(arg.right)
        return False
    if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name):
        # repr()/ascii() escape control bytes; the sanitisers neutralise them.
        return arg.func.id in _SANITIZERS or arg.func.id in ("repr", "ascii")
    return False


def _is_print_call(node):
    f = node.func
    if isinstance(f, ast.Name) and f.id == "print":
        return "print"
    if (
        isinstance(f, ast.Attribute)
        and f.attr == "write"
        and isinstance(f.value, ast.Attribute)
        and getattr(f.value.value, "id", "") == "sys"
        and f.value.attr in ("stdout", "stderr")
    ):
        return "write"
    return None


def check_file(path, relpath, source_lines):
    with open(path, encoding="utf-8") as fh:
        try:
            tree = ast.parse("".join(source_lines), filename=path)
        except SyntaxError:
            return []
    violations = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        kind = _is_print_call(node)
        if kind is None:
            continue
        args = [a for a in node.args if not isinstance(a, ast.Starred)]
        if all(_is_safe_arg(a) for a in args):
            continue  # empty print() / literal / repr / numeric / already-sanitised
        # a marker on the first OR last physical line of the statement clears it
        first, last = node.lineno, getattr(node, "end_lineno", node.lineno)
        if any(_MARKER in source_lines[i - 1] for i in (first, last)):
            continue
        violations.append((node.lineno, kind))
    return violations


def main():
    root = os.getcwd()
    failures = []
    for guarded in GUARDED_PATHS:
        for dirpath, _dirs, files in os.walk(os.path.join(root, guarded)):
            for name in files:
                if not name.endswith(".py"):
                    continue
                path = os.path.join(dirpath, name)
                relpath = os.path.relpath(path, root)
                if relpath.startswith(_EXEMPT_PREFIXES) or relpath in _EXEMPT_FILES:
                    continue
                with open(path, encoding="utf-8") as fh:
                    lines = fh.readlines()
                for lineno, kind in check_file(path, relpath, lines):
                    failures.append((relpath, lineno, kind))
    if failures:
        print(
            f"{len(failures)} unsafe print/write site(s) (CWE-150/1007/1236). Route "
            "through nltk.termsec.safe_print, or add a trailing "
            "'# unsafe-print ok: <why>' marker:\n"
        )
        for relpath, lineno, kind in sorted(failures):
            print(f"  {relpath}:{lineno}: bare {kind}(<value>)")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
