# Natural Language Toolkit: capped-read memory tests
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""A capped read must cost the bytes read, not the cap, and read the same.

``safe_json_load`` reads at most ``JSON_MAX_BYTES + 1`` bytes, and
``SeekableUnicodeStreamReader.read(n)`` reads ``n`` bytes of its stream. A
buffered stream allocates the whole request before it reads, so each model
file loaded reserved 200 MiB (a perceptron tagger load peaked at 227 MiB of
traced memory against 34.5 MiB for the same files through ``json.load``).
Large requests are now asked in 1 MiB steps. These tests pin that the steps
return the same bytes and leave the stream where one read would, that the
caps refuse exactly what they refused, and that the peak no longer follows
the cap.
"""

import io
import json
import tracemalloc

import pytest

import nltk.jsontags as jsontags
from nltk.data import SeekableUnicodeStreamReader
from nltk.jsontags import (
    JSON_MAX_BYTES,
    JSON_MAX_DEPTH,
    JSONTaggedDecoder,
    safe_json_load,
    safe_json_loads,
)


def _streams(data):
    yield "BytesIO", io.BytesIO(data)
    yield "BufferedReader", io.BufferedReader(io.BytesIO(data), buffer_size=7)
    yield "TextIOWrapper", io.TextIOWrapper(io.BytesIO(data), encoding="utf-8")


@pytest.mark.parametrize("step", [1, 3, 1 << 20])
def test_capped_json_read_refuses_and_reads_exactly_as_one_read(step, monkeypatch):
    """With a cap of 10 bytes, every document from 0 to 25 bytes, from every
    stream kind, is refused exactly when it is over 10 bytes and otherwise
    decided as ``json.loads`` decides it, and the stream is left where one
    read of cap + 1 bytes leaves it."""
    monkeypatch.setattr(jsontags, "_READ_STEP", step)
    for n in range(26):
        data = b" " * max(0, n - 1) + (b"1" if n else b"")
        for name, stream in _streams(data):
            raw = getattr(stream, "buffer", stream)
            if n > 10:
                with pytest.raises(ValueError, match="exceeds the 10-byte limit"):
                    safe_json_load(stream, max_bytes=10)
            elif n == 0:
                with pytest.raises(json.JSONDecodeError):
                    safe_json_load(stream, max_bytes=10)
            else:
                assert safe_json_load(stream, max_bytes=10) == 1, (name, n)
            assert raw.tell() == min(n, 11), (name, n)


_TEXTS = {
    "utf-8": "plain, " + "\u00e9t\u00e9 " * 40 + "\u65e5\u672c\u8a9e " * 30,
    "utf-16": "plain, " + "\u00e9t\u00e9 " * 40 + "\u65e5\u672c\u8a9e " * 30,
    "shift_jis": "plain, " + "\u65e5\u672c\u8a9e " * 60,
    "iso2022_jp": "plain, " + "\u65e5\u672c\u8a9e abc " * 60,
    "latin-1": "plain, " + "\u00e9t\u00e9 " * 80,
}


@pytest.mark.parametrize("step", [1, 2, 5, 1 << 20])
@pytest.mark.parametrize("encoding", sorted(_TEXTS))
def test_seekable_reader_reads_the_same_in_steps(step, encoding, monkeypatch):
    """A read of a SeekableUnicodeStreamReader returns the same text, and the
    same tell(), in steps as in one read, for multi-byte and stateful (shift
    sequence) encodings, since the bytes are joined before they are decoded."""
    data = _TEXTS[encoding].encode(encoding)

    def read_twice(size):
        reader = SeekableUnicodeStreamReader(io.BytesIO(data), encoding)
        return [reader.read(size), reader.tell(), reader.read(size), reader.tell()]

    for size in (len(data) // 3, len(data) // 2, len(data), len(data) + 3, 10**8):
        monkeypatch.setattr(jsontags, "_READ_STEP", 10**10)  # one read
        want = read_twice(size)
        monkeypatch.setattr(jsontags, "_READ_STEP", step)
        assert read_twice(size) == want, size
    assert "".join(read_twice(len(data))[0::2]) == _TEXTS[encoding]


def _peak_of(fn):
    tracemalloc.start()
    try:
        fn()
        return tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()


def test_a_small_json_file_no_longer_reserves_the_cap():
    """A 1 KB document read from a buffered stream, directly and through a
    SeekableUnicodeStreamReader, peaks far below the 200 MiB cap."""
    doc = json.dumps({"w%d" % i: i / 7 for i in range(40)}).encode("utf-8")
    assert JSON_MAX_BYTES >= 100 * 2**20
    direct = _peak_of(lambda: safe_json_load(io.BufferedReader(io.BytesIO(doc))))
    decoded = _peak_of(
        lambda: safe_json_load(
            SeekableUnicodeStreamReader(io.BufferedReader(io.BytesIO(doc)), "utf-8")
        )
    )
    assert direct < 4 * 2**20, direct
    assert decoded < 4 * 2**20, decoded


@pytest.mark.parametrize(
    "encoding, char",
    [
        ("utf-16-le", "中"),
        ("utf-16-be", "中"),
        ("utf-16-le", "\U0001f600"),
        ("utf-32-le", "\U0001f600"),
    ],
)
def test_depth_scan_of_utf16_and_utf32_costs_less_than_the_document(encoding, char):
    """The depth scan decodes UTF-16 and UTF-32 as the parser will, in steps,
    keeping only their ASCII characters, so an 8 MiB document peaks below its
    own size; decoding it whole and encoding it again as UTF-8 peaked at two
    to three times it, all before the scan could refuse anything."""
    doc = ('["' + char * (8 * 2**20 // len(char.encode(encoding))) + '"]').encode(
        encoding
    )
    peak = _peak_of(lambda: jsontags._scan_json_depth(doc, JSON_MAX_DEPTH))
    assert peak < len(doc), (peak, len(doc))
    assert jsontags._scan_json_depth(doc, JSON_MAX_DEPTH) == 1


def _refusal(data):
    with pytest.raises(ValueError, match="nesting depth exceeds"):
        safe_json_loads(data)


@pytest.mark.parametrize("deep_at", ["start", "end"])
@pytest.mark.parametrize(
    "form", ["bytes", "bytearray", "str", "utf-16-le", "utf-32-le"]
)
def test_depth_scan_costs_a_few_steps_whatever_the_form(form, deep_at, monkeypatch):
    """The scan reads the text in steps and resolves escapes within each, so a
    4 MiB document with escapes throughout, too deep near its start or its end,
    is refused at a peak of a few steps in every form. Encoding a str whole and
    resolving the escapes of the whole text copied it once or twice before the
    scan could refuse anything."""
    monkeypatch.setattr(jsontags, "_READ_STEP", 1 << 16)
    unit = 'a\\"b\\\\c'
    pad = '"' + unit * (4 * 2**20 // len(unit)) + '"'
    deep = "[" * (JSON_MAX_DEPTH + 1) + "]" * (JSON_MAX_DEPTH + 1)
    doc = "[" + (deep + ", " + pad if deep_at == "start" else pad + ", " + deep) + "]"
    data = {
        "bytes": doc.encode("utf-8"),
        "bytearray": bytearray(doc.encode("utf-8")),
        "str": doc,
        "utf-16-le": doc.encode("utf-16-le"),
        "utf-32-le": doc.encode("utf-32-le"),
    }[form]
    scan = _peak_of(lambda: jsontags._scan_json_depth(data, JSON_MAX_DEPTH))
    refusal = _peak_of(lambda: _refusal(data))
    assert scan < 2**20 and refusal < 2**20, (scan, refusal, len(data))


@pytest.mark.parametrize("step", [1, 2, 3, 1 << 20])
def test_byte_cap_counts_every_utf8_byte_in_steps(step, monkeypatch):
    """The UTF-8 size of a str is counted a step at a time. With characters of
    every width split between steps, a document exactly at the cap loads and
    one byte over is refused with its exact size, through both chokepoints."""
    monkeypatch.setattr(jsontags, "_READ_STEP", step)
    doc = '["a", "é", "中", "\U0001f600", "\ud800", {"k": "\\u0041"}]'
    size = len(doc.encode("utf-8", "surrogatepass"))
    over = f"{size} bytes, over the {size - 1}-byte limit"
    encoded = doc.encode("utf-8", "surrogatepass")
    for data in (doc, encoded, bytearray(encoded)):
        assert safe_json_loads(data, max_bytes=size) == json.loads(doc)
        with pytest.raises(ValueError, match=over):
            safe_json_loads(data, max_bytes=size - 1)
    monkeypatch.setattr(JSONTaggedDecoder, "MAX_DECODE_BYTES", size)
    assert json.loads(doc, cls=JSONTaggedDecoder) == json.loads(doc)
    monkeypatch.setattr(JSONTaggedDecoder, "MAX_DECODE_BYTES", size - 1)
    with pytest.raises(ValueError, match=over):
        json.loads(doc, cls=JSONTaggedDecoder)
