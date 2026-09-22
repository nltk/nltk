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
