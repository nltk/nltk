# Natural Language Toolkit: the Toolbox encoding threat model, case by case
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""The ``encoding`` a Toolbox file is read and written with, attacked through
every entry route: a filename, a ``FileSystemPathPointer``, a
``ZipFilePathPointer`` and the corpus reader, which opens a PathPointer.

1. Codecs that are no text encoding (``zlib_codec``, ``bz2_codec``,
   ``rot_13``...) and odd codec names: refused before any file is opened.
2. Error handlers and codecs that change what the writer emits: the output
   reads back with the markers written, or the writer refuses it.
3. BOMs and byte orders (UTF-8, UTF-16, UTF-32, doubled and mid-file BOMs)
   and stateful codecs across the PathPointer reader's read boundaries.
4. Invalid, overlong and surrogate sequences; NUL; mixed line ends; Unicode
   separators; a long line; on every route and encoding.
5. The shipped corpus recoded into every encoding, read on every route and
   written back; the chunk parse's ``findall``; ``ToolboxSettings``.

Hostile cases have teeth: the code before this change is put back in
process, or the input is shown to be live, and the assertion fails.
"""

import bz2
import codecs
import importlib
import io
import os
import sys
import zipfile
import zlib
from xml.etree.ElementTree import Element, ElementTree, SubElement, tostring

import pytest

import nltk.data
from nltk import pathsec
from nltk.corpus.reader.toolbox import ToolboxCorpusReader
from nltk.data import (
    FileSystemPathPointer,
    PathPointer,
    SeekableUnicodeStreamReader,
    ZipFilePathPointer,
)

#: The module itself: ``import nltk.toolbox as tb`` binds the LazyModule that
#: nltk/__init__ puts in its place, on which monkeypatch restores a stale copy.
tb = importlib.import_module("nltk.toolbox")


def plant(directory, name, data, mode=0o600):
    """Write ``data`` (bytes) under ``directory`` and return the path."""
    path = os.path.join(str(directory), name)
    with open(path, "wb") as handle:
        handle.write(data)
    os.chmod(path, mode)
    return path


def zipped(directory, name, path):
    zpath = os.path.join(str(directory), name + ".zip")
    with zipfile.ZipFile(zpath, "w") as archive:
        archive.write(path, name)
    os.chmod(zpath, 0o600)
    return zpath


def by_route(directory, name, data, encoding):
    """The fields of ``data`` planted as ``name``, read on every route;
    an exception is returned as its type name."""
    path = plant(directory, name, data)
    zpath = zipped(directory, name, path)
    readers = {
        "filename": lambda: tb.StandardFormat(path, encoding),
        "pointer": lambda: tb.StandardFormat(FileSystemPathPointer(path), encoding),
        "zip": lambda: tb.StandardFormat(ZipFilePathPointer(zpath, name), encoding),
    }
    out = {}
    for route, make in readers.items():
        try:
            out[route] = list(make().fields(unwrap=False))
        except Exception as exc:
            out[route] = type(exc).__name__
    try:
        reader = ToolboxCorpusReader(str(directory), [name], encoding=encoding)
        out["corpus reader"] = reader.fields(name, unwrap=False, encoding=encoding)
    except Exception as exc:
        out["corpus reader"] = type(exc).__name__
    return out


def tree_of(*records):
    root = Element("toolbox_data")
    for fields in records:
        rec = SubElement(root, "record")
        for mkr, value in fields:
            SubElement(rec, mkr).text = value
    return root


def opens_under(monkeypatch, root):
    """Record every os.open of a path under ``root``."""
    real, seen = os.open, []

    def spy(path, *args, **kwargs):
        if str(path).startswith(str(root)):
            seen.append(path)
        return real(path, *args, **kwargs)

    monkeypatch.setattr(os, "open", spy)
    return seen


def develop_open(self, sfm_file):
    """StandardFormat.open as develop has it, for teeth."""
    if isinstance(sfm_file, PathPointer):
        self._file = sfm_file.open(self._encoding)
    else:
        self._file = pathsec.open(sfm_file, "r", encoding=self._encoding)


def develop_reading(monkeypatch):
    """Put back develop's open and its line iteration (the stream's own), and
    develop's reader, which noted the byte order a BOM named but kept decoding
    with the generic codec."""
    monkeypatch.setattr(tb.StandardFormat, "open", develop_open)
    monkeypatch.setattr(tb.StandardFormat, "_lines", lambda self: iter(self._file))
    real_check_bom = SeekableUnicodeStreamReader._check_bom

    def develop_check_bom(self):
        encoding = self.encoding
        length = real_check_bom(self)
        self.encoding = encoding
        return length

    monkeypatch.setattr(SeekableUnicodeStreamReader, "_check_bom", develop_check_bom)

    def develop_incr_decode(self, data):
        # develop's stateless decode of one block, truncation retried
        while True:
            try:
                return self.decode(data, "strict")
            except UnicodeDecodeError as exc:
                if exc.end == len(data):
                    return self.decode(data[: exc.start], self.errors)
                elif self.errors == "strict":
                    raise
                else:
                    return self.decode(data, self.errors)

    def develop_read(self, size=None):
        # develop decoded each block on its own, with the stateless decoder
        if size == 0:
            return ""
        if self._bom and self.stream.tell() == 0:
            self.stream.read(self._bom)
        new_bytes = self.stream.read() if size is None else self.stream.read(size)
        data = self.bytebuffer + new_bytes
        chars, consumed = develop_incr_decode(self, data)
        if size is not None and not chars and new_bytes:
            while not chars:
                new_bytes = self.stream.read(1)
                if not new_bytes:
                    break
                data += new_bytes
                chars, consumed = develop_incr_decode(self, data)
        self.bytebuffer = data[consumed:]
        return chars

    monkeypatch.setattr(
        SeekableUnicodeStreamReader, "_incr_decode", develop_incr_decode
    )
    monkeypatch.setattr(SeekableUnicodeStreamReader, "_read", develop_read)


# 1. Codecs that are no text encoding, and odd names.

NOT_TEXT = [
    "zlib_codec",
    "bz2_codec",
    "base64_codec",
    "hex_codec",
    "uu_codec",
    "quopri_codec",
    "rot_13",
]
PAYLOAD = "\\lx a\n\\ge marker\n"


def encoded_payload(codec):
    if codec == "rot_13":
        return codecs.encode(PAYLOAD, codec).encode("ascii")
    return codecs.encode(PAYLOAD.encode("ascii"), codec)


def _corpus(path, encoding):
    reader = ToolboxCorpusReader(
        os.path.dirname(path), [os.path.basename(path)], encoding=encoding
    )
    return reader


ENTRIES = {
    "StandardFormat by filename": lambda p, e: tb.StandardFormat(p, e),
    "StandardFormat by pointer": lambda p, e: tb.StandardFormat(
        FileSystemPathPointer(p), e
    ),
    "ToolboxData": lambda p, e: tb.ToolboxData(p, e).parse(key="lx"),
    "ToolboxSettings": lambda p, e: tb.ToolboxSettings(FileSystemPathPointer(p), e),
    "corpus reader fields": lambda p, e: _corpus(p, e).fields(os.path.basename(p)),
    "corpus reader xml": lambda p, e: _corpus(p, e).xml(os.path.basename(p)),
    "to_sfm_string": lambda p, e: tb.to_sfm_string(tree_of([("lx", "a")]), encoding=e),
}


@pytest.mark.parametrize("codec", NOT_TEXT)
@pytest.mark.parametrize("entry", sorted(ENTRIES))
def test_a_codec_that_is_no_text_encoding_is_refused_before_any_open(
    pathsec_sandbox, monkeypatch, codec, entry
):
    path = plant(pathsec_sandbox.root, "c.db", encoded_payload(codec))
    opened = opens_under(monkeypatch, pathsec_sandbox.root)
    with pytest.raises(LookupError, match="not a text encoding"):
        ENTRIES[entry](path, codec)
    assert opened == []


@pytest.mark.parametrize("codec", ["zlib_codec", "bz2_codec"])
def test_no_text_encoding_teeth(pathsec_sandbox, monkeypatch, codec):
    """Unchecked, the PathPointer route expands a planted bomb: the reader
    decodes with any codec, unlike open(). The check is applied twice, by
    Toolbox before the open and by the reader itself, so both are lifted."""
    raw = b"\\lx a\n" + b"a" * 1_000_000
    data = (zlib if codec == "zlib_codec" else bz2).compress(raw, 9)
    assert len(data) * 500 < len(raw)
    path = plant(pathsec_sandbox.root, "bomb.db", data)
    monkeypatch.setattr(tb, "_text_encoding", lambda encoding: encoding)
    monkeypatch.setattr(nltk.data, "text_encoding", lambda encoding: encoding)
    sf = tb.StandardFormat(FileSystemPathPointer(path), codec)
    assert sf._file.read() == raw
    with pytest.raises((LookupError, OSError)) as caught:
        tb.StandardFormat(path, codec)  # open() has its own check
    # pathsec.open then closes the descriptor fdopen closed (EBADF), so the
    # LookupError may arrive as the context of an OSError.
    refusal = [caught.value, caught.value.__context__]
    assert any(isinstance(e, LookupError) for e in refusal), refusal


@pytest.mark.parametrize("codec", ["zlib_codec", "bz2_codec"])
def test_the_reader_refuses_a_bomb_codec_on_its_own(
    pathsec_sandbox, monkeypatch, codec
):
    """With only Toolbox's check lifted, SeekableUnicodeStreamReader refuses the
    codec itself, so every PathPointer route is covered, not just this one."""
    raw = b"\\lx a\n" + b"a" * 1_000_000
    data = (zlib if codec == "zlib_codec" else bz2).compress(raw, 9)
    path = plant(pathsec_sandbox.root, "bomb.db", data)
    monkeypatch.setattr(tb, "_text_encoding", lambda encoding: encoding)
    with pytest.raises(LookupError, match="not a text encoding"):
        tb.StandardFormat(FileSystemPathPointer(path), codec)
    with pytest.raises(LookupError, match="not a text encoding"):
        FileSystemPathPointer(path).open(codec)


@pytest.mark.parametrize(
    "codec",
    NOT_TEXT + ["utf-8", "cp1252", "utf-16", "gbk", "iso2022_jp", "idna", "punycode"],
)
def test_the_check_is_the_one_open_applies(codec):
    """``_text_encoding`` refuses exactly the codecs TextIOWrapper refuses."""
    try:
        io.TextIOWrapper(io.BytesIO(), encoding=codec)
        accepted_by_open = True
    except LookupError:
        accepted_by_open = False
    try:
        tb._text_encoding(codec)
        accepted_here = True
    except LookupError:
        accepted_here = False
    assert accepted_here == accepted_by_open


@pytest.mark.parametrize("codec", NOT_TEXT)
def test_unchecked_the_writer_fails_inside_the_codec(monkeypatch, codec):
    """str.encode refuses such a codec, the incremental encoder the writer
    uses does not: unchecked, it fails on the first line, inside the codec;
    the check refuses it first, with the error str.encode gives."""
    with pytest.raises(LookupError):
        "\\lx a\n".encode(codec)
    monkeypatch.setattr(tb, "_text_encoding", lambda encoding: encoding)
    with pytest.raises(TypeError):
        tb.to_sfm_string(tree_of([("lx", "a")]), encoding=codec)


ODD_NAMES = [
    "utf-8/../x",
    "../../etc/passwd",
    "utf-8" + chr(0),
    "",
    " ",
    "encodings.utf_8",
    "aliases",
    "no-such-codec",
    123,
    b"utf-8",
]


@pytest.mark.parametrize("name", ODD_NAMES, ids=repr)
@pytest.mark.parametrize("entry", sorted(ENTRIES))
def test_an_odd_codec_name_is_refused_before_any_open(
    pathsec_sandbox, monkeypatch, name, entry
):
    path = plant(pathsec_sandbox.root, "c.db", PAYLOAD.encode("ascii"))
    opened = opens_under(monkeypatch, pathsec_sandbox.root)
    with pytest.raises((LookupError, ValueError, TypeError)):
        ENTRIES[entry](path, name)
    assert opened == []


#: Text codecs no Toolbox file uses, whose meaning is the codec's own: every
#: route decodes them alike, with no expansion beyond the codec's.
ODD_TEXT = ["idna", "punycode", "utf-7", "unicode_escape", "raw_unicode_escape"]


@pytest.mark.parametrize("codec", ODD_TEXT)
def test_an_odd_text_codec_reads_alike_on_every_route(pathsec_sandbox, codec):
    try:
        data = PAYLOAD.encode(codec)
    except UnicodeError:
        data = PAYLOAD.encode("ascii")
    routes = by_route(pathsec_sandbox.root, "odd.db", data, codec)
    assert len({repr(v) for v in routes.values()}) == 1, routes


# 2. What the writer emits.

WRITE_ENCODINGS = [
    "ascii",
    "latin-1",
    "cp1252",
    "cp037",
    "utf-8",
    "utf-8-sig",
    "utf-16",
    "gbk",
    "iso2022_jp",
    "utf-7",
]
WRITE_ERRORS = [
    "strict",
    "ignore",
    "replace",
    "surrogateescape",
    "surrogatepass",
    "backslashreplace",
    "namereplace",
    "xmlcharrefreplace",
]
WRITE_PAYLOADS = {
    "ignore drops a letter before a marker": ("ge", "x\n\u00e9\\lx smuggled"),
    "an escape starts a line": ("ge", "x\n\u00e9 tail"),
    "an escaped byte is a backslash in cp037": ("ge", "x\n\udce0lx smuggled"),
    "a low surrogate": ("ge", "x\n\udc5clx smuggled"),
    "a lone surrogate": ("ge", "x\ud800y"),
    "a marker loses a letter": ("l\u00e9x", "value"),
    "benign text": ("ge", "caf\u00e9 \u4e2d\u6587 \u3042"),
}


def _written(mkr, value):
    tree = tree_of([("lx", "a"), (mkr, value), ("gp", "end")], [("lx", "b")])
    return tree, ["lx", mkr, "gp", "lx"]


def _read_back(directory, data, encoding):
    path = plant(directory, "w.db", data)
    verdicts = {}
    for route, src in (("filename", path), ("pointer", FileSystemPathPointer(path))):
        try:
            verdicts[route] = [m for m, _ in tb.StandardFormat(src, encoding).fields()]
        except UnicodeDecodeError:
            verdicts[route] = "unreadable"
    return verdicts


@pytest.mark.parametrize("errors", WRITE_ERRORS)
@pytest.mark.parametrize("payload", sorted(WRITE_PAYLOADS))
def test_the_writer_output_reads_back_with_its_markers_or_is_refused(
    pathsec_sandbox, payload, errors
):
    tree, markers = _written(*WRITE_PAYLOADS[payload])
    for encoding in WRITE_ENCODINGS:
        try:
            data = tb.to_sfm_string(tree, encoding=encoding, errors=errors)
        except (ValueError, UnicodeError, LookupError):
            continue  # refused (ValueError) or the codec's own error
        for route, got in _read_back(pathsec_sandbox.root, data, encoding).items():
            assert got in (markers, "unreadable"), (encoding, route, got)


@pytest.mark.parametrize("encoding", WRITE_ENCODINGS)
def test_benign_text_round_trips_in_every_encoding_that_holds_it(
    pathsec_sandbox, encoding
):
    tree, markers = _written(*WRITE_PAYLOADS["benign text"])
    try:
        "".join(WRITE_PAYLOADS["benign text"]).encode(encoding)
    except UnicodeEncodeError:
        tree, markers = _written("ge", "plain gloss")
    data = tb.to_sfm_string(tree, encoding=encoding)
    for route, got in _read_back(pathsec_sandbox.root, data, encoding).items():
        assert got == markers, (route, got)
    path = plant(pathsec_sandbox.root, "w.db", data)
    assert tostring(tb.ToolboxData(path, encoding).parse(key="lx")) == tostring(
        tb.ToolboxData(FileSystemPathPointer(path), encoding).parse(key="lx")
    )


#: Cases the writer of the pre-change head wrote and the reader read back
#: with other markers.
SMUGGLED_BEFORE = [
    ("ignore drops a letter before a marker", "ascii", "ignore"),
    ("an escape starts a line", "ascii", "backslashreplace"),
    ("an escape starts a line", "ascii", "namereplace"),
    ("an escaped byte is a backslash in cp037", "cp037", "surrogateescape"),
    ("a marker loses a letter", "ascii", "ignore"),
    ("a marker loses a letter", "ascii", "replace"),
]


def _pre_change_encode(lines, encoding, errors, unicode_fields):
    """The writer of the pre-change head: each line through str.encode."""
    chunks = []
    for mkr, line in lines:
        utf8 = mkr is not None and unicode_fields is not None and mkr in unicode_fields
        chunks.append(line.encode("utf8" if utf8 else encoding, errors))
    return b"".join(chunks)


@pytest.mark.parametrize("payload, encoding, errors", SMUGGLED_BEFORE)
def test_a_lossy_writer_case_is_refused(pathsec_sandbox, payload, encoding, errors):
    tree, _ = _written(*WRITE_PAYLOADS[payload])
    with pytest.raises(ValueError, match="reads back as marker"):
        tb.to_sfm_string(tree, encoding=encoding, errors=errors)


@pytest.mark.parametrize("payload, encoding, errors", SMUGGLED_BEFORE)
def test_lossy_writer_teeth(pathsec_sandbox, monkeypatch, payload, encoding, errors):
    tree, markers = _written(*WRITE_PAYLOADS[payload])
    monkeypatch.setattr(tb, "_encode_sfm", _pre_change_encode)
    data = tb.to_sfm_string(tree, encoding=encoding, errors=errors)
    got = _read_back(pathsec_sandbox.root, data, encoding)["filename"]
    assert got != markers


def test_a_codec_that_encodes_each_field_apart_is_refused(pathsec_sandbox, monkeypatch):
    """punycode encodes each piece on its own and decodes a file as one piece,
    so the second field's marker lands inside the first field's value."""
    tree, markers = _written("ge", "gloss")
    with pytest.raises(ValueError, match="reads back as marker"):
        tb.to_sfm_string(tree, encoding="punycode")
    monkeypatch.setattr(tb, "_encode_sfm", _pre_change_encode)  # teeth
    data = tb.to_sfm_string(tree, encoding="punycode")
    assert _read_back(pathsec_sandbox.root, data, "punycode")["filename"] != markers


@pytest.mark.parametrize(
    "encoding, bom",
    [
        ("utf-16", (codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)),
        ("utf-32", (codecs.BOM_UTF32_LE, codecs.BOM_UTF32_BE)),
        ("utf-8-sig", (codecs.BOM_UTF8,)),
    ],
)
def test_an_encoded_output_carries_one_bom_and_reads_back(
    pathsec_sandbox, monkeypatch, encoding, bom
):
    tree, markers = _written("ge", "gloss")
    data = tb.to_sfm_string(tree, encoding=encoding)
    assert data.startswith(bom) and sum(data.count(b) for b in bom) == 1
    for got in _read_back(pathsec_sandbox.root, data, encoding).values():
        assert got == markers
    monkeypatch.setattr(tb, "_encode_sfm", _pre_change_encode)  # teeth
    data = tb.to_sfm_string(tree, encoding=encoding)
    assert sum(data.count(b) for b in bom) == len(markers) + 1
    assert _read_back(pathsec_sandbox.root, data, encoding)["filename"] != markers


@pytest.mark.parametrize("encoding", ["utf-8", "latin-1", "cp1252", "gbk"])
def test_unicode_fields_read_back_with_their_markers(pathsec_sandbox, encoding):
    tree, markers = _written("ge", "caf\u00e9")
    data = tb.to_sfm_string(tree, encoding=encoding, unicode_fields={"ge"})
    assert data.count("caf\u00e9".encode()) == 1
    for got in _read_back(pathsec_sandbox.root, data, encoding).values():
        assert got == markers


def test_unicode_fields_in_an_encoding_that_is_not_ascii_compatible_are_refused():
    tree, _ = _written("ge", "x%\u0800lx smuggled")
    with pytest.raises(ValueError, match="reads back as marker"):
        tb.to_sfm_string(tree, encoding="cp037", unicode_fields={"ge"})
    data = _pre_change_encode(  # teeth: the UTF-8 bytes read as cp037
        [(None, ""), ("ge", "\\ge x%\u0800lx smuggled\n")], "cp037", "strict", {"ge"}
    )
    assert "\n\\" in data.decode("cp037")


# 3. BOMs, byte orders and read boundaries.

TEXT = "\\lx a\n\\ge b\n"
EXPECTED = [("lx", "a"), ("ge", "b")]
BOMS = {
    "utf-16 LE BOM": ("utf-16", codecs.BOM_UTF16_LE + TEXT.encode("utf-16-le")),
    "utf-16 BE BOM": ("utf-16", codecs.BOM_UTF16_BE + TEXT.encode("utf-16-be")),
    "utf-32 LE BOM": ("utf-32", codecs.BOM_UTF32_LE + TEXT.encode("utf-32-le")),
    "utf-32 BE BOM": ("utf-32", codecs.BOM_UTF32_BE + TEXT.encode("utf-32-be")),
    "utf-16-le with a BOM": (
        "utf-16-le",
        codecs.BOM_UTF16_LE + TEXT.encode("utf-16-le"),
    ),
    "utf-16-be with a BOM": (
        "utf-16-be",
        codecs.BOM_UTF16_BE + TEXT.encode("utf-16-be"),
    ),
    "utf-8 with a BOM": ("utf-8", codecs.BOM_UTF8 + TEXT.encode()),
    "utf_8 with a BOM": ("utf_8", codecs.BOM_UTF8 + TEXT.encode()),
    "utf-8-sig with a BOM": ("utf-8-sig", codecs.BOM_UTF8 + TEXT.encode()),
    "cp1252 with UTF-8 BOM bytes": ("cp1252", codecs.BOM_UTF8 + TEXT.encode()),
}


@pytest.mark.parametrize("label", sorted(BOMS))
def test_a_bom_and_its_byte_order_read_alike_on_every_route(pathsec_sandbox, label):
    encoding, data = BOMS[label]
    for route, got in by_route(pathsec_sandbox.root, "b.db", data, encoding).items():
        assert got == EXPECTED, (route, got)


def test_utf16_without_a_bom_reads_no_other_fields(pathsec_sandbox):
    """Pinned: open() refuses UTF-16 without a BOM (UnicodeError before Python
    3.13, its subclass UnicodeDecodeError since); the PathPointer reader
    decodes it in the native byte order, as on develop."""
    data = TEXT.encode("utf-16-le" if sys.byteorder == "little" else "utf-16-be")
    refused = ("UnicodeError", "UnicodeDecodeError")
    for route, got in by_route(pathsec_sandbox.root, "n.db", data, "utf-16").items():
        assert got == EXPECTED or got in refused, (route, got)


#: Repeated BOMs: a codec that reads a BOM takes one, the first line drops
#: one more; any left is data, so the first line has no marker.
DOUBLED = {
    "utf-8, two": ("utf-8", codecs.BOM_UTF8 * 2 + TEXT.encode(), None),
    "utf_8, two": ("utf_8", codecs.BOM_UTF8 * 2 + TEXT.encode(), None),
    "cp1252, two": ("cp1252", codecs.BOM_UTF8 * 2 + TEXT.encode(), None),
    "utf-16-le, two": (
        "utf-16-le",
        codecs.BOM_UTF16_LE * 2 + TEXT.encode("utf-16-le"),
        None,
    ),
    "utf-8-sig, two": ("utf-8-sig", codecs.BOM_UTF8 * 2 + TEXT.encode(), "lx"),
    "utf-16, two": ("utf-16", codecs.BOM_UTF16_LE * 2 + TEXT.encode("utf-16-le"), "lx"),
    "utf-16, three": (
        "utf-16",
        codecs.BOM_UTF16_LE * 3 + TEXT.encode("utf-16-le"),
        None,
    ),
    "utf-32 big endian, three": (
        "utf-32",
        codecs.BOM_UTF32_BE * 3 + TEXT.encode("utf-32-be"),
        None,
    ),
}


@pytest.mark.parametrize("label", sorted(DOUBLED))
def test_repeated_boms_read_alike_on_every_route(pathsec_sandbox, label):
    encoding, data, first = DOUBLED[label]
    routes = by_route(pathsec_sandbox.root, "d.db", data, encoding)
    assert len({repr(v) for v in routes.values()}) == 1, routes
    assert routes["filename"][0][0] == first


def test_bom_teeth(pathsec_sandbox, monkeypatch):
    """develop's open, by the literal codec name: the reader's BOM table
    drops a BOM, then decodes big endian UTF-16 in the native order; and with
    this branch's U+FEFF drop, two UTF-8 BOMs read differently by route."""
    develop_reading(monkeypatch)
    encoding, data = BOMS["utf-16 BE BOM"]
    routes = by_route(pathsec_sandbox.root, "b.db", data, encoding)
    assert routes["filename"] == EXPECTED and routes["pointer"] != EXPECTED
    encoding, data, _ = DOUBLED["utf-8, two"]
    routes = by_route(pathsec_sandbox.root, "d.db", data, encoding)
    assert routes["filename"][0][0] is None and routes["pointer"][0][0] == "lx"


