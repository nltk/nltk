#!/usr/bin/env python3
# Natural Language Toolkit: sandboxed-open CI guard
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""Fail if a bare builtin ``open(`` is used in a sandbox-sensitive module.

Modules that resolve *untrusted* paths (corpus readers reading corpus files,
``nltk.data`` resolving resource names) must open files through the pathsec
sandbox -- ``from nltk.pathsec import open as pathsec_open`` -- so path
traversal / symlink-TOCTOU protections apply (CWE-22/59). The two historical
aliases (``pathsec_open`` / ``_secure_open``) both point at ``nltk.pathsec.open``;
this guard makes the *policy* enforceable regardless of the alias, which is the
security intent behind issue #3740 (superseding a one-off alias rename that could
silently drift again).

An AST check is used rather than a regex so that only the *builtin* ``open(...)``
(``ast.Name`` ``open``) is flagged -- ``pathsec_open(...)``, ``self.open(...)``,
``fp.open()``, ``os.open(...)``, ``gzip.open(...)`` etc. (all ``ast.Attribute``
or differently-named) are correctly ignored.

A deliberate, reviewed exception may be annotated with a trailing
``# sandboxed-open ok: <reason>`` comment on the same line.

Usage: ``python tools/check_no_unsandboxed_open.py`` (exit 1 on any violation).
"""

import ast
import os
import sys

# Sandbox-sensitive modules that must never open a file with the builtin. These
# are currently clean; the guard keeps them that way.
# The WHOLE package. This list used to name a dozen modules, which meant a bare
# open or an unpinned temp file anywhere else went unnoticed; nltk/parse,
# nltk/sem, nltk/twitter and nltk/app all had violations that nothing flagged.
# Guarding everything and annotating the few genuine exceptions is the only way
# the rule holds as the codebase changes.
GUARDED_PATHS = ["nltk"]

# The test tree is exempt for one specific reason: a security test has to stage
# its attack target OUTSIDE the sandbox, and the secured helpers refuse exactly
# that, which is the point of them. Tests that write INSIDE the sandbox were
# converted to pathsec separately; this exemption is not a licence for the rest.
_EXEMPT_PREFIXES = (os.path.join("nltk", "test"),)

SUPPRESS_MARKER = "# sandboxed-open ok"

# Opening a path through a compression or archive helper bypasses the sentinel
# just as a builtin open() does. These are only safe when handed an ALREADY
# secured file object, so a call whose first argument is a path is a violation.
# Creating a temp file without dir= puts it in the system temp directory, which
# on Linux is the shared, world-writable /tmp and is deliberately NOT a pathsec
# root. Callers must pass dir=nltk.data.staging_tempdir() (or another in-root
# directory) so scratch output stays inside the sandbox.
_TEMPFILE_FACTORIES = {"mkstemp", "NamedTemporaryFile", "TemporaryFile"}

_PATH_TAKING = {
    ("gzip", "open"),
    ("bz2", "open"),
    ("lzma", "open"),
    ("codecs", "open"),
    ("io", "open"),
    ("tarfile", "open"),
    ("zipfile", "ZipFile"),
}


def _is_secured_handle(arg, secured_names):
    """True if *arg* is a pathsec-produced file object rather than a path."""
    if isinstance(arg, ast.Call):
        func = arg.func
        if isinstance(func, ast.Name) and "pathsec" in func.id:
            return True
        if isinstance(func, ast.Attribute) and "pathsec" in getattr(
            getattr(func, "value", None), "id", ""
        ):
            return True
    if isinstance(arg, ast.Name) and arg.id in secured_names:
        return True
    return False


def _secured_names(tree):
    """Names bound from a pathsec open in this module, e.g. ``raw = pathsec_open(...)``."""
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and _is_secured_handle(node.value, set()):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        elif isinstance(node, ast.withitem) and _is_secured_handle(
            node.context_expr, set()
        ):
            if isinstance(node.optional_vars, ast.Name):
                names.add(node.optional_vars.id)
    return names


def _is_exempt(path):
    normalised = os.path.normpath(path)
    return any(normalised.startswith(prefix) for prefix in _EXEMPT_PREFIXES)


def _iter_py_files(path):
    if os.path.isfile(path):
        yield path
        return
    for dirpath, _dirs, files in os.walk(path):
        for name in files:
            if name.endswith(".py"):
                yield os.path.join(dirpath, name)


def find_violations(paths):
    violations = []
    for base in paths:
        for py in _iter_py_files(base):
            if _is_exempt(py):
                continue
            with open(
                py, encoding="utf-8"
            ) as fh:  # sandboxed-open ok: the guard itself
                source = fh.read()
            try:
                tree = ast.parse(source, py)
            except SyntaxError:
                continue
            lines = source.splitlines()
            secured_names = _secured_names(tree)
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                bare_builtin = (
                    isinstance(node.func, ast.Name) and node.func.id == "open"
                )
                # A compression/archive helper handed a PATH bypasses the
                # sentinel too. Handed an already-secured file object it is
                # fine, so only a call whose first argument is not itself a
                # pathsec call (or a name bound from one) is reported.
                path_taking = (
                    isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Name)
                    and (node.func.value.id, node.func.attr) in _PATH_TAKING
                    and node.args
                    and not _is_secured_handle(node.args[0], secured_names)
                )
                unpinned_tempfile = (
                    isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "tempfile"
                    and node.func.attr in _TEMPFILE_FACTORIES
                    and not any(kw.arg == "dir" for kw in node.keywords)
                )
                if not (bare_builtin or path_taking or unpinned_tempfile):
                    continue
                # Scan every physical line of the call so a suppression
                # marker still counts if the formatter wrapped the call.
                end = getattr(node, "end_lineno", node.lineno) or node.lineno
                span = lines[node.lineno - 1 : end]
                if any(SUPPRESS_MARKER in ln for ln in span):
                    continue
                line = span[0].strip() if span else ""
                violations.append((py, node.lineno, line.strip()))
    return violations


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(root)
    violations = find_violations(GUARDED_PATHS)
    if not violations:
        print("sandboxed-open guard: OK (no un-sandboxed open() in guarded modules)")
        return 0
    print(
        "sandboxed-open guard: FAILED -- builtin open() in a sandbox-sensitive module."
    )
    print("Use `from nltk.pathsec import open as pathsec_open` (or annotate a reviewed")
    print(f"exception with `{SUPPRESS_MARKER}: <reason>`). Offenders:\n")
    for path, lineno, text in violations:
        print(f"  {path}:{lineno}: {text}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
