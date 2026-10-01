"""Regression test for the uncaught NoneType dereference in
``nltk.corpus.reader.childes.CHILDESCorpusReader.convert_age`` (CWE-476).

``convert_age`` matched its input against a rigid ``P<d>Y<d>M?...`` pattern and
immediately did ``m.group(1)`` without checking that the match succeeded. Any
string that does not fit the shape made ``re.match`` return ``None``, so the
group access raised a cryptic ``AttributeError: 'NoneType' object has no
attribute 'group'`` out of this public helper. It now fails with a clear,
catchable ``ValueError`` instead, and the internal corpus walk
(``age(..., month=True)`` -> ``_get_age``) still degrades to ``None`` on a
malformed age rather than crashing.
"""

import pytest

from nltk.corpus.reader.childes import NS, CHILDESCorpusReader

# CHILDES ages and their value in months (years * 12 + months, +1 when the
# optional day field is > 15). These must be unchanged by the fix.
_VALID_AGES = {
    "P2Y10M": 34,
    "P0Y0M": 0,
    "P2Y1M15D": 25,  # 15 days -> not rounded up
    "P2Y1M20D": 26,  # 20 days -> rounded up
    "P2Y10": 34,  # trailing month marker is optional
}

# Strings that do not fit the CHILDES age shape (from the report's PoC).
_MALFORMED_AGES = ["", "garbage", "P2Y", "2Y3M", "P10M", "P2YxM"]


@pytest.fixture(scope="module")
def reader(tmp_path_factory):
    """A reader needs no corpus files for the pure string->int helper, but the
    root must exist (a hard-coded ``/tmp`` is absent on Windows)."""
    root = tmp_path_factory.mktemp("childes")
    return CHILDESCorpusReader(str(root), r"nonexistent\.xml")


@pytest.mark.parametrize("age_string,months", _VALID_AGES.items())
def test_convert_age_valid_strings_preserved(reader, age_string, months):
    """Well-formed ages convert exactly as before."""
    assert reader.convert_age(age_string) == months


@pytest.mark.parametrize("payload", _MALFORMED_AGES)
def test_convert_age_rejects_malformed_with_valueerror(reader, payload):
    """A malformed age raises a clear ValueError, not a cryptic AttributeError."""
    with pytest.raises(ValueError):
        reader.convert_age(payload)


def _age_in_months(tmp_path, age_attr):
    """Build a one-participant CHILDES file and read its child age in months."""
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<CHAT xmlns="{NS}"><Participants>'
        f'<participant id="CHI" role="Target_Child" age="{age_attr}"/>'
        "</Participants></CHAT>"
    )
    (tmp_path / "f.xml").write_text(xml, encoding="utf-8")
    reader = CHILDESCorpusReader(str(tmp_path), r"f\.xml", lazy=False)
    return reader.age(month=True)


def test_corpus_walk_degrades_gracefully_on_malformed_age(tmp_path):
    """The internal walk still returns None for a malformed age (not a crash)."""
    assert _age_in_months(tmp_path, "garbage") == [None]


def test_corpus_walk_converts_valid_age(tmp_path):
    """Sanity: a well-formed age still converts through the public walk."""
    assert _age_in_months(tmp_path, "P2Y10M") == [34]
