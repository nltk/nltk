"""The chat80 store between the path check and the backend's own open.

shelve, dbm and sqlite reopen a store's backing names by path after NLTK has
checked them (CWE-367). Every case here swaps a backing name in exactly that
gap, deterministically, by wrapping the backend's open; a benign counterpart
shows the same call still works when nothing is swapped. The outside target
carries SENTINEL and must never be read back or changed.
"""

import dbm
import importlib
import os
import shelve
import sqlite3
import stat

import pytest

import nltk.data
from nltk.sem import chat80

SENTINEL = b"SENTINEL-do-not-touch\n"
BACKENDS = ["dbm.dumb", "dbm.ndbm", "dbm.gnu", "dbm.sqlite3"]
RELATION = {"city_of": ["athens", "bangkok", "berlin"], "size": "large"}


def _backend(name):
    try:
        return importlib.import_module(name)
    except ImportError:
        pytest.skip(f"{name} is not built on this interpreter")


def _store_with(module, base, relation):
    """A shelf at *base* written through *module*; returns its backing names."""
    inner = module.open(base, "n")
    outer = shelve.Shelf(inner)
    outer.update(relation)
    outer[chat80._STORE_MANIFEST_KEY] = sorted(relation)
    outer.close()
    folder, stem = os.path.split(base)
    return sorted(n for n in os.listdir(folder) if n.startswith(stem))


def _force_backend(monkeypatch, module):
    monkeypatch.setattr(dbm, "_defaultmod", module)
    monkeypatch.setattr(dbm, "_modules", {module.__name__: module})


def _swap_before(monkeypatch, target, swap):
    """Call *swap* right before the backend opens *target* by name."""
    real = shelve.open

    def opening(name, *args, **kwargs):
        if name == target:
            swap()
        return real(name, *args, **kwargs)

    monkeypatch.setattr(shelve, "open", opening)


pinned = pytest.mark.skipif(
    os.name == "nt",
    reason="an open file cannot be swapped on Windows, so no handle is held",
)
needs_symlink = pytest.mark.skipif(
    os.name == "nt", reason="symlinks need privilege on Windows"
)


@pytest.fixture
def staged(pathsec_sandbox):
    root, outside = pathsec_sandbox
    victim = str(outside / "victim.db")
    with open(victim, "wb") as f:
        f.write(SENTINEL)
    nltk.data.clear_cache()
    yield str(root), str(outside), victim
    nltk.data.clear_cache()


def _assert_untouched(path):
    with open(path, "rb") as f:
        assert f.read() == SENTINEL, "the outside file was changed"


# =========================================================================
# 1. A backing name swapped between the check and the backend open
# =========================================================================
@needs_symlink
@pytest.mark.parametrize("backend", BACKENDS)
def test_val_load_refuses_a_name_swapped_for_a_symlink_in_the_gap(
    staged, monkeypatch, backend
):
    root, outside, victim = staged
    module = _backend(backend)
    _force_backend(monkeypatch, module)
    base = os.path.join(root, "store")
    backing = _store_with(module, base, RELATION)
    decoy_base = os.path.join(outside, "decoy")
    decoy = _store_with(module, decoy_base, {"size": "tiny"})

    def swap():
        for name in backing:
            os.remove(os.path.join(root, name))
        for name in decoy:
            os.symlink(
                os.path.join(outside, name),
                os.path.join(root, name.replace("decoy", "store")),
            )

    _swap_before(monkeypatch, base, swap)
    with pytest.raises(PermissionError, match="Security Violation"):
        chat80.val_load(base)


@pinned
@pytest.mark.parametrize("backend", BACKENDS)
def test_val_load_refuses_a_name_swapped_for_another_file_in_the_gap(
    staged, monkeypatch, backend
):
    """The swapped-in file is a regular file in the root, so only the pinned
    inode comparison can tell it was not the file that passed the check."""
    root, outside, victim = staged
    module = _backend(backend)
    _force_backend(monkeypatch, module)
    base = os.path.join(root, "store")
    backing = _store_with(module, base, RELATION)
    decoy = _store_with(module, os.path.join(root, "decoy"), {"size": "tiny"})
    swapped = os.path.join(root, backing[0])
    replacement = os.path.join(root, decoy[0])

    def swap():
        os.replace(replacement, swapped)

    _swap_before(monkeypatch, base, swap)
    with pytest.raises(PermissionError, match="swapped between the check"):
        chat80.val_load(base)


@needs_symlink
@pytest.mark.parametrize("backend", BACKENDS)
def test_val_dump_refuses_a_name_swapped_for_a_symlink_in_the_gap(
    staged, monkeypatch, backend
):
    root, outside, victim = staged
    module = _backend(backend)
    _force_backend(monkeypatch, module)
    corpus = os.path.join(root, "corpora", "chat80")
    os.makedirs(corpus)
    with open(os.path.join(corpus, "cities.pl"), "w", encoding="utf8") as f:
        f.write("city(athens,greece,1368).\n")
    base = os.path.join(root, "store")
    backing = _store_with(module, base, RELATION)
    decoy_base = os.path.join(outside, "decoy")
    decoy = _store_with(module, decoy_base, {"size": "tiny"})

    def swap():
        for name in backing:
            os.remove(os.path.join(root, name))
        for name in decoy:
            os.symlink(
                os.path.join(outside, name),
                os.path.join(root, name.replace("decoy", "store")),
            )

    _swap_before(monkeypatch, base, swap)
    rels = [
        {
            "rel_name": "city",
            "closures": [],
            "schema": ["city", "country", "population"],
            "filename": "cities.pl",
        }
    ]
    # the write side is detected after the backend's open; what keeps an
    # outside file safe is _refuse_shared_store_dir, tested below
    with pytest.raises(PermissionError, match="Security Violation"):
        chat80.val_dump(rels, base)


