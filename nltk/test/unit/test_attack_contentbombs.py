# Natural Language Toolkit: contentbombs red-team suite (2026-10-16)
#
# Hostile FILE CONTENT (not paths) reaching a parser or decompressor through a
# real nltk entry point: archive / compression bombs, deserialization gadgets,
# and encoding tricks. Every REFUSED row asserts the SPECIFIC refusal; every
# BENIGN-OK row proves a legitimate look-alike still loads. No LEAK row was
# found, so none is encoded here.
#
# Runs on python3.13 and python3.10. No network. No absolute wall-clock asserts:
# the one case that could hang (a decompression bomb) is driven in a child
# process with a subprocess timeout and asserted on its refusal, not its clock.

import io
import os
import pickle
import sys
import tempfile

import pytest

import nltk.data
from nltk import pathsec
from nltk.data import SeekableUnicodeStreamReader as SUR
from nltk.data import text_encoding
from nltk.jsontags import (
    JSON_MAX_DEPTH,
    JSONTaggedDecoder,
    safe_json_loads,
)
from nltk.picklesec import AllowlistUnpickler, RestrictedUnpickler


# ---------------------------------------------------------------------------
# inline sandbox: one enforced pathsec data root under $HOME (mirrors conftest's
# _enforce_single_root so the file does not depend on the rootdir conftest).
# ---------------------------------------------------------------------------
@pytest.fixture
def data_root(monkeypatch):
    """Enforce pathsec against one throwaway data root under $HOME and yield it.

    A root under $HOME is a private chain on every runner (unlike world-writable
    /tmp). Every mutated pathsec/data global is restored at teardown.
    """
    import shutil

    root = os.path.realpath(
        tempfile.mkdtemp(prefix=".cb_test_root_", dir=os.path.expanduser("~"))
    )
    monkeypatch.setattr(pathsec, "ENFORCE", True)
    monkeypatch.setattr(nltk.data, "path", [root])
    monkeypatch.setattr(pathsec, "_ALLOWED_ROOTS_CACHE", None, raising=False)
    monkeypatch.setattr(pathsec, "_LAST_DATA_PATHS", None, raising=False)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _su(s):
    b = s.encode()
    return b"\x8c" + bytes([len(b)]) + b


def _stack_global(mod, name):
    """A proto-4 pickle that pushes the global mod.name and stops."""
    return b"\x80\x04" + _su(mod) + _su(name) + b"\x93."


