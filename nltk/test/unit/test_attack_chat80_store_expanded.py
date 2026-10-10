# Natural Language Toolkit: store-path attack tests (chat80 valuation stores)
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Attack tests for the chat80 persistent-store sinks (GHSA-7j4p-88wx-5jrc,
GHSA-xv54-447f-mj22, GHSA-xmfg-f9cm-w86q; CWE-59 / CWE-73).

``val_dump`` / ``val_load`` hand a caller path to ``shelve`` (whose dbm backend
picks its own backing names: ``.db`` for ndbm, ``.dat``/``.dir``/``.bak`` for
dumb, the bare name for gdbm and sqlite3), ``cities2table`` hands one to
``sqlite3`` (``-journal`` / ``-wal`` / ``-shm`` sidecars) and ``sql_demo``
resolves ``corpora/city_database/city.db`` through ``nltk.data.find``. Every
attack plants a link or special file at one of those names inside a registered
data root, drives the real function, and judges by what the filesystem shows
afterwards: an outside target must be byte-identical, nothing may appear outside
the root, and no outside canary may be read. Benign stores at the end prove
the round trip still works with whichever dbm backend this interpreter picks.
"""

import contextlib
import dbm
import io
import os
import pickle
import shutil
import socket
import sqlite3
import stat

import pytest

import nltk.data
import nltk.pathsec as pathsec
from nltk.sem import chat80
from nltk.test.unit import timing

CANARY = "STORE_OUTSIDE_CANARY"
SENTINEL = b"SENTINEL-do-not-touch\n"
#: a refusal by the store guards: PermissionError, or the SystemExit val_load
#: turns an unopenable store into (its message carries the security text)
REFUSED = (PermissionError, ValueError, SystemExit)

BACKENDS = [name for name in ("dbm.dumb", "dbm.ndbm", "dbm.gnu", "dbm.sqlite3")]


def _backend(name):
    try:
        return __import__(name, fromlist=["open"])
    except ImportError:
        pytest.skip(f"{name} not available on this interpreter")


def _outside_shelf(module, base):
    """A shelf written by ``module`` at ``base`` holding CANARY; returns the
    backing file names it created (relative to the base's directory)."""
    store = module.open(base, "n")
    store[b"canary"] = pickle.dumps({CANARY})
    store.close()
    prefix = os.path.basename(base)
    return sorted(
        name for name in os.listdir(os.path.dirname(base)) if name.startswith(prefix)
    )


def _assert_refused(fn, *args):
    with pytest.raises(REFUSED) as info:
        fn(*args)
    assert "Security Violation" in str(info.value), info.value


def _assert_untouched(path, before_stat, content):
    with open(path, "rb") as f:
        assert f.read() == content, f"{path} was modified"
    assert os.stat(path).st_mtime_ns == before_stat.st_mtime_ns


def _write_cities(root):
    """A tiny Chat-80 corpus under the sandbox root: the ``city`` relation for
    cities2table and the ``borders`` relation the ``borders`` bundle loads."""
    corpus = os.path.join(root, "corpora", "chat80")
    os.makedirs(corpus, exist_ok=True)
    with open(os.path.join(corpus, "atk.pl"), "w", encoding="utf8") as f:
        f.write("city(athens,greece,1368).\n")
    with open(os.path.join(corpus, "borders.pl"), "w", encoding="utf8") as f:
        f.write("borders(greece,albania).\nborders(greece,bulgaria).\n")


@pytest.fixture
def staged(pathsec_sandbox):
    root, outside = pathsec_sandbox
    victim = str(outside / "victim.txt")
    with open(victim, "wb") as f:
        f.write(SENTINEL)
    # nltk.data.load caches corpora/chat80/*.pl by name, whichever root it came
    # from; drop the cache both ways so the tiny corpus and the real one never mix.
    nltk.data.clear_cache()
    yield str(root), str(outside), victim
    nltk.data.clear_cache()


# =========================================================================
# val_load / _restricted_shelve_open: links at every backing name, per backend
# =========================================================================
@pytest.mark.parametrize("backend", BACKENDS)
def test_val_load_refuses_symlinked_backing_names_per_backend(staged, backend):
    root, outside, _ = staged
    module = _backend(backend)
    out_base = os.path.join(outside, "secret")
    backing = _outside_shelf(module, out_base)
    assert backing, f"{backend} wrote no backing file"
    in_base = os.path.join(root, "store")
    before = {}
    for name in backing:
        suffix = name[len("secret") :]
        target = os.path.join(outside, name)
        os.symlink(target, in_base + suffix)
        with open(target, "rb") as f:
            before[target] = (os.stat(target), f.read())
    _assert_refused(chat80.val_load, in_base)
    _assert_refused(chat80._restricted_shelve_open, in_base)
    for target, (st, content) in before.items():
        _assert_untouched(target, st, content)


@pytest.mark.parametrize("backend", BACKENDS)
def test_val_load_refuses_hardlinked_backing_names_per_backend(staged, backend):
    root, outside, _ = staged
    module = _backend(backend)
    out_base = os.path.join(outside, "secret")
    backing = _outside_shelf(module, out_base)
    in_base = os.path.join(root, "store")
    for name in backing:
        suffix = name[len("secret") :]
        try:
            os.link(os.path.join(outside, name), in_base + suffix)
        except OSError:
            pytest.skip("cannot hardlink across these locations")
    _assert_refused(chat80.val_load, in_base)


# =========================================================================
# val_dump: the write side (the advisory's truncate-and-overwrite primitive)
# =========================================================================
@pytest.mark.parametrize(
    "suffix", ["", ".db", ".dat", ".dir", ".bak", "-journal", "-wal", "-shm"]
)
def test_val_dump_refuses_symlink_at_each_backing_name_and_victim_survives(
    staged, suffix
):
    root, outside, victim = staged
    base = os.path.join(root, "pwn")
    os.symlink(victim, base + suffix)
    before = os.stat(victim)
    _assert_refused(chat80.val_dump, [], base)
    _assert_untouched(victim, before, SENTINEL)
    assert sorted(os.listdir(outside)) == ["victim.txt"]


def test_val_dump_refuses_hardlink_at_backing_name(staged):
    root, outside, victim = staged
    base = os.path.join(root, "pwn")
    try:
        os.link(victim, base + ".db")
    except OSError:
        pytest.skip("cannot hardlink across these locations")
    before = os.stat(victim)
    _assert_refused(chat80.val_dump, [], base)
    _assert_untouched(victim, before, SENTINEL)


def test_val_dump_refuses_symlinked_parent_directory(staged):
    root, outside, victim = staged
    os.symlink(outside, os.path.join(root, "dirlink"), target_is_directory=True)
    _assert_refused(chat80.val_dump, [], os.path.join(root, "dirlink", "pwn"))
    assert sorted(os.listdir(outside)) == ["victim.txt"]


def test_val_dump_link_planted_after_validation_is_still_refused(staged, monkeypatch):
    """A link that appears between validate_path and the store open (the race
    the advisory's threat model allows) is caught by the O_NOFOLLOW open of the
    backing names, so the victim survives."""
    root, outside, victim = staged
    base = os.path.join(root, "pwn")
    real = chat80.validate_path

    def validate_then_plant(*args, **kwargs):
        real(*args, **kwargs)
        for suffix in chat80._STORE_SIDECAR_SUFFIXES:
            if not os.path.lexists(base + suffix):
                os.symlink(victim, base + suffix)

    monkeypatch.setattr(chat80, "validate_path", validate_then_plant)
    before = os.stat(victim)
    _assert_refused(chat80.val_dump, [], base)
    _assert_untouched(victim, before, SENTINEL)


@pytest.mark.parametrize("fn", ["val_dump", "val_load", "cities2table"])
def test_relative_and_traversal_names_are_refused(staged, fn):
    root, outside, _ = staged
    _write_cities(root)
    # climbs from the root back down into the outside dir with '..' components
    try:
        traversal = os.path.join(root, os.path.relpath(outside, root), "pwn")
    except ValueError:
        pytest.skip("root and outside dir are on different drives")
    assert ".." in traversal.replace("\\", "/").split("/")
    assert os.path.realpath(traversal).startswith(os.path.realpath(outside))
    for name in ("relative_store", "../pwn", traversal):
        with pytest.raises(REFUSED) as info:
            if fn == "cities2table":
                chat80.cities2table("atk.pl", "city", name, setup=True)
            else:
                getattr(chat80, fn)(*(([], name) if fn == "val_dump" else (name,)))
        assert "Security Violation" in str(info.value)
    assert sorted(os.listdir(outside)) == ["victim.txt"]


def test_relative_name_is_allowed_only_from_inside_the_root(staged):
    """BENIGN: with the working directory inside the data root, a relative
    store name resolves inside it and val_dump creates the store there."""
    root, outside, _ = staged
    os.chdir(root)
    chat80.val_dump([], "rel_store")
    assert any(name.startswith("rel_store") for name in os.listdir(root))


@pytest.mark.parametrize(
    "name",
    ["pwn" + chr(0) + "x", "pwn\n", "pw\rn", "\tpwn", "CON", "NUL", "COM1", "aux.db"],
)
def test_nul_control_and_device_names_create_nothing_outside(staged, name):
    """NUL is refused outright; a control character is an odd in-root file name
    on POSIX and an invalid one on Windows (OSError, nothing created); a Windows
    device name is an in-root name on POSIX and a refused device on Windows.
    Whatever the platform does, nothing may leave the root."""
    root, outside, _ = staged
    try:
        chat80.val_dump([], os.path.join(root, name))
    except REFUSED as exc:
        assert "Security Violation" in str(exc)
        if chr(0) in name:
            assert "NUL" in str(exc)
    except OSError as exc:
        assert os.name != "posix", f"POSIX refused an ordinary name: {exc}"
    assert sorted(os.listdir(outside)) == ["victim.txt"]


class _LyingName(str):
    def __new__(cls, real, shown):
        obj = str.__new__(cls, real)
        obj._shown = shown
        return obj

    def __str__(self):
        return self._shown

    def __repr__(self):
        return repr(self._shown)

    @property
    def path(self):
        return self._shown


class _ShiftingPath:
    """os.PathLike whose __fspath__ flips from an in-root to an outside name."""

    def __init__(self, first, then):
        self._answers = [first, then]

    def __fspath__(self):
        return self._answers.pop(0) if len(self._answers) > 1 else self._answers[0]


@pytest.mark.parametrize("fn", ["val_dump", "cities2table"])
def test_lying_str_subclass_is_refused_on_its_real_characters(staged, fn):
    root, outside, _ = staged
    lying = _LyingName(os.path.join(outside, "pwn"), os.path.join(root, "ok"))
    with pytest.raises(PermissionError, match="Unauthorized path"):
        if fn == "val_dump":
            chat80.val_dump([], lying)
        else:
            chat80.cities2table("atk.pl", "city", lying, setup=True)
    assert sorted(os.listdir(outside)) == ["victim.txt"]


def test_shifting_path_like_creates_nothing_outside(staged):
    root, outside, _ = staged
    shifting = _ShiftingPath(os.path.join(root, "ok"), os.path.join(outside, "pwn"))
    with pytest.raises((TypeError, PermissionError, ValueError)):
        chat80.val_dump([], shifting)
    assert sorted(os.listdir(outside)) == ["victim.txt"]


def _finishes_within(seconds, fn):
    """``(finished, exception)`` for ``fn`` run on a thread, judged by the time
    charged to it (see nltk.test.unit.timing)."""
    finished, exc, _charged = timing.finishes_within(seconds, fn)
    return finished, exc


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="no FIFOs on this platform")
@pytest.mark.parametrize("suffix", ["", ".db", "-wal"])
@pytest.mark.parametrize("fn", ["val_load", "val_dump"])
def test_fifo_at_backing_name_is_refused_without_blocking(staged, suffix, fn):
    root, outside, _ = staged
    base = os.path.join(root, "store")
    os.mkfifo(base + suffix)
    call = (
        (lambda: chat80.val_load(base))
        if fn == "val_load"
        else (lambda: chat80.val_dump([], base))
    )
    finished, exc = _finishes_within(10, call)
    assert finished, f"{fn} blocked on the planted FIFO"
    assert isinstance(exc, REFUSED) and "Security Violation" in str(exc), exc