def _boundary_files():
    smuggle = "\\lx smuggled\n"
    return {
        "utf-8-sig": lambda pad: codecs.BOM_UTF8
        + ("\\lx a\n\\ge " + "x" * pad + "\n").encode()
        + codecs.BOM_UTF8
        + smuggle.encode(),
        "utf-16": lambda pad: codecs.BOM_UTF16_LE
        + ("\\lx a\n\\ge " + "x" * pad + "\n").encode("utf-16-le")
        + codecs.BOM_UTF16_LE
        + smuggle.encode("utf-16-le"),
        "utf-32": lambda pad: codecs.BOM_UTF32_LE
        + ("\\lx a\n\\ge " + "x" * pad + "\n").encode("utf-32-le")
        + codecs.BOM_UTF32_LE
        + smuggle.encode("utf-32-le"),
        "iso2022_jp": lambda pad: (
            "\\lx a\n\\ge " + "x" * pad + "\u3042\u3044\u3046" * 3 + "\n\\lx b\n"
        ).encode("iso2022_jp"),
        "utf-7": lambda pad: (
            "\\lx a\n\\ge " + "x" * pad + "\u00e9\u00e8" * 9 + "\n\\lx b\n"
        ).encode("utf-7"),
        "hz": lambda pad: (
            "\\lx a\n\\ge " + "x" * pad + "\u4e2d\u6587" * 9 + "\n\\lx b\n"
        ).encode("hz"),
    }