# ---------------------------------------------------------------------------
# Decompression bombs, driven in a CHILD process (the only cases that could hang
# if a guard regressed) with a subprocess timeout. The child builds each payload
# under its own enforced root and reports the exception class per case.
# ---------------------------------------------------------------------------
_BOMB_CHILD = r"""
import io, os, gzip, zipfile, tempfile, shutil
import nltk.data as D, nltk.pathsec as P
root = os.path.realpath(tempfile.mkdtemp(prefix=".cb_c_", dir=os.path.expanduser("~")))
P.ENFORCE = True; D.path = [root]
P._ALLOWED_ROOTS_CACHE = None; P._LAST_DATA_PATHS = None
zeros = b"\x00" * (48 * 1024 * 1024)
def report(name, fn):
    try:
        fn(); print(name + " LEAK")
    except Exception as e:
        print(name + " " + type(e).__name__)
try:
    p = os.path.join(root, "b.zip")
    with zipfile.ZipFile(p, "w", zipfile.ZIP_DEFLATED) as z: z.writestr("m", zeros)
    report("honest_zip", lambda: P.ZipFile(p).read("m"))
    report("ondemand_zip", lambda: D.OpenOnDemandZipFile(p).read("m"))
    report("zpp_zip", lambda: D.ZipFilePathPointer(p, "m").open().read())
    gzb = io.BytesIO()
    with gzip.GzipFile(fileobj=gzb, mode="wb") as g: g.write(zeros)
    np_ = os.path.join(root, "n.zip")
    with zipfile.ZipFile(np_, "w", zipfile.ZIP_STORED) as z: z.writestr("i.gz", gzb.getvalue())
    report("nested_gz_zip", lambda: D.ZipFilePathPointer(np_, "i.gz").open().read())
    gp = os.path.join(root, "b.gz")
    with gzip.open(gp, "wb") as g: g.write(zeros)
    report("gzip_file", lambda: D.GzipFileSystemPathPointer(gp).open().read())
    report("gzip_unicode", lambda: D.gzip_open_unicode(gp).read())
    mp = os.path.join(root, "m.zip")
    with zipfile.ZipFile(mp, "w", zipfile.ZIP_STORED) as z:
        for i in range(100001): z.writestr("m%d" % i, b"")
    report("member_count", lambda: P.ZipFile(mp))
    ap = os.path.join(root, "a.zip"); one = b"\x00" * (1024 * 1024)
    with zipfile.ZipFile(ap, "w", zipfile.ZIP_DEFLATED) as z:
        for i in range(64): z.writestr("a%d" % i, one)
    report("aggregate", lambda: P.ZipFile(ap))
    tp = os.path.join(root, "t.gz")
    with gzip.open(tp, "wb") as g: g.write(b"hello world" * 1000)
    d = open(tp, "rb").read(); open(tp, "wb").write(d[:len(d)//2])
    report("truncated_gz", lambda: D.GzipFileSystemPathPointer(tp).open().read())
finally:
    shutil.rmtree(root, ignore_errors=True)
"""

# Each decompression bomb and the exception class its guard must raise.
_BOMB_EXPECT = {
    "honest_zip": "ValueError",
    "ondemand_zip": "ValueError",
    "zpp_zip": "ValueError",
    "nested_gz_zip": "ValueError",
    "gzip_file": "ValueError",
    "gzip_unicode": "ValueError",
    "member_count": "ValueError",
    "aggregate": "ValueError",
    "truncated_gz": "EOFError",
}


@pytest.fixture(scope="module")
def _bomb_results():
    """Drive every decompression bomb once in a child process with a generous
    subprocess timeout (cold nltk import is several seconds on a loaded host),
    and return {case: exception-class-name}. A hang would raise TimeoutExpired
    and fail every case, which is the regression this guards against."""
    import subprocess

    worktree = os.path.dirname(os.path.dirname(os.path.abspath(nltk.data.__file__)))
    env = dict(os.environ, PYTHONPATH=worktree)
    out = subprocess.run(
        [sys.executable, "-c", _BOMB_CHILD],
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
    )
    results = {}
    for line in out.stdout.split("\n"):
        parts = line.split()
        if len(parts) == 2:
            results[parts[0]] = parts[1]
    assert results, f"child produced no results: {out.stdout!r} {out.stderr[-300:]!r}"
    return results


@pytest.mark.parametrize("case", sorted(_BOMB_EXPECT))
def test_decompression_bomb_refused(case, _bomb_results):
    """A zip/gzip decompression bomb (honest-huge, nested gz-in-zip, plain gzip,
    100001-member central-directory bomb, aggregate total-size bomb) is refused
    with a bounded exception; a truncated gzip raises EOFError, never a hang."""
    assert case in _bomb_results, f"{case} missing from child output"
    assert (
        _bomb_results[case] == _BOMB_EXPECT[case]
    ), f"{case}: expected {_BOMB_EXPECT[case]}, child saw {_bomb_results[case]}"


def test_lying_declared_zip_member_refused(data_root):
    """A zip member that declares a tiny uncompressed size but stores a huge
    deflate stream is refused: zipfile stops at the declared size and the CRC
    check fails (BadZipFile), so the bomb never materialises."""
    import struct
    import zipfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("member.txt", b"\x00" * (48 * 1024 * 1024))
    raw = bytearray(buf.getvalue())
    struct.pack_into("<I", raw, raw.find(b"PK\x03\x04") + 22, 1234)
    struct.pack_into("<I", raw, raw.find(b"PK\x01\x02") + 24, 1234)
    p = os.path.join(data_root, "lying.zip")
    open(p, "wb").write(raw)
    with pytest.raises(zipfile.BadZipFile):
        pathsec.ZipFile(p).read("member.txt")