@pytest.mark.skipif(
    os.name != "posix" or not hasattr(socket, "AF_UNIX"), reason="POSIX only"
)
def test_unix_socket_at_backing_name_is_refused(staged):
    root, outside, _ = staged
    base = os.path.join(root, "store")
    if len(base) + 3 > 100:
        pytest.skip("socket path too long for AF_UNIX here")
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        sock.bind(base + ".db")
        assert stat.S_ISSOCK(os.lstat(base + ".db").st_mode)
        _assert_refused(chat80.val_load, base)
        _assert_refused(chat80.val_dump, [], base)
    finally:
        sock.close()


def test_huge_sparse_store_is_not_read_through_by_the_guard(staged):
    """A multi-gigabyte (sparse) file at the store name: the link guard only
    opens and closes it, and the backend reads a header; nothing scans it."""
    root, outside, _ = staged
    base = os.path.join(root, "huge")
    with open(base, "wb") as f:
        f.truncate(4 * 1024**3)
    finished, exc = _finishes_within(20, lambda: chat80.val_load(base))
    assert finished, "val_load spent more than 20s on a sparse 4 GiB store"
    assert exc is not None and not isinstance(exc, MemoryError)


# =========================================================================
# cities2table: the sqlite write sink and its sidecars
# =========================================================================
@pytest.mark.parametrize("suffix", ["", "-journal", "-wal", "-shm"])
def test_cities2table_refuses_symlink_at_db_and_sidecars(staged, suffix):
    root, outside, victim = staged
    _write_cities(root)
    db = os.path.join(root, "city.db")
    os.symlink(victim, db + suffix)
    before = os.stat(victim)
    _assert_refused(chat80.cities2table, "atk.pl", "city", db, True)
    _assert_untouched(victim, before, SENTINEL)
    assert sorted(os.listdir(outside)) == ["victim.txt"]


