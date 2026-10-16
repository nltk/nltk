"""Red-team regression tests: filesystem paths, links, names, archives, downloader.

Class ``pathlinks`` for the 2026-10-16 sweep. Every test here is a REFUSED or a
BENIGN-OK row from FINDINGS.md: it drives a REAL public nltk entry point under
``pathsec.ENFORCE`` and asserts either the specific refusal (exception type and
message fragment) or the correct acceptance of a legitimate input. No LEAK rows
exist for this class (nothing escaped), so none are smuggled in here.

Self-contained: it builds the enforced single-root sandbox inline the way
nltk/test/unit/conftest.py does, so it runs from anywhere on python3.13 AND
python3.10 (no tkinter, no pytest-timeout, no network). Anything that could hang
(a FIFO or device open) runs in a forked child joined with a timeout; the
timeout is a thread-free guard that does not need pytest-timeout.

Run:
    python3.13 -m pytest nltk/test/unit/test_attack_pathlinks_redteam_20261016.py
  -p no:cacheprovider \
"""

import gzip
import multiprocessing as mp
import os
import shutil
import tempfile
import unicodedata
import zipfile

import pytest

import nltk
import nltk.data
from nltk import pathsec

HOME = os.path.expanduser("~")
POSIX = os.name == "posix"
FORK = mp.get_context("fork") if POSIX else mp.get_context()


# --------------------------------------------------------------------------
# Inline enforced sandbox (mirrors conftest._enforce_single_root).
# --------------------------------------------------------------------------
def _make_home_dir(prefix):
    return tempfile.mkdtemp(prefix=prefix, dir=HOME)


@pytest.fixture
def sandbox(monkeypatch):
    """Enforce pathsec against one throwaway data root under $HOME; yield
    (root, outside) where ``outside`` is a dir guaranteed out of every root."""
    root = os.path.realpath(_make_home_dir(".nltk_rt_root_"))
    outside = os.path.realpath(_make_home_dir(".nltk_rt_outside_"))
    monkeypatch.setattr(pathsec, "ENFORCE", True)
    monkeypatch.setattr(nltk.data, "path", [root])
    monkeypatch.setattr(pathsec, "_ALLOWED_ROOTS_CACHE", None, raising=False)
    monkeypatch.setattr(pathsec, "_LAST_DATA_PATHS", None, raising=False)
    monkeypatch.setattr(nltk.data, "_STAGING_TEMPDIR", None, raising=False)
    corp = os.path.join(root, "corpora", "mini")
    os.makedirs(corp)
    with open(os.path.join(corp, "a.txt"), "w") as f:
        f.write("hello world\n")
    os.makedirs(os.path.join(corp, "nested"))
    with open(os.path.join(corp, "nested", "b.txt"), "w") as f:
        f.write("nested data\n")
    secret = os.path.join(outside, "secret.txt")
    with open(secret, "w") as f:
        f.write("TOPSECRET\n")
    try:
        yield root, outside, corp, secret
    finally:
        shutil.rmtree(root, ignore_errors=True)
        shutil.rmtree(outside, ignore_errors=True)


def _reader(corp, pattern=r".*"):
    from nltk.corpus.reader import PlaintextCorpusReader

    return PlaintextCorpusReader(corp, pattern)


# --------------------------------------------------------------------------
# Forked-open helper for hang-prone opens (FIFO / device): must never hang.
# --------------------------------------------------------------------------
def _child_open(path, q):
    try:
        with pathsec.open(path, "rb") as f:
            q.put(("RET", f.read(16)))
    except (PermissionError, ValueError) as e:
        q.put(("REFUSED", f"{type(e).__name__}: {e}"))
    except OSError as e:
        q.put(("OSERROR", f"{type(e).__name__}: {e}"))


def _forked_open(path, timeout=8):
    q = FORK.Queue()
    p = FORK.Process(target=_child_open, args=(path, q))
    p.start()
    p.join(timeout)
    if p.is_alive():
        p.terminate()
        p.join()
        return ("HANG", f">{timeout}s")
    try:
        return q.get_nowait()
    except Exception:
        return ("NORESULT", "")


