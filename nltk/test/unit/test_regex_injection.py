# Natural Language Toolkit: regex-injection / anchoring hardening tests
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""A value that is semantically a literal must be re.escape'd before it is spliced
into a regex; otherwise a metacharacter changes the pattern (a filter bypass) or an
unbalanced ``(``/``[`` raises re.error mid-iteration (a crash/DoS)."""

import xml.etree.ElementTree as ET

import pytest


def _mte_word(tags, tagset, ana, text="w"):
    from nltk.corpus.reader.mte import MTEFileReader

    reader = MTEFileReader.__new__(MTEFileReader)  # skip path validation
    reader._tagset = tagset
    reader._tags = tags
    elt = ET.Element("w")
    elt.attrib["ana"] = ana
    elt.text = text
    return reader._tagged_word_elt(elt, None)


@pytest.mark.parametrize("bad", ["(", "[a-z", "\\", "(?P<", "*"])
def test_mte_tags_metachar_injection_does_not_crash(bad):
    # An unbalanced / metacharacter tag filter used to raise re.error on every
    # tagged word (aborting the whole corpus read); it is now escaped.
    _mte_word(bad, "msd", "Ncmsn")  # must not raise


def test_mte_tags_wildcard_dash_still_works():
    # MSD tag filters use ``-`` as a per-position wildcard; that must be preserved.
    assert _mte_word("N----", "msd", "Ncmsn") == ("w", "Ncmsn")
    assert _mte_word("Nc", "msd", "Ncmsn") == ("w", "Ncmsn")


def test_mte_tags_literal_metachar_no_longer_defeats_filter():
    # A ``.*`` filter is now a literal ".*", so it does NOT match every tag.
    assert _mte_word(".*", "msd", "Ncmsn") is None


def test_chat80_relation_name_metachar_injection_does_not_crash():
    chat80 = pytest.importorskip("nltk.sem.chat80")
    try:
        chat80._str2records("cities.pl", "(")  # unbalanced paren: must not re.error
    except LookupError:
        pytest.skip("chat80 corpus data not installed")


def test_chat80_legitimate_relation_still_reads():
    chat80 = pytest.importorskip("nltk.sem.chat80")
    try:
        recs = chat80._str2records("cities.pl", "city")
    except LookupError:
        pytest.skip("chat80 corpus data not installed")
    assert isinstance(recs, list) and recs


@pytest.mark.parametrize("bait", ["foo/.\n./x", "foo/.\t./x", "foo/.\r./x"])
def test_data_no_protocol_control_char_split_traversal_rejected(bait):
    # url2pathname strips TAB/LF/CR, which can splice ".."; the no-protocol path
    # must reject these exactly as find() does (CWE-22).
    from nltk.data import _reject_unsafe_no_protocol

    with pytest.raises(ValueError):
        _reject_unsafe_no_protocol(bait)


def test_data_no_protocol_legitimate_resource_passes():
    from nltk.data import _reject_unsafe_no_protocol

    _reject_unsafe_no_protocol("corpora/brown/ca01")  # must not raise
