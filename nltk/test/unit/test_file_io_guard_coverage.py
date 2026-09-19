# Natural Language Toolkit: coverage of the file-I/O guard itself
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""The guard that enforces sandboxed file I/O must itself be checked.

``tools/check_no_unsandboxed_open.py`` is what stops a bare ``open``, an
unpinned temp file or a path-taking ``gzip.open`` from reappearing. It used to
scan a hand-written list of a dozen modules, so violations in ``nltk/parse``,
``nltk/sem``, ``nltk/twitter`` and ``nltk/app`` went unnoticed for as long as
they existed. These tests pin that it now covers the whole package and that it
actually fails on each class of violation, because a guard that passes
unconditionally is worse than none: it looks like coverage.
"""

import ast
import pathlib
import subprocess
import sys

import pytest

_REPO = pathlib.Path(__file__).resolve().parents[3]
_GUARD = _REPO / "tools" / "check_no_unsandboxed_open.py"


def _run_guard():
    return subprocess.run(
        [sys.executable, str(_GUARD)], capture_output=True, text=True, cwd=str(_REPO)
    )


def _find_violations_in(directory):
    # Run the guard's own scanner against an isolated directory so the teeth
    # check never plants a file in the live package tree, which would race the
    # tree-walking tests under xdist.
    import importlib.util

    spec = importlib.util.spec_from_file_location("_guard_tool_under_test", _GUARD)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.find_violations([str(directory)])


@pytest.mark.skipif(not _GUARD.exists(), reason="guard script not in this checkout")
def test_guard_passes_on_the_current_tree():
    result = _run_guard()
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.skipif(not _GUARD.exists(), reason="guard script not in this checkout")
def test_guard_covers_the_whole_package_not_a_shortlist():
    """A curated list silently excludes whatever nobody remembered to add."""
    source = _GUARD.read_text()
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "GUARDED_PATHS" for t in node.targets
        ):
            paths = ast.literal_eval(node.value)
            assert paths == ["nltk"], f"guard scans only {paths}"
            return
    pytest.fail("GUARDED_PATHS not found in the guard script")


@pytest.mark.skipif(not _GUARD.exists(), reason="guard script not in this checkout")
@pytest.mark.parametrize(
    "body, label",
    [
        ("def go(p):\n    return open(p).read()\n", "bare builtin open"),
        (
            "import tempfile\n\n\ndef go():\n    return tempfile.mkstemp(prefix='x')\n",
            "temp file with no dir=",
        ),
        (
            "import gzip\n\n\ndef go(p):\n    return gzip.open(p, 'rb')\n",
            "gzip.open on a path",
        ),
        (
            "import zipfile\n\n\ndef go(p):\n    return zipfile.ZipFile(p)\n",
            "zipfile.ZipFile on a path",
        ),
    ],
)
def test_guard_has_teeth_for_each_violation_class(body, label, tmp_path):
    """Plant one violation at a time in an isolated temp dir and require the
    guard to flag it. The probe never touches the live package tree, so a
    parallel tree-walking test cannot read it or race its removal (xdist).
    """
    planted = tmp_path / "_guard_teeth_probe.py"
    planted.write_text(body)
    violations = _find_violations_in(tmp_path)
    assert violations, f"guard did not catch {label}"
    assert any("_guard_teeth_probe" in str(v) for v in violations), violations
    planted.write_text("def go(p):\n    return 1\n")
    assert _find_violations_in(tmp_path) == [], "guard flagged a clean file"


def test_no_source_module_creates_a_temp_file_outside_the_sandbox():
    """Every tempfile factory in nltk source must pin dir=.

    Without it the file lands in the system temp dir, which on Linux is the
    shared world-writable /tmp and is deliberately not a pathsec root.
    """
    factories = {"mkstemp", "NamedTemporaryFile", "TemporaryFile"}
    offenders = []
    for path in sorted((_REPO / "nltk").rglob("*.py")):
        if "test" in path.parts:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "tempfile"
                and node.func.attr in factories
                and not any(kw.arg == "dir" for kw in node.keywords)
            ):
                offenders.append(f"{path.relative_to(_REPO)}:{node.lineno}")
    assert offenders == [], f"temp files not pinned to a data root: {offenders}"
