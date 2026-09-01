#!/usr/bin/env python3
# Natural Language Toolkit: JSON-deserialization CI guard
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""Fail if any JSON is deserialized with bare ``json`` instead of nltk.jsontags.

``json.load`` / ``json.loads`` build an arbitrary object graph from the input
with no bound on nesting depth or size, so a deeply nested or oversized document
from an untrusted source is a denial of service: unbounded recursion crashes the
interpreter (CWE-674) and a huge document exhausts memory/CPU (CWE-400).
``nltk.jsontags`` is the choke point that makes JSON reading safe:
:func:`~nltk.jsontags.safe_json_loads` and :func:`~nltk.jsontags.safe_json_load`
are drop-in replacements for ``json.loads`` / ``json.load`` that enforce a max
nesting depth and byte cap, and :class:`~nltk.jsontags.JSONTaggedDecoder` bounds
the decode depth for the tag machinery.

This guard enforces the policy structurally: any call to ``json.load``,
``json.loads`` or ``json.JSONDecoder`` (on the bare ``json`` / ``simplejson`` /
``ujson`` / ``orjson`` / ``_json`` module, under any import alias, or imported
bare with ``from json import loads``) anywhere under ``nltk/`` is a violation.
Read through ``jsontags.safe_json_load`` / ``safe_json_loads`` instead.

Serialization (``json.dump`` / ``json.dumps``) is NOT guarded: writing runs no
untrusted input and cannot recurse or allocate on an attacker's behalf.

The things that are not violations are structural, not exceptions:

* ``nltk/jsontags.py`` itself: it is the wrapper every call routes *through*, so
  it necessarily uses the ``json`` module directly (just as ``nltk/pathsec.py``
  is the sandbox ``check_no_unsandboxed_open`` is built around).
* the safe wrappers themselves (``safe_json_load`` / ``safe_json_loads`` /
  ``JSONTaggedDecoder``) are called by their own names, not on the ``json``
  module, so they are (correctly) ignored.

A deliberate, reviewed exception may be annotated with a trailing
``# json-load ok: <reason>`` comment on the same line.

An AST check is used rather than a text search so that ``obj.load(...)`` (a method
on some other object), ``pickle.load(...)``, ``yaml.load(...)`` etc. are correctly
ignored: only a call whose receiver resolves to the bare ``json`` (or a sibling)
module, or a name imported directly from it, matches. Import aliases
(``import json as j``, ``from json import loads``) are tracked per file so neither
can smuggle a bare deserialization past the guard.

Usage: ``python tools/check_all_json_through_jsontags.py`` (exit 1 on any
violation).
"""

import ast
import os
import sys

# The whole shipped package is guarded. Everything here is currently routed
# through jsontags; the guard keeps it that way as the codebase changes.
GUARDED_PATHS = ["nltk"]

# The test tree is exempt: tests legitimately exercise raw ``json`` behaviour
# (e.g. to craft the deep/oversized payloads jsontags must refuse, or to assert
# on stdlib semantics), and a test is not part of the library's attack surface.
_EXEMPT_PREFIXES = (os.path.join("nltk", "test"),)

# ``nltk/jsontags.py`` is the wrapper itself: it must use ``json`` directly.
_EXEMPT_FILES = (os.path.join("nltk", "jsontags.py"),)

# The stdlib / drop-in json modules whose deserializing calls must go through
# jsontags. The C accelerator ``_json`` is included for completeness.
_JSON_MODULES = frozenset({"json", "simplejson", "ujson", "orjson", "_json"})

# Attributes that deserialize JSON (unbounded recursion / allocation) and so must
# route through jsontags. ``dump`` / ``dumps`` serialise and are intentionally
# excluded; ``JSONDecoder`` is a deserializer constructor and is guarded.
_GUARDED_FUNCS = frozenset({"load", "loads", "JSONDecoder"})

SUPPRESS_MARKER = "# json-load ok"


class _JsonCallVisitor(ast.NodeVisitor):
    def __init__(self, path, suppressed_lines):
        self.path = path
        self.suppressed_lines = suppressed_lines
        self.violations = []
        # Local name -> json module (``import json`` / ``import json as j`` /
        # ``import ujson as json``). Seeded so a file that shadows without
        # importing (unlikely) still trips on the bare module names.
        self._module_aliases = set(_JSON_MODULES)
        # Local name -> the guarded func it was imported as
        # (``from json import loads`` -> ``loads``).
        self._func_aliases = {}

    def _flag(self, node, what):
        if node.lineno not in self.suppressed_lines:
            self.violations.append((node.lineno, what))

    def visit_Import(self, node):
        for alias in node.names:
            if alias.name in _JSON_MODULES:
                self._module_aliases.add(alias.asname or alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module in _JSON_MODULES:
            for alias in node.names:
                if alias.name == "*":
                    # ``from json import *`` pulls the guarded callables in
                    # untracked; refuse it outright.
                    self._flag(node, f"from {node.module} import *")
                elif alias.name in _GUARDED_FUNCS:
                    self._func_aliases[alias.asname or alias.name] = alias.name
        self.generic_visit(node)

    def visit_Call(self, node):
        func = node.func
        # ``json.loads(...)`` / ``j.load(...)``: attribute on a json module.
        if isinstance(func, ast.Attribute) and func.attr in _GUARDED_FUNCS:
            recv = func.value
            if isinstance(recv, ast.Name) and recv.id in self._module_aliases:
                self._flag(node, f"{recv.id}.{func.attr}(...)")
        # ``loads(...)``: a guarded func imported bare from a json module.
        elif isinstance(func, ast.Name) and func.id in self._func_aliases:
            self._flag(node, f"{func.id}(...)  [from json]")
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
    return any(norm == p or norm.startswith(p + os.sep) for p in _EXEMPT_PREFIXES)


def _suppressed_lines(source):
    return {
        i
        for i, line in enumerate(source.splitlines(), start=1)
        if SUPPRESS_MARKER in line
    }


def main():
    violations = []
    for path in _iter_py_files(GUARDED_PATHS):
        if _is_exempt(path):
            continue
        try:
            with open(path, encoding="utf-8") as fh:
                source = fh.read()
            tree = ast.parse(source, filename=path)
        except (OSError, SyntaxError) as exc:
            print(f"{path}: could not parse ({exc})", file=sys.stderr)
            violations.append((path, 0, "unparseable"))
            continue
        visitor = _JsonCallVisitor(path, _suppressed_lines(source))
        visitor.visit(tree)
        for lineno, what in visitor.violations:
            violations.append((path, lineno, what))

    if violations:
        print(
            "JSON deserialization must route through nltk.jsontags, not bare json "
            f"(found {len(violations)}):\n",
            file=sys.stderr,
        )
        for path, lineno, what in violations:
            print(f"  {path}:{lineno}: {what}", file=sys.stderr)
        print(
            "\nRead through jsontags.safe_json_load / safe_json_loads (or "
            "JSONTaggedDecoder for tagged objects); they bound nesting depth and "
            "size. See nltk/jsontags.py. A reviewed exception may be annotated "
            f"with a trailing '{SUPPRESS_MARKER}: <reason>' comment.",
            file=sys.stderr,
        )
        return 1

    print("OK: every JSON deserialization routes through nltk.jsontags.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