# ==========================================================================
# CorpusReader fileid attacks
# ==========================================================================
def test_symlink_leaf_reader_refused(sandbox):
    """A symlink leaf inside the corpus root pointing at an outside secret is
    refused by the reader's scoped containment check (CWE-59)."""
    root, outside, corp, secret = sandbox
    os.symlink(secret, os.path.join(corp, "slink.txt"))
    with pytest.raises(ValueError, match="escapes root"):
        _reader(corp).raw("slink.txt")


def test_intermediate_dir_symlink_reader_refused(sandbox):
    """An intermediate DIRECTORY symlink inside the root pointing outside is
    refused: validate_path resolves it and sees the escape (GHSA-g58v class)."""
    root, outside, corp, secret = sandbox
    os.symlink(outside, os.path.join(corp, "dsub"))
    with pytest.raises(ValueError, match="escapes root"):
        _reader(corp).raw("dsub/secret.txt")


def test_symlink_chain_pathsec_open_refused(sandbox):
    """A symlink chain ending outside the root is refused at pathsec.open."""
    root, outside, corp, secret = sandbox
    c2 = os.path.join(corp, "c2.txt")
    c1 = os.path.join(corp, "c1.txt")
    os.symlink(secret, c2)
    os.symlink(c2, c1)
    with pytest.raises(PermissionError, match="Unauthorized path"):
        pathsec.open(c1)


def test_dangling_symlink_pathsec_open_refused(sandbox):
    """A dangling symlink to an outside path is refused on the out-of-root
    target, not followed to a create."""
    root, outside, corp, secret = sandbox
    os.symlink(os.path.join(outside, "nope.txt"), os.path.join(corp, "d.txt"))
    with pytest.raises(PermissionError, match="Unauthorized path"):
        pathsec.open(os.path.join(corp, "d.txt"))


@pytest.mark.skipif(not POSIX, reason="hardlink semantics are POSIX")
def test_hardlink_to_outside_refused(sandbox):
    """A hardlink planted inside the root to an outside inode is refused by the
    fstat st_nlink>1 check (a hardlink has no symlink to resolve)."""
    root, outside, corp, secret = sandbox
    hl = os.path.join(corp, "hard.txt")
    try:
        os.link(secret, hl)
    except OSError:
        pytest.skip("cross-device link not possible here")
    with pytest.raises(PermissionError, match="multiply-linked"):
        pathsec.open(hl)


@pytest.mark.skipif(not POSIX, reason="FIFO is POSIX")
def test_fifo_open_refused_without_hanging(sandbox):
    """A FIFO planted at a path a reader opens is refused (O_NONBLOCK keeps the
    open from blocking); the forked child must return well under the timeout."""
    root, outside, corp, secret = sandbox
    fifo = os.path.join(corp, "pipe.txt")
    os.mkfifo(fifo)
    kind, msg = _forked_open(fifo, timeout=8)
    assert kind == "REFUSED", f"expected refusal, got {kind}: {msg}"
    assert "FIFO" in msg or "special file" in msg


@pytest.mark.skipif(not POSIX, reason="device nodes are POSIX")
@pytest.mark.parametrize("dev", ["/dev/zero", "/dev/stdin", "/dev/fd/0"])
def test_device_via_symlink_refused_without_hanging(sandbox, dev):
    """A symlink to a character device is refused (the device is out of root /
    O_NOFOLLOW refuses the link); the child must not hang reading the device."""
    root, outside, corp, secret = sandbox
    link = os.path.join(corp, "dev_" + dev.replace("/", "_"))
    os.symlink(dev, link)
    kind, msg = _forked_open(link, timeout=8)
    assert kind == "REFUSED", f"expected refusal, got {kind}: {msg}"


@pytest.mark.parametrize("fileid", ["/etc/passwd", "../../../etc/passwd", "..\\..\\x"])
def test_reader_open_rejects_abs_and_dotdot(sandbox, fileid):
    """reader.open refuses absolute and parent-traversal fileids lexically."""
    root, outside, corp, secret = sandbox
    with pytest.raises(ValueError, match="must be relative"):
        _reader(corp).open(fileid)


