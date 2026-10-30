# -*- coding: utf-8 -*-
# Natural Language Toolkit: CSV cell sanitisation
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT
"""
CSV cell sanitisation for the 3.4 maintenance line, named as in the 3.10
line's ``nltk.csvsec``. A cell whose first non-blank character is one of
``= + - @ | %`` (or a tab or carriage return) is evaluated as a formula by
spreadsheets (CWE-1236); :func:`sanitize_csv_field` applies the industry
neutralisation, an apostrophe prefix, and leaves numbers and plain numeric
strings alone. The 3.10 module also wraps ``csv.writer`` and validates the
dialect; this line sanitises at the ``writerow`` calls.
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import re

from six import binary_type, text_type

__all__ = ["sanitize_csv_field"]

_FORMULA_LEADS = ("=", "+", "-", "@", "|", "%", "\t", "\r")
_PLAIN_NUMBER_RE = re.compile(r"^[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?$")


def sanitize_csv_field(value):
    """Neutralise a spreadsheet formula lead at the start of a CSV cell.

    Numbers, booleans and None pass through; a plain numeric string such as
    ``-3.5`` passes through; any other text whose first non-blank character
    is a formula lead gets an apostrophe in front (CWE-1236).
    """
    if value is None or isinstance(value, (int, float, bool)):
        return value
    if isinstance(value, binary_type) and not isinstance(value, text_type):
        try:
            text = value.decode("utf-8")
        except UnicodeDecodeError:
            return value
    else:
        text = value if isinstance(value, text_type) else text_type(value)
    stripped = text.lstrip(" ")
    if stripped.startswith(_FORMULA_LEADS) and not _PLAIN_NUMBER_RE.match(stripped):
        return "'" + text
    return value
