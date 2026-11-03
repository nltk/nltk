# Natural Language Toolkit: EXT-opcode pre-scan regression tests
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""The EXT-opcode pre-scan must frame a pickle exactly as the unpickler does.

``RestrictedUnpickler`` and ``AllowlistUnpickler`` refuse the EXT1/EXT2/EXT4
opcodes up front, because on a warm ``copyreg._extension_cache`` the C
unpickler resolves them without calling ``find_class``. The scan used to be
``pickletools.genops``, which validates argument CONTENT and gave up (treating
the pickle as clean) at the first argument it could not parse. The C unpickler
parses some of those arguments fine: ``I0x1`` is a base-0 integer to it and a
``ValueError`` to genops. So ``I0x1``, a POP and then EXT1 loaded the cached
global through ``RestrictedUnpickler``, which allows no global at all.

The scan now follows the framing only: every argument is stepped over by its
length, its length prefix or its newline, whatever its content, so it can never
stop before the unpickler does. These tests run the real loaders on crafted
payloads with a warm extension cache, check the framing against
``pickletools.genops`` at every opcode boundary and every argument byte of real
pickles (protocols 0 to 5), and repeat the streamed scan with chunk sizes that
cut every argument. No randomness: every payload is enumerated.
"""

import copyreg
import io
import pickle
import pickletools
import struct

import pytest

import nltk.picklesec as picklesec
from nltk.picklesec import (
    RestrictedUnpickler,
    _reject_extension_opcodes,
    allowlisted_pickle_load,
)

_CODE = 0x5E  # an extension code nothing else in the test run registers


class _Marker:
    """Stands in for the dangerous callable a library could have registered."""


@pytest.fixture
def warm_extension():
    """Register ``_Marker`` as extension ``_CODE`` and warm the C unpickler's
    cache with it, as a process that used the extension once would be."""
    copyreg.add_extension(__name__, "_Marker", _CODE)
    try:
        assert pickle.loads(pickle.EXT1 + bytes([_CODE]) + pickle.STOP) is _Marker
        assert copyreg._extension_cache.get(_CODE) is _Marker
        yield
    finally:
        copyreg.remove_extension(__name__, "_Marker", _CODE)
        copyreg._extension_cache.pop(_CODE, None)


def _ext_tail():
    return pickle.POP + pickle.EXT1 + bytes([_CODE]) + pickle.STOP


# Argument contents the C unpickler and pickletools may judge differently.
# Each line opcode is followed by POP, EXT1 and STOP, so a scan that stopped at
# the line would never see the EXT opcode.
_LINE_CONTENTS = (
    b"0x1",
    b"0o7",
    b"0b1",
    b" 1",
    b"1 ",
    b"1_0",
    b"+1",
    b"-0",
    b"",
    b"01",
    b"00",
    b"1L",
    b"0x10L",
    b"1e5",
    b"nan",
    b"inf",
    b"abc",
    b"'unterminated",
    b"'quoted'",
    b'"dq"',
    b"\xff\xfe",
    b"\\u0041",
    b"\x82\x01",
)
_LINE_OPCODES = (b"I", b"L", b"F", b"S", b"V", b"g", b"p", b"P")


def _crafted_payloads():
    for opcode in _LINE_OPCODES:
        for content in _LINE_CONTENTS:
            yield opcode + content + b"\n" + _ext_tail()
    for opcode in (b"c", b"i"):
        for first in (b"builtins", b"no such module", b"\xff"):
            for second in (b"int", b"", b"\xfe"):
                yield opcode + first + b"\n" + second + b"\n" + _ext_tail()


def test_base0_int_line_no_longer_hides_ext(warm_extension):
    """The bypass itself: the C unpickler runs the EXT opcode after ``I0x1``,
    and both NLTK loaders now refuse the pickle before it does."""
    payload = b"I0x1\n" + _ext_tail()
    assert pickle.loads(payload) is _Marker  # the C unpickler accepts the line
    with pytest.raises(pickle.UnpicklingError, match="EXT1"):
        RestrictedUnpickler(io.BytesIO(payload)).load()
    with pytest.raises(pickle.UnpicklingError, match="EXT1"):
        allowlisted_pickle_load(
            io.BytesIO(payload), allowed_globals={("builtins", "int")}
        )


@pytest.mark.parametrize("payload", list(_crafted_payloads()))
def test_scan_never_stops_on_argument_content(payload, warm_extension):
    """Whatever a line argument holds, the EXT opcode after it is refused, by
    both the in-memory and the streamed scan; this includes every content the
    C unpickler accepts and so would run the EXT opcode after."""
    with pytest.raises(pickle.UnpicklingError, match="EXT1"):
        _reject_extension_opcodes(payload)
    with pytest.raises(pickle.UnpicklingError, match="EXT1"):
        _reject_extension_opcodes(io.BufferedReader(io.BytesIO(payload)))
    with pytest.raises(pickle.UnpicklingError):
        RestrictedUnpickler(io.BytesIO(payload)).load()


def test_crafted_battery_holds_real_bypasses(warm_extension):
    """The battery is not vacuous: on this interpreter the C unpickler runs
    the EXT opcode after several of these lines."""
    ran = 0
    for payload in _crafted_payloads():
        try:
            ran += pickle.loads(payload) is _Marker
        except Exception:
            continue
    assert ran >= 3


def _frame(body):
    return pickle.FRAME + struct.pack("<Q", len(body)) + body


@pytest.mark.parametrize(
    "payload",
    [
        b"\x80\x04" + _frame(b"I1") + b"2\n" + _ext_tail(),
        b"\x80\x04" + _frame(b"\x8c\x03a") + b"bc" + _ext_tail(),
        b"\x80\x04" + _frame(b"K\x01") + _ext_tail(),
        b"\x80\x04" + _frame(b"K\x01" + _frame(b"0")) + _ext_tail()[1:],
        b"\x80\x04" + _frame(b"J\x01\x02") + b"\x03\x04" + _ext_tail(),
    ],
    ids=["line", "counted", "after", "nested", "fixed"],
)
def test_arguments_across_a_frame_boundary(payload, warm_extension):
    """The unpickler reads an argument straight across a frame's end, so the
    scan does too; each payload runs the EXT opcode in the C unpickler."""
    assert pickle.loads(payload) is _Marker
    assert pickle.Unpickler(io.BytesIO(payload)).load() is _Marker
    with pytest.raises(pickle.UnpicklingError, match="EXT1"):
        RestrictedUnpickler(io.BytesIO(payload)).load()


def _sample_objects():
    """Real-shaped values that exercise every argument kind the protocols
    emit: small, medium and huge ints, floats, short and long str and bytes,
    non-ASCII text, bytearray, the containers, and booleans and None."""
    return [
        {"w": [1, 255, 256, 65535, 65536, -1, 2**31, 2**70, -(2**2000)]},
        [0.5, -1e300, 3.141592653589793, "", "x" * 300, "é中\U0001f600"],
        (b"", b"\x82\x83\x84" * 90, bytes(range(256)), bytearray(b"\x82" * 3)),
        {frozenset({1, 2}), (None, True, False)},
        {("w%d" % i, "NN"): i / 7 for i in range(40)},
    ]


def _real_pickles():
    for proto in range(pickle.HIGHEST_PROTOCOL + 1):
        for index, obj in enumerate(_sample_objects()):
            yield f"p{proto}-o{index}", pickle.dumps(obj, protocol=proto)


def _argument_bytes(data):
    """Offsets of the bytes inside arguments that framing never looks at: the
    payload of a counted argument, a fixed-size argument, and a line's text."""
    ops = list(pickletools.genops(data))
    for (op, _arg, pos), nxt in zip(ops, [p for _o, _a, p in ops[1:]] + [len(data)]):
        if op.arg is None:
            continue
        n = op.arg.n
        if n >= 0:
            yield from range(pos + 1, pos + 1 + n)
        elif n == pickletools.UP_TO_NEWLINE:
            yield from (i for i in range(pos + 1, nxt) if data[i] != 0x0A)
        else:
            width = {-2: 1, -3: 4, -4: 4, -5: 8}[n]
            yield from range(pos + 1 + width, nxt)