def test_casefold_symlink_refused(sandbox):
    """On case-insensitive APFS a symlink named UP.txt -> outside, requested as
    'up.txt', is still refused: resolution reaches the out-of-root target."""
    root, outside, corp, secret = sandbox
    os.symlink(secret, os.path.join(corp, "UP.txt"))
    with pytest.raises(ValueError, match="escapes root"):
        _reader(corp).raw("up.txt")


# ==========================================================================
# CorpusReader / pathsec BENIGN look-alikes (no over-blocking)
# ==========================================================================
def test_benign_reader_words(sandbox):
    """A legitimate in-root fileid reads correctly."""
    root, outside, corp, secret = sandbox
    assert _reader(corp, r".*\.txt").words("a.txt")[:2] == ["hello", "world"]


def test_benign_reader_nested_fileid(sandbox):
    """A legitimate nested-directory fileid reads correctly."""
    root, outside, corp, secret = sandbox
    assert "nested" in _reader(corp, r".*\.txt").raw("nested/b.txt")


def test_benign_nfc_nonascii_fileid(sandbox):
    """A legitimate NFC non-ascii fileid is accepted and read."""
    root, outside, corp, secret = sandbox
    name = unicodedata.normalize("NFC", "r" + chr(0xE9) + "sum" + chr(0xE9)) + ".txt"
    with open(os.path.join(corp, name), "w") as f:
        f.write("accent\n")
    assert "accent" in _reader(corp).raw(name)


def test_benign_casefold_in_root(sandbox):
    """Requesting A.TXT for an in-root a.txt on APFS reads the legit file (the
    case-fold stays inside the root, so it must NOT be refused)."""
    root, outside, corp, secret = sandbox
    try:
        got = _reader(corp).raw("A.TXT")
    except (ValueError, OSError):
        pytest.skip("case-sensitive volume: A.TXT is simply absent")
    assert "hello" in got


def test_benign_find_returns_pointer(sandbox):
    """find() of a legitimate nested resource returns a pointer, not a refusal."""
    root, outside, corp, secret = sandbox
    ptr = nltk.data.find("corpora/mini/a.txt")
    assert ptr is not None


# ==========================================================================
# pathsec.open primitive refusals
# ==========================================================================
def test_pathsec_open_nul_refused(sandbox):
    """A NUL byte in a path is refused before any open."""
    root, outside, corp, secret = sandbox
    with pytest.raises(PermissionError, match="NUL byte"):
        pathsec.open(os.path.join(corp, "a" + chr(0) + ".txt"))


def test_symlink_leaf_pathsec_open_refused(sandbox):
    """A symlink leaf pointing outside the root is refused at pathsec.open."""
    root, outside, corp, secret = sandbox
    os.symlink(secret, os.path.join(corp, "s.txt"))
    with pytest.raises(PermissionError, match="Unauthorized path"):
        pathsec.open(os.path.join(corp, "s.txt"))


# ==========================================================================
# nltk.data.find traversal spellings
# ==========================================================================
_FIND_TRAVERSALS = [
    "corpora/../../etc/passwd",
    "corpora/%2e%2e/x",
    "corpora/..%2fx",
    "corpora\\..\\x",
    "file:///etc/passwd",
    "file://localhost/etc/passwd",
    "/etc/passwd",
    "\\\\server\\share\\x",
    "C:\\Windows\\x",
    "corpora/..",
]


@pytest.mark.parametrize("name", _FIND_TRAVERSALS)
def test_find_rejects_traversal_spellings(sandbox, name):
    """Every traversal / absolute / drive / UNC / file-url spelling of a
    resource name is refused by find() with a ValueError."""
    root, outside, corp, secret = sandbox
    with pytest.raises(ValueError, match="Unsafe resource path"):
        nltk.data.find(name)


