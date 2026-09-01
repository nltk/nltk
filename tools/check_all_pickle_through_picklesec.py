#!/usr/bin/env python3
# Natural Language Toolkit: picklesec CI guard
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""Fail if any pickle in the shipped library is read or written with bare ``pickle``.

Unpickling runs arbitrary code: a crafted pickle can reconstruct any global and
invoke it (REDUCE), poison object STATE (BUILD / ``__setstate__``), or reach a
nested-unpickle sink, so ``pickle.load``/``loads`` on an attacker-controlled byte
stream is remote code execution (CWE-502). ``nltk.picklesec`` is the single choke
point that makes deserialisation safe: :class:`nltk.picklesec.RestrictedUnpickler`
forbids every global, :class:`nltk.picklesec.AllowlistUnpickler` permits only an
explicit ``(module, name)`` allowlist bounded by hard guards (no dotted / dunder
names, denied modules, numpy scalar wrapper), and :func:`allowlisted_pickle_load`
is the loader every model uses. Writing routes through :func:`pickle_dump` /
:func:`pickle_dumps` so ALL serialisation has one audited home too.

This guard enforces the policy structurally: any call to ``pickle.load``,
``pickle.loads``, ``pickle.dump``, ``pickle.dumps``, ``pickle.Unpickler`` or
``pickle.Pickler`` (on the bare ``pickle`` / ``cPickle`` / ``_pickle`` module,
under any import alias) anywhere under ``nltk/`` is a violation. Load through a
picklesec unpickler; write through ``picklesec.pickle_dump`` / ``pickle_dumps``.

There is deliberately NO suppression marker: the whole point is that no pickle
bypasses the guard, so an exception cannot be annotated away. The things that are
not violations are structural, not exceptions:

* ``nltk/picklesec.py`` itself: it is the wrapper every call routes *through*, so
  it necessarily uses the ``pickle`` module directly (just as ``nltk/redos.py``
  is the wrapper ``check_all_regex_through_redos`` is built around).
* Non-executing members of the module: ``pickle.UnpicklingError``,
  ``pickle.PickleError``, ``pickle.HIGHEST_PROTOCOL``, ``pickle.DEFAULT_PROTOCOL``
  and friends reconstruct nothing and run no code, so they are allowed.
* Picklesec's own unpickler subclasses/instances (``RestrictedUnpickler(...)``,
  ``AllowlistUnpickler(...).load()``) are calls on those names, not on the
  ``pickle`` module, so they are (correctly) ignored.

An AST check is used rather than a text search so that ``obj.load(...)`` (a method
on a picklesec unpickler instance), ``self.dump(...)``, ``json.dumps(...)`` etc.
are correctly ignored: only a call whose receiver resolves to the bare
``pickle``/``cPickle``/``_pickle`` module (or a name imported directly from it)
matches. Import aliases (``import pickle as p``, ``from pickle import loads``)
are tracked per file so neither can smuggle a bare call past the guard.

Usage: ``python tools/check_all_pickle_through_picklesec.py`` (exit 1 on any
violation).
"""

import ast
import os
import sys

# The whole shipped package is guarded. Everything here is currently routed
# through picklesec; the guard keeps it that way as the codebase changes.
GUARDED_PATHS = ["nltk"]

# The test tree is exempt: tests legitimately exercise raw ``pickle`` behaviour
# (e.g. to craft the malicious payloads picklesec must refuse, or to assert on
# stdlib semantics), and a test is not part of the library's attack surface.
_EXEMPT_PREFIXES = (os.path.join("nltk", "test"),)

# ``nltk/picklesec.py`` is the wrapper itself: it must use ``pickle`` directly.
_EXEMPT_FILES = (os.path.join("nltk", "picklesec.py"),)

# The stdlib pickle modules whose executing calls must go through picklesec.
_PICKLE_MODULES = frozenset({"pickle", "cPickle", "_pickle"})

# Attributes that reconstruct an object graph or build a (de)serialiser, i.e. run
# untrusted code / must be audited. Exceptions and protocol constants
# (``UnpicklingError``, ``PickleError``, ``HIGHEST_PROTOCOL`` ...) are excluded.
_GUARDED_FUNCS = frozenset({"load", "loads", "dump", "dumps", "Unpickler", "Pickler"})


class _PickleCallVisitor(ast.NodeVisitor):
    def __init__(self, path):
        self.path = path
        self.violations = []
        # Local name -> pickle module (``import pickle`` / ``import pickle as p``
        # / ``import _pickle as pickle``). Seeded so a file that shadows without
        # importing (unlikely) still trips on the bare module names.
        self._module_aliases = set(_PICKLE_MODULES)
        # Local name -> the guarded func it was imported as
        # (``from pickle import loads`` -> ``loads``).
        self._func_aliases = {}

    def visit_Import(self, node):
        for alias in node.names:
            if alias.name in _PICKLE_MODULES:
                self._module_aliases.add(alias.asname or alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module in _PICKLE_MODULES:
            for alias in node.names:
                if alias.name == "*":
                    # ``from pickle import *`` pulls the guarded callables into
                    # the namespace untracked; refuse it outright.
                    self.violations.append(
                        (node.lineno, f"from {node.module} import *")
                    )
                elif alias.name in _GUARDED_FUNCS:
                    self._func_aliases[alias.asname or alias.name] = alias.name
        self.generic_visit(node)

    def visit_Call(self, node):
        func = node.func
        # ``pickle.load(...)`` / ``p.dump(...)``: attribute on a pickle module.
        if isinstance(func, ast.Attribute) and func.attr in _GUARDED_FUNCS:
            recv = func.value
            if isinstance(recv, ast.Name) and recv.id in self._module_aliases:
                self.violations.append((node.lineno, f"{recv.id}.{func.attr}(...)"))
        # ``loads(...)``: a guarded func imported bare from a pickle module.
        elif isinstance(func, ast.Name) and func.id in self._func_aliases:
            self.violations.append((node.lineno, f"{func.id}(...)  [from pickle]"))
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
        visitor = _PickleCallVisitor(path)
        visitor.visit(tree)
        for lineno, what in visitor.violations:
            violations.append((path, lineno, what))

    if violations:
        print(
            "Pickle calls must route through nltk.picklesec, not bare pickle "
            f"(found {len(violations)}):\n",
            file=sys.stderr,
        )
        for path, lineno, what in violations:
            print(f"  {path}:{lineno}: {what}", file=sys.stderr)
        print(
            "\nLoad through a picklesec unpickler "
            "(RestrictedUnpickler / AllowlistUnpickler / allowlisted_pickle_load); "
            "write through picklesec.pickle_dump / pickle_dumps. "
            "See nltk/picklesec.py.",
            file=sys.stderr,
        )
        return 1

    print("OK: every pickle call routes through nltk.picklesec.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