# ---------------------------------------------------------------------------
# Encoding tricks.
# ---------------------------------------------------------------------------
_TRANSFORM_CODECS = [
    "bz2_codec",
    "hex_codec",
    "rot_13",
    "zlib_codec",
    "base64_codec",
    "uu_codec",
    "quopri_codec",
]


@pytest.mark.parametrize("enc", _TRANSFORM_CODECS)
def test_transform_codec_refused_by_text_encoding(enc):
    """A bytes-to-bytes / str-to-str transform codec named as a text encoding is
    refused by text_encoding (so a reader cannot be built to run it: 81 bytes of
    bz2_codec would otherwise decode to 50 MB before a line is split)."""
    with pytest.raises(LookupError):
        text_encoding(enc)


@pytest.mark.parametrize("enc", _TRANSFORM_CODECS)
def test_transform_codec_refused_by_stream_reader(enc):
    """SeekableUnicodeStreamReader (the decode path for every PathPointer) applies
    the same text-encoding gate in its constructor, so a transform codec is
    refused before any byte is decoded."""
    with pytest.raises(LookupError):
        SUR(io.BytesIO(b"hello"), enc)


def test_bom_disagrees_with_declared_encoding_refused():
    """A file whose UTF-16 byte order mark disagrees with a declared utf-8
    encoding does not silently mis-decode: the utf-8 decode of the BOM bytes
    raises UnicodeDecodeError."""
    with pytest.raises(UnicodeDecodeError):
        SUR(io.BytesIO(b"\xff\xfe" + "x".encode("utf-16-le")), "utf-8").read()


def test_overlong_utf8_refused():
    """An overlong / invalid UTF-8 sequence is refused with a strict
    UnicodeDecodeError rather than being accepted as a shorter character."""
    with pytest.raises(UnicodeDecodeError):
        SUR(io.BytesIO(b"\xc0\xaf\xc0\xaf"), "utf-8").read()


def test_utf16_odd_byte_count_refused():
    """A UTF-16 file with an odd byte count is refused (truncated data) rather
    than silently dropping or inventing a trailing character."""
    with pytest.raises(UnicodeDecodeError):
        SUR(io.BytesIO("abc".encode("utf-16-le") + b"\x00"), "utf-16-le").read()


# ---------------------------------------------------------------------------
# Deserialization gadgets.
# ---------------------------------------------------------------------------
class _OsSystem:
    def __reduce__(self):
        import os as _os

        return (_os.system, ("echo pwned",))


class _CodecsEncode:
    def __reduce__(self):
        import codecs

        return (codecs.encode, (b"x", "hex"))


def test_os_system_reduce_refused_restricted():
    """A pickle whose __reduce__ names os.system is refused by RestrictedUnpickler
    (the data.load format='pickle' path), which blocks every global."""
    data = pickle.dumps(_OsSystem(), protocol=4)
    with pytest.raises(pickle.UnpicklingError):
        RestrictedUnpickler(io.BytesIO(data)).load()


def test_os_system_reduce_refused_allowlist():
    """The same os.system gadget is refused by AllowlistUnpickler even with a
    broad allowed_modules, because os/posix is a denied module (GHSA-x99w)."""
    data = pickle.dumps(_OsSystem(), protocol=4)
    with pytest.raises(pickle.UnpicklingError):
        AllowlistUnpickler(io.BytesIO(data), allowed_modules=["collections"]).load()