@pytest.mark.parametrize("code", [0x00, 0x0A, 0x0D, 0x1B, 0x7F, 0x2028])
def test_find_rejects_control_chars(sandbox, code):
    """NUL, newline, CR, ESC, DEL and U+2028 in a resource name are refused."""
    root, outside, corp, secret = sandbox
    name = "corpora/x" + chr(code) + "y"
    with pytest.raises(ValueError, match="Unsafe resource path"):
        nltk.data.find(name)


@pytest.mark.parametrize("code", [0xFF0F, 0x2215, 0x2044])
def test_find_slash_lookalikes_do_not_escape(sandbox, code):
    """Unicode slash look-alikes are NOT path separators, so they name a single
    missing component: find() raises LookupError (not found), never returning an
    out-of-root pointer. Proves no traversal via homoglyph slashes."""
    root, outside, corp, secret = sandbox
    name = "corpora/x" + chr(code) + "y"
    with pytest.raises(LookupError):
        nltk.data.find(name)


# ==========================================================================
# Zip member attacks + benign zip
# ==========================================================================
def _mkzip(path, build):
    with zipfile.ZipFile(path, "w") as z:
        build(z)
    return path


def test_zip_dotdot_member_refused(sandbox):
    """A '..'-escaping zip member is refused on extractall."""
    root, outside, corp, secret = sandbox
    zp = _mkzip(
        os.path.join(corp, "dd.zip"),
        lambda z: (z.writestr("../escape.txt", "X"), z.writestr("ok.txt", "Y")),
    )
    with pytest.raises(PermissionError, match="Traversal member"):
        pathsec.ZipFile(zp).extractall(os.path.join(corp, "exd"))


def test_zip_absolute_member_refused(sandbox):
    """An absolute zip member is refused on extractall."""
    root, outside, corp, secret = sandbox
    zp = _mkzip(os.path.join(corp, "abs.zip"), lambda z: z.writestr("/abs.txt", "X"))
    with pytest.raises(PermissionError, match="Traversal member"):
        pathsec.ZipFile(zp).extractall(os.path.join(corp, "exa"))


def test_zip_backslash_member_refused(sandbox):
    """A backslash-separated '..' zip member is refused on extractall."""
    root, outside, corp, secret = sandbox
    zp = _mkzip(os.path.join(corp, "bk.zip"), lambda z: z.writestr("..\\esc.txt", "X"))
    with pytest.raises(PermissionError, match="refusing member path|Traversal"):
        pathsec.ZipFile(zp).extractall(os.path.join(corp, "exbk"))


def test_zip_colliding_case_members_refused(sandbox):
    """Two members colliding on a case-insensitive filesystem are refused on
    extractall (resource poisoning)."""
    root, outside, corp, secret = sandbox
    zp = _mkzip(
        os.path.join(corp, "coll.zip"),
        lambda z: (
            z.writestr("pkg/Weights.json", "A"),
            z.writestr("pkg/weights.json", "B"),
        ),
    )
    with pytest.raises(ValueError, match="collide|same file"):
        pathsec.ZipFile(zp).extractall(os.path.join(corp, "exc"))


@pytest.mark.skipif(not POSIX, reason="symlink materialisation is POSIX")
def test_zip_symlink_member_neutralised(sandbox):
    """A zip symlink member is extracted as a REGULAR file holding the link text,
    never a real symlink, so it cannot redirect a later read outside the root."""
    root, outside, corp, secret = sandbox
    zp = os.path.join(corp, "sl.zip")
    with zipfile.ZipFile(zp, "w") as z:
        zi = zipfile.ZipInfo("pkg/link")
        zi.external_attr = 0xA1FF << 16  # symlink mode bits
        z.writestr(zi, "/etc/passwd")
        z.writestr("pkg/real.txt", "Y")
    dest = os.path.join(corp, "exsl")
    pathsec.ZipFile(zp).extractall(dest)
    link = os.path.join(dest, "pkg", "link")
    assert os.path.exists(link)
    assert not os.path.islink(link), "symlink member must not be materialised"
    with open(link) as f:
        assert f.read() == "/etc/passwd"  # plain text, not a link


