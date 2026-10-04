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
``os.popen``, ``os.startfile``, ``asyncio.create_subprocess_*``, ``pty.spawn``)
anywhere else silently loses every one of those layers, as ``java()`` and
``dot2img`` once did. ``shutil.which`` is flagged too: the Windows search it
mirrors starts in the current directory, which is exactly the planted-binary
lookup the finder refuses.

An AST check is used rather than a regex so that a spawn reached through a
bound name is caught as well, and so that an unrelated attribute named ``run``
is not. The spawner may be reached through ``from subprocess import Popen``,
``import subprocess as sp``, ``from subprocess import *``, a rebound name
(``launch = subprocess.Popen``), an attribute chain ending in the module
(``nltk.pathsec.subprocess.Popen``), ``getattr(subprocess, "Popen")``, a module
loaded by name (``importlib.import_module("subprocess")``, ``__import__``), or
source handed to ``exec``/``eval``/``compile``; every one of these is a
violation. A deliberate, reviewed exception may be annotated with a trailing
``# spawn ok: <reason>`` comment on the same line.

The private ``_follow_link_parents`` keyword of ``spawn_trusted`` (the
kernel-style walk of a ``..`` inside a symlink's text, which ``dot2img``
exposes to the user as ``follow_link_parents``) is reserved for the Graphviz
caller: any reference to that name in another module is a violation, so no
other tool wrapper can opt out of the default refusal.

