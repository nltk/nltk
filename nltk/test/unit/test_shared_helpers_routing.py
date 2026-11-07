# Natural Language Toolkit: modules route through nltk.xmlsec and nltk.data
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Every module that used to roll its own BOM table, text-encoding check,
XML structure scan or element-name rule now goes through ``nltk.data`` and
``nltk.xmlsec``. Each test here drives the module's public behaviour and shows
the shared helper is what decides."""

import bz2
import codecs
import io
import sys

import pytest

from nltk import xmlsec
from nltk.corpus.reader.xmldocs import XMLCorpusView
from nltk.data import BOMS, FileSystemPathPointer, encoding_from_bom, text_encoding

XML_TEXT = "<doc><w>caf\u00e9</w><w>\u65e5\u672c</w></doc>"


def _plant(root, name, data):
    path = root / name
    with open(
        path, "wb"
    ) as handle:  # sandboxed-open ok: fixture under the sandbox root
        handle.write(data)
    path.chmod(0o600)
    return str(path)


# nltk.data: one BOM table


def test_bom_table_tries_utf32_before_utf16_and_names_real_codecs():
    names = [encoding for _, encoding in BOMS]
    last32 = max(i for i, n in enumerate(names) if "32" in n)
    first16 = min(i for i, n in enumerate(names) if "16" in n)
    assert last32 < first16
    for bom, encoding in BOMS:
        assert codecs.lookup(encoding).name
        assert encoding_from_bom(bom + b"tail") == encoding
    assert encoding_from_bom(b"<?xml") is None
    assert encoding_from_bom(b"") is None


def test_the_utf32_little_endian_mark_is_not_read_as_utf16():
    assert encoding_from_bom(codecs.BOM_UTF32_LE) == "utf-32-le"
    assert codecs.BOM_UTF32_LE.startswith(codecs.BOM_UTF16_LE)


# XMLCorpusView detects the encoding through the shared table and check


@pytest.mark.parametrize("bom, encoding", BOMS)
def test_xml_view_reads_a_bom_marked_file_through_the_shared_table(
    pathsec_sandbox, bom, encoding
):
    path = _plant(pathsec_sandbox.root, "bom.xml", bom + XML_TEXT.encode(encoding))
    view = XMLCorpusView(FileSystemPathPointer(path), ".*/w")
    assert view._encoding == encoding
    assert [w.text for w in view] == ["caf\u00e9", "\u65e5\u672c"]


@pytest.mark.parametrize("declared", ["utf-8", "latin-1", "UTF-16"])
def test_xml_view_honours_a_declared_text_encoding(pathsec_sandbox, declared):
    body = f'<?xml version="1.0" encoding="{declared}"?>' + XML_TEXT
    if declared == "latin-1":
        body = body.replace("\u65e5\u672c", "ni")
    path = _plant(pathsec_sandbox.root, "decl.xml", body.encode(declared))
    view = XMLCorpusView(FileSystemPathPointer(path), ".*/w")
    if declared == "UTF-16":
        assert view._encoding == "utf-16-le"  # the BOM the codec wrote decides
    else:
        assert codecs.lookup(view._encoding).name == codecs.lookup(declared).name
    assert [w.text for w in view][0] == "caf\u00e9"


@pytest.mark.parametrize("codec", ["bz2_codec", "zlib_codec", "rot_13"])
def test_xml_view_refuses_a_declared_codec_that_is_no_text_encoding(
    pathsec_sandbox, codec
):
    # The declaration names the codec; a bytes-to-bytes one would inflate
    # the file through the reader. The shared check refuses it first.
    prolog = f'<?xml version="1.0" encoding="{codec}"?>\n'.encode()
    bomb = bz2.compress(b"<doc>" + b"<w/>" * 1_000_000 + b"</doc>", 9)
    path = _plant(pathsec_sandbox.root, "bomb.xml", prolog + bomb)
    with pytest.raises(LookupError, match="not a text encoding"):
        XMLCorpusView(FileSystemPathPointer(path), ".*/w")


def test_xml_view_teeth_the_declared_codec_reaches_the_reader_unchecked(
    pathsec_sandbox, monkeypatch
):
    # A declaration cannot sit in front of bz2 bytes, so the detector is made
    # to hand the reader the declared name unchecked, as it did before.
    import nltk.data

    payload = b"<doc>" + b"<w/>" * 100_000 + b"</doc>"
    path = _plant(pathsec_sandbox.root, "bomb.xml", bz2.compress(payload, 9))
    monkeypatch.setattr(XMLCorpusView, "_detect_encoding", lambda self, f: "bz2_codec")
    monkeypatch.setattr(nltk.data, "text_encoding", lambda name: name)
    view = XMLCorpusView(FileSystemPathPointer(path), ".*/w")
    assert view._encoding == "bz2_codec"
    view._open()
    assert len(view._stream.read()) == len(payload)  # the reader inflated it


# The downloader's index scan is xmlsec.screen with the index ceilings


def test_downloader_index_scan_is_xmlsec_screen_with_the_index_ceilings(monkeypatch):
    from nltk import downloader

    calls = []
    monkeypatch.setattr(downloader, "screen", lambda data, **kw: calls.append(kw))
    downloader._check_index_structure(b"<nltk_data/>")
    assert calls == [
        {
            "max_elements": downloader.MAX_INDEX_ELEMENTS,
            "max_attributes": downloader.MAX_INDEX_ATTRIBUTES,
            "max_token_bytes": downloader.MAX_INDEX_TOKEN_BYTES,
        }
    ]


def test_downloader_index_scan_refuses_more_elements_than_the_index_ceiling():
    from nltk import downloader

    few = b"<nltk_data>" + b"<e/>" * 10 + b"</nltk_data>"
    downloader._check_index_structure(few)
    many = (
        b"<nltk_data>" + b"<e/>" * (downloader.MAX_INDEX_ELEMENTS + 1) + b"</nltk_data>"
    )
    with pytest.raises(ValueError, match="element count"):
        downloader._check_index_structure(many)
    assert (
        downloader.MAX_INDEX_ELEMENTS < xmlsec.MAX_ELEMENTS
    )  # tighter than the module's


def test_downloader_index_scan_refuses_an_entity_declaration():
    from nltk import downloader

    data = b'<!DOCTYPE d [<!ENTITY a "aaaa">]><nltk_data>&a;</nltk_data>'
    with pytest.raises(ValueError):
        downloader._check_index_structure(data)


def test_xmlsec_screen_takes_lower_ceilings_and_keeps_the_module_defaults():
    data = b"<r>" + b"<e/>" * 50 + b"</r>"
    xmlsec.screen(data)
    with pytest.raises(xmlsec.StructureForbidden, match="element count"):
        xmlsec.screen(data, max_elements=20)
    token = b"<r>" + b"<!--" + b"x" * 300 + b"-->" + b"</r>"
    xmlsec.screen(token)
    with pytest.raises(xmlsec.StructureForbidden, match="markup token"):
        xmlsec.screen(token, max_token_bytes=200)


# internals decodes child output with the encoding open() would pick


def test_stdout_decoder_uses_the_shared_default(monkeypatch):
    from nltk import internals

    class Stdout:
        encoding = None

    monkeypatch.setattr(sys, "__stdout__", Stdout())
    assert internals._decode_stdoutdata("already text") == "already text"
    assert internals._decode_stdoutdata(b"abc") == "abc"
    Stdout.encoding = "bz2_codec"
    with pytest.raises(LookupError, match="not a text encoding"):
        internals._decode_stdoutdata(b"abc")
    assert text_encoding("utf-8") == "utf-8"


# Toolbox writes a chunk grammar label as an element name through xmlsec


def test_toolbox_chunk_label_is_written_as_one_element():
    from xml.etree.ElementTree import tostring

    import nltk.toolbox as tb

    data = tb.ToolboxData()
    data.open_string("\\lx a\n\\ps n\n\n\\lx b\n\\ps v\n")
    tree = data.parse(grammar="x<y: {<ps>}", key="lx")
    labels = {e.tag for e in tree.iter()}
    assert "x_y" in labels and not any("<" in label for label in labels)
    xml = tostring(tree).decode()
    assert xml.count("<x_y>") == 2 and "<x<y" not in xml