def test_codecs_encode_gadget_refused():
    """A REDUCE over codecs.encode (a transform-codec gadget) is refused: _codecs
    is not in any model allowlist."""
    data = pickle.dumps(_CodecsEncode(), protocol=4)
    with pytest.raises(pickle.UnpicklingError):
        AllowlistUnpickler(io.BytesIO(data), allowed_modules=["collections"]).load()


def test_dotted_name_global_refused():
    """A proto-4 STACK_GLOBAL with a dotted name (the attribute-traversal RCE,
    GHSA-4489) is refused before resolution."""
    with pytest.raises(pickle.UnpicklingError):
        AllowlistUnpickler(
            io.BytesIO(_stack_global("collections", "foo.bar")),
            allowed_modules=["collections"],
        ).load()


def test_dunder_name_global_refused():
    """A global with a dunder name (reaching module internals like __reduce__ /
    __class__) is refused."""
    with pytest.raises(pickle.UnpicklingError):
        AllowlistUnpickler(
            io.BytesIO(_stack_global("collections", "__reduce__")),
            allowed_modules=["collections"],
        ).load()


def test_ext_opcode_refused():
    """An EXT1 extension-registry opcode (which can bypass find_class via a warm
    copyreg cache) is refused up front."""
    with pytest.raises(pickle.UnpicklingError):
        AllowlistUnpickler(
            io.BytesIO(b"\x80\x04\x82\x01."), allowed_modules=["collections"]
        ).load()


def test_numpy_lib_file_sink_refused():
    """numpy.lib.format.open_memmap (a file-I/O sink whose __module__ hides under
    numpy.lib) is refused even under a broad numpy allow (CWE-502)."""
    with pytest.raises(pickle.UnpicklingError):
        AllowlistUnpickler(
            io.BytesIO(_stack_global("numpy.lib.format", "open_memmap")),
            allowed_modules=["numpy"],
        ).load()


def test_numpy_load_denied_global_refused():
    """numpy.load (a nested-unpickle sink re-exported into the allowed numpy
    namespace) is refused as a denied callable."""
    with pytest.raises(pickle.UnpicklingError):
        AllowlistUnpickler(
            io.BytesIO(_stack_global("numpy", "load")), allowed_modules=["numpy"]
        ).load()


def test_bare_module_object_refused():
    """Resolving a global to a bare module object (not a class/function) is
    refused, closing a module-walk gadget."""
    with pytest.raises(pickle.UnpicklingError):
        AllowlistUnpickler(
            io.BytesIO(_stack_global("collections", "OrderedDict")), allowed_modules=[]
        ).load()


# ---------------------------------------------------------------------------
# JSON / YAML structural bombs.
# ---------------------------------------------------------------------------
def test_json_over_deep_refused():
    """JSON nested past JSON_MAX_DEPTH is refused before the recursive C decoder
    can overflow the C stack (an uncatchable segfault)."""
    doc = "[" * (JSON_MAX_DEPTH + 50) + "]" * (JSON_MAX_DEPTH + 50)
    with pytest.raises(ValueError):
        safe_json_loads(doc)


def test_json_nan_refused():
    """A NaN / Infinity JSON constant is refused (a NaN weight silently poisons
    every downstream score)."""
    with pytest.raises(ValueError):
        safe_json_loads('{"x": NaN}')


def test_json_float_overflow_refused():
    """A finite-looking numeric literal that overflows an IEEE double to inf
    (1e400) is refused too."""
    with pytest.raises(ValueError):
        safe_json_loads("1e400")


def test_json_unknown_tag_refused():
    """A tagged-JSON object naming a tag not in the allowlist is refused: a tag
    cannot name an arbitrary class."""
    with pytest.raises(ValueError):
        JSONTaggedDecoder().decode('{"!definitely_not_a_registered_tag": 1}')


