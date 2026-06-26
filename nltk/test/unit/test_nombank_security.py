"""Regression tests for uncaught crashes on a malformed line in the NomBank
instance parser (CWE-248 uncaught exception).

``NombankInstance.parse`` converted the sentence/word-number fields with
``int(...)`` and split the predicate and each argument on ``-`` without
validating them, so a malformed corpus line raised a cryptic, uncaught
``ValueError`` (``invalid literal for int()`` / ``not enough values to unpack``).
``parse`` is called by ``NombankCorpusReader.instances()`` via
``_read_instance_block`` with no surrounding handler, so one bad line aborted
iteration over the whole corpus. It now fails with the same clear
``"Badly formatted nombank line"`` ``ValueError`` the parser already raises for
other malformed lines; valid lines are unchanged.
"""

import pytest

from nltk.corpus.reader.nombank import NombankInstance

_VALID = "wsj.mrg 0 16 rise 01 16:0-rel"


def test_parse_rejects_non_numeric_sentnum():
    with pytest.raises(ValueError, match="Badly formatted nombank line"):
        NombankInstance.parse("wsj.mrg X 16 rise 01 16:0-rel 17:1-ARG1")


def test_parse_rejects_non_numeric_wordnum():
    with pytest.raises(ValueError, match="Badly formatted nombank line"):
        NombankInstance.parse("wsj.mrg 0 XX rise 01 16:0-rel 17:1-ARG1")


def test_parse_rejects_argument_without_separator():
    with pytest.raises(ValueError, match="Badly formatted nombank line"):
        NombankInstance.parse("wsj.mrg 0 16 rise 01 16:0-rel BADARG")


def test_parse_valid_line_preserved():
    """A well-formed line still parses to the same fields."""
    inst = NombankInstance.parse(_VALID)
    assert inst.fileid == "wsj.mrg"
    assert inst.sentnum == 0
    assert inst.wordnum == 16
    assert inst.baseform == "rise"
    assert inst.sensenumber == "01"
    assert inst.arguments == ()


def test_parse_valid_line_with_argument_preserved():
    """A well-formed line with an argument still parses the argument id."""
    inst = NombankInstance.parse(_VALID + " 17:1-ARG1")
    assert len(inst.arguments) == 1
    assert inst.arguments[0][1] == "ARG1"
