"""Regression tests for reading UTF-8 NKJP corpus files."""

import pytest

from nltk.corpus.reader.nkjp import NKJPCorpusReader


@pytest.fixture
def nkjp_reader(pathsec_sandbox):
    root = pathsec_sandbox.root
    sample = root / "sample"
    sample.mkdir()
    files = {
        "header.xml": "<teiHeader/>",
        "text.xml": (
            '<TEI><text><body><div><ab xml:id="ab_1">'
            "Zażółć gęślą jaźń."
            "</ab></div></body></text></TEI>"
        ),
        "ann_segmentation.xml": (
            "<TEI><text><body><p><s>"
            '<seg corresp="text.xml#string-range(ab_1,0,6)"/>'
            '<seg corresp="text.xml#string-range(ab_1,7,5)"/>'
            '<seg corresp="text.xml#string-range(ab_1,13,4)"/>'
            '<seg corresp="text.xml#string-range(ab_1,17,1)"/>'
            "</s></p></body></text></TEI>"
        ),
        "ann_morphosyntax.xml": (
            "<TEI><text><body><p><s>"
            '<seg><fs><f name="orth"><string>Zażółć</string></f></fs></seg>'
            '<seg><fs><f name="orth"><string>gęślą</string></f></fs></seg>'
            '<seg><fs><f name="orth"><string>jaźń</string></f></fs></seg>'
            "</s></p></body></text></TEI>"
        ),
    }
    for name, content in files.items():
        (sample / name).write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n' + content,
            encoding="utf-8",
        )
    return NKJPCorpusReader(str(root), fileids="sample")


@pytest.mark.parametrize(
    ("method", "expected"),
    [
        ("raw", ["Zażółć gęślą jaźń."]),
        ("words", ["Zażółć", "gęślą", "jaźń"]),
        ("sents", ["Zażółć gęślą jaźń."]),
    ],
)
def test_read_nkjp_text(nkjp_reader, method, expected):
    assert getattr(nkjp_reader, method)() == expected
