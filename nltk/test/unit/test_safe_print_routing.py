# Natural Language Toolkit: safe_print routing tests
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Every direct ``print`` call in NLTK library code now routes through the
single ``nltk.termsec.safe_print`` chokepoint. These tests pin two things:

1. The sink CONTRACT that both the pass-through stub and the sanitising
   implementation (pull request #3914) satisfy: clean text is emitted
   byte-identically, and print's keyword surface (sep/end/file/flush) works.
   Deliberately NOT asserted: ``safe_print is print``, so the sanitising
   implementation can replace the stub without touching this file.
2. COMPLETENESS: an AST scan proving no direct builtin ``print`` name (call or
   reference) remains in library code, so a future module cannot quietly
   bypass the chokepoint. The scan is positional (ast), so strings, comments
   and doctest examples do not trip it.
"""

import ast
import io
import json
import os
import subprocess
import sys
from pathlib import Path

import nltk
from nltk.termsec import safe_print

_LIB_ROOT = Path(nltk.__file__).parent
# The chokepoint itself and the test tree are the only exemptions.
_EXEMPT = {"termsec.py"}


def _library_files():
    for path in sorted(_LIB_ROOT.rglob("*.py")):
        rel = path.relative_to(_LIB_ROOT)
        if "test" in rel.parts:
            continue
        if rel.name in _EXEMPT and len(rel.parts) == 1:
            continue
        yield path


class TestSafePrintContract:
    def test_clean_text_emitted_byte_identically(self, capsys):
        safe_print("ordinary café text 3.14")
        assert capsys.readouterr().out == "ordinary café text 3.14\n"

    def test_multiple_values_and_sep_end(self, capsys):
        safe_print("a", "b", sep=", ", end="!\n")
        assert capsys.readouterr().out == "a, b!\n"

    def test_no_arguments_prints_newline(self, capsys):
        safe_print()
        assert capsys.readouterr().out == "\n"

    def test_file_keyword_is_honoured(self):
        buf = io.StringIO()
        safe_print("to a buffer", file=buf)
        assert buf.getvalue() == "to a buffer\n"

    def test_non_string_values(self, capsys):
        safe_print(42, 3.14, None)
        assert capsys.readouterr().out == "42 3.14 None\n"


class TestNoDirectPrintRemains:
    def test_no_builtin_print_name_in_library_code(self):
        offenders = []
        for path in _library_files():
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Name) and node.id == "print":
                    offenders.append(f"{path.relative_to(_LIB_ROOT)}:{node.lineno}")
        assert (
            not offenders
        ), "direct print bypasses the safe_print chokepoint: " + ", ".join(offenders)

    def test_scan_has_teeth(self, tmp_path):
        # the detector must flag a real print call, and must ignore strings
        flagged = ast.parse("print('x')")
        assert any(
            isinstance(n, ast.Name) and n.id == "print" for n in ast.walk(flagged)
        )
        quiet = ast.parse("s = 'print(1)'  # print(2)")
        assert not any(
            isinstance(n, ast.Name) and n.id == "print" for n in ast.walk(quiet)
        )

    def test_every_converted_module_imports_the_chokepoint(self):
        # any module that CALLS safe_print must import it from nltk.termsec
        missing = []
        for path in _library_files():
            src = path.read_text(encoding="utf-8")
            tree = ast.parse(src)
            calls = any(
                isinstance(n, ast.Call)
                and isinstance(n.func, ast.Name)
                and n.func.id == "safe_print"
                for n in ast.walk(tree)
            )
            if not calls:
                continue
            imported = any(
                isinstance(n, ast.ImportFrom)
                and n.module == "nltk.termsec"
                and any(a.name == "safe_print" for a in n.names)
                for n in ast.walk(tree)
            )
            if not imported:
                missing.append(str(path.relative_to(_LIB_ROOT)))
        assert not missing, "safe_print used without import: " + ", ".join(missing)


_CHOKEPOINT_NAMES = {
    "safe_print",
    "sanitize_terminal",
    "sanitize_csv_field",
    "SafeCsvWriter",
}
_CHOKEPOINT_MODULES = {"nltk.termsec", "nltk.csvsec"}


def _import_time_loads(tree):
    """Name loads that run while the module body executes: everything except
    function and lambda bodies (their decorators and defaults still run now)."""
    loads = []

    def visit(node):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for child in (
                node.decorator_list + node.args.defaults + node.args.kw_defaults
            ):
                if child is not None:
                    visit(child)
            return
        if isinstance(node, ast.Lambda):
            return
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            loads.append(node)
        for child in ast.iter_child_nodes(node):
            visit(child)

    visit(tree)
    return loads


def _chokepoint_uses_before_import(source):
    tree = ast.parse(source)
    bound_at = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module in _CHOKEPOINT_MODULES:
            for alias in node.names:
                bound_at.setdefault(alias.asname or alias.name, node.lineno)
    return [
        (node.id, node.lineno)
        for node in _import_time_loads(tree)
        if node.id in _CHOKEPOINT_NAMES
        and (node.id not in bound_at or node.lineno < bound_at[node.id])
    ]


class TestChokepointImportOrder:
    """A chokepoint name used while the module body runs (an import-time
    fallback such as ``except ImportError: safe_print(...)``) must already be
    bound. pyflakes and ruff F821 are order-blind, so two such sites shipped
    (nltk.tgrep and nltk/__init__) and raised NameError on their fallback
    path; this scan is order-aware."""

    def test_no_chokepoint_name_used_at_import_time_before_its_import(self):
        offenders = []
        for path in _library_files():
            source = path.read_text(encoding="utf-8")
            for name, lineno in _chokepoint_uses_before_import(source):
                offenders.append(f"{path.relative_to(_LIB_ROOT)}:{lineno} ({name})")
        assert not offenders, offenders

    def test_detector_has_teeth(self):
        late = (
            "try:\n    import dep\nexcept ImportError:\n    safe_print('x')\n"
            "from nltk.termsec import safe_print\n"
        )
        assert _chokepoint_uses_before_import(late) == [("safe_print", 4)]
        early = (
            "from nltk.termsec import safe_print\n"
            "try:\n    import dep\nexcept ImportError:\n    safe_print('x')\n"
        )
        assert _chokepoint_uses_before_import(early) == []
        deferred = (
            "def f():\n    safe_print('x')\nfrom nltk.termsec import safe_print\n"
        )
        assert _chokepoint_uses_before_import(deferred) == []
        class_body = "class C:\n    x = sanitize_terminal('y')\n"
        assert _chokepoint_uses_before_import(class_body) == [("sanitize_terminal", 2)]


_BLOCK_PYPARSING = """
import builtins, sys
real_import = builtins.__import__
def fake(name, *args, **kwargs):
    if name.split(".")[0] == "pyparsing":
        raise ModuleNotFoundError("blocked", name=name)
    return real_import(name, *args, **kwargs)
builtins.__import__ = fake
sys.modules.pop("pyparsing", None)
import nltk.tgrep
print("IMPORT OK")
"""

_GUI_FAILS = """
import builtins, importlib.util, types, warnings
real_import = builtins.__import__
real_find_spec = importlib.util.find_spec
importlib.util.find_spec = (
    lambda name, *a, **k: object() if name == "tkinter" else real_find_spec(name, *a, **k)
)
class Stub(types.ModuleType):
    @property
    def download_gui(self):
        raise RuntimeError("tk init failed: " + chr(27) + "[2J" + chr(0x202E) + "evil")
def fake(name, globals=None, locals=None, fromlist=(), level=0):
    module = real_import(name, globals, locals, fromlist, level)
    if name == "nltk.downloader" and fromlist and "download_gui" in fromlist:
        stub = Stub("nltk.downloader")
        stub.__dict__.update({k: v for k, v in vars(module).items() if k != "download_gui"})
        return stub
    return module
builtins.__import__ = fake
warnings.simplefilter("always")
import nltk
print("IMPORT OK")
"""

# NLTK's install requirements (setup.py install_requires) stay importable;
# every other package outside the standard library is refused, so each
# ``except ImportError`` fallback in the tree really executes.
_BLOCK_OPTIONAL_DEPS = """
import builtins, importlib, json, os, sys, warnings
warnings.simplefilter("ignore")
ALLOWED = set(sys.stdlib_module_names) | {
    "nltk", "click", "joblib", "regex", "tqdm", "defusedxml"
}
real_import = builtins.__import__
def fake(name, globals=None, locals=None, fromlist=(), level=0):
    top = name.split(".")[0]
    if level == 0 and top not in ALLOWED and not top.startswith("_"):
        raise ModuleNotFoundError("blocked: " + name, name=name)
    return real_import(name, globals, locals, fromlist, level)
builtins.__import__ = fake
for key in [k for k in sys.modules if k.split(".")[0] not in ALLOWED]:
    del sys.modules[key]
import nltk
root = os.path.dirname(nltk.__file__)
names = []
for dirpath, _dirs, files in os.walk(root):
    rel = os.path.relpath(dirpath, root)
    if rel.split(os.sep)[0] == "test":
        continue
    for filename in sorted(files):
        if filename.endswith(".py"):
            parts = [] if rel == "." else rel.split(os.sep)
            stem = filename[:-3]
            if stem != "__init__":
                parts.append(stem)
            names.append(".".join(["nltk", *parts]))
ok, blocked, bugs = 0, [], []
for name in sorted(set(names)):
    try:
        importlib.import_module(name)
        ok += 1
    except ImportError as e:
        blocked.append([name, str(e)[:80]])
    except Exception as e:
        bugs.append([name, type(e).__name__, str(e)[:120]])
print(json.dumps({"ok": ok, "blocked": blocked, "bugs": bugs}))
"""


def _run_child(code):
    root = Path(nltk.__file__).resolve().parents[1]
    # CI runs with safe path enabled, so the checkout is made importable by
    # PYTHONPATH; the child's streams are forced to UTF-8 for the payloads
    env = dict(os.environ, PYTHONPATH=str(root), PYTHONIOENCODING="utf-8")
    return subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=root,
        env=env,
    )


class TestImportTimeFallbacksRunForReal:
    """The fallback branches are executed in a child interpreter with the
    dependency really missing: a NameError there is exactly the bug that
    shipped, and no mock can stand in for the import machinery."""

    def test_tgrep_without_pyparsing_prints_its_warning_and_imports(self):
        proc = _run_child(_BLOCK_PYPARSING)
        assert proc.returncode == 0, proc.stderr
        assert "IMPORT OK" in proc.stdout
        assert "nltk.tgrep will not work without the `pyparsing` package" in proc.stdout

    def test_downloader_gui_failure_warning_is_sanitised_and_imports(self):
        proc = _run_child(_GUI_FAILS)
        assert proc.returncode == 0, proc.stderr
        assert "IMPORT OK" in proc.stdout
        assert "Corpus downloader GUI not loaded" in proc.stderr
        assert "\\x1b[2J" in proc.stderr and "\\u202e" in proc.stderr
        assert chr(27) not in proc.stderr and chr(0x202E) not in proc.stderr

    def test_every_module_imports_with_every_optional_dependency_blocked(self):
        proc = _run_child(_BLOCK_OPTIONAL_DEPS)
        assert proc.returncode == 0, proc.stderr[-2000:]
        summary = json.loads(proc.stdout.strip().splitlines()[-1])
        assert summary["bugs"] == [], summary["bugs"]
        # only a module with a hard third-party dependency (twython/requests
        # for twitter, matplotlib for the plotting ones) may fail to import
        hard_dependency = (
            "nltk.twitter",
            "nltk.draw.dispersion",
            "nltk.app.wordfreq_app",
        )
        for name, _reason in summary["blocked"]:
            assert name.startswith(hard_dependency), summary["blocked"]
        assert summary["ok"] >= 250, summary