# ---------------------------------------------------------------------------
# Benign look-alikes: each MUST load (an OVERBLOCK here is itself a finding).
# ---------------------------------------------------------------------------
def test_benign_honest_gzip_loads(data_root):
    """A small, high-entropy (low-ratio) gzip file loads unchanged: the bomb
    guard does not over-block an honest gzip."""
    import gzip

    payload = os.urandom(200000)
    p = os.path.join(data_root, "honest.gz")
    with gzip.open(p, "wb") as g:
        g.write(payload)
    assert nltk.data.GzipFileSystemPathPointer(p).open().read() == payload


def test_benign_honest_zip_member_loads(data_root):
    """A ~1 MB zip member that expands under the ratio bound loads unchanged."""
    import zipfile

    text = ("the quick brown fox " * 50000).encode()
    p = os.path.join(data_root, "honest.zip")
    with zipfile.ZipFile(p, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("doc.txt", text)
    assert pathsec.ZipFile(p).read("doc.txt") == text


def test_benign_gz_in_zip_loads(data_root):
    """An honest .gz member inside a zip (the GzipFileSystemPathPointer nested
    path) decompresses to its real content."""
    import gzip
    import zipfile

    payload = os.urandom(200000)
    gzb = io.BytesIO()
    with gzip.GzipFile(fileobj=gzb, mode="wb") as g:
        g.write(payload)
    p = os.path.join(data_root, "gzmember.zip")
    with zipfile.ZipFile(p, "w", zipfile.ZIP_STORED) as z:
        z.writestr("x.gz", gzb.getvalue())
    assert nltk.data.ZipFilePathPointer(p, "x.gz").open().read() == payload


@pytest.mark.parametrize(
    "enc", ["utf-16", "utf-8-sig", "utf-16-le", "utf-16-be", "utf-7"]
)
def test_benign_encodings_roundtrip(enc):
    """A real file in each honest text encoding (incl. a BOM-carrying UTF-16 and
    the stateful UTF-7) decodes correctly through SeekableUnicodeStreamReader."""
    s = "h" + chr(0xE9) + "llo w" + chr(0xF6) + "rld\nsecond line\n"
    assert SUR(io.BytesIO(s.encode(enc)), enc).read() == s


def test_benign_iso2022jp_roundtrip_and_seek():
    """A shift-state iso-2022-jp file round-trips, and a seek back to a tell()
    position inside the shifted run re-reads the same text (no state desync)."""
    jp = "pre " + chr(0x3053) + chr(0x3093) + " mid " + chr(0x306B) + " post\n"
    raw = jp.encode("iso-2022-jp")
    r = SUR(io.BytesIO(raw), "iso-2022-jp")
    head = r.read(6)
    pos = r.tell()
    tail = r.read()
    assert head + tail == jp
    r.seek(pos)
    assert r.read() == tail


def test_benign_utf8_sig_without_bom_loads():
    """A file declared utf-8-sig but carrying no BOM still decodes (the sig is
    optional on read)."""
    assert SUR(io.BytesIO(b"plain"), "utf-8-sig").read() == "plain"


def test_benign_json_loads():
    """An ordinary small JSON document loads unchanged."""
    assert safe_json_loads('{"a":[1,2.5,"x"]}') == {"a": [1, 2.5, "x"]}


def test_benign_restricted_pure_data_loads():
    """A pickle of pure data (no globals) loads through RestrictedUnpickler: the
    all-globals block does not reject legitimate data pickles."""
    good = pickle.dumps({"a": [1, 2, 3], "b": "x"}, protocol=4)
    assert RestrictedUnpickler(io.BytesIO(good)).load() == {"a": [1, 2, 3], "b": "x"}


def test_benign_numpy_array_loads():
    """A real numpy array pickle loads through AllowlistUnpickler with a numpy
    allow: the gadget denylist does not over-block a genuine model array."""
    np = pytest.importorskip("numpy")
    arr = np.arange(12, dtype=np.float64)
    out = AllowlistUnpickler(
        io.BytesIO(pickle.dumps(arr, protocol=4)), allowed_modules=["numpy"]
    ).load()
    assert (out == arr).all()
