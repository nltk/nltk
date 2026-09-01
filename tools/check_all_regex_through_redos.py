#!/usr/bin/env python3
# Natural Language Toolkit: redos CI guard
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""Fail if any regex in the shipped library is compiled or run with bare ``re``.

Every regular expression in NLTK is applied to input that can be attacker
controlled -- a corpus file, a caller-supplied pattern, a token stream -- so a
catastrophically backtracking pattern or a compile-time bomb is a denial of
service (CWE-1333 / CWE-400). ``nltk.redos`` is the single choke point that
makes that safe: :func:`nltk.redos.compile` refuses a compile-time bomb up front
(:func:`nltk.redos.check_pattern`) and wraps every match in a wall-clock timeout,
and the ``re``-compatible module helpers (``redos.match``/``search``/``sub``/
``split``/``findall``/``finditer``/``fullmatch``/``subn``) route the inline calls
through the same guards.

This guard enforces the policy structurally: a call to ``re.<f>(...)`` or
``regex.<f>(...)`` -- for any pattern-consuming ``<f>`` (``compile``, ``match``,
``search``, ``findall``, ``finditer``, ``fullmatch``, ``sub``, ``subn``,
``split``) -- anywhere under ``nltk/`` is a violation. Use ``redos`` instead.

There is deliberately NO suppression marker: the whole point is that no regex
bypasses the guard, so an exception cannot be annotated away. The two things that
are not violations are structural, not exceptions:

* ``nltk/redos.py`` itself -- it is the wrapper every call routes *through*, so
  it necessarily uses the ``regex`` engine directly (just as ``nltk/pathsec.py``
  is the sandbox that ``check_no_unsandboxed_open`` is built around).
* Non-matching members of the ``re`` module that cannot run a pattern -- flags
  (``re.I``/``re.U`` ...), ``re.escape``, ``re.error``, ``re.Pattern``,
  ``re.purge``. These consume or produce no untrusted match, so they are allowed.

An AST check is used rather than a text search so that ``obj.sub(...)`` (a method
on a pattern object -- which is already a hardened ``TimedPattern`` if it came
from ``redos``), ``self.search(...)``, ``str.split(...)`` etc. are correctly
ignored: only a call whose receiver is the bare ``re``/``regex`` module matches.

Usage: ``python tools/check_all_regex_through_redos.py`` (exit 1 on any
violation).
"""

import ast
import os
import sys

# The whole shipped package is guarded. Everything here is currently routed
# through redos; the guard keeps it that way as the codebase changes.
GUARDED_PATHS = ["nltk"]

# The test tree is exempt: tests legitimately exercise raw ``re`` behaviour
# (e.g. to demonstrate what redos protects against, or to assert on stdlib
# semantics), and a test is not part of the library's attack surface.
_EXEMPT_PREFIXES = (os.path.join("nltk", "test"),)

# ``nltk/redos.py`` is the wrapper itself -- it must use the engine directly.
_EXEMPT_FILES = (os.path.join("nltk", "redos.py"),)

# The bare-module modules whose pattern-consuming calls must go through redos.
_GUARDED_MODULES = frozenset({"re", "regex"})

# Functions that actually compile or run a pattern (so must route through redos).
# ``escape``/``purge``/``template`` and flag/constant/exception attributes run no
# untrusted match and are intentionally excluded.
_GUARDED_FUNCS = frozenset(
    {
        "compile",
        "match",
        "search",
        "findall",
        "finditer",
        "fullmatch",
        "sub",
        "subn",
        "split",
    }
)


class _RegexCallVisitor(ast.NodeVisitor):
    def __init__(self, path):
        self.path = path
        self.violations = []

    def visit_Call(self, node):
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr in _GUARDED_FUNCS:
            recv = func.value
            if isinstance(recv, ast.Name) and recv.id in _GUARDED_MODULES:
                self.violations.append(
                    (node.lineno, f"{recv.id}.{func.attr}(...)")
                )
        self.generic_visit(node)


def _iter_py_files(paths):
    for base in paths:
        for root, _dirs, files in os.walk(base):
            for name in sorted(files):
                if name.endswith(".py"):
                    yield os.path.join(root, name)


def _is_exempt(path):
    norm = os.path.normpath(path)
    if norm in {os.path.normpath(f) for f in _EXEMPT_FILES}:
        return True
    return any(
        norm == p or norm.startswith(p + os.sep) for p in _EXEMPT_PREFIXES
    )


def main():
    violations = []
    for path in _iter_py_files(GUARDED_PATHS):
        if _is_exempt(path):
            continue
        try:
            with open(path, encoding="utf-8") as fh:
                tree = ast.parse(fh.read(), filename=path)
        except (OSError, SyntaxError) as exc:
            print(f"{path}: could not parse ({exc})", file=sys.stderr)
            violations.append((path, 0, "unparseable"))
            continue
        visitor = _RegexCallVisitor(path)
        visitor.visit(tree)
        for lineno, what in visitor.violations:
            violations.append((path, lineno, what))

    if violations:
        print(
            "Regex calls must route through nltk.redos, not bare re/regex "
            f"(found {len(violations)}):\n",
            file=sys.stderr,
        )
        for path, lineno, what in violations:
            print(f"  {path}:{lineno}: {what}", file=sys.stderr)
        print(
            "\nUse redos.compile(...) for compiled patterns, or the re-compatible "
            "redos.match/search/sub/split/findall/finditer/fullmatch/subn helpers "
            "for inline calls. See nltk/redos.py.",
            file=sys.stderr,
        )
        return 1

    print("OK: every regex call routes through nltk.redos.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