@needs_symlink
def test_sql_query_is_bound_to_the_pinned_inode_not_the_name(staged, monkeypatch):
    """After the check the NAME is pointed at a decoy database; the query must
    still answer from the database that passed the check."""
    root, outside, victim = staged
    corpus = os.path.join(root, "corpora", "chat80")
    os.makedirs(corpus)
    real_db = os.path.join(corpus, "city.db")
    con = sqlite3.connect(real_db)
    con.execute("CREATE TABLE city_table (City text, Country text, Population int)")
    con.execute("INSERT INTO city_table VALUES ('athens', 'greece', 1368)")
    con.commit()
    con.close()
    decoy = os.path.join(outside, "decoy.db")
    con = sqlite3.connect(decoy)
    con.execute("CREATE TABLE city_table (City text, Country text, Population int)")
    con.execute("INSERT INTO city_table VALUES ('decoy', 'nowhere', 1)")
    con.commit()
    con.close()
    real_connect = sqlite3.connect

    def connecting(name, *args, **kwargs):
        if isinstance(name, str) and name == real_db:
            os.remove(real_db)
            os.symlink(decoy, real_db)
        return real_connect(name, *args, **kwargs)

    monkeypatch.setattr(sqlite3, "connect", connecting)
    rows = list(
        chat80.sql_query("corpora/chat80/city.db", "SELECT City FROM city_table")
    )
    assert rows == [("athens",)], rows


# =========================================================================
# 2. The store's directory must be one no other account can write
# =========================================================================
@pytest.mark.skipif(os.name != "posix", reason="directory modes are POSIX")
@pytest.mark.parametrize("mode", [0o777, 0o775, 0o757])
def test_a_store_in_a_directory_another_account_can_write_is_refused(
    staged, monkeypatch, mode
):
    root, outside, victim = staged
    module = _backend("dbm.dumb")
    _force_backend(monkeypatch, module)
    shared = os.path.join(root, "shared")
    os.mkdir(shared)
    base = os.path.join(shared, "store")
    _store_with(module, base, RELATION)
    os.chmod(shared, mode)
    try:
        with pytest.raises(PermissionError, match="writable by another account"):
            chat80.val_load(base)
        with pytest.raises(PermissionError, match="writable by another account"):
            chat80.cities2table(
                os.path.join(root, "nothing.pl"), "city", os.path.join(shared, "x.db")
            )
    finally:
        os.chmod(shared, 0o700)


@pytest.mark.skipif(os.name != "posix", reason="directory modes are POSIX")
def test_a_sticky_shared_ancestor_is_accepted_a_plain_shared_one_is_not(
    staged, monkeypatch
):
    root, outside, victim = staged
    module = _backend("dbm.dumb")
    _force_backend(monkeypatch, module)
    above = os.path.join(root, "above")
    private = os.path.join(above, "private")
    os.makedirs(private)
    base = os.path.join(private, "store")
    _store_with(module, base, RELATION)
    try:
        os.chmod(above, 0o1777)
        assert chat80.val_load(base)["size"] == "large"
        os.chmod(above, 0o777)
        with pytest.raises(PermissionError, match="not sticky"):
            chat80.val_load(base)
    finally:
        os.chmod(above, 0o700)


# =========================================================================
# 3. Benign counterparts and teeth
# =========================================================================
@pytest.mark.parametrize("backend", BACKENDS)
def test_an_unswapped_store_still_loads_per_backend(staged, monkeypatch, backend):
    root, outside, victim = staged
    module = _backend(backend)
    _force_backend(monkeypatch, module)
    base = os.path.join(root, "store")
    _store_with(module, base, RELATION)
    val = chat80.val_load(base)
    assert val["size"] == "large"
    assert set(val["city_of"]) == {"athens", "bangkok", "berlin"}


@pinned
def test_the_pinned_check_is_load_bearing(staged, monkeypatch):
    """With the post-open verification removed, the swapped-in decoy is read
    back as if it were the store that passed the check."""
    root, outside, victim = staged
    module = _backend("dbm.dumb")
    _force_backend(monkeypatch, module)
    base = os.path.join(root, "store")
    backing = _store_with(module, base, RELATION)
    decoy = _store_with(module, os.path.join(root, "decoy"), {"size": "tiny"})

    def swap():
        for name in backing:
            os.remove(os.path.join(root, name))
        for name in decoy:
            os.replace(
                os.path.join(root, name),
                os.path.join(root, name.replace("decoy", "store")),
            )

    _swap_before(monkeypatch, base, swap)
    monkeypatch.setattr(
        chat80, "_verify_store_files", lambda pins, *a, **k: chat80._close_pins(pins)
    )
    assert chat80.val_load(base)["size"] == "tiny"


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="no FIFOs on this platform")
def test_store_files_are_regular_after_the_open(staged):
    """A FIFO put in place of a backing name is refused by the post-open check
    without blocking the reader."""
    root, outside, victim = staged
    base = os.path.join(root, "store")
    os.mkfifo(base + ".db")
    with pytest.raises((PermissionError, OSError)):
        chat80._verify_store_files({}, base, context="test")
