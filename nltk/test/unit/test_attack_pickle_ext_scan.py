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
    """The bypass itself. CPython 3.10 to 3.13 read an INT line in base 0, so
    their C unpickler takes ``I0x1`` as 1 and runs the EXT opcode after it,
    where genops gave up; 3.14 reads it in base 10 and refuses the line. Each
    interpreter is held to what it does, and both NLTK loaders refuse the
    pickle before it runs either way."""
    payload = b"I0x1\n" + _ext_tail()
    try:
        base0 = pickle.loads(b"I0x1\n.")
    except ValueError:  # UnpicklingError is a ValueError subclass too
        base0 = None
    if base0 == 1:
        assert pickle.loads(payload) is _Marker
    else:
        assert base0 is None
        with pytest.raises(ValueError):
            pickle.loads(payload)
    with pytest.raises(pickle.UnpicklingError, match="EXT1"):
        RestrictedUnpickler(io.BytesIO(payload)).load()
    with pytest.raises(pickle.UnpicklingError, match="EXT1"):
        allowlisted_pickle_load(
            io.BytesIO(payload), allowed_globals={("builtins", "int")}
        )


@pytest.mark.parametrize(
    "payload",
    [pytest.param(p, id=f"crafted{i}") for i, p in enumerate(_crafted_payloads())],
)
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


# Opcodes whose argument crosses the end of their frame, then an EXT opcode;
# "hidden" runs EXT1 where BININT's argument is read from after the frame,
# while read in order that EXT1 is a SHORT_BINSTRING's payload.
_STRADDLING = {
    "line": b"\x80\x04" + _frame(b"I1") + b"2\n" + _ext_tail(),
    "counted": b"\x80\x04" + _frame(b"\x8c\x03a") + b"bc" + _ext_tail(),
    "fixed": b"\x80\x04" + _frame(b"J\x01\x02") + b"\x03\x04" + _ext_tail(),
    "nested": b"\x80\x04" + _frame(b"K\x01" + _frame(b"0")) + _ext_tail()[1:],
    "hidden": b"\x80\x04"
    + _frame(b"J\x01\x02")
    + b"\x00\x00U\x03"
    + pickle.EXT1
    + bytes([_CODE])
    + b"..",
}


@pytest.mark.parametrize("name", sorted(_STRADDLING))
def test_argument_across_a_frame_end_cannot_hide_ext(name, warm_extension, monkeypatch):
    """Where an opcode crosses the end of its frame (or a frame opens inside
    one) the unpickler may read a different opcode stream, so an EXT opcode
    byte anywhere after that point is refused, by both loaders and by the
    in-memory and streamed scans, whatever this interpreter's unpickler does."""
    payload = _STRADDLING[name]
    with pytest.raises(pickle.UnpicklingError):
        RestrictedUnpickler(io.BytesIO(payload)).load()
    with pytest.raises(pickle.UnpicklingError):
        allowlisted_pickle_load(
            io.BytesIO(payload), allowed_globals={("builtins", "int")}
        )
    for chunk in (1, 3, 1 << 20):
        monkeypatch.setattr(picklesec, "_SCAN_CHUNK", chunk)
        with pytest.raises(pickle.UnpicklingError):
            _reject_extension_opcodes(io.BufferedReader(io.BytesIO(payload)))


def _file_unpickler_outcome(payload):
    try:
        return pickle.Unpickler(io.BytesIO(payload)).load()
    except Exception as exc:
        return exc


def test_hidden_ext_runs_exactly_where_the_unpickler_drops_the_frame():
    """Read in order the "hidden" payload holds no EXT opcode. This
    interpreter's file-backed unpickler is first classified on a probe with
    no EXT byte: it reads straight on across the frame's end (5), reads the
    argument from after the frame (BININT 03 04 4B 05), or refuses the
    crossing. The hidden payload then does exactly what that predicts: a
    SHORT_BINSTRING it cannot decode, the registered global, or a refusal."""
    payload = _STRADDLING["hidden"]
    ops = [op.name for op, _arg, _pos in pickletools.genops(payload)]
    assert "EXT1" not in ops and "SHORT_BINSTRING" in ops
    probe = b"\x80\x04" + _frame(b"J\x01\x02") + b"\x03\x04K\x05."
    reads = _file_unpickler_outcome(probe)
    copyreg.add_extension(__name__, "_Marker", _CODE)
    try:
        pickle.loads(pickle.EXT1 + bytes([_CODE]) + pickle.STOP)
        outcome = _file_unpickler_outcome(payload)
    finally:
        copyreg.remove_extension(__name__, "_Marker", _CODE)
        copyreg._extension_cache.pop(_CODE, None)
    if reads == 5:  # in order: the EXT1 byte is string payload
        assert isinstance(outcome, UnicodeDecodeError), outcome
    elif reads == int.from_bytes(b"\x03\x04K\x05", "little", signed=True):
        assert outcome is _Marker, outcome  # the bypass the frame rule closes
    else:
        assert isinstance(reads, pickle.UnpicklingError), reads
        assert isinstance(outcome, pickle.UnpicklingError), outcome