BOUNDARY_PADS = range(0, 160)


def _boundary_disagreements(directory, encoding):
    make = _boundary_files()[encoding]
    found = []
    for pad in BOUNDARY_PADS:
        path = plant(directory, "edge.db", make(pad))
        by_name = list(tb.StandardFormat(path, encoding).fields(unwrap=False))
        pointer = FileSystemPathPointer(path)
        try:
            by_pointer = list(tb.StandardFormat(pointer, encoding).fields(unwrap=False))
        except UnicodeDecodeError:
            by_pointer = None
        if by_name != by_pointer:
            found.append((pad, by_name, by_pointer))
    return found


@pytest.mark.parametrize("encoding", sorted(_boundary_files()))
def test_a_bom_or_shift_state_at_a_read_boundary_reads_alike(pathsec_sandbox, encoding):
    assert _boundary_disagreements(pathsec_sandbox.root, encoding) == []


@pytest.mark.parametrize("encoding", sorted(_boundary_files()))
def test_read_boundary_teeth(pathsec_sandbox, monkeypatch, encoding):
    """develop decoded each readline span on its own: a BOM there was dropped
    (a field smuggled) and a shift state lost."""
    develop_reading(monkeypatch)
    found = _boundary_disagreements(pathsec_sandbox.root, encoding)
    assert found
    if encoding in ("utf-16", "utf-32"):
        assert any(p and p[-1] == ("lx", "smuggled") for _, _, p in found)