def _check_framing(data, chunk, monkeypatch):
    boundaries = [pos for _op, _arg, pos in pickletools.genops(data)]
    inside = list(_argument_bytes(data))
    assert boundaries and (inside or len(data) < 8)
    if chunk is not None:
        monkeypatch.setattr(picklesec, "_SCAN_CHUNK", chunk)

    def scan(buf):
        if chunk is None:
            _reject_extension_opcodes(buf)
        else:
            _reject_extension_opcodes(io.BufferedReader(io.BytesIO(buf)))

    scan(data)
    for pos in boundaries:
        with pytest.raises(pickle.UnpicklingError):
            scan(data[:pos] + pickle.EXT1 + b"\x01" + data[pos:])
    for pos in inside:
        for ext in (0x82, 0x83, 0x84):
            scan(data[:pos] + bytes([ext]) + data[pos + 1 :])


@pytest.mark.parametrize("chunk", [None, 64])
@pytest.mark.parametrize("name,data", list(_real_pickles()))
def test_framing_matches_genops_everywhere(name, data, chunk, monkeypatch):
    """On real pickles the scan agrees with ``pickletools.genops`` at every
    position: an EXT opcode inserted at any opcode boundary is refused, and an
    EXT byte written over any argument byte is not mistaken for an opcode. The
    in-memory scan and a streamed scan in 64-byte chunks are both checked."""
    _check_framing(data, chunk, monkeypatch)