Usage: ``python tools/check_all_spawns_through_pathsec.py`` (exit 1 on any
violation).
"""

import ast
import os
import re
import sys

GUARDED_PATHS = ["nltk"]

# The test tree stages attack binaries and drives the real spawn under test.
_EXEMPT_PREFIXES = (os.path.join("nltk", "test"),)

# The chokepoint itself.
_ALLOWED_FILES = {os.path.join("nltk", "pathsec.py")}

SUPPRESS_MARKER = "# spawn ok"

# The private spawn keyword and the only non-test module that may name it.
_PRIVATE_SPAWN_KEYWORD = "_follow_link_parents"
_PRIVATE_KEYWORD_CALLERS = {os.path.join("nltk", "parse", "dependencygraph.py")}

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
    "asyncio": {"create_subprocess_exec", "create_subprocess_shell"},
    "pty": {"spawn"},
}

# Callables that load a module from its name at run time.
_DYNAMIC_IMPORTERS = {"importlib.import_module", "__import__"}

# Builtins that compile source at run time, invisible to this AST walk.
_CODE_RUNNERS = {"exec", "eval", "compile"}

_SPAWNING_MODULE_RE = re.compile(r"\b(" + "|".join(sorted(_SPAWNING)) + r")\b")
_SPAWNER_OR_IMPORT_RE = re.compile(
    r"\b(import|"
    + "|".join(sorted({name for names in _SPAWNING.values() for name in names}))
    + r")\b"
)


class _Bindings:
    """What the module's names stand for, as far as a static walk can tell:
    ``spawners`` (local name to dotted spawner), ``modules`` (local name to
    spawning module), ``importers`` (local name to dynamic importer) and
    ``stars`` (spawning modules star-imported)."""

    def __init__(self):
        self.spawners = {}
        self.modules = {}
        self.importers = {}
        self.stars = set()


def _constant_str(node):
    return (
        node.value
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
        else None
    )


def _dynamic_import(call, bindings):
    """The spawning module a ``import_module("x")`` / ``__import__("x")`` call
    loads, or None."""
    func = call.func
    importer = None
    if isinstance(func, ast.Name):
        importer = bindings.importers.get(func.id)
        if func.id == "__import__":
            importer = "__import__"
    elif isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
        if func.attr == "import_module" and func.value.id == "importlib":
            importer = "importlib.import_module"
    if importer is None or not call.args:
        return None
    name = _constant_str(call.args[0])
    if name is None:
        return None
    module = name.split(".")[0]
    return module if module in _SPAWNING else None


def _module_of(node, bindings):
    """The spawning module an expression denotes, or None: a (possibly aliased)
    name, any attribute chain ending in the module, or a dynamic import."""
    if isinstance(node, ast.Name):
        module = bindings.modules.get(node.id, node.id)
        return module if module in _SPAWNING else None
    if isinstance(node, ast.Attribute):
        return node.attr if node.attr in _SPAWNING else None
    if isinstance(node, ast.Call):
        return _dynamic_import(node, bindings)
    return None


def _getattr_spawner(call, bindings):
    """``getattr(<spawning module>, "<spawner>")`` names a spawner."""
    func = call.func
    if not (
        isinstance(func, ast.Name) and func.id == "getattr" and len(call.args) >= 2
    ):
        return None
    module = _module_of(call.args[0], bindings)
    attr = _constant_str(call.args[1])
    if module and attr in _SPAWNING[module]:
        return f"{module}.{attr} (via getattr)"
    return None


def _spawner_of(node, bindings):
    """The dotted spawner an expression denotes, or None."""
    if isinstance(node, ast.Name):
        if node.id in bindings.spawners:
            return bindings.spawners[node.id]
        for module in bindings.stars:
            if node.id in _SPAWNING[module]:
                return f"{module}.{node.id} (via star import)"
        return None
    if isinstance(node, ast.Attribute):
        module = _module_of(node.value, bindings)
        if module and node.attr in _SPAWNING[module]:
            return f"{module}.{node.attr}"
        return None
    if isinstance(node, ast.Call):
        return _getattr_spawner(node, bindings)
    return None


def _bindings(tree):
    bindings = _Bindings()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module in _SPAWNING:
                for alias in node.names:
                    if alias.name == "*":
                        bindings.stars.add(node.module)
                    elif alias.name in _SPAWNING[node.module]:
                        bound = alias.asname or alias.name
                        bindings.spawners[bound] = f"{node.module}.{alias.name}"
            elif node.module == "importlib":
                for alias in node.names:
                    if alias.name == "import_module":
                        bound = alias.asname or alias.name
                        bindings.importers[bound] = "importlib.import_module"
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in _SPAWNING:
                    bindings.modules[alias.asname or alias.name] = alias.name
    # a rebound name (launch = subprocess.Popen; sp = subprocess; m =
    # import_module("os")) is followed too, to a fixpoint so chains resolve
    assignments = [
        (node.targets[0] if isinstance(node, ast.Assign) else node.target, node.value)
        for node in ast.walk(tree)
        if isinstance(node, (ast.Assign, ast.AnnAssign))
        and node.value is not None
        and (not isinstance(node, ast.Assign) or len(node.targets) == 1)
    ]
    changed = True
    while changed:
        changed = False
        for target, value in assignments:
            if not isinstance(target, ast.Name):
                continue
            spawner = _spawner_of(value, bindings)
            if spawner and bindings.spawners.get(target.id) != spawner:
                bindings.spawners[target.id] = spawner
                changed = True
            module = _module_of(value, bindings)
            if module and bindings.modules.get(target.id) != module:
                bindings.modules[target.id] = module
                changed = True
    return bindings


def _smuggled(call, bindings):
    """A reference that reaches a spawner without a direct call: a dynamic
    import of a spawning module, or source run through exec/eval/compile that
    names one."""
    module = _dynamic_import(call, bindings)
    if module:
        return f"dynamic import of {module}"
    func = call.func
    if isinstance(func, ast.Name) and func.id in _CODE_RUNNERS:
        for arg in call.args:
            source = _constant_str(arg)
            if (
                source
                and _SPAWNING_MODULE_RE.search(source)
                and _SPAWNER_OR_IMPORT_RE.search(source)
            ):
                return f"{func.id} of source naming a spawning module"
    return None


def _names_private_keyword(node):
    """The node spells the private spawn keyword: as a keyword argument, a
    string (``**{"_follow_link_parents": True}``, ``getattr``/``setattr``), or
    a bare name or attribute."""
    if isinstance(node, ast.keyword):
        return node.arg == _PRIVATE_SPAWN_KEYWORD
    if isinstance(node, ast.Constant):
        return node.value == _PRIVATE_SPAWN_KEYWORD
    if isinstance(node, ast.Name):
        return node.id == _PRIVATE_SPAWN_KEYWORD
    if isinstance(node, ast.Attribute):
        return node.attr == _PRIVATE_SPAWN_KEYWORD
    return False


def _is_private_keyword_caller(path):
    path = os.path.normpath(path)
    return any(
        path == caller or path.endswith(os.sep + caller)
        for caller in _PRIVATE_KEYWORD_CALLERS
    )


def _private_keyword_violations(path, tree):
    if _is_private_keyword_caller(path):
        return []
    found = []
    for node in ast.walk(tree):
        if _names_private_keyword(node):
            lineno = getattr(node, "lineno", None)
            found.append(
                f"{path}:{lineno}: {_PRIVATE_SPAWN_KEYWORD} is reserved for the "
                "Graphviz caller (nltk.parse.dependencygraph.dot2img); every other "
                "tool wrapper keeps the default refusal of a '..' in a symlink"
            )
    return found


def _violations(path):
    with open(path, encoding="utf-8") as fh:
        source = fh.read()
    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError as exc:
        return [f"{path}:{exc.lineno}: cannot parse ({exc.msg})"]
    lines = source.splitlines()
    bindings = _bindings(tree)
    found = _private_keyword_violations(path, tree)
    seen = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        spawner = _spawner_of(node.func, bindings) or _getattr_spawner(node, bindings)
        spawner = spawner or _smuggled(node, bindings)
        if spawner is None or (node.lineno, spawner) in seen:
            continue
        seen.add((node.lineno, spawner))
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