def test_no_encoding_reads_the_same_on_both_routes(pathsec_sandbox, monkeypatch):
    path = plant(pathsec_sandbox.root, "n.db", "\\lx caf\u00e9\n".encode())
    by_name = list(tb.StandardFormat(path).fields())
    assert list(tb.StandardFormat(FileSystemPathPointer(path)).fields()) == by_name
    develop_reading(monkeypatch)  # teeth: develop's pointer handed out bytes
    with pytest.raises(TypeError):
        list(tb.StandardFormat(FileSystemPathPointer(path)).fields())


@pytest.mark.parametrize("encoding", ["cp1252", "utf-8", "UTF-16", "mac roman"])
def test_the_pathpointer_route_opens_through_the_pointer(
    pathsec_sandbox, monkeypatch, encoding
):
    """The PathPointer route is ``sfm_file.open(encoding)``: NLTK's own
    contained open, decoded by the reader every PathPointer gives, with the
    codec the caller named."""
    path = plant(pathsec_sandbox.root, "p.db", TEXT.encode(encoding))
    calls = []
    real = FileSystemPathPointer.open

    def spy(self, encoding=None):
        calls.append(encoding)
        return real(self, encoding)

    monkeypatch.setattr(FileSystemPathPointer, "open", spy)
    sf = tb.StandardFormat(FileSystemPathPointer(path), encoding)
    assert isinstance(sf._file, SeekableUnicodeStreamReader) and len(calls) == 1
    assert codecs.lookup(calls[0]).name == codecs.lookup(encoding).name
    assert list(sf.fields()) == EXPECTED


