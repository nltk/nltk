#!/usr/bin/env python3
# Natural Language Toolkit: process-spawn chokepoint CI guard
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""Fail if the library starts a process anywhere but ``nltk.pathsec``.

Every external tool NLTK runs (Prover9/Mace4, megam, tadm, hunpos, SENNA,
C&C/Boxer, REPP, Graphviz dot, svn and every JVM launch) goes through
``nltk.pathsec.spawn_trusted``: the binary is resolved absolute-only by the
finder, its whole directory chain is checked for ownership before exec, no
shell re-interprets the argv, and the child gets a scrubbed environment
(CWE-426 / CWE-427 / CWE-78 / CWE-732). A bare ``subprocess.Popen`` (or
``run``, ``call``, ``check_output``, ``os.system``, ``os.exec*``, ``os.spawn*``,
``os.popen``, ``os.startfile``) anywhere else silently loses every one of those
layers, as ``java()`` and ``dot2img`` once did. ``shutil.which`` is flagged too:
the Windows search it mirrors starts in the current directory, which is exactly
the planted-binary lookup the finder refuses.

An AST check is used rather than a regex so that a spawn reached through an
imported name (``from subprocess import Popen``) is caught as well, and so that
an unrelated attribute named ``run`` is not. A deliberate, reviewed exception may
be annotated with a trailing ``# spawn ok: <reason>`` comment on the same line.

Usage: ``python tools/check_all_spawns_through_pathsec.py`` (exit 1 on any
violation).
"""

import ast
import os
import sys

GUARDED_PATHS = ["nltk"]

# The test tree stages attack binaries and drives the real spawn under test.
_EXEMPT_PREFIXES = (os.path.join("nltk", "test"),)

# The chokepoint itself.
_ALLOWED_FILES = {os.path.join("nltk", "pathsec.py")}

SUPPRESS_MARKER = "# spawn ok"

_SPAWNING = {
    "subprocess": {
        "Popen",
        "run",
        "call",
        "check_call",
        "check_output",
        "getoutput",
        "getstatusoutput",
    },
    "os": {
        "system",
        "popen",
        "startfile",
        "execl",
        "execle",
        "execlp",
        "execlpe",
        "execv",
        "execve",
        "execvp",
        "execvpe",
        "spawnl",
        "spawnle",
        "spawnlp",
        "spawnlpe",
        "spawnv",
        "spawnve",
        "spawnvp",
        "spawnvpe",
        "posix_spawn",
        "posix_spawnp",
    },
    "shutil": {"which"},
}


def _imported_spawners(tree):
    """Local names bound by ``from <module> import <spawner> [as name]``, and
    module aliases bound by ``import <module> [as name]``."""
    names, modules = {}, {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module in _SPAWNING:
            for alias in node.names:
                if alias.name in _SPAWNING[node.module]:
                    names[alias.asname or alias.name] = f"{node.module}.{alias.name}"
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in _SPAWNING:
                    modules[alias.asname or alias.name] = alias.name
    return names, modules


def _spawn_name(node, imported):
    """The dotted spawner a call node reaches, or None."""
    names, modules = imported
    func = node.func
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
        module = modules.get(func.value.id, func.value.id)
        if func.attr in _SPAWNING.get(module, ()):
            return f"{module}.{func.attr}"
    if isinstance(func, ast.Name) and func.id in names:
        return names[func.id]
    return None


def _violations(path):
    with open(path, encoding="utf-8") as fh:
        source = fh.read()
    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError as exc:
        return [f"{path}:{exc.lineno}: cannot parse ({exc.msg})"]
    lines = source.splitlines()
    imported = _imported_spawners(tree)
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        spawner = _spawn_name(node, imported)
        if spawner is None:
            continue
        line = lines[node.lineno - 1] if node.lineno - 1 < len(lines) else ""
        if SUPPRESS_MARKER in line:
            continue
        found.append(
            f"{path}:{node.lineno}: {spawner} outside nltk.pathsec; route the "
            "launch through pathsec.spawn_trusted (resolve the binary with "
            "internals.find_binary_absolute first)"
        )
    return found


def _guarded_files():
    for root_dir in GUARDED_PATHS:
        for dirpath, _dirnames, filenames in os.walk(root_dir):
            if dirpath.startswith(_EXEMPT_PREFIXES):
                continue
            for name in sorted(filenames):
                if name.endswith(".py"):
                    path = os.path.join(dirpath, name)
                    if path not in _ALLOWED_FILES:
                        yield path


def main():
    problems = []
    for path in sorted(_guarded_files()):
        problems.extend(_violations(path))
    if problems:
        print("Process spawns outside the nltk.pathsec chokepoint:")
        for problem in problems:
            print("  " + problem)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
