import os
from io import BytesIO

import pytest

from nltk.corpus.reader import SeekableUnicodeStreamReader


def check_reader(unicode_string, encoding):
    bytestr = unicode_string.encode(encoding)
    stream = BytesIO(bytestr)
    reader = SeekableUnicodeStreamReader(stream, encoding)

    # Should open at the start of the file
    assert reader.tell() == 0

    # Compare original string to contents from `.readlines()`
    assert unicode_string == "".join(reader.readlines())

    # Should be at the end of the file now
    stream.seek(0, os.SEEK_END)
    assert reader.tell() == stream.tell()

    reader.seek(0)  # go back to start

    # Compare original string to contents from `.read()`
    contents = ""
    char = None
    while char != "":
        char = reader.read(1)
        contents += char
    assert unicode_string == contents


# Call `check_reader` with a variety of input strings and encodings.
ENCODINGS = ["ascii", "latin1", "greek", "hebrew", "utf-16", "utf-8"]

STRINGS = [
    """
    This is a test file.
    It is fairly short.
    """,
    "This file can be encoded with latin1. \x83",
    """\
    This is a test file.
    Here's a blank line:

    And here's some unicode: \xee \u0123 \uffe3
    """,
    """\
    This is a test file.
    Unicode characters: \xf3 \u2222 \u3333\u4444 \u5555
    """,
    """\
    This is a larger file.  It has some lines that are longer \
    than 72 characters.  It's got lots of repetition.  Here's \
    some unicode chars: \xee \u0123 \uffe3 \ueeee \u2345

    How fun!  Let's repeat it twenty times.
    """
    * 20,
]


@pytest.mark.parametrize("string", STRINGS)
def test_reader(string):
    for encoding in ENCODINGS:
        # skip strings that can't be encoded with the current encoding
        try:
            string.encode(encoding)
        except UnicodeEncodeError:
            continue
        check_reader(string, encoding)


def test_reader_stream_closes_when_deleted():
    reader = SeekableUnicodeStreamReader(BytesIO(b""), "ascii")
    assert not reader.stream.closed
    reader.__del__()
    assert reader.stream.closed


def teardown_module(module=None):
    import gc

    gc.collect()


# Every PathPointer decodes through this reader, so it applies the test open()
# applies to a codec, and decodes a BOM-marked file in the order the BOM names.

import bz2  # noqa: E402
import codecs  # noqa: E402
import zlib  # noqa: E402

from nltk.data import FileSystemPathPointer, text_encoding  # noqa: E402


@pytest.mark.parametrize("codec", ["bz2_codec", "zlib_codec", "base64_codec", "rot_13"])
def test_a_codec_that_is_no_text_encoding_is_refused_before_a_byte_is_read(codec):
    with pytest.raises(LookupError, match="not a text encoding"):
        text_encoding(codec)

    class Counting(BytesIO):
        reads = 0

        def read(self, *args):
            self.reads += 1
            return super().read(*args)

    stream = Counting(b"x")
    with pytest.raises(LookupError, match="not a text encoding"):
        SeekableUnicodeStreamReader(stream, codec)
    assert stream.reads == 0  # refused before the BOM probe, the first read


@pytest.mark.parametrize("codec", ["bz2_codec", "zlib_codec"])
def test_teeth_the_reader_expands_a_bomb_without_the_check(monkeypatch, codec):
    import nltk.data

    raw = b"a" * 1_000_000
    data = (bz2 if codec == "bz2_codec" else zlib).compress(raw, 9)
    assert len(data) * 500 < len(raw)
    monkeypatch.setattr(nltk.data, "text_encoding", lambda encoding: encoding)
    assert SeekableUnicodeStreamReader(BytesIO(data), codec).read() == raw


@pytest.mark.parametrize(
    "encoding, bom, order",
    [
        ("utf-16", codecs.BOM_UTF16_BE, "utf-16-be"),
        ("utf-16", codecs.BOM_UTF16_LE, "utf-16-le"),
        ("UTF 16", codecs.BOM_UTF16_BE, "utf-16-be"),
        ("utf-32", codecs.BOM_UTF32_BE, "utf-32-be"),
        ("utf-32", codecs.BOM_UTF32_LE, "utf-32-le"),
    ],
)
def test_a_bom_names_the_byte_order_the_reader_decodes_with(encoding, bom, order):
    text = "abc\nd\u00e9f\n" * 3
    data = bom + text.encode(order)
    reader = SeekableUnicodeStreamReader(BytesIO(data), encoding)
    assert reader.encoding == order
    assert reader.read() == text
    reader.seek(0)
    assert "".join(reader.readlines()) == text
    assert SeekableUnicodeStreamReader(BytesIO(data), encoding).readline() == "abc\n"


def test_teeth_without_the_repick_a_big_endian_file_reads_as_other_characters(
    monkeypatch,
):
    real = SeekableUnicodeStreamReader._check_bom

    def develop_check_bom(self):
        encoding = self.encoding
        length = real(self)
        self.encoding = encoding  # develop kept the generic decoder
        return length

    monkeypatch.setattr(SeekableUnicodeStreamReader, "_check_bom", develop_check_bom)
    data = codecs.BOM_UTF16_BE + "abc\n".encode("utf-16-be")
    try:
        got = SeekableUnicodeStreamReader(BytesIO(data), "utf-16").read()
    except UnicodeError:  # the generic decoder never sees the BOM (3.11: UnicodeError)
        got = None
    assert got != "abc\n"