# 4. Invalid sequences, NUL, line ends, separators, a long line.

INVALID = {
    "overlong LF": b"\xc0\x8a",
    "overlong backslash": b"\xc1\x9c",
    "lone surrogate": b"\xed\xa0\x80",
    "invalid byte": b"\xff",
    "truncated sequence": b"\xe2\x80",
}


@pytest.mark.parametrize("label", sorted(INVALID))
def test_an_invalid_sequence_before_a_marker_is_refused_on_every_route(
    pathsec_sandbox, label
):
    data = b"\\lx a\n\\ge x\n" + INVALID[label] + b"\\lx smuggled\n\\gp end\n"
    for route, got in by_route(pathsec_sandbox.root, "i.db", data, "utf-8").items():
        assert got == "UnicodeDecodeError", (route, got)


@pytest.mark.parametrize("label", sorted(INVALID))
def test_invalid_sequence_teeth(label):
    """Decoded leniently, the line after the invalid bytes is a marker; the
    readers decode strictly whatever errors a caller passes."""
    data = b"\\lx a\n\\ge x\n" + INVALID[label] + b"\\lx smuggled\n"
    assert "\n\\lx smuggled" in data.decode("utf-8", "ignore")


@pytest.mark.parametrize("errors", ["ignore", "replace", "surrogateescape"])
def test_errors_passed_to_a_reader_never_reach_the_decoder(pathsec_sandbox, errors):
    data = b"\\lx a\n\\ge x\n\xff\\lx smuggled\n"
    path = plant(pathsec_sandbox.root, "e.db", data)
    reader = ToolboxCorpusReader(str(pathsec_sandbox.root), ["e.db"])
    with pytest.raises(UnicodeDecodeError):
        reader.fields("e.db", errors=errors)
    with pytest.raises(UnicodeDecodeError):
        tb.ToolboxSettings(path, "utf-8").parse(errors=errors)


