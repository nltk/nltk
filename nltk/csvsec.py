# Natural Language Toolkit: CSV/TSV output safety helpers
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Neutralise untrusted values before they are written as CSV/TSV cells.

A cell a later opener evaluates is a code sink: a leading ``= + - @`` makes a
spreadsheet run the cell as a formula (CWE-1236), and a control sequence in the
text drives the terminal when the file is displayed (CWE-150, via
:func:`nltk.termsec.sanitize_terminal`).

:class:`SafeCsvWriter` (or :func:`safe_csv_writer`) is the intended API: a
drop-in for ``csv.writer`` whose rows pass through ONE fixed cell pipeline,
so no caller ever needs a per-type special case:

1. refuse an integer render bomb (:func:`nltk.termsec._refuse_int_bomb`);
2. pass an EXACT ``int``/``float``/``bool``/``None`` through with its type
   preserved (their ``str()`` cannot carry a payload, and the csv module
   renders them natively);
3. materialise EVERY other object with ``str()`` here, never later at the
   writer, so a crafted ``__str__`` cannot smuggle a payload past the guard;
4. escape terminal control sequences, bidi overrides and invisible
   characters; and
5. defuse a spreadsheet formula lead, keeping a genuine number's sign.

:func:`sanitize_csv_field` runs that same pipeline for a single cell and is
re-exported from :mod:`nltk.termsec` for backward compatibility.
"""

import csv as _csv

from nltk.termsec import _refuse_int_bomb, sanitize_terminal

__all__ = ["SafeCsvWriter", "safe_csv_writer", "sanitize_csv_field"]

# A leading one of these makes a spreadsheet evaluate a CSV cell as a formula, so
# crafted cell text can run a formula when the file is opened (CWE-1236). Leading
# whitespace is stripped before the test because a spreadsheet ignores it too.
_CSV_FORMULA_LEADS = ("=", "+", "-", "@")

# No legitimate numeric cell approaches this length; a longer formula-led string
# is defused without being parsed at all, which keeps the check independent of
# the float() parser's behaviour on adversarial digit runs.
_MAX_NUMERIC_CELL_LEN = 10_000


def _looks_numeric(text):
    if len(text) > _MAX_NUMERIC_CELL_LEN:
        return False
    # float() also accepts inf/nan and digit-group underscores (1_0), which a
    # spreadsheet would NOT treat as a plain number, so the leading + / - is not a
    # genuine number sign there; reject them so the formula lead is still defused.
    lowered = text.lower()
    if "inf" in lowered or "nan" in lowered or "_" in text:
        return False
    try:
        float(text)
        return True
    except ValueError:
        return False


def sanitize_csv_field(value):
    """Return *value* neutralised for writing as a CSV/TSV cell.

    Runs the module's fixed cell pipeline (see the module docstring): the
    integer render backstop, the exact-primitive pass-through (type
    preserved), ``str()`` materialisation of every other object HERE rather
    than later at the writer (a raising ``__str__`` fails closed in this
    helper), terminal-control neutralisation, and formula-lead defusal. A
    genuine number keeps its sign; any other value with a leading ``= + - @``
    is prefixed with an apostrophe so the spreadsheet treats it as text, and a
    formula-led string longer than any legitimate number is defused without
    being parsed at all.
    """
    _refuse_int_bomb(value)
    if value is None or type(value) in (int, float, bool):
        return value
    if not isinstance(value, str):
        value = str(value)
    text = sanitize_terminal(value)
    # Strip every leading whitespace (space, tab, and any Unicode space such as a
    # no-break space) a spreadsheet skips before finding the formula lead.
    lead = text.lstrip()
    if lead[:1] in _CSV_FORMULA_LEADS and not _looks_numeric(lead):
        text = "'" + text
    return text


class SafeCsvWriter:
    """Drop-in ``csv.writer`` whose every cell runs the sanitising pipeline.

    Construction mirrors ``csv.writer(fileobj, dialect, **fmtparams)``; the
    underlying writer performs all quoting, so structural characters inside a
    sanitised cell (an embedded newline, a quote, the delimiter) are handled
    by the csv module exactly as for any other value.
    """

    def __init__(self, fileobj, dialect="excel", **fmtparams):
        self._writer = _csv.writer(fileobj, dialect, **fmtparams)

    def writerow(self, row):
        return self._writer.writerow([sanitize_csv_field(v) for v in row])

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)

    @property
    def dialect(self):
        return self._writer.dialect


def safe_csv_writer(fileobj, dialect="excel", **fmtparams):
    """Return a :class:`SafeCsvWriter` over *fileobj*, like ``csv.writer``."""
    return SafeCsvWriter(fileobj, dialect, **fmtparams)