def test_cities2table_refuses_hardlinked_db(staged):
    root, outside, victim = staged
    _write_cities(root)
    db = os.path.join(root, "city.db")
    try:
        os.link(victim, db)
    except OSError:
        pytest.skip("cannot hardlink across these locations")
    before = os.stat(victim)
    _assert_refused(chat80.cities2table, "atk.pl", "city", db, True)
    _assert_untouched(victim, before, SENTINEL)


def test_cities2table_benign_builds_and_sql_query_reads_it(staged):
    root, outside, _ = staged
    _write_cities(root)
    db = os.path.join(root, "built", "city.db")
    os.makedirs(os.path.dirname(db))
    chat80.cities2table("atk.pl", "city", db, setup=True)
    rows = chat80.sql_query(
        "built/city.db", "SELECT Country FROM city_table"
    ).fetchall()
    assert rows == [("greece",)]


# =========================================================================
# sql_demo: the advisory's other entry point
# =========================================================================
def _plant_city_db(root, target):
    corp = os.path.join(root, "corpora", "city_database")
    os.makedirs(corp)
    os.symlink(target, os.path.join(corp, "city.db"))


def test_sql_demo_refuses_symlinked_city_db(staged):
    root, outside, _ = staged
    secret = os.path.join(outside, "secret.db")
    con = sqlite3.connect(secret)
    con.execute("CREATE TABLE city_table (City, Country, Population)")
    con.execute("INSERT INTO city_table VALUES (?, ?, ?)", (CANARY, "x", 1))
    con.commit()
    con.close()
    _plant_city_db(root, secret)
    printed = io.StringIO()
    with pytest.raises(PermissionError, match="Security Violation"):
        with contextlib.redirect_stdout(printed):
            chat80.sql_demo()
    assert CANARY not in printed.getvalue()