@pytest.mark.parametrize("label", sorted(INVALID))
def test_invalid_bytes_at_the_end_smuggle_nothing(pathsec_sandbox, label):
    """Pinned: by filename open() refuses them; a PathPointer's reader drops
    undecodable bytes at the very end of a file. Neither adds a field."""
    data = b"\\lx a\n\\ge x" + INVALID[label]
    routes = by_route(pathsec_sandbox.root, "t.db", data, "utf-8")
    assert routes["filename"] == "UnicodeDecodeError"
    for route in ("pointer", "zip", "corpus reader"):
        assert routes[route] in ([("lx", "a"), ("ge", "x")], "UnicodeDecodeError")


ENCODINGS = ["utf-8", "utf-8-sig", "cp1252", "latin-1", "utf-16", "gbk", "mac-roman"]
SEPARATORS = {
    "VT": chr(0x0B),
    "FF": chr(0x0C),
    "FS": chr(0x1C),
    "GS": chr(0x1D),
    "RS": chr(0x1E),
    "NEL": chr(0x85),
    "LS": chr(0x2028),
    "PS": chr(0x2029),
}
SHAPES = {
    "NUL in a value": (
        "\\lx a%sb\n\\ge c\n" % chr(0),
        [("lx", "a%sb" % chr(0)), ("ge", "c")],
    ),
    "NUL in a marker": (
        "\\l%sx a\n\\ge c\n" % chr(0),
        [("l%sx" % chr(0), "a"), ("ge", "c")],
    ),
    "NUL before a marker": (
        "\\lx a\n%s\\lx smuggled\n" % chr(0),
        [("lx", "a\n%s\\lx smuggled" % chr(0))],
    ),
    "CRLF, CR and LF mixed": (
        "\\lx a\r\nmore\r\\ge b\n\\gp c\r\n",
        [("lx", "a\nmore"), ("ge", "b"), ("gp", "c")],
    ),
}
for _label, _sep in SEPARATORS.items():
    SHAPES["%s before a marker" % _label] = (
        "\\lx a\n\\ge gloss%s\\lx smuggled\n" % _sep,
        [("lx", "a"), ("ge", "gloss%s\\lx smuggled" % _sep)],
    )


