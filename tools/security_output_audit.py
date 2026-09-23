#!/usr/bin/env python3
# Natural Language Toolkit: output entry-point security scanner
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""Automatic scanner for OUTPUT_ENTRY_POINT_LEDGER.md.

Two independent passes, so the ledger's claims can be re-verified on demand
instead of trusted:

1. **Sink inventory (AST, never regex on source).** Walks the package for
   every output entry point a user-facing exploit could ride through: bare
   ``print`` calls and non-call ``print`` references, ``sys.stdout`` and
   ``sys.stderr`` writes, and ``csv.writer`` / ``csv.DictWriter``
   constructions, alongside their routed counterparts (``safe_print``,
   ``SafeCsvWriter``, ``SafeCsvDictWriter``). Files that shadow the name
   ``print`` are flagged rather than silently miscounted.

2. **Live exploit battery.** When ``nltk.termsec`` and ``nltk.csvsec`` are
   importable (they land with PR #3914), every attack class in the ledger is
   RUN against the real functions: terminal control bytes and escape
   sequences, Trojan Source bidi overrides, lone surrogates, integer render
   bombs, the lying str-subclass materialisation exploit, CSV formula leads
   (fullwidth and whitespace-padded included), the lying int subclass, the
   QUOTE_NONE structural forgery, mid-row atomicity and the DictWriter
   channels. The battery's leak detectors are independently derived and
   self-tested first: if a detector loses its teeth the scan aborts instead
   of reporting a clean result.

3. **Source hygiene.** Every source file in the package is scanned for a
   LITERAL bidi control or invisible format character (the Trojan Source
   class, CVE-2021-42574, inside the repository itself). Security sources
   spell these as escapes; a literal one is reported with its file, line
   and code point and fails the scan. Escapes in text are never flagged.

Exit status: 0 clean, 1 if any exploit LEAK or literal Trojan Source
character (or, in strict-sinks mode, any bare sink), 2 if a detector fails
its own teeth test. The battery is skipped
with a notice when the sanitiser modules are absent, so the scanner is safe
to run on branches that predate them.
"""

import argparse
import ast
import csv
import io
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Pass 1: AST sink inventory
# ---------------------------------------------------------------------------

_ROUTED_CSV = {
    "SafeCsvWriter",
    "SafeCsvDictWriter",
    "safe_csv_writer",
    "safe_csv_dict_writer",
}


def _is_stdio_write(node):
    """True for sys.stdout.write / sys.stderr.write attribute chains."""
    if not (isinstance(node, ast.Attribute) and node.attr == "write"):
        return False
    value = node.value
    return (
        isinstance(value, ast.Attribute)
        and value.attr in ("stdout", "stderr")
        and isinstance(value.value, ast.Name)
        and value.value.id == "sys"
    )


def _shadows_print(tree):
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == "print":
                return True
            if any(a.arg == "print" for a in node.args.args):
                return True
        if isinstance(node, ast.Name) and node.id == "print":
            if isinstance(node.ctx, ast.Store):
                return True
    return False


def scan_sinks(package_dir):
    """Inventory every output sink under *package_dir* (tests excluded)."""
    totals = {
        "print_calls": 0,
        "print_refs": 0,
        "safe_print_calls": 0,
        "stdio_writes": 0,
        "csv_writers": 0,
        "routed_csv_writers": 0,
    }
    per_file = {}
    shadowed = []
    for path in sorted(Path(package_dir).rglob("*.py")):
        rel = path.relative_to(package_dir)
        if rel.parts and rel.parts[0] == "test":
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError as exc:
            per_file[str(rel)] = {"error": f"{type(exc).__name__}: {exc}"}
            continue
        if _shadows_print(tree):
            shadowed.append(str(rel))
        counts = dict.fromkeys(totals, 0)
        call_func_ids = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                call_func_ids.add(id(node.func))
                func = node.func
                if isinstance(func, ast.Name):
                    if func.id == "print":
                        counts["print_calls"] += 1
                    elif func.id == "safe_print":
                        counts["safe_print_calls"] += 1
                    elif func.id in _ROUTED_CSV:
                        counts["routed_csv_writers"] += 1
                elif isinstance(func, ast.Attribute):
                    if _is_stdio_write(func):
                        counts["stdio_writes"] += 1
                    elif (
                        func.attr in ("writer", "DictWriter")
                        and isinstance(func.value, ast.Name)
                        and func.value.id == "csv"
                    ):
                        counts["csv_writers"] += 1
                    elif func.attr in _ROUTED_CSV:
                        counts["routed_csv_writers"] += 1
        for node in ast.walk(tree):
            # a non-call reference (functools.partial(print, ...), a print
            # passed as a callback) is a sink the call scan cannot see
            if (
                isinstance(node, ast.Name)
                and node.id == "print"
                and isinstance(node.ctx, ast.Load)
                and id(node) not in call_func_ids
            ):
                counts["print_refs"] += 1
        if any(counts.values()):
            per_file[str(rel)] = counts
            for key, value in counts.items():
                totals[key] += value
    return totals, per_file, shadowed


# ---------------------------------------------------------------------------
# Pass 2: live exploit battery
# ---------------------------------------------------------------------------

_ESC = "\x1b"
_RLO = "\u202e"


def _live_control(text):
    """Independent detector: any control byte a terminal could act on."""
    for ch in text:
        cp = ord(ch)
        if cp in (0x09, 0x0A):
            continue
        if cp < 0x20 or cp == 0x7F or 0x80 <= cp <= 0x9F:
            return True
    return False


def _forged_row(raw, terminator="\r\n"):
    """Independent detector: a physical line after the first that begins
    (whitespace skipped) with a spreadsheet formula lead."""
    body = raw[: -len(terminator)] if raw.endswith(terminator) else raw
    lines = body.split("\n")
    return any(line.lstrip().startswith(("=", "+", "@")) for line in lines[1:])


def _detector_teeth():
    """The detectors must flag known-bad and pass known-good, else abort."""
    ok = (
        _live_control("x\x1by")
        and _live_control("x\x9by")
        and _live_control("x\x7fy")
        and not _live_control("plain\ttext\n")
        and _forged_row("x\\\n=SUM(A1)\r\n")
        and not _forged_row('"a\n=b"\r\n'.replace("\n", " "))
    )
    return ok


class _Probes:
    """Every ledger attack class, run against the real sanitisers."""

    def __init__(self, termsec, csvsec):
        self.termsec = termsec
        self.csvsec = csvsec

    def run(self):
        results = []
        for name in sorted(dir(self)):
            if name.startswith("probe_"):
                try:
                    status, detail = getattr(self, name)()
                except Exception as exc:
                    status, detail = "LEAK", f"probe crashed: {exc!r:.120}"
                results.append((name[len("probe_") :], status, detail))
        return results

    def probe_control_bytes(self):
        sanitize = self.termsec.sanitize_terminal
        dangerous = (
            [chr(c) for c in range(0x00, 0x20) if chr(c) not in "\t\n"]
            + [chr(0x7F)]
            + [chr(c) for c in range(0x80, 0xA0)]
        )
        for ctrl in dangerous:
            out = sanitize(f"x{ctrl}y")
            if ctrl in out or _live_control(out):
                return "LEAK", f"U+{ord(ctrl):04X} survived: {out!r}"
        return "PASS", f"{len(dangerous)} control bytes escaped"

    def probe_escape_sequences(self):
        sanitize = self.termsec.sanitize_terminal
        corpus = [
            "\x1b[2J\x1b[H",
            "\x1b]0;pwned\x07",
            "\x1b]8;;http://evil\x07link\x1b]8;;\x07",
            "safe\x08\x08evil",
            "line1\rSPOOFED",
            "\x9bpwn",
            "\x9d0;t\x07",
        ]
        for payload in corpus:
            if _live_control(sanitize(payload)):
                return "LEAK", f"live control from {payload!r}"
        return "PASS", f"{len(corpus)} sequences neutralised"

    def probe_bidi_overrides(self):
        sanitize = self.termsec.sanitize_terminal
        for payload in [_RLO + "evil", "\u202d flip", "\u2066iso"]:
            out = sanitize(payload)
            if any(ch in out for ch in (_RLO, "\u202d", "\u2066")):
                return "LEAK", f"bidi control survived from {payload!r}"
        return "PASS", "overrides and unbalanced isolates escaped"

    def probe_lone_surrogate(self):
        out = self.termsec.sanitize_terminal("a" + chr(0xD800) + "b")
        if chr(0xD800) in out:
            return "LEAK", "lone surrogate survived"
        return "PASS", f"escaped to {out!r}"

    def probe_int_bomb(self):
        bomb = 1 << 400_000
        for func in (
            self.termsec.sanitize_terminal,
            self.termsec.safe_print,
            self.csvsec.sanitize_csv_field,
        ):
            try:
                func(bomb)
            except ValueError:
                continue
            return "LEAK", f"{func.__name__} rendered a 400k-bit int"
        return "PASS", "refused at every entry point"

    def probe_lying_str_subclass(self):
        class LyingChar(str):
            def __hash__(self):
                return hash("\t")

            def __eq__(self, other):
                return other == "\t" if type(other) is str else NotImplemented

        class LyingText(str):
            def __str__(self):
                return self

            def __iter__(self):
                yield LyingChar(_ESC)
                yield from iter("[2Jpwn")

        out = self.termsec.sanitize_terminal(LyingText(_ESC + "[2Jpwn"))
        if _ESC in out or type(out) is not str:
            return "LEAK", f"lying subclass rode through: {out!r}"
        return "PASS", "buffer re-materialised, membership lie ignored"

    def probe_fake_clean_iterator(self):
        class FakeClean(str):
            def __str__(self):
                return self

            def __iter__(self):
                yield from iter("innocent")

        out = self.termsec.sanitize_terminal(FakeClean(_ESC + "]0;p\x07"))
        if _ESC in out or "\x07" in out or "innocent" in out:
            return "LEAK", f"iterator performance believed: {out!r}"
        return "PASS", "real buffer scanned"

    def probe_csv_formula_leads(self):
        sanitize = self.csvsec.sanitize_csv_field
        leads = [
            "=SUM(A1)",
            "+cmd",
            "-2+3+cmd",
            "@SUM(A1)",
            "%0A=x",
            "|calc",
            "\uff1dSUM(A1)",
            "\uff0bx",
            "==SUM(A1)",
            "\t=padded",
            "\u00a0=padded",
            "\u3000=padded",
            "\ufeff=bom",
            "=cmd|' /C calc'!A1",
        ]
        lead_chars = (
            "=",
            "+",
            "-",
            "@",
            "%",
            "|",
            "\uff1d",
            "\uff0b",
            "\uff0d",
            "\uff20",
        )
        for payload in leads:
            out = sanitize(payload)
            if out.lstrip().startswith(lead_chars):
                return "LEAK", f"live lead from {payload!r}: {out!r}"
        benign = ["-1,234.56", "+42", "-3.5", "2026-09-23"]
        for value in benign:
            if sanitize(value) != value:
                return "WARN", f"benign number rewritten: {value!r}"
        return "PASS", f"{len(leads)} leads defused, {len(benign)} numbers kept"

    def probe_lying_int_subclass(self):
        class EvilInt(int):
            def __str__(self):
                return "=cmd|' /C calc'!A1"

        buf = io.StringIO()
        self.csvsec.SafeCsvWriter(buf).writerow([EvilInt(7)])
        (row,) = list(csv.reader(io.StringIO(buf.getvalue())))
        if row[0].lstrip().startswith("="):
            return "LEAK", f"EvilInt smuggled a formula: {row[0]!r}"
        return "PASS", f"materialised then defused: {row[0]!r}"

    def probe_quote_none_guard(self):
        make_writer = self.csvsec.SafeCsvWriter
        make_dict = self.csvsec.SafeCsvDictWriter
        for build in (
            lambda: make_writer(io.StringIO(), quoting=csv.QUOTE_NONE, escapechar="\\"),
            lambda: make_dict(
                io.StringIO(), ["a"], quoting=csv.QUOTE_NONE, escapechar="\\"
            ),
        ):
            try:
                build()
            except ValueError:
                continue
            return "LEAK", "QUOTE_NONE accepted without single_line"

        class Unquoted(csv.excel):
            quoting = csv.QUOTE_NONE
            escapechar = "\\"

        try:
            make_writer(io.StringIO(), dialect=Unquoted)
            return "LEAK", "dialect object smuggled QUOTE_NONE"
        except ValueError:
            pass
        buf = io.StringIO()
        writer = make_writer(
            buf, single_line=True, quoting=csv.QUOTE_NONE, escapechar="\\"
        )
        writer.writerow(["x\n=SUM(A1)", "=2+5"])
        raw = buf.getvalue()
        if _forged_row(raw) or "\n" in raw[:-2]:
            return "LEAK", f"single_line QUOTE_NONE forged a row: {raw!r}"
        return "PASS", "refused unless single_line; no physical newline leaks"

    def probe_dialect_characters(self):
        make_writer = self.csvsec.SafeCsvWriter
        hostile = [
            (
                "escapechar",
                dict(single_line=True, quoting=csv.QUOTE_NONE, escapechar="="),
            ),
            ("escapechar", dict(doublequote=False, escapechar="=")),
            ("quotechar", dict(quotechar="=")),
            ("delimiter", dict(delimiter="=")),
            ("lineterminator", dict(lineterminator="\n=")),
        ]
        for name, fmtparams in hostile:
            try:
                make_writer(io.StringIO(), **fmtparams)
            except ValueError:
                continue
            return "LEAK", f"{name} in the lead set accepted: {fmtparams!r}"
        try:
            make_writer(io.StringIO(), quotechar=None, escapechar="\\")
            return "LEAK", "quotechar=None accepted without single_line"
        except (ValueError, TypeError):
            pass
        buf = io.StringIO()
        make_writer(buf, delimiter="|").writerow(["", "=SUM(A1)"])
        (row,) = list(csv.reader(io.StringIO(buf.getvalue()), delimiter="|"))
        if row[1].lstrip().startswith("="):
            return "LEAK", f"pipe-delimited cell not defused: {row!r}"
        return "PASS", "lead-character dialects refused; pipe delimiter still defuses"

    def probe_midrow_atomicity(self):
        def poison():
            yield "a"
            yield "=b"
            raise RuntimeError("mid-row")

        buf = io.StringIO()
        try:
            self.csvsec.SafeCsvWriter(buf).writerow(poison())
        except RuntimeError:
            pass
        if buf.getvalue():
            return "LEAK", f"partial row written: {buf.getvalue()!r}"
        return "PASS", "zero bytes on mid-row failure"

    def probe_dict_writer_channels(self):
        buf = io.StringIO()
        writer = self.csvsec.SafeCsvDictWriter(
            buf, ["name", "=evil"], restval="=missing", extrasaction="ignore"
        )
        writer.writeheader()
        writer.writerow({"name": "=SUM(A1)", "smuggled": "@cmd"})
        rows = list(csv.reader(io.StringIO(buf.getvalue())))
        header, row = rows
        if header[1].lstrip().startswith("="):
            return "LEAK", f"header lead live: {header!r}"
        if row[0].lstrip().startswith("=") or row[1].lstrip().startswith("="):
            return "LEAK", f"cell lead live: {row!r}"
        if len(row) != 2:
            return "LEAK", f"extra key written: {row!r}"
        return "PASS", "fieldnames, restval and extras all contained"

    def probe_idempotence(self):
        sanitize = self.termsec.sanitize_terminal
        for payload in ["x\x1b[31m" + _RLO, "a\x00b", chr(0xD800), "\x9bpwn"]:
            once = sanitize(payload)
            if sanitize(once) != once:
                return "LEAK", f"second pass changed output for {payload!r}"
        return "PASS", "sanitised output is a fixed point"


def run_battery():
    try:
        import nltk  # noqa: F401
    except ImportError:
        # not installed and not on the path: fall back to this checkout
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    try:
        import nltk.csvsec as csvsec
        import nltk.termsec as termsec
    except ImportError as exc:
        return None, f"battery skipped: {exc} (modules land with PR #3914)"
    return _Probes(termsec, csvsec).run(), None


# ---------------------------------------------------------------------------
# Pass 3: source hygiene (literal Trojan Source characters in the repository)
# ---------------------------------------------------------------------------

# Bidi formatting characters, zero-width smuggling characters, the invisible
# math operators, line/paragraph separators and a mid-file BOM: none belongs
# LITERALLY in a source file, where a reviewer cannot see it. The joiners
# ZWNJ/ZWJ are excluded (legitimate emoji and script test data, the same
# allowlist nltk.termsec keeps) as are the lone bidi marks and the visible
# spaces, which reorder or hide nothing.
_SOURCE_SUSPECTS = frozenset(
    set(range(0x202A, 0x202F))
    | set(range(0x2066, 0x206A))
    | set(range(0x2060, 0x2065))
    | {0x200B, 0xFEFF, 0x00AD, 0x2028, 0x2029, 0x180E}
)


def scan_source_hygiene(package_dir):
    """Return [(relative path, line, U+XXXX)] for every literal suspect."""
    hits = []
    for path in sorted(Path(package_dir).rglob("*.py")):
        rel = str(path.relative_to(package_dir))
        text = path.read_text(encoding="utf-8", errors="replace")
        if text.startswith("\ufeff"):
            # a leading BOM is an encoding signature, not a hidden character
            text = text[1:]
        for number, line in enumerate(text.splitlines(), 1):
            for ch in line:
                if ord(ch) in _SOURCE_SUSPECTS:
                    hits.append((rel, number, f"U+{ord(ch):04X}"))
    return hits


def _hygiene_teeth():
    return any(
        ord(ch) in _SOURCE_SUSPECTS for ch in "a" + chr(0x202E) + "b"
    ) and not any(ord(ch) in _SOURCE_SUSPECTS for ch in "plain \\u202e text")


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Scan output entry points and run the ledger exploit battery"
    )
    parser.add_argument(
        "package_dir",
        nargs="?",
        default=str(Path(__file__).resolve().parent.parent / "nltk"),
        help="package directory to inventory (default: the repo's nltk/)",
    )
    parser.add_argument(
        "--strict-sinks",
        action="store_true",
        help="fail when any bare print/stdio/csv sink remains (post PR #3915)",
    )
    args = parser.parse_args(argv)

    if not (_detector_teeth() and _hygiene_teeth()):
        print("FATAL: a detector failed its own teeth test; aborting.")
        return 2

    totals, per_file, shadowed = scan_sinks(args.package_dir)
    bare = totals["print_calls"] + totals["print_refs"] + totals["stdio_writes"]
    bare += totals["csv_writers"]
    print("== Sink inventory ==")
    for key, value in totals.items():
        print(f"  {key:20s} {value}")
    print(f"  files with sinks     {len(per_file)}")
    if shadowed:
        print(f"  SHADOWED print in: {', '.join(shadowed)}")
    print(f"  bare sinks total     {bare}")

    battery, skip_reason = run_battery()
    leaks = 0
    print("== Exploit battery ==")
    if battery is None:
        print(f"  {skip_reason}")
    else:
        for name, status, detail in battery:
            print(f"  [{status:4s}] {name}: {detail}")
            if status == "LEAK":
                leaks += 1
        print(f"  {len(battery)} probes, {leaks} leaks")

    hygiene = scan_source_hygiene(args.package_dir)
    print("== Source hygiene ==")
    if hygiene:
        for rel, number, cp in hygiene[:40]:
            print(f"  LITERAL {cp} at {rel}:{number}")
        print(f"  {len(hygiene)} literal Trojan Source characters")
    else:
        print("  no literal bidi or invisible characters in any source")

    if leaks or hygiene:
        return 1
    if args.strict_sinks and bare:
        print(f"strict-sinks: {bare} bare sinks remain")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