def test_text_encoding_maps_none_to_the_platform_default():
    import locale

    assert text_encoding(None) == locale.getpreferredencoding(False)
    assert text_encoding("utf-8") == "utf-8"
    with pytest.raises(LookupError):
        text_encoding("no-such-codec")


def test_a_path_pointer_refuses_a_bomb_codec_and_reads_big_endian(pathsec_sandbox):
    root = pathsec_sandbox.root
    path = root / "be.txt"
    with open(
        path, "wb"
    ) as handle:  # sandboxed-open ok: fixture under the sandbox root
        handle.write(codecs.BOM_UTF16_BE + "abc\n".encode("utf-16-be"))
    path.chmod(0o600)
    assert FileSystemPathPointer(str(path)).open("utf-16").read() == "abc\n"
    with pytest.raises(LookupError, match="not a text encoding"):
        FileSystemPathPointer(str(path)).open("bz2_codec")


# The sequential reads carry the decoder's state from block to block, and
# every position tell() hands out can be decoded from after a seek.

STATEFUL_TEXT = "\u65e5\u672c\u8a9e\u306e\u884c %d\n"


def _every_shape(encoding, data, text):
    """readline with several size patterns, a seek back to every position,
    sized reads, and char_seek_forward, all against ``text``."""
    for sizes in ((None,), (1,), (3,), (7, None, 2)):
        reader = SeekableUnicodeStreamReader(BytesIO(data), encoding)
        lines, positions, i = [], [], 0
        while True:
            position = reader.tell()
            line = reader.readline(sizes[i % len(sizes)])
            i += 1
            if not line:
                break
            lines.append(line)
            positions.append(position)
        assert "".join(lines) == text, (encoding, sizes)
        for j, position in enumerate(positions):
            reader.seek(position)
            assert reader.read() == "".join(lines[j:]), (encoding, sizes, j)
    reader.seek(0)
    out = ""
    while True:
        chunk = reader.read(3)
        if not chunk:
            break
        out += chunk
    assert out == text
    reader.seek(0)
    reader.char_seek_forward(8 * 7)
    assert reader.readline() == STATEFUL_TEXT % 7
    return reader


@pytest.mark.parametrize("encoding", ["iso2022_jp", "iso2022_kr", "utf-7", "cp932"])
def test_a_stateful_codec_reads_the_same_in_blocks_as_whole(encoding):
    text = "".join(STATEFUL_TEXT % n for n in range(60))
    reader = _every_shape(encoding, text.encode(encoding), text)
    assert reader.read() == "".join(STATEFUL_TEXT % n for n in range(8, 60))


def test_only_a_position_inside_a_shifted_run_is_remembered():
    text = "".join(STATEFUL_TEXT % n for n in range(60))
    reader = _every_shape("utf-8", text.encode("utf-8"), text)
    assert reader._seek_states == {}
    reader = _every_shape("iso2022_jp", text.encode("iso2022_jp"), text)
    assert reader._seek_states  # readline(1) stopped inside the runs


@pytest.mark.parametrize("encoding", ["utf_16", "utf_32", "utf_8_sig"])
@pytest.mark.parametrize("order", ["le", "be"])
def test_a_bom_the_codec_reads_itself_holds_across_a_seek(encoding, order):
    # under this spelling the codec, not the reader, reads the BOM
    text = "".join(STATEFUL_TEXT % n for n in range(60))
    if encoding == "utf_8_sig":
        if order == "be":
            pytest.skip("no byte order")
        data = text.encode("utf-8-sig")
    else:
        width = encoding[-2:]
        bom = getattr(codecs, f"BOM_UTF{width}_{order.upper()}")
        data = bom + text.encode(f"utf-{width}-{order}")
    reader = SeekableUnicodeStreamReader(BytesIO(data), encoding)
    assert reader._bom is None
    assert reader.read() == text
    _every_shape(encoding, data, text)


def test_teeth_a_stateless_decode_per_block_loses_the_shift_state(monkeypatch):
    text = "".join(STATEFUL_TEXT % n for n in range(60))
    data = text.encode("iso2022_jp")

    def stateless_read(self, size=None):
        if size == 0:
            return ""
        new_bytes = self.stream.read() if size is None else self.stream.read(size)
        block = self.bytebuffer + new_bytes
        chars, consumed = self._incr_decode(block)
        self.bytebuffer = block[consumed:]
        return chars

    monkeypatch.setattr(SeekableUnicodeStreamReader, "_read", stateless_read)
    reader = SeekableUnicodeStreamReader(BytesIO(data), "iso2022_jp")
    assert "".join(iter(reader.readline, "")) != text


def test_a_character_cut_short_at_the_end_is_an_error_as_in_open():
    data = "abc\u00e9".encode()[:-1]
    reader = SeekableUnicodeStreamReader(BytesIO(data), "utf-8")
    with pytest.raises(UnicodeDecodeError):
        reader.read()
    reader = SeekableUnicodeStreamReader(BytesIO(data), "utf-8", errors="replace")
    assert reader.read() == "abc\ufffd"