@pytest.mark.parametrize("shape", sorted(SHAPES))
@pytest.mark.parametrize("encoding", ENCODINGS)
def test_every_shape_reads_alike_on_every_route_and_encoding(
    pathsec_sandbox, encoding, shape
):
    text, expected = SHAPES[shape]
    try:
        data = text.encode(encoding)
    except UnicodeEncodeError:
        pytest.skip("%s cannot encode it" % encoding)
    for route, got in by_route(pathsec_sandbox.root, "s.db", data, encoding).items():
        assert got == expected, (route, got)


@pytest.mark.parametrize("label", sorted(SEPARATORS))
@pytest.mark.parametrize("encoding", ["utf-8", "utf-16", "gbk"])
def test_separator_teeth(pathsec_sandbox, monkeypatch, encoding, label):
    """develop's line iteration splits the PathPointer route there."""
    text = "\\lx a\n\\ge gloss%s\\lx smuggled\n" % SEPARATORS[label]
    try:
        data = text.encode(encoding)
    except UnicodeEncodeError:
        pytest.skip("%s cannot encode it" % encoding)
    develop_reading(monkeypatch)
    pointer = FileSystemPathPointer(plant(pathsec_sandbox.root, "t.db", data))
    sf = tb.StandardFormat(pointer, encoding)
    assert [m for m, _ in sf.fields(unwrap=False)] == ["lx", "ge", "lx"]


@pytest.mark.parametrize("route", ["filename", "pointer"])
def test_a_long_line_is_one_field_on_both_file_routes(pathsec_sandbox, route):
    size = 16 * 2**20
    data = b"\\lx " + b"a" * size + b"\r\n\\ge end\n"
    path = plant(pathsec_sandbox.root, "long.db", data)
    src = path if route == "filename" else FileSystemPathPointer(path)
    got = list(tb.StandardFormat(src, "utf-8").fields())
    assert [m for m, _ in got] == ["lx", "ge"] and len(got[0][1]) == size


# 5. The shipped corpus in every encoding; findall; ToolboxSettings.


REAL = {
    "rotokas.dic": ("utf8", "lx"),
    "iu_mien_samp.db": ("utf8", "lx"),
    "test.dic": ("utf8", None),
    "MDF/MDF_AltH.db": ("cp1252", "lx"),
    "MDF/MDFSampl.db": ("cp1252", "lx"),
    "rotokas/river.txt": ("utf8", "ref"),
    "MDF/MDF_AltH.typ": ("cp1252", "settings"),
    "MDF/MDF.typ": ("cp1252", "settings"),
    "MDF/English.lng": ("cp1252", "settings"),
}
RECODED = {
    "utf-8": ("utf-8", lambda t: t.encode("utf-8")),
    "utf-8 with a BOM": ("utf-8", lambda t: codecs.BOM_UTF8 + t.encode("utf-8")),
    "utf-8-sig": ("utf-8-sig", lambda t: t.encode("utf-8-sig")),
    "cp1252": ("cp1252", lambda t: t.encode("cp1252")),
    "latin-1": ("latin-1", lambda t: t.encode("latin-1")),
    "utf-16 LE BOM": ("utf-16", lambda t: codecs.BOM_UTF16_LE + t.encode("utf-16-le")),
    "utf-16 BE BOM": ("utf-16", lambda t: codecs.BOM_UTF16_BE + t.encode("utf-16-be")),
    "gbk": ("gbk", lambda t: t.encode("gbk")),
    "mac-roman": ("mac-roman", lambda t: t.encode("mac-roman")),
}