def test_sql_demo_benign_prints_installed_rows_if_present():
    try:
        nltk.data.find("corpora/city_database/city.db")
    except LookupError:
        pytest.skip("city_database corpus not installed")
    printed = io.StringIO()
    with contextlib.redirect_stdout(printed):
        chat80.sql_demo()
    assert "athens" in printed.getvalue()


# =========================================================================
# BENIGN round trips with whichever dbm backend this interpreter picks
# =========================================================================
def test_val_dump_then_restricted_reload_round_trip_records_backend(staged):
    root, outside, _ = staged
    _write_cities(root)
    base = os.path.join(root, "roundtrip")
    chat80.val_dump([chat80.borders], base)
    created = sorted(n for n in os.listdir(root) if n.startswith("roundtrip"))
    assert created, "val_dump wrote nothing in-root"
    assert dbm.whichdb(base) in ("dbm.dumb", "dbm.ndbm", "dbm.gnu", "dbm.sqlite3"), (
        dbm.whichdb(base),
        created,
    )
    shelf = chat80._restricted_shelve_open(base)
    try:
        # val_dump stores the concept labels the bundle yields, not its name
        assert set(shelf.keys()) == {"albania", "border", "bulgaria", "greece"}
        assert set(shelf["border"]) == {
            ("greece", "albania"),
            ("albania", "greece"),
            ("greece", "bulgaria"),
            ("bulgaria", "greece"),
        }
    finally:
        shelf.close()
    assert sorted(os.listdir(outside)) == ["victim.txt"]


def test_val_load_round_trip_reaches_the_valuation_rebuild(staged):
    """The public val_load reads the store it just wrote through every guard;
    whether the Valuation rebuild then accepts the derived list-valued symbol
    is the separately documented pre-existing limitation (see
    test_full_functionality_smoke), not a containment question."""
    from nltk.sem import Valuation

    root, outside, _ = staged
    _write_cities(root)
    base = os.path.join(root, "roundtrip")
    chat80.val_dump([chat80.borders], base)
    try:
        loaded = chat80.val_load(base)
    except ValueError as exc:
        assert "Valuation" in str(exc) or "list" in str(exc) or "set" in str(exc), exc
    else:
        assert isinstance(loaded, Valuation) and "borders" in dict(loaded)


def test_val_load_reports_a_missing_store_without_touching_anything(staged):
    root, outside, _ = staged
    with pytest.raises(SystemExit, match="Cannot read file"):
        chat80.val_load(os.path.join(root, "absent"))
    assert not any(n.startswith("absent") for n in os.listdir(root))
