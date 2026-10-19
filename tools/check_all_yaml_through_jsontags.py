#!/usr/bin/env python3
# Natural Language Toolkit: YAML-deserialization CI guard
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""Fail if any YAML is deserialized with bare ``yaml`` instead of nltk.jsontags.

PyYAML's ``yaml.safe_load`` (and its siblings) build an object graph from the
input with no bound on nesting depth, node count or size, so a deeply nested or
oversized document from an untrusted source is a denial of service: the safe
loader composes the node graph with ordinary Python recursion, so a document a
few hundred levels deep raises an uncaught ``RecursionError`` (CWE-674), and a
large flat document runs for minutes in the pure-Python resolver (CWE-400).
``nltk.jsontags`` is the choke point that makes YAML reading safe:
:func:`~nltk.jsontags.safe_yaml_loads` and :func:`~nltk.jsontags.safe_yaml_load`
are drop-in replacements for ``yaml.safe_load`` that enforce a max nesting
depth, a max node count and a byte cap, raising a bounded ``ValueError``.

This guard enforces the policy structurally: any call to a deserializing
``yaml`` attribute (``load``, ``safe_load``, ``full_load``, ``unsafe_load`` and
their ``*_all`` forms) on the bare ``yaml`` / ``ruamel.yaml`` / ``oyaml``
module, under any import alias, or imported bare with
``from yaml import safe_load`` anywhere under ``nltk/`` is a violation. Read
through ``jsontags.safe_yaml_load`` / ``safe_yaml_loads`` instead.

Serialization (``yaml.dump`` / ``yaml.safe_dump``) is NOT guarded: writing runs
no untrusted input and cannot recurse or allocate on an attacker's behalf.

The things that are not violations are structural, not exceptions:

* ``nltk/jsontags.py`` itself: it is the wrapper every call routes through, so
  it necessarily uses the ``yaml`` module directly (just as ``nltk/pathsec.py``
  is the sandbox ``check_no_unsandboxed_open`` is built around).
* the safe wrappers themselves (``safe_yaml_load`` / ``safe_yaml_loads``) are
  called by their own names, not on the ``yaml`` module, so they are ignored.

A deliberate, reviewed exception may be annotated with a trailing
``# yaml-load ok: <reason>`` comment on the same line.

An AST check is used rather than a text search so that ``obj.load(...)`` (a
method on some other object), ``json.load(...)`` etc. are correctly ignored:
only a call whose receiver resolves to the bare ``yaml`` (or a sibling) module,
or a name imported directly from it, matches. Import aliases
(``import yaml as y``, ``from yaml import safe_load``) are tracked per file so
neither can smuggle a bare deserialization past the guard.

Usage: ``python tools/check_all_yaml_through_jsontags.py`` (exit 1 on any
violation).
"""

import ast
import os
import sys

# The whole shipped package is guarded.
GUARDED_PATHS = ["nltk"]

# The test tree is exempt: tests legitimately exercise raw ``yaml`` behaviour
# (e.g. to craft the deep/oversized payloads jsontags must refuse), and a test
# is not part of the library's attack surface.
_EXEMPT_PREFIXES = (os.path.join("nltk", "test"),)

# ``nltk/jsontags.py`` is the wrapper itself: it must use ``yaml`` directly.
_EXEMPT_FILES = (os.path.join("nltk", "jsontags.py"),)

# The YAML modules whose deserializing calls must go through jsontags.
_YAML_MODULES = frozenset({"yaml", "oyaml"})

# Attributes that deserialize YAML and so must route through jsontags. ``dump``
# / ``safe_dump`` serialise and are intentionally excluded.
_GUARDED_FUNCS = frozenset(
    {
        "load",
        "safe_load",
        "full_load",
        "unsafe_load",
        "load_all",
        "safe_load_all",
        "full_load_all",
        "unsafe_load_all",
    }
)

SUPPRESS_MARKER = "# yaml-load ok"


def _attr_root_name(node):
    # Walk an attribute chain (``ruamel.yaml`` down to its root Name) so a call
    # reached through a submodule attribute is still attributed to the root.
    while isinstance(node, ast.Attribute):
        node = node.value
    return node.id if isinstance(node, ast.Name) else None


class _YamlCallVisitor(ast.NodeVisitor):
    def __init__(self, path, suppressed_lines):
        self.path = path
        self.suppressed_lines = suppressed_lines
        self.violations = []
        # Local name -> yaml module (``import yaml`` / ``import yaml as y`` /
        # ``import oyaml as yaml``). Seeded with the bare module names.
        self._module_aliases = set(_YAML_MODULES)
        # Local name -> the guarded func it was imported as
        # (``from yaml import safe_load`` -> ``safe_load``).
        self._func_aliases = {}

    def _flag(self, node, what):
        if node.lineno not in self.suppressed_lines:
            self.violations.append((node.lineno, what))

    def visit_Import(self, node):
        for alias in node.names:
            # ``import yaml`` / ``import yaml as y`` / ``import ruamel.yaml``.
            root = alias.name.split(".", 1)[0]
            if root in _YAML_MODULES or alias.name in _YAML_MODULES:
                self._module_aliases.add(alias.asname or root)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        module = node.module or ""
        if module.split(".", 1)[0] in _YAML_MODULES or module in _YAML_MODULES:
            for alias in node.names:
                if alias.name == "*":
                    # ``from yaml import *`` pulls the guarded callables in
                    # untracked; refuse it outright.
                    self._flag(node, f"from {module} import *")
                elif alias.name in _GUARDED_FUNCS:
                    # ``from yaml import safe_load``.
                    self._func_aliases[alias.asname or alias.name] = alias.name
        self.generic_visit(node)

    def visit_Call(self, node):
        func = node.func
        # ``yaml.safe_load(...)`` / a guarded attribute on a yaml module chain.
        if isinstance(func, ast.Attribute) and func.attr in _GUARDED_FUNCS:
            root = _attr_root_name(func.value)
            if root is not None and root in self._module_aliases:
                self._flag(node, f"{root}.{func.attr}(...)")
        # ``safe_load(...)``: a guarded func imported bare from a yaml module.
        elif isinstance(func, ast.Name) and func.id in self._func_aliases:
            self._flag(node, f"{func.id}(...)  [from yaml]")
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
        visitor = _YamlCallVisitor(path, _suppressed_lines(source))
        visitor.visit(tree)
        for lineno, what in visitor.violations:
            violations.append((path, lineno, what))

    if violations:
        print(
            "YAML deserialization must route through nltk.jsontags, not bare yaml "
            f"(found {len(violations)}):\n",
            file=sys.stderr,
        )
        for path, lineno, what in violations:
            print(f"  {path}:{lineno}: {what}", file=sys.stderr)
        print(
            "\nRead through jsontags.safe_yaml_load / safe_yaml_loads; they bound "
            "nesting depth, node count and size. See nltk/jsontags.py. A reviewed "
            f"exception may be annotated with a trailing '{SUPPRESS_MARKER}: "
            "<reason>' comment.",
            file=sys.stderr,
        )
        return 1

    print("OK: every YAML deserialization routes through nltk.jsontags.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