@pytest.mark.parametrize("chunk", [1, 2, 3])
@pytest.mark.parametrize("proto", [0, 2, 4, 5])
def test_framing_with_chunks_cutting_every_argument(proto, chunk, monkeypatch):
    """The streamed scan with chunks of one to three bytes, so every length
    prefix, fixed argument and line is split across reads."""
    obj = [1, 300, 70000, 2**70, 0.25, "ab", "é" * 3, b"\x82" * 4, (None, True)]
    _check_framing(pickle.dumps(obj, protocol=proto), chunk, monkeypatch)


@pytest.mark.parametrize("chunk", [1, 5, 1 << 20])
def test_long_arguments_are_skipped_not_read_whole(chunk, monkeypatch):
    """Counted arguments far longer than a chunk, full of EXT bytes, are
    skipped by their length; a line longer than many chunks is followed to its
    newline; the EXT opcode after each is still found."""
    monkeypatch.setattr(picklesec, "_SCAN_CHUNK", chunk)
    blob = b"\x82\x83\x84" * 5000
    clean = [
        b"\x80\x04\x8e" + struct.pack("<Q", len(blob)) + blob + b"0.",
        b"\x80\x04\x8d" + struct.pack("<Q", len(blob)) + blob + b"0.",
        b"B" + struct.pack("<I", len(blob)) + blob + b"0.",
        b"S'" + b"a" * 20000 + b"'\n0.",
    ]
    for data in clean:
        _reject_extension_opcodes(data)
        _reject_extension_opcodes(io.BytesIO(data))
        tainted = data[:-1] + pickle.EXT2 + b"\x01\x00."
        with pytest.raises(pickle.UnpicklingError, match="EXT2"):
            _reject_extension_opcodes(tainted)
        with pytest.raises(pickle.UnpicklingError, match="EXT2"):
            _reject_extension_opcodes(io.BytesIO(tainted))


def test_scan_ends_where_the_unpickler_does():
    """STOP ends the pickle and a byte that is no opcode ends the load, so an
    EXT byte after either is data the unpickler never runs."""
    for data in (b"K\x01." + pickle.EXT1 + b"\x01", b"\xff" + pickle.EXT1 + b"\x01"):
        _reject_extension_opcodes(data)
        _reject_extension_opcodes(io.BytesIO(data))


def test_every_opcode_has_a_framing():
    """Each opcode of this interpreter's pickle protocols is either framed or
    ends the scan, from the same table the unpickler documents."""
    for op in pickletools.opcodes:
        code = ord(op.code)
        framed = (
            picklesec._ADVANCE[code]
            or picklesec._LENGTH_PREFIX[code]
            or picklesec._LINES[code]
        )
        ends = op.name == "STOP" or op.name.startswith("EXT")
        assert bool(framed) != ends, op.name
    assert {op.code for op in pickletools.opcodes} >= {
        chr(c) for c in range(256) if picklesec._ADVANCE[c]
    }


def _outcome(scan, data):
    try:
        scan(data)
        return "clean"
    except pickle.UnpicklingError as exc:
        return str(exc)


def test_byte_search_decides_like_the_framing():
    """Bytes holding no EXT opcode value are passed without framing; every
    short input decides exactly as framing it would: all strings of up to two
    bytes, and three-byte strings over the bytes that matter."""
    full = picklesec._scan_opcodes
    inputs = [bytes([a]) for a in range(256)]
    inputs += [bytes([a, b]) for a in range(256) for b in range(256)]
    alphabet = b"\x82\x83\x84.\n\x00\x01IKUXc\x8c\x8e\x95\xff"
    inputs += [bytes([a, b, c]) for a in alphabet for b in alphabet for c in alphabet]
    for data in inputs:
        assert _outcome(_reject_extension_opcodes, data) == _outcome(
            lambda d: full(d, 0), data
        ), data


def test_bytesio_judged_in_place_from_its_position():
    """A plain BytesIO is judged from its current position, which is left
    where it was; bytes before the position are never read by the unpickler."""
    ext = pickle.EXT1 + b"\x01" + pickle.STOP
    stream = io.BytesIO(ext + b"K\x01.")
    stream.seek(len(ext))
    _reject_extension_opcodes(stream)
    assert stream.tell() == len(ext)
    assert RestrictedUnpickler(stream).load() == 1
    stream = io.BytesIO(b"K\x01" + ext)
    stream.seek(2)
    with pytest.raises(pickle.UnpicklingError, match="EXT1"):
        _reject_extension_opcodes(stream)
    assert stream.tell() == 2


def test_bytesio_subclass_is_read_not_trusted():
    """A BytesIO subclass can serve the unpickler other bytes than its buffer,
    so only an exact BytesIO is judged in place; a subclass is scanned through
    the read calls the unpickler itself makes."""

    class Lying(io.BytesIO):
        def read(self, size=-1):
            return io.BytesIO(pickle.EXT1 + b"\x01" + pickle.STOP).read(size)

        def readline(self, size=-1):
            return b""

    with pytest.raises(pickle.UnpicklingError, match="EXT1"):
        _reject_extension_opcodes(Lying(b"K\x01."))