@pytest.fixture(scope="module")
def real_corpus():
    """The shipped files and their fields read by filename, taken before a
    test's sandbox narrows pathsec to its own root."""
    found = {}
    for rel, (native, _) in REAL.items():
        try:
            path = str(nltk.data.find("corpora/toolbox/" + rel))
        except LookupError:
            continue
        with open(path, "rb") as handle:
            raw = handle.read()
        found[rel] = (raw, list(tb.StandardFormat(path, native).fields(unwrap=False)))
    return found


@pytest.mark.parametrize("target", sorted(RECODED))
@pytest.mark.parametrize("rel", sorted(REAL))
def test_the_real_corpus_recoded_reads_alike_and_writes_back(
    real_corpus, pathsec_sandbox, rel, target
):
    if rel not in real_corpus:
        pytest.skip("the toolbox corpus is not installed")
    raw, expected = real_corpus[rel]
    native, key = REAL[rel]
    encoding, encode = RECODED[target]
    try:
        data = encode(raw.decode(native))
    except UnicodeEncodeError:
        pytest.skip(f"{target} cannot encode {rel}")
    for route, got in by_route(pathsec_sandbox.root, "r.db", data, encoding).items():
        assert got == expected, route
    planted = os.path.join(str(pathsec_sandbox.root), "r.db")
    if key == "settings":
        tree = tb.ToolboxSettings(planted, encoding).parse(unwrap=False)
        back = tb.ToolboxSettings()
        back.open_string(tb.to_settings_string(ElementTree(tree)))
        assert tostring(back.parse(unwrap=False)) == tostring(tree)
        return
    tree = tb.ToolboxData(planted, encoding).parse(key=key)
    out = plant(
        pathsec_sandbox.root, "out.db", tb.to_sfm_string(tree, encoding=encoding)
    )
    for src in (out, FileSystemPathPointer(out)):
        assert tostring(tb.ToolboxData(src, encoding).parse(key=key)) == tostring(tree)


ELEMENT_PATHS = ["record", "header", "toolbox_data", "*", ".//record", "record[1]"]
ELEMENT_PATHS += ["{ns}record", "..", "record/lx"]


@pytest.mark.parametrize("marker", ELEMENT_PATHS)
def test_a_marker_spelled_as_an_element_path_adds_no_record(marker):
    """``db.findall("record")`` reads the tree ToolboxData builds, whose top
    level holds only header and record; a marker never becomes a path."""
    text = "\\_sh head\n\\lx a\n\\%s x\n\\lx b\n" % marker
    td = tb.ToolboxData()
    td.open_string(text)
    db = td.parse(key="lx")
    assert [child.tag for child in db] == ["header", "record", "record"]
    td = tb.ToolboxData()
    td.open_string(text)
    chunked = td.parse(grammar="g: {<lx>}", key="lx")
    assert len(chunked.findall("record")) == 2


def test_toolbox_settings_keeps_its_no_argument_call(pathsec_sandbox):
    path = plant(
        pathsec_sandbox.root, "s.typ", "\\+set\n\\a \u00e9\n\\-set\n".encode("cp1252")
    )
    ts = tb.ToolboxSettings()
    ts.open_string("\\+set\n\\a b\n\\-set\n")
    assert tostring(ts.parse(unwrap=False)) == b"<set><a>b</a></set>"
    ts = tb.ToolboxSettings()
    ts._encoding = "cp1252"
    ts.open(path)
    assert tostring(ts.parse(unwrap=False)) == b"<set><a>&#233;</a></set>"


@pytest.mark.parametrize("by_keyword", [False, True])
def test_toolbox_settings_opens_a_filename_through_pathsec(
    pathsec_sandbox, monkeypatch, by_keyword
):
    path = plant(
        pathsec_sandbox.root, "s.typ", "\\+set\n\\a \u00e9\n\\-set\n".encode("cp1252")
    )
    calls = []
    real = tb.pathsec_open

    def spy(file, *args, **kwargs):
        calls.append((file, kwargs.get("encoding"), kwargs.get("context")))
        return real(file, *args, **kwargs)

    monkeypatch.setattr(tb, "pathsec_open", spy)
    if by_keyword:
        ts = tb.ToolboxSettings(filename=path, encoding="cp1252")
    else:
        ts = tb.ToolboxSettings(path, "cp1252")
    assert calls == [(path, "cp1252", "toolbox.StandardFormat")]
    assert tostring(ts.parse(unwrap=False)) == b"<set><a>&#233;</a></set>"


def test_toolbox_settings_constructor_teeth(monkeypatch):
    """develop's constructor took no argument, so demo() could not give the
    settings file its encoding."""
    assert "__init__" in vars(tb.ToolboxSettings)

    def develop_init(self):
        super(tb.ToolboxSettings, self).__init__()

    monkeypatch.setattr(tb.ToolboxSettings, "__init__", develop_init)
    with pytest.raises(TypeError):
        tb.ToolboxSettings("MDF_AltH.typ", "cp1252")
