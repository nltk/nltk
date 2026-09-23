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
    SafeCsvWriter,
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


class TestNumericLeadLengthCap:
    def test_million_digit_lead_defused_promptly(self):
        payload = "-" + "9" * 1_000_000
        start = time.perf_counter()
        out = sanitize_csv_field(payload)
        elapsed = time.perf_counter() - start
        assert out.startswith("'-")  # defused without being parsed
        assert elapsed < 1.0  # measured in milliseconds; generous no-hang bound

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


def test_termsec_reexport_is_the_same_function():
    import nltk.termsec as termsec

    assert termsec.sanitize_csv_field is sanitize_csv_field
