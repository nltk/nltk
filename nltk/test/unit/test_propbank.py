"""Regression tests for uncaught crashes on a malformed line in the PropBank
instance parser (CWE-248 uncaught exception).

``PropbankInstance.parse`` converted the sentence/word-number fields with
``int(...)`` and split each argument on ``-`` without validating them, so a
malformed corpus line raised a cryptic, uncaught ``ValueError`` (``invalid
literal for int()`` / ``not enough values to unpack``). ``parse`` is called by
``PropbankCorpusReader.instances()`` via ``_read_instance_block`` with no
surrounding handler, so one bad line aborted iteration over the whole corpus.
It now fails with the same clear ``"Badly formatted propbank line"`` ``ValueError``
the parser already raises for other malformed lines; valid lines are unchanged.
"""

import pytest

from nltk.corpus.reader.propbank import PropbankInstance

_VALID = "wsj.mrg 0 16 gold rise.01 vp--a 16:0-rel"


def test_parse_rejects_non_numeric_sentnum():
    with pytest.raises(ValueError, match="Badly formatted propbank line"):
        PropbankInstance.parse("wsj.mrg X 16 gold rise.01 vp--a 16:0-rel")


def test_parse_rejects_non_numeric_wordnum():
    with pytest.raises(ValueError, match="Badly formatted propbank line"):
        PropbankInstance.parse("wsj.mrg 0 XX gold rise.01 vp--a 16:0-rel")


def test_parse_rejects_argument_without_separator():
    with pytest.raises(ValueError, match="Badly formatted propbank line"):
        PropbankInstance.parse("wsj.mrg 0 16 gold rise.01 vp--a 16:0-rel BADARG")


def test_parse_valid_line_preserved():
    """A well-formed line still parses to the same fields."""
    inst = PropbankInstance.parse(_VALID)
    assert inst.fileid == "wsj.mrg"
    assert inst.sentnum == 0
    assert inst.wordnum == 16
    assert inst.tagger == "gold"
    assert inst.roleset == "rise.01"
    assert inst.arguments == ()


def test_parse_valid_line_with_argument_preserved():
    """A well-formed line with an argument still parses the argument id."""
    inst = PropbankInstance.parse(_VALID + " 15:1-ARG0")
    assert len(inst.arguments) == 1
    assert inst.arguments[0][1] == "ARG0"
