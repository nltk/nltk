"""Regression tests for tgrep /regex/ node-literal handling.

A tgrep query may contain a ``/regex/`` node literal, which is compiled through
``nltk.redos``. redos refuses a source larger than ``MAX_PATTERN_LENGTH`` as a
compile-time DoS guard (raising ``ValueError``, or ``redos.error`` for a
malformed literal). An oversized or invalid literal must be reported as a query
error (``TgrepException``) rather than surfacing the raw refusal; ordinary
queries are unaffected.
"""

import pytest

import nltk.redos as redos
from nltk import tgrep


def test_ordinary_query_compiles():
    assert tgrep.tgrep_compile("NN") is not None


def test_oversized_regex_literal_raises_tgrep_exception():
    oversized = "/" + "a" * (redos.MAX_PATTERN_LENGTH + 10) + "/"
    with pytest.raises(tgrep.TgrepException):
        tgrep.tgrep_compile(oversized)
