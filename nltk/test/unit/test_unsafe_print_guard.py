# Natural Language Toolkit: no-unsafe-print guard teeth tests
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""The ``no-unsafe-print`` pre-commit guard (``tools/check_unsafe_print.py``)
is what keeps the safe_print routing structural. Every way an unsanitised
value can reach a terminal sink is planted here and must be FLAGGED, every
provably-harmless form must still be ACCEPTED, and the review marker must
only clear a site from a real comment that carries a reason. Each bypass
below was found by probing the guard for real before it was closed."""

import importlib.util
from pathlib import Path

import pytest

_TOOL = Path(__file__).resolve().parents[3] / "tools" / "check_unsafe_print.py"


@pytest.fixture(scope="module")
def guard():
    if not _TOOL.exists():
        pytest.skip("guard not present in this checkout")
    spec = importlib.util.spec_from_file_location("check_unsafe_print", _TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _kinds(guard, source):
    return [kind for _lineno, kind in guard.check_source(source)]


# Every form that can put a raw value on a terminal: each must be flagged.
FLAGGED = {
    "bare-print": "print(untrusted)",
    "print-fstring": 'print(f"{untrusted}")',
    "print-percent-s": 'print("%s" % untrusted)',
    "print-percent-c": 'print("%c" % n)',
    "print-fstring-c-spec": 'print(f"{n:c}")',
    "print-fstring-width-spec": 'print(f"{untrusted:>10}")',
    "print-format-method": 'print("{}".format(untrusted))',
    "print-join": 'print(" ".join(untrusted))',
    "print-str-call": "print(str(untrusted))",
    "print-conditional": "print(a if c else b)",
    "print-concat": 'print("a" + untrusted)',
    "print-starred": "print(*untrusted)",
    "print-starred-even-if-repr": "print(*[repr(x) for x in xs])",
    "print-sep-keyword": 'print("x", sep=untrusted)',
    "print-end-keyword": 'print("x", end=untrusted)',
    "print-file-stderr": "print(untrusted, file=sys.stderr)",
    "print-percent-dict": 'print("%(n)s" % {"n": untrusted})',
    "print-percent-dict-r": 'print("%(n)r" % {"n": untrusted})',
    "print-in-lambda": "f = lambda v: print(v)",
    "print-in-nested-def": "def g():\n    def h(v):\n        print(v)\n",
    "builtins-print": "import builtins\nbuiltins.print(untrusted)",
    "print-alias": "p = print\np(untrusted)",
    "print-partial": "import functools\np = functools.partial(print)\np(untrusted)",
    "print-map": "list(map(print, xs))",
    "builtins-print-alias": "import builtins\np = builtins.print",
    "getattr-builtins-print": 'getattr(builtins, "print")(untrusted)',
    "stdout-write": "sys.stdout.write(untrusted)",
    "stderr-write": "sys.stderr.write(untrusted)",
    "dunder-stdout-write": "sys.__stdout__.write(untrusted)",
    "bare-stdout-write": "from sys import stdout\nstdout.write(untrusted)",
    "os-write-fd1": "os.write(1, untrusted)",
    "os-write-fd2": "os.write(2, untrusted)",
    "click-echo": "click.echo(untrusted)",
    "click-secho": 'click.secho(untrusted, fg="red")',
    "warnings-warn": 'warnings.warn("bad %s" % untrusted)',
    "warnings-warn-explicit": 'warnings.warn_explicit(untrusted, UserWarning, "f", 1)',
    "bare-warn": "from warnings import warn\nwarn(untrusted)",
    "sys-exit": 'sys.exit("cannot read %s" % name)',
    "raise-systemexit": "raise SystemExit(name)",
    "quit-message": "quit(untrusted)",
    "input-prompt": "input(untrusted)",
    "logging-module-warning": 'logging.warning("%s", untrusted)',
    "logging-module-info-fstring": 'logging.info(f"Iter {i}: {c}")',
    "logger-debug-percent-s": 'logger.debug("%s", untrusted)',
    "logger-debug-bare-value": "logger.debug(untrusted)",
    "logger-dot-log": 'logger.log(10, "%s", untrusted)',
    "getlogger-bound-name": (
        'lg = logging.getLogger(__name__)\nlg.warning("%s", untrusted)'
    ),
    "log-conventional-name": 'log.error("%s", untrusted)',
    "log-starred-args": 'logger.debug("%r", *untrusted)',
    "log-mismatched-pairing": 'logger.debug("%s %d", *pair)',
    "marker-without-reason": "print(untrusted)  # unsafe-print ok",
    "marker-empty-reason": "print(untrusted)  # unsafe-print ok:   ",
    "marker-inside-string-literal": 'print(untrusted, "unsafe-print ok: fake")',
    "marker-on-middle-line": (
        "print(\n    untrusted,  # unsafe-print ok: not first or last line\n    x,\n)"
    ),
    "marker-does-not-clear-alias": "p = print  # unsafe-print ok: aliasing hides the sink",
}

# Every provably-harmless form: each must still be accepted.
ACCEPTED = {
    "safe-print": "safe_print(untrusted)",
    "safe-print-starred": "safe_print(*untrusted)",
    "safe-print-sep": "safe_print(untrusted, sep=untrusted)",
    "print-empty": "print()",
    "print-literal": 'print("hello")',
    "print-bytes-literal": "print(b'\\x1b[2J')",
    "print-repr": "print(repr(untrusted))",
    "print-ascii": "print(ascii(untrusted))",
    "print-percent-r": 'print("%r" % untrusted)',
    "print-percent-a": 'print("%a" % untrusted)',
    "print-percent-numeric": 'print("%d %.3f %x %e" % (a, b, c, d))',
    "print-percent-positional-pairing": 'print("%s=%d" % (repr(name), count))',
    "print-fstring-repr": 'print(f"{untrusted!r}")',
    "print-fstring-ascii": 'print(f"{untrusted!a}")',
    "print-fstring-numeric-spec": 'print(f"{n:d} {x:.2f} {n:x}")',
    "print-fstring-sanitised-inner": 'print(f"{sanitize_terminal(x)}")',
    "print-format-method-safe": 'print("{}".format(repr(untrusted)))',
    "print-sanitize-terminal": "print(sanitize_terminal(untrusted))",
    "print-sanitize-csv-field": "print(sanitize_csv_field(untrusted))",
    "print-str-of-safe": "print(str(repr(untrusted)))",
    "print-concat-safe": 'print("a" + repr(untrusted))',
    "print-sep-literal": 'print("a", "b", sep=", ")',
    "print-sep-sanitised": 'print("a", sep=sanitize_terminal(s))',
    "stderr-write-literal": 'sys.stderr.write("literal\\n")',
    "stderr-write-numeric": 'sys.stderr.write("%d\\n" % n)',
    "bare-stdout-write-sanitised": (
        "from sys import stdout\nstdout.write(sanitize_terminal(untrusted))"
    ),
    "os-write-other-fd": "os.write(3, untrusted)",
    "warnings-warn-sanitised": 'warnings.warn("bad %s" % sanitize_terminal(untrusted))',
    "bare-warn-repr": 'from warnings import warn\nwarn(f"Tag {tag!r} unknown")',
    "sys-exit-int": "sys.exit(1)",
    "sys-exit-sanitised": 'sys.exit("cannot read %s" % sanitize_terminal(name))',
    "input-literal": 'input("Downloader> ")',
    "input-numeric-fstring": 'input(f"Enter 1-{n:d}: ")',
    "logger-literal-only": 'logger.debug("starting")',
    "logger-percent-r-and-d": 'logger.debug("%r %d", untrusted, n)',
    "logger-wrapped": 'logger.debug("%s", sanitize_terminal(untrusted))',
    "logger-positional-pairing": 'logger.debug("%s: %f", sanitize_terminal(a), ret)',
    "logger-dot-log-safe": 'logger.log(10, "%r", untrusted)',
    "logging-info-numeric": 'logging.info("Iter %r: %r/%r=%r", i, c, n, pc)',
    "unrelated-write": "outfile.write(untrusted)",
    "unrelated-warn-method": "obj.warn(untrusted)",
    "unrelated-echo": "shell.echo(untrusted)",
    "math-log-not-a-logger": "from math import log\ny = log(x)",
    "pprint-repr-based": "pprint(untrusted)",
    "marker-with-reason-first-line": (
        "print(untrusted)  # unsafe-print ok: fixed literal table"
    ),
    "marker-with-reason-last-line": (
        "print(\n    untrusted\n)  # unsafe-print ok: reviewed benign"
    ),
    "marker-on-input": "input(prompt)  # unsafe-print ok: prompt is literal text",
    "marker-on-warn": "warn(msg)  # unsafe-print ok: message is repr-built",
}


@pytest.mark.parametrize("name", sorted(FLAGGED))
def test_bypass_is_flagged(guard, name):
    assert _kinds(guard, FLAGGED[name]), f"guard let through: {name}"


@pytest.mark.parametrize("name", sorted(ACCEPTED))
def test_safe_form_is_accepted(guard, name):
    assert not _kinds(guard, ACCEPTED[name]), f"guard false positive: {name}"


def test_kind_labels_name_the_sink(guard):
    assert _kinds(guard, "print(untrusted)") == ["print"]
    assert _kinds(guard, "p = print") == ["print-alias"]
    assert _kinds(guard, "sys.stdout.write(untrusted)") == ["write"]
    assert _kinds(guard, "warnings.warn(untrusted)") == ["warn"]
    assert _kinds(guard, "sys.exit(untrusted)") == ["exit"]
    assert _kinds(guard, "input(untrusted)") == ["input"]
    assert _kinds(guard, 'logger.info("%s", untrusted)') == ["log"]


def test_every_violation_reports_its_line(guard):
    source = "x = 1\nprint(a)\ny = 2\nsys.stderr.write(b)\n"
    assert guard.check_source(source) == [(2, "print"), (4, "write")]


def test_syntax_error_source_is_not_a_crash(guard):
    assert guard.check_source("print(") == []


def test_c_conversion_is_never_numeric_safe(guard):
    # chr(27) is ESC: a %c / :c field can emit a live control byte
    assert "c" not in guard._SAFE_PERCENT
    assert "c" not in guard._NUMERIC_SPEC_END
    assert "s" not in guard._SAFE_PERCENT
    assert "s" not in guard._NUMERIC_SPEC_END


def test_marker_regex_needs_comment_colon_and_reason(guard):
    assert guard._MARKER.search("# unsafe-print ok: why")
    assert not guard._MARKER.search("# unsafe-print ok")
    assert not guard._MARKER.search("# unsafe-print ok:    ")
    assert not guard._MARKER.search("unsafe-print ok: outside a comment")