def test_zip_nested_gzip_bomb_refused(sandbox):
    """A gzip bomb nested inside a zip member is refused on read: the second
    decompression layer is bounded (GHSA-rv69 class)."""
    root, outside, corp, secret = sandbox
    from nltk.data import ZipFilePathPointer

    gzbytes = gzip.compress(b"\x00" * (50 * 1024 * 1024))
    zp = os.path.join(corp, "bomb.zip")
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_STORED) as z:
        z.writestr("pkg/data.gz", gzbytes)
    with pytest.raises(ValueError, match="bomb"):
        ZipFilePathPointer(zp, "pkg/data.gz").open().read()


def test_benign_zip_member_read(sandbox):
    """A legitimate zip member reads correctly through ZipFilePathPointer."""
    root, outside, corp, secret = sandbox
    from nltk.data import ZipFilePathPointer

    zp = _mkzip(
        os.path.join(corp, "good.zip"),
        lambda z: z.writestr("good/a.txt", "benign zip content\n"),
    )
    assert b"benign" in ZipFilePathPointer(zp, "good/a.txt").open().read()


# ==========================================================================
# TOCTOU directory-swap race: no out-of-root bytes ever returned
# ==========================================================================
_RACE = {}


def _swapper():
    d, evil, stop = _RACE["d"], _RACE["evil"], _RACE["stop"]
    while not stop.is_set():
        try:
            os.rename(d, d + ".bak")
            os.symlink(evil, d)
            os.unlink(d)
            os.rename(d + ".bak", d)
        except OSError:
            try:
                if os.path.islink(d):
                    os.unlink(d)
                if os.path.exists(d + ".bak"):
                    os.rename(d + ".bak", d)
            except OSError:
                pass


@pytest.mark.skipif(not POSIX, reason="race uses symlink swaps, POSIX")
def test_toctou_dir_swap_never_leaks(sandbox):
    """Racing a directory component against a symlink-to-outside between the
    containment check and the open must NEVER return out-of-root bytes
    (O_NOFOLLOW walk / fd re-validation closes the TOCTOU window)."""
    root, outside, corp, secret = sandbox
    race_dir = os.path.join(corp, "race")
    os.makedirs(race_dir)
    with open(os.path.join(race_dir, "f.txt"), "w") as f:
        f.write("INROOT\n")
    evil = os.path.join(outside, "evil")
    os.makedirs(evil)
    with open(os.path.join(evil, "f.txt"), "w") as f:
        f.write("LEAKED\n")
    target = os.path.join(corp, "race", "f.txt")
    _RACE["d"] = race_dir
    _RACE["evil"] = evil
    _RACE["stop"] = FORK.Event()
    sw = FORK.Process(target=_swapper)
    sw.start()
    try:
        leaked = 0
        for _ in range(200):
            try:
                with pathsec.open(target, "rb") as f:
                    if b"LEAKED" in f.read():
                        leaked += 1
            except (PermissionError, ValueError, OSError):
                pass
        assert leaked == 0, f"out-of-root bytes leaked {leaked} times"
    finally:
        _RACE["stop"].set()
        sw.join(2)
        if sw.is_alive():
            sw.terminate()


# ==========================================================================
# Downloader package-metadata refusals (no network: construction only)
# ==========================================================================
@pytest.mark.parametrize(
    "kw,match",
    [
        (dict(id="p", url="http://x/p.zip", subdir="../evil"), "subdir"),
        (dict(id="p", url="http://x/p.zip", subdir="/evil"), "subdir"),
        (dict(id="p", url="http://x/p.zip", subdir="\\\\srv\\share"), "subdir"),
        (dict(id="../../evil", url="http://x/p.zip"), "id"),
        (dict(id="a/b", url="http://x/p.zip"), "id"),
    ],
)
def test_package_metadata_traversal_refused(kw, match):
    """A Package whose subdir or id carries traversal / separators / absolute
    form is refused at construction, before it can name a write target."""
    from nltk.downloader import Package

    with pytest.raises(ValueError, match=match):
        Package(**kw)