@pytest.mark.parametrize(
    "payload",
    [
        b"\x80\x04" + _frame(b"J\x01\x02") + b"\x03\x04K\x05.",
        b"\x80\x04" + _frame(b"K\x82J\x01\x02") + b"\x03\x04K\x05.",
        b"\x80\x04" + _frame(b"K\x01" + _frame(b"0")) + b"K\x02.",
    ],
    ids=["no-ext-byte", "ext-byte-before", "nested-no-ext"],
)
def test_ambiguous_frame_with_no_ext_byte_after_passes_the_scan(payload, monkeypatch):
    """No byte at or after the ambiguous point can be an EXT opcode, so the
    scan passes the pickle, as the byte search already does for a pickle with
    no EXT value at all (whether the unpickler then loads it is its own call)."""
    _reject_extension_opcodes(payload)
    for chunk in (1, 3, 1 << 20):
        monkeypatch.setattr(picklesec, "_SCAN_CHUNK", chunk)
        _reject_extension_opcodes(io.BufferedReader(io.BytesIO(payload)))


def _sample_objects():
    """Real-shaped values that exercise every argument kind the protocols
    emit: small, medium and huge ints, floats, short and long str and bytes,
    non-ASCII text, bytearray, the containers, and booleans and None. Sets
    hold ints only, whose iteration order is the same in every process (a
    pytest-xdist worker collects the same ids as its peers)."""
    return [
        {"w": [1, 255, 256, 65535, 65536, -1, 2**31, 2**70, -(2**2000)]},
        [0.5, -1e300, 3.141592653589793, "", "x" * 300, "\u00e9\u4e2d\U0001f600"],
        (b"", b"\x82\x83\x84" * 90, bytes(range(256)), bytearray(b"\x82" * 3)),
        [{1, 2}, frozenset({3, 4}), (None, True, False)],
        {("w%d" % i, "NN"): i / 7 for i in range(40)},
    ]


def _real_pickles():
    for proto in range(pickle.HIGHEST_PROTOCOL + 1):
        for index, obj in enumerate(_sample_objects()):
            name = f"p{proto}-o{index}"
            yield pytest.param(name, pickle.dumps(obj, protocol=proto), id=name)


def _argument_bytes(data):
    """Offsets of the bytes inside arguments that framing never looks at: the
    payload of a counted argument, a fixed-size argument (a frame's length is
    framing itself), and a line's text."""
    ops = list(pickletools.genops(data))
    for (op, _arg, pos), nxt in zip(ops, [p for _o, _a, p in ops[1:]] + [len(data)]):
        if op.arg is None or op.name == "FRAME":
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
    obj = [1, 300, 70000, 2**70, 0.25, "ab", "\u00e9" * 3, b"\x82" * 4, (None, True)]
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
    """Each opcode of this interpreter's pickle protocols is framed by the
    tables built from pickletools, or is one the scan decides itself (STOP,
    FRAME and the three EXT opcodes); no byte that is no opcode is framed."""
    codes = {ord(op.code): op for op in pickletools.opcodes}
    for code, op in codes.items():
        framed = (
            picklesec._ADVANCE[code]
            or picklesec._LENGTH_PREFIX[code]
            or picklesec._LINES[code]
        )
        decided = op.name in ("STOP", "FRAME") or op.name.startswith("EXT")
        assert bool(framed) != decided, op.name
    for code in set(range(256)) - set(codes):
        assert not (
            picklesec._ADVANCE[code]
            or picklesec._LENGTH_PREFIX[code]
            or picklesec._LINES[code]
        ), code
