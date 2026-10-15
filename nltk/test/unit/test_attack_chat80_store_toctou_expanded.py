"""The chat80 store between the path check and the backend's own open.

shelve, dbm and sqlite reopen a store's backing names by path after NLTK has
checked them (CWE-367). Every case here swaps a backing name in exactly that
gap, deterministically, by wrapping the backend's open; a benign counterpart
shows the same call still works when nothing is swapped. The outside target
carries SENTINEL and must never be read back or changed.

Where the OS will not rename or remove a file while a handle holds it open,
the held pin itself stops the swap; the cases then require that nothing
changed and that the call answers from the store that passed the check.
"""

import dbm
import importlib
import os
import re
import shelve
import sqlite3
import stat

import pytest

import nltk.data
from nltk import pathsec
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


def _listing(folder):
    """What each name in *folder* is, to show a refused swap changed nothing."""
    listing = {}
    for name in sorted(os.listdir(folder)):
        st = os.lstat(os.path.join(folder, name))
        listing[name] = (stat.S_IFMT(st.st_mode), st.st_ino, st.st_size)
    return listing


def _attempt(outcome, folder, swap):
    """Run the attacker's *swap* once and record whether it happened ("swapped")
    or the OS refused it because a pinned handle holds the name ("held")."""
    if outcome:
        return
    before = _listing(folder)
    try:
        swap()
    except PermissionError as exc:
        assert _listing(folder) == before, f"a refused swap changed the store: {exc}"
        outcome["held"] = exc
    else:
        outcome["swapped"] = True


def _swap_before(monkeypatch, target, swap):
    """Attempt *swap* right before the backend opens *target* by name; returns
    the outcome record :func:`_attempt` fills. A sqlite store is opened by
    ``pathsec.connect_sqlite_read_only`` instead of ``shelve.open``, so both
    opens are hooked and the swap lands in whichever gap the store takes."""
    real = shelve.open
    real_connect = pathsec.connect_sqlite_read_only
    outcome = {}

    def opening(name, *args, **kwargs):
        if name == target:
            _attempt(outcome, os.path.dirname(target), swap)
        return real(name, *args, **kwargs)

    def connecting(path, *args, **kwargs):
        if path == target:
            _attempt(outcome, os.path.dirname(target), swap)
        return real_connect(path, *args, **kwargs)

    monkeypatch.setattr(shelve, "open", opening)
    monkeypatch.setattr(pathsec, "connect_sqlite_read_only", connecting)
    return outcome


def _checked_or_refused(outcome, call, match):
    """Run *call* after a swap attempt. It either returns, and the caller checks
    the result is the checked store's, or it refuses with *match*, which only a
    swap that happened can justify. Returns the result, or None when refused."""
    try:
        result = call()
    except PermissionError as exc:
        assert outcome.get("swapped"), f"refused although nothing was swapped: {exc}"
        assert re.search(match, str(exc)), exc
        return None
    assert outcome, "the swap was never attempted"
    return result


def _assert_checked_store(result):
    if result is not None:
        assert result["size"] == "large", "the swapped-in store was read"
        assert set(result["city_of"]) == {"athens", "bangkok", "berlin"}


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

    outcome = _swap_before(monkeypatch, base, swap)
    result = _checked_or_refused(
        outcome, lambda: chat80.val_load(base), "Security Violation"
    )
    _assert_checked_store(result)


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

    outcome = _swap_before(monkeypatch, base, swap)
    result = _checked_or_refused(
        outcome, lambda: chat80.val_load(base), "swapped between the check"
    )
    _assert_checked_store(result)


def _write_city_corpus(root):
    corpus = os.path.join(root, "corpora", "chat80")
    os.makedirs(corpus)
    with open(os.path.join(corpus, "cities.pl"), "w", encoding="utf8") as f:
        f.write("city(athens,greece,1368).\n")
    return [
        {
            "rel_name": "city",
            "closures": [],
            "schema": ["city", "country", "population"],
            "filename": "cities.pl",
        }
    ]


def _read_all(folder, names):
    out = {}
    for name in names:
        with open(os.path.join(folder, name), "rb") as f:
            out[name] = f.read()
    return out


@pytest.mark.parametrize("backend", BACKENDS)
def test_val_dump_refuses_names_swapped_for_symlinks_while_it_writes(
    staged, monkeypatch, backend
):
    """The backend writes inside a fresh private directory, never at the store's
    names; links planted there meanwhile are refused when the store is put in
    place, and the outside decoy store is left byte for byte as it was."""
    root, outside, victim = staged
    module = _backend(backend)
    _force_backend(monkeypatch, module)
    rels = _write_city_corpus(root)
    base = os.path.join(root, "store")
    backing = _store_with(module, base, RELATION)
    decoy = _store_with(module, os.path.join(outside, "decoy"), {"size": "tiny"})
    decoy_bytes = _read_all(outside, decoy)

    def swap():
        for name in backing:
            os.remove(os.path.join(root, name))
        for name in decoy:
            os.symlink(
                os.path.join(outside, name),
                os.path.join(root, name.replace("decoy", "store")),
            )

    real = shelve.open
    outcome = {}

    def writing(name, *args, **kwargs):
        shelf = real(name, *args, **kwargs)
        assert os.path.dirname(name) != root, "the backend opened a store name"
        _attempt(outcome, root, swap)
        return shelf

    monkeypatch.setattr(shelve, "open", writing)
    with pytest.raises(PermissionError, match="Security Violation"):
        chat80.val_dump(rels, base)
    assert outcome.get("swapped")
    assert _read_all(outside, decoy) == decoy_bytes
    _assert_untouched(victim)