# ==========================================================================
# make_staging_dir / validate_private_dir
# ==========================================================================
@pytest.mark.skipif(not POSIX, reason="POSIX mode bits")
def test_validate_private_dir_group_writable_refused(sandbox):
    """A group-writable directory is refused (CWE-367: another account could
    swap a name between the check and the open)."""
    root, outside, corp, secret = sandbox
    gw = os.path.join(root, "groupwrite")
    os.makedirs(gw)
    os.chmod(gw, 0o775)
    with pytest.raises(PermissionError):
        pathsec.validate_private_dir(gw)


def test_make_private_dir_symlink_parent_refused(sandbox):
    """make_private_dir on a parent that is a symlink to outside is refused."""
    root, outside, corp, secret = sandbox
    syl = os.path.join(root, "privsym")
    os.symlink(outside, syl)
    with pytest.raises((PermissionError, ValueError)):
        pathsec.make_private_dir(syl)


def test_make_private_dir_bad_prefix_refused(sandbox):
    """A traversal prefix for make_private_dir is refused (filename fragment
    only, no separators / '..')."""
    root, outside, corp, secret = sandbox
    with pytest.raises(ValueError, match="fragment"):
        pathsec.make_private_dir(root, prefix="../x")


def test_benign_staging_dir_created_private(sandbox):
    """make_staging_dir creates a private directory inside the root."""
    root, outside, corp, secret = sandbox
    sd = nltk.data.make_staging_dir(prefix="probe_")
    assert os.path.isdir(sd)
    assert pathsec.is_private_dir(sd)


# ==========================================================================
# chat80 val_dump / val_load path handling
# ==========================================================================
def test_chat80_val_dump_outside_root_refused(sandbox):
    """val_dump refuses an out-of-sandbox db path."""
    root, outside, corp, secret = sandbox
    from nltk.sem import chat80

    with pytest.raises((PermissionError, ValueError)):
        chat80.val_dump([chat80.city], os.path.join(outside, "x"))


def test_chat80_val_load_outside_root_refused(sandbox):
    """val_load refuses an out-of-sandbox db path."""
    root, outside, corp, secret = sandbox
    from nltk.sem import chat80

    with pytest.raises((PermissionError, ValueError)):
        chat80.val_load(os.path.join(outside, "y"))


def test_chat80_val_load_symlink_backing_refused(sandbox):
    """A symlink planted at a chat80 backing name pointing outside is refused
    before the store is reopened by path."""
    root, outside, corp, secret = sandbox
    from nltk.sem import chat80

    dbdir = os.path.join(root, "store")
    os.makedirs(dbdir)
    os.symlink(os.path.join(outside, "target.db"), os.path.join(dbdir, "linked.db"))
    with pytest.raises((PermissionError, ValueError, OSError)):
        chat80.val_load(os.path.join(dbdir, "linked"))


def test_benign_chat80_roundtrip(sandbox, monkeypatch):
    """A legitimate chat80 val_dump + val_load round-trip inside the root works
    (needs the real chat80 .pl corpus in ~/nltk_data; skipped if absent)."""
    root, outside, corp, secret = sandbox
    chat_dir = os.path.join(HOME, "nltk_data", "corpora", "chat80")
    if not os.path.isdir(chat_dir):
        pytest.skip("chat80 corpus not installed in ~/nltk_data")
    from nltk.sem import chat80

    monkeypatch.setattr(nltk.data, "path", [root, os.path.join(HOME, "nltk_data")])
    monkeypatch.setattr(pathsec, "_ALLOWED_ROOTS_CACHE", None, raising=False)
    monkeypatch.setattr(pathsec, "_LAST_DATA_PATHS", None, raising=False)
    dbdir = os.path.join(root, "store2")
    os.makedirs(dbdir)
    db = os.path.join(dbdir, "cities")
    chat80.val_dump([chat80.city], db)
    val = chat80.val_load(db)
    assert len(list(val)) > 0