@pytest.mark.parametrize("backend", BACKENDS)
def test_val_dump_replaces_a_name_planted_at_the_rename_never_follows_it(
    staged, monkeypatch, backend
):
    """A link planted at a store name just before val_dump renames the new file
    onto it is replaced, not followed: the decoy is untouched and the store is
    the one just written."""
    root, outside, victim = staged
    module = _backend(backend)
    _force_backend(monkeypatch, module)
    rels = _write_city_corpus(root)
    base = os.path.join(root, "store")
    _store_with(module, base, RELATION)
    decoy = _store_with(module, os.path.join(outside, "decoy"), {"size": "tiny"})
    decoy_bytes = _read_all(outside, decoy)
    real = os.replace
    planted = []

    def replacing(src, dst, *args, **kwargs):
        if os.path.dirname(os.path.abspath(dst)) == os.path.abspath(root):
            target = os.path.join(outside, decoy[0])
            if os.path.lexists(dst):
                os.remove(dst)
            os.symlink(target, dst)
            planted.append(dst)
        return real(src, dst, *args, **kwargs)

    monkeypatch.setattr(os, "replace", replacing)
    chat80.val_dump(rels, base)
    monkeypatch.setattr(os, "replace", real)
    assert planted
    assert _read_all(outside, decoy) == decoy_bytes
    for name in planted:
        assert stat.S_ISREG(os.lstat(name).st_mode)
    val = chat80.val_load(base)
    assert val["city"] == ["athens"]
    _assert_untouched(victim)


@pytest.mark.parametrize("backend", BACKENDS)
def test_val_dump_replaces_an_existing_store(staged, monkeypatch, backend):
    """Dumping over an existing store replaces it whole: no key of the old one
    survives, and no staging directory is left behind."""
    root, outside, victim = staged
    module = _backend(backend)
    _force_backend(monkeypatch, module)
    rels = _write_city_corpus(root)
    base = os.path.join(root, "store")
    _store_with(module, base, {"stale": "old"})
    before = set(os.listdir(root))
    chat80.val_dump(rels, base)
    chat80.val_dump(rels, base)
    val = chat80.val_load(base)
    assert "stale" not in val and val["city"] == ["athens"]
    # sqlite leaves empty -wal/-shm sidecars after a read-only open on every
    # tree; what must not remain is a staging directory
    assert not [n for n in os.listdir(root) if n.startswith(".nltk_chat80_")]


def test_sql_query_is_bound_to_the_pinned_inode_not_the_name(staged, monkeypatch):
    """Right before sqlite opens anything the NAME is pointed at a decoy
    database; the query must still answer from the database that passed the
    check, or be refused."""
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
    outcome = {}

    def swap():
        os.remove(real_db)
        os.symlink(decoy, real_db)

    def connecting(name, *args, **kwargs):
        _attempt(outcome, corpus, swap)
        return real_connect(name, *args, **kwargs)

    monkeypatch.setattr(sqlite3, "connect", connecting)
    rows = _checked_or_refused(
        outcome,
        lambda: list(
            chat80.sql_query("corpora/chat80/city.db", "SELECT City FROM city_table")
        ),
        "Security Violation",
    )
    if rows is not None:
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


@pytest.mark.parametrize("mutant", ["no post-open check", "pins released at once"])
def test_the_pinned_check_is_load_bearing(staged, monkeypatch, mutant):
    """With the defence taken apart the swapped-in decoy is read back as if it
    were the store that passed the check. With only the post-open check gone
    the pins are still held, and where the OS will not swap a held name they
    alone stop the swap, so the checked store is read."""
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

    outcome = _swap_before(monkeypatch, base, swap)
    monkeypatch.setattr(
        chat80, "_verify_store_files", lambda pins, *a, **k: pathsec.release(pins)
    )
    if mutant == "pins released at once":
        pin = chat80._pin_store_files
        monkeypatch.setattr(
            chat80,
            "_pin_store_files",
            lambda base, context: pathsec.release(pin(base, context)) or {},
        )
    size = chat80.val_load(base)["size"]
    if outcome.get("held"):
        assert mutant == "no post-open check", outcome
        assert size == "large"
    else:
        assert outcome.get("swapped")
        assert size == "tiny"


@pytest.mark.parametrize("kind", ["directory", "fifo"])
def test_store_files_are_regular_after_the_open(staged, kind):
    """A directory or FIFO put in place of a backing name is refused by the
    post-open check, which inspects the name and never opens it to block."""
    root, outside, victim = staged
    base = os.path.join(root, "store")
    make = os.mkdir if kind == "directory" else getattr(os, "mkfifo", None)
    if make is None:
        pytest.skip("this filesystem has no FIFOs")
    make(base + ".db")
    with pytest.raises(PermissionError, match="no longer a regular file"):
        chat80._verify_store_files({}, base, context="test")
