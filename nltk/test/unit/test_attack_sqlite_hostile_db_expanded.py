# Natural Language Toolkit: a hostile sqlite database as corpus data
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""A corpus database is attacker data: its SCHEMA may hold SQL the reader
runs (a view, a trigger), hand its bytes to an extension parser (a virtual
table), or make a tiny file loop or amplify. Every read-only connection from
``pathsec.connect_sqlite_read_only`` screens the schema, runs no SQL from the
file (``trusted_schema`` off) and interrupts a statement past
``MAX_SQLITE_STEPS``. Both readers on it, PanLex Lite and chat80, inherit
that; their honest stores and the real packages still load. The writer,
``chat80.cities2table``, opens a store that may already exist and gets the
same arming from ``pathsec.connect_sqlite_writable``: a trigger planted in
that store ran on its INSERT (one hung it, one wrote 3 GB in 15 s).

Found by planting these files as ``corpora/panlex_lite/db.sqlite``: a view
with an endless recursive CTE hung ``__init__`` (1.2 GB in 15 s), a view of
``zeroblob(900 MB)`` rows took 4 GB from a 12 KB file, a self-joining view
hung ``translations()``, fts4/fts5/rtree tables were read as ``lv``.
"""

import os
import shelve
import sqlite3

import pytest

import nltk.data
from nltk import pathsec
from nltk.corpus.reader.panlex_lite import PanLexLiteCorpusReader
from nltk.sem import chat80

REFUSED = (PermissionError, ValueError)

LV = (
    "CREATE TABLE lv (lv INTEGER PRIMARY KEY, lc TEXT, uid TEXT, tt TEXT);"
    "INSERT INTO lv VALUES (1,'eng','eng-000','English'),"
    "(2,'fra','fra-000','français');"
)
EX_DNX = (
    "CREATE TABLE ex (ex INTEGER PRIMARY KEY, lv INTEGER, tt TEXT);"
    "CREATE TABLE dnx (mn INTEGER, ex INTEGER, uq INTEGER, ap INTEGER, ui INTEGER);"
    "INSERT INTO ex VALUES (10, 1, 'dog'), (20, 2, 'chien');"
    "INSERT INTO dnx VALUES (100, 10, 9, 5, 7), (100, 20, 9, 5, 7);"
)
RECURSIVE = "WITH RECURSIVE n(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM n)"


def _count_to(rows):
    """A recursive CTE that stops after ``rows`` rows (the LIMIT sits inside
    the CTE; on the outer SELECT it would bound nothing)."""
    return (
        "WITH RECURSIVE n(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM n LIMIT %d)"
        " SELECT count(*) FROM n" % rows
    )


# (name, script replacing the lv table, what the schema screen must name)
HOSTILE = [
    (
        "view_endless_recursion",
        EX_DNX + "CREATE VIEW lv AS " + RECURSIVE + " SELECT x AS lv, 'eng' AS lc,"
        " 'u'||x AS uid, 'n' AS tt FROM n;",
        "view (lv)",
    ),
    (
        "view_blob_bomb",
        EX_DNX + "CREATE VIEW lv AS " + RECURSIVE + " SELECT x AS lv, 'eng' AS lc,"
        " zeroblob(900000000) AS uid, 'n' AS tt FROM n LIMIT 64;",
        "view (lv)",
    ),
    (
        "view_load_extension",
        EX_DNX + "CREATE VIEW lv AS SELECT 1 AS lv, 'eng' AS lc,"
        " load_extension('evil') AS uid, 'x' AS tt;",
        "view (lv)",
    ),
    (
        "view_self_join_on_ex",
        LV
        + EX_DNX.replace("TABLE ex ", "TABLE ex0 ").replace("INTO ex ", "INTO ex0 ")
        + "CREATE VIEW ex AS SELECT a.ex, a.lv, a.tt FROM ex0 a, ex0 b, ex0 c, ex0 d,"
        " ex0 e, ex0 f, ex0 g, ex0 h, ex0 i, ex0 j, ex0 k, ex0 l, ex0 m, ex0 n;",
        "view (ex)",
    ),
    (
        "trigger",
        LV + EX_DNX + "CREATE TRIGGER t AFTER INSERT ON lv BEGIN"
        " SELECT RAISE(ABORT, 'x'); END;",
        "trigger (t)",
    ),
    (
        "virtual_table_fts4",
        EX_DNX + "CREATE VIRTUAL TABLE lv USING fts4(lc, uid, tt);"
        "INSERT INTO lv VALUES ('eng','eng-000','English');",
        "virtual table (lv)",
    ),
    (
        "virtual_table_fts5",
        EX_DNX + "CREATE VIRTUAL TABLE lv USING fts5(lc, uid, tt);"
        "INSERT INTO lv VALUES ('eng','eng-000','English');",
        "virtual table (lv)",
    ),
    (
        "virtual_table_rtree",
        EX_DNX + "CREATE VIRTUAL TABLE lv USING rtree(lv, lc, uid, tt, x);"
        "INSERT INTO lv VALUES (1, 1, 2, 1, 2);",
        "virtual table (lv)",
    ),
    (
        "virtual_table_spelled_with_comments",
        EX_DNX + "create/* */Virtual--\n  TABLE lv USING fts5(lc, uid, tt);",
        "virtual table (lv)",
    ),
]


def _db(path, script):
    """Write a database holding ``script``, or skip when this sqlite build
    cannot (a virtual-table module it was built without)."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    connection = sqlite3.connect(path)
    try:
        connection.executescript(script)
        connection.commit()
    except sqlite3.OperationalError as exc:
        connection.close()
        pytest.skip("this sqlite cannot build the fixture: %s" % exc)
    finally:
        connection.close()
    return path


def _panlex_root(root, script=LV + EX_DNX):
    corpus = os.path.join(str(root), "panlex_lite")
    _db(os.path.join(corpus, "db.sqlite"), script)
    return corpus


def _city_db(root, script):
    name = "corpora/city_database/city.db"
    _db(os.path.join(str(root), *name.split("/")), script)
    return name


# =========================================================================
# The schema screen, through both readers
# =========================================================================
@pytest.mark.parametrize("name, script, named", HOSTILE, ids=[h[0] for h in HOSTILE])
def test_panlex_refuses_a_database_whose_schema_is_not_plain(
    restricted_sandbox, name, script, named
):
    corpus = _panlex_root(restricted_sandbox, script)
    with pytest.raises(REFUSED, match="Security Violation") as info:
        PanLexLiteCorpusReader(corpus)
    assert "schema holds a " + named in str(info.value)


@pytest.mark.parametrize("name, script, named", HOSTILE, ids=[h[0] for h in HOSTILE])
def test_chat80_sql_query_refuses_a_store_whose_schema_is_not_plain(
    restricted_sandbox, name, script, named
):
    store = _city_db(restricted_sandbox, script)
    with pytest.raises(REFUSED, match="Security Violation") as info:
        chat80.sql_query(store, "SELECT 1")
    assert "schema holds a " + named in str(info.value)


def test_honest_schemas_still_load_through_both_readers(restricted_sandbox):
    reader = PanLexLiteCorpusReader(_panlex_root(restricted_sandbox))
    assert reader.translations("eng-000", "dog", "fra-000") == [("chien", 9)]
    store = _city_db(
        restricted_sandbox,
        "CREATE TABLE city_table (City, Country, Population);"
        "CREATE INDEX by_country ON city_table (Country);"
        "INSERT INTO city_table VALUES ('shanghai', 'china', 5407);",
    )
    rows = chat80.sql_query(store, "SELECT City FROM city_table").fetchall()
    assert rows == [("shanghai",)]


def test_the_screened_connection_runs_no_sql_from_the_file(restricted_sandbox):
    corpus = _panlex_root(restricted_sandbox)
    connection = PanLexLiteCorpusReader(corpus)._c.connection
    assert connection.execute("PRAGMA trusted_schema").fetchall() == [(0,)]
    assert connection.execute("PRAGMA cell_size_check").fetchall() == [(1,)]


@pytest.mark.parametrize(
    "kind, rootpage, reason",
    [
        ("table", 2, None),
        ("index", 3, None),
        ("table", 0, "virtual table"),
        ("table", None, "virtual table"),
        ("view", 0, "view"),
        ("trigger", 0, "trigger"),
        ("index", 0, "index"),
        ("shadow", 5, "shadow"),
    ],
)
def test_plain_schema_object_classification(kind, rootpage, reason):
    assert pathsec._plain_schema_object(kind, rootpage) == reason


def test_every_hostile_fixture_is_seen_through_sqlite_own_root_pages(
    restricted_sandbox,
):
    """The screen reads rootpage, not the SQL text, so no spelling of CREATE
    VIRTUAL TABLE, comment or case, can hide one; the fixtures prove the
    column: every planted object has none, every plain table has one."""
    for name, script, named in HOSTILE:
        path = os.path.join(str(restricted_sandbox), name + ".sqlite")
        _db(path, script)
        connection = sqlite3.connect(path)
        try:
            rows = connection.execute(
                "SELECT type, name, rootpage FROM sqlite_master"
            ).fetchall()
        finally:
            connection.close()
        kind, label = named.split(" (")
        label = label.rstrip(")")
        assert [r for r in rows if r[1] == label and not r[2]], (name, rows)
        assert all(
            r[2] for r in rows if r[1] in ("ex", "dnx", "ex0") and r[0] == "table"
        )


def test_teeth_without_the_screen_a_view_is_read_as_a_table(restricted_sandbox):
    """The screen is what stops the file's SQL: with it removed the recursive
    view is executed, and only the step budget ends it."""
    corpus = _panlex_root(restricted_sandbox, HOSTILE[0][1])
    original = pathsec._plain_schema_object
    pathsec._plain_schema_object = lambda kind, sql: None
    try:
        with pytest.raises(PermissionError, match="exceeded MAX_SQLITE_STEPS"):
            PanLexLiteCorpusReader(corpus)
    finally:
        pathsec._plain_schema_object = original


# =========================================================================
# The step budget
# =========================================================================
def _connection(root):
    path = _db(os.path.join(str(root), "plain.sqlite"), "CREATE TABLE t (x);")
    return pathsec.connect_sqlite_read_only(path, context="budget-test")


def test_a_statement_past_the_budget_is_refused_with_the_security_message(
    restricted_sandbox,
):
    connection = _connection(restricted_sandbox)
    with pytest.raises(PermissionError, match=r"Security Violation \[budget-test\]"):
        connection.execute(RECURSIVE + " SELECT count(*) FROM n").fetchone()
    # the connection stays usable and the next statement starts a fresh budget
    assert connection.execute("SELECT 1").fetchall() == [(1,)]


@pytest.mark.parametrize("fetch", ["iterate", "fetchall", "fetchmany", "fetchone"])
def test_the_budget_covers_every_way_rows_are_pulled(restricted_sandbox, fetch):
    connection = _connection(restricted_sandbox)
    cursor = connection.execute(RECURSIVE + " SELECT x FROM n")
    with pytest.raises(PermissionError, match="exceeded MAX_SQLITE_STEPS"):
        if fetch == "iterate":
            for _row in cursor:
                pass
        elif fetch == "fetchall":
            cursor.fetchall()
        elif fetch == "fetchmany":
            while cursor.fetchmany(100000):
                pass
        else:
            while cursor.fetchone() is not None:
                pass


def test_the_budget_counts_per_statement_not_per_connection(
    restricted_sandbox, monkeypatch
):
    """Calibrated on the connection itself, so the step cost of the statement
    on this sqlite build does not matter: a budget 1.5x one statement lets
    three of them run in a row, which a per-connection count would refuse."""
    connection = _connection(restricted_sandbox)
    statement = _count_to(200000)
    assert connection.execute(statement).fetchone() == (200000,)
    used = connection._steps * pathsec._SQLITE_STEP_GRAIN
    assert 0 < used < pathsec.MAX_SQLITE_STEPS
    monkeypatch.setattr(pathsec, "MAX_SQLITE_STEPS", used * 3 // 2)
    for _ in range(3):
        assert connection.execute(statement).fetchone() == (200000,)
    plain = connection.cursor(factory=sqlite3.Cursor)
    with pytest.raises(sqlite3.OperationalError, match="interrupted"):
        plain.execute(statement).fetchone()


def test_a_plain_cursor_asked_for_by_a_caller_is_never_budgeted_later(
    restricted_sandbox,
):
    """A caller that bypasses the counting cursor keeps the handler but loses
    the per-statement reset, so it is interrupted no later than the budget."""
    connection = _connection(restricted_sandbox)
    cursor = connection.cursor(factory=sqlite3.Cursor)
    with pytest.raises(sqlite3.OperationalError, match="interrupted"):
        cursor.execute(RECURSIVE + " SELECT count(*) FROM n").fetchone()


def test_teeth_the_budget_is_what_ends_the_statement(restricted_sandbox, monkeypatch):
    connection = _connection(restricted_sandbox)
    bounded = _count_to(3000000)
    with pytest.raises(PermissionError, match="exceeded MAX_SQLITE_STEPS"):
        connection.execute(bounded).fetchone()
    monkeypatch.setattr(pathsec, "MAX_SQLITE_STEPS", 10**12)
    assert connection.execute(bounded).fetchone() == (3000000,)


def test_the_reader_methods_surface_the_budget_refusal(restricted_sandbox, monkeypatch):
    """Through the reader's own streaming loop and fetchall, not only a bare
    cursor: a store needing more than the budget is refused by name."""
    script = LV + EX_DNX
    corpus = _panlex_root(restricted_sandbox, script)
    db = os.path.join(corpus, "db.sqlite")
    connection = sqlite3.connect(db)
    connection.executemany(
        "INSERT INTO ex VALUES (?, 2, ?)", [(100 + i, "w%d" % i) for i in range(3000)]
    )
    connection.executemany(
        "INSERT INTO dnx VALUES (100, ?, 9, 5, ?)", [(100 + i, i) for i in range(3000)]
    )
    connection.commit()
    connection.close()
    reader = PanLexLiteCorpusReader(corpus)
    assert len(reader.translations("eng-000", "dog", "fra-000")) == 3001
    monkeypatch.setattr(pathsec, "MAX_SQLITE_STEPS", 50000)
    with pytest.raises(PermissionError, match=r"\[PanLexLiteCorpusReader\]"):
        reader.translations("eng-000", "dog", "fra-000")
    with pytest.raises(PermissionError, match="exceeded MAX_SQLITE_STEPS"):
        reader.meanings("eng-000", "dog")


# =========================================================================
# Parameters and sidecars against an honest store
# =========================================================================
@pytest.mark.parametrize(
    "text",
    [
        "dog\0' OR 1=1 --",
        "d" * 10_000_000,
        b"dog",
        None,
        "dog' UNION SELECT name, 1 FROM sqlite_master --",
        "%",
        "_og",
    ],
    ids=[
        "nul",
        "ten-megabytes",
        "bytes",
        "none",
        "union-injection",
        "percent",
        "underscore",
    ],
)
def test_query_parameters_are_bound_not_spliced(restricted_sandbox, text):
    reader = PanLexLiteCorpusReader(_panlex_root(restricted_sandbox))
    assert reader.translations("eng-000", text, "fra-000") == []
    assert reader.meanings("eng-000", text) == []
    # lc=None is the documented "every variety"; anything else is one code
    expected = [("eng-000", "English"), ("fra-000", "fran\u00e7ais")]
    assert reader.language_varieties(text) == (expected if text is None else [])
    assert reader.translations("eng-000", "dog", "fra-000") == [("chien", 9)]


@pytest.mark.parametrize("route", ["descriptor", "by-name"])
def test_a_hot_journal_beside_the_database_is_neither_replayed_nor_touched(
    restricted_sandbox, monkeypatch, route
):
    """Both routes open the file immutable: the descriptor route (POSIX) and
    the by-name route (Windows, forced here by hiding /dev/fd), which without
    immutable=1 tried to roll the planted journal back and failed read-only."""
    if route == "by-name":
        real_isdir = os.path.isdir
        monkeypatch.setattr(
            pathsec.os.path,
            "isdir",
            lambda p: False if p == "/dev/fd" else real_isdir(p),
        )
    corpus = _panlex_root(restricted_sandbox)
    journal = os.path.join(corpus, "db.sqlite-journal")
    payload = b"\xd9\xd5\x05\xf9\x20\xa1\x63\xd7" + b"\0" * 504
    with open(journal, "wb") as handle:
        handle.write(payload)
    before = sorted(os.listdir(corpus))
    reader = PanLexLiteCorpusReader(corpus)
    assert reader.translations("eng-000", "dog", "fra-000") == [("chien", 9)]
    assert sorted(os.listdir(corpus)) == before
    with open(journal, "rb") as handle:
        assert handle.read() == payload


# =========================================================================
# The write sink: cities2table on a store that already exists
# =========================================================================
CITY_TABLE = "CREATE TABLE city_table (City text, Country text, Population int);"
ENDLESS_COUNT = "(" + RECURSIVE + " SELECT count(*) FROM n)"

# (name, script of the planted store, what the schema screen must name)
HOSTILE_STORE = [
    (
        "trigger_endless_cte_on_insert",
        CITY_TABLE + "CREATE TRIGGER t AFTER INSERT ON city_table BEGIN"
        " SELECT RAISE(ABORT, 'x') WHERE " + ENDLESS_COUNT + " < 0; END;",
        "trigger (t)",
    ),
    (
        "trigger_blob_bomb_on_insert",
        CITY_TABLE + "CREATE TABLE bomb (b BLOB);"
        "CREATE TRIGGER t AFTER INSERT ON city_table BEGIN INSERT INTO bomb"
        " SELECT zeroblob(200000000) FROM (" + RECURSIVE + " SELECT x FROM n"
        " LIMIT 20); END;",
        "trigger (t)",
    ),
    (
        "view_in_place_of_the_table_with_instead_of_trigger",
        "CREATE TABLE real_rows (City, Country, Population);"
        "CREATE VIEW city_table AS SELECT * FROM real_rows;"
        "CREATE TRIGGER t INSTEAD OF INSERT ON city_table BEGIN"
        " SELECT RAISE(ABORT, 'x') WHERE " + ENDLESS_COUNT + " < 0; END;",
        "view (city_table)",
    ),
    (
        "virtual_table_fts5_as_the_table",
        "CREATE VIRTUAL TABLE city_table USING fts5(City, Country, Population);",
        "virtual table (city_table)",
    ),
]


@pytest.fixture
def city_corpus(restricted_sandbox):
    """The sandbox root with a three-city ``city`` relation under
    ``corpora/chat80``; the data cache is dropped both ways so the tiny corpus
    and a real one never mix."""
    corpus = os.path.join(restricted_sandbox, "corpora", "chat80")
    os.makedirs(corpus)
    with open(os.path.join(corpus, "atk.pl"), "w", encoding="utf8") as handle:
        handle.write(
            "city(athens,greece,1368).\ncity(bangkok,thailand,1178).\n"
            "city(shanghai,china,5407).\n"
        )
    nltk.data.clear_cache()
    yield restricted_sandbox
    nltk.data.clear_cache()


def _store_bytes(path):
    with open(path, "rb") as handle:
        return handle.read()


def _rows(path):
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        return connection.execute("SELECT City FROM city_table").fetchall()
    finally:
        connection.close()


@pytest.mark.parametrize(
    "name, script, named", HOSTILE_STORE, ids=[h[0] for h in HOSTILE_STORE]
)
@pytest.mark.parametrize("setup", [False, True])
def test_cities2table_refuses_a_planted_store_whose_schema_is_not_plain(
    city_corpus, name, script, named, setup
):
    """A store that already exists at the caller's path is attacker data: a
    trigger in it runs on cities2table's own INSERT (the endless one hung the
    writer, the blob one wrote 3 GB in 15 s), and so does an INSTEAD OF
    trigger on a view standing in for the table. Refused before any write,
    whichever way the caller opens it."""
    db = _db(os.path.join(city_corpus, "city.db"), script)
    before = _store_bytes(db)
    with pytest.raises(REFUSED, match="Security Violation") as info:
        chat80.cities2table("atk.pl", "city", db, setup=setup)
    assert "schema holds a " + named in str(info.value)
    assert _store_bytes(db) == before
    assert sorted(os.listdir(city_corpus)) == ["city.db", "corpora"]


def test_cities2table_appends_to_an_honest_existing_store(city_corpus):
    db = _db(os.path.join(city_corpus, "city.db"), CITY_TABLE)
    chat80.cities2table("atk.pl", "city", db, setup=False)
    chat80.cities2table("atk.pl", "city", db, setup=False)
    assert _rows(db) == [("athens",), ("bangkok",), ("shanghai",)] * 2


def test_cities2table_builds_a_fresh_store_on_the_armed_connection(city_corpus):
    db = os.path.join(city_corpus, "city.db")
    chat80.cities2table("atk.pl", "city", db, setup=True)
    assert _rows(db) == [("athens",), ("bangkok",), ("shanghai",)]
    with pytest.raises(sqlite3.OperationalError, match="already exists"):
        chat80.cities2table("atk.pl", "city", db, setup=True)


def test_cities2table_write_is_budgeted_past_the_screen(city_corpus, monkeypatch):
    """Teeth for the second layer on the writer: with the schema screen
    disarmed, the planted trigger does run on the INSERT, and the step budget
    ends it with the security message instead of a hang; nothing is
    committed."""
    monkeypatch.setattr(pathsec, "_plain_schema_object", lambda kind, root: None)
    db = _db(os.path.join(city_corpus, "city.db"), HOSTILE_STORE[0][1])
    with pytest.raises(PermissionError, match="MAX_SQLITE_STEPS") as info:
        chat80.cities2table("atk.pl", "city", db, setup=False)
    assert "Security Violation [chat80.cities2table]" in str(info.value)
    assert _rows(db) == []


def test_connect_sqlite_writable_creates_and_arms_the_store(restricted_sandbox):
    db = os.path.join(restricted_sandbox, "fresh.db")
    connection = pathsec.connect_sqlite_writable(db, context="t")
    try:
        assert os.path.isfile(db)
        assert connection.execute("PRAGMA trusted_schema").fetchall() == [(0,)]
        assert connection.execute("PRAGMA cell_size_check").fetchall() == [(1,)]
        with pytest.raises(sqlite3.DatabaseError, match="not authorized"):
            connection.execute("ATTACH DATABASE ':memory:' AS other")
        connection.execute("CREATE TABLE t (x)")
        connection.execute("INSERT INTO t VALUES (1)")
        connection.commit()
        assert connection.execute("SELECT x FROM t").fetchall() == [(1,)]
        with pytest.raises(PermissionError, match="MAX_SQLITE_STEPS"):
            connection.execute(RECURSIVE + " SELECT count(*) FROM n").fetchall()
    finally:
        connection.close()


@pytest.mark.parametrize("suffix", ["", "-journal", "-wal", "-shm"])
def test_connect_sqlite_writable_refuses_a_link_at_any_name(restricted_sandbox, suffix):
    target = _db(os.path.join(restricted_sandbox, "elsewhere.db"), CITY_TABLE)
    db = os.path.join(restricted_sandbox, "store.db")
    os.symlink(target, db + suffix)
    before = _store_bytes(target)
    with pytest.raises(REFUSED, match="Security Violation"):
        pathsec.connect_sqlite_writable(db, context="t")
    assert _store_bytes(target) == before


# =========================================================================
# The valuation store: val_load on a sqlite file at the store name
# =========================================================================
DICT = "CREATE TABLE Dict (key BLOB UNIQUE NOT NULL, value BLOB NOT NULL);"

# (name, script of the planted store, what the schema screen must name)
HOSTILE_VALUATION = [
    (
        "view_endless_recursion",
        "CREATE VIEW Dict AS " + RECURSIVE + " SELECT CAST(x AS BLOB) AS key,"
        " X'80' AS value FROM n;",
        "view (Dict)",
    ),
    (
        "view_blob_bomb",
        "CREATE VIEW Dict AS " + RECURSIVE + " SELECT zeroblob(900000000) AS key,"
        " X'80' AS value FROM n LIMIT 64;",
        "view (Dict)",
    ),
    (
        "virtual_table_fts5",
        "CREATE VIRTUAL TABLE Dict USING fts5(key, value);",
        "virtual table (Dict)",
    ),
    (
        "trigger",
        DICT + "CREATE TRIGGER t AFTER INSERT ON Dict BEGIN"
        " SELECT RAISE(ABORT, 'x'); END;",
        "trigger (t)",
    ),
]


def _sqlite_valuation(path, raw_items):
    """A store in the dbm.sqlite3 layout holding ``raw_items`` (bytes key,
    pickled value), built by hand so the route is driven on every Python,
    not only where dbm itself writes sqlite."""
    _db(path, DICT)
    connection = sqlite3.connect(path)
    with connection:
        connection.executemany(
            "INSERT INTO Dict VALUES (CAST(? AS BLOB), CAST(? AS BLOB))", raw_items
        )
    connection.close()
    return path


def _real_store(root):
    """val_dump's own store for a three-city corpus under the sandbox, the
    Valuation it loads to, and its raw (key, value) pairs."""
    corpus = os.path.join(root, "corpora", "chat80")
    os.makedirs(corpus)
    with open(os.path.join(corpus, "cities.pl"), "w", encoding="utf8") as handle:
        handle.write(
            "city(athens,greece,1368).\ncity(bangkok,thailand,1178).\n"
            "city(shanghai,china,5407).\n"
        )
    nltk.data.clear_cache()
    base = os.path.join(root, "dumped")
    chat80.val_dump([chat80.city], base)
    loaded = chat80.val_load(base)
    with shelve.open(base, "r") as shelf:
        raw = [(key.encode("utf-8"), shelf.dict[key.encode("utf-8")]) for key in shelf]
    nltk.data.clear_cache()
    return loaded, raw


@pytest.mark.parametrize(
    "name, script, named", HOSTILE_VALUATION, ids=[h[0] for h in HOSTILE_VALUATION]
)
def test_val_load_refuses_a_sqlite_store_whose_schema_is_not_plain(
    restricted_sandbox, name, script, named
):
    """dbm picks its sqlite backend (Python 3.13+) by file header and ran the
    planted schema on val_load's first lookup: the endless view hung it, the
    blob view took 1.9 GB, the fts5 table was accepted as the store. The
    store now opens on the armed connector, which refuses them by name."""
    store = _db(os.path.join(restricted_sandbox, "store"), script)
    before = _store_bytes(store)
    with pytest.raises(PermissionError, match="Security Violation") as info:
        chat80.val_load(store)
    assert "schema holds a " + named in str(info.value)
    assert _store_bytes(store) == before
    assert sorted(os.listdir(restricted_sandbox)) == ["store"]


def test_val_load_reads_a_sqlite_store_on_the_armed_connection(
    restricted_sandbox, monkeypatch
):
    """The real pairs val_dump wrote, copied into a hand-built sqlite store,
    load to the same Valuation through the connector on every Python."""
    loaded, raw = _real_store(restricted_sandbox)
    assert loaded["city"] == ["athens", "bangkok", "shanghai"]
    assert b"__nltk_keys__" in dict(raw) and len(raw) > 2
    contexts = []
    real_connect = pathsec.connect_sqlite_read_only

    def spy(path, names=None, context="", **kwargs):
        contexts.append(context)
        return real_connect(path, names=names, context=context, **kwargs)

    monkeypatch.setattr(pathsec, "connect_sqlite_read_only", spy)
    copy = _sqlite_valuation(os.path.join(restricted_sandbox, "copy"), raw)
    assert chat80.val_load(copy) == loaded
    assert contexts == ["chat80._restricted_shelve_open"]


def test_val_load_never_queries_a_view_named_dict_even_without_the_screen(
    restricted_sandbox, monkeypatch
):
    """Second line behind the screen: the store must hold the backend's own
    ``Dict`` TABLE, so with the screen disarmed the endless view is still
    never queried; the file is reported unreadable like any other."""
    monkeypatch.setattr(pathsec, "_plain_schema_object", lambda kind, root: None)
    store = _db(os.path.join(restricted_sandbox, "store"), HOSTILE_VALUATION[0][1])
    with pytest.raises(SystemExit, match="Cannot read file"):
        chat80.val_load(store)


def test_val_load_statements_are_budgeted(restricted_sandbox, monkeypatch):
    """The budget reaches the store's own lookups: a plain ``Dict`` without
    the backend's unique index is scanned per lookup, and with the budget
    set below one scan the first lookup is refused with the security
    message, before the manifest check that would refuse the padding."""
    _loaded, raw = _real_store(restricted_sandbox)
    store = _sqlite_valuation(os.path.join(restricted_sandbox, "copy"), raw)
    connection = sqlite3.connect(store)
    with connection:
        connection.executescript(
            "CREATE TABLE wide (key BLOB, value BLOB);"
            "INSERT INTO wide SELECT key, value FROM Dict;"
            "INSERT INTO wide "
            + _count_to(20000).replace(
                "SELECT count(*) FROM n", "SELECT 'k' || x, X'80' FROM n"
            )
            + ";"
            "DROP TABLE Dict; ALTER TABLE wide RENAME TO Dict;"
        )
    connection.close()
    # the padding keys are refused by the manifest check, after the lookups
    with pytest.raises(ValueError, match="manifest does not name"):
        chat80.val_load(store)
    monkeypatch.setattr(pathsec, "MAX_SQLITE_STEPS", 1000)
    with pytest.raises(PermissionError, match="MAX_SQLITE_STEPS") as info:
        chat80.val_load(store)
    assert "Security Violation [chat80._restricted_shelve_open]" in str(info.value)


def test_val_load_ignores_a_hot_journal_beside_a_sqlite_store(restricted_sandbox):
    loaded, raw = _real_store(restricted_sandbox)
    copy = _sqlite_valuation(os.path.join(restricted_sandbox, "copy"), raw)
    payload = b"\xd9\xd5\x05\xf9\x20\xa1\x63\xd7" + b"\0" * 504
    with open(copy + "-journal", "wb") as handle:
        handle.write(payload)
    before = sorted(os.listdir(restricted_sandbox))
    assert chat80.val_load(copy) == loaded
    assert sorted(os.listdir(restricted_sandbox)) == before
    assert _store_bytes(copy + "-journal") == payload


@pytest.mark.parametrize(
    "script", ["CREATE TABLE other (x);", DICT.replace("Dict", "dict")]
)
def test_val_load_reports_a_sqlite_file_without_the_backend_table_as_unreadable(
    restricted_sandbox, script
):
    store = _db(os.path.join(restricted_sandbox, "store"), script)
    with pytest.raises(SystemExit, match="Cannot read file"):
        chat80.val_load(store)


def test_val_load_sqlite_store_without_manifest_is_still_refused(restricted_sandbox):
    store = _db(os.path.join(restricted_sandbox, "store"), DICT)
    with pytest.raises(ValueError, match="no key manifest"):
        chat80.val_load(store)


def test_is_sqlite_store_decides_on_the_pinned_handle_and_dbm_precedence(
    restricted_sandbox,
):
    store = _db(os.path.join(restricted_sandbox, "store"), DICT)
    with open(store, "rb") as handle:
        assert chat80._is_sqlite_store(store, {store: handle})
        assert handle.tell() == 0
        with open(store, "rb") as sibling:
            assert not chat80._is_sqlite_store(
                store, {store: handle, store + ".dir": sibling}
            )
    assert not chat80._is_sqlite_store(store, {})
    other = os.path.join(restricted_sandbox, "plain")
    with open(other, "wb") as handle:
        handle.write(b"not a database at all, just bytes")
    with open(other, "rb") as handle:
        assert not chat80._is_sqlite_store(other, {other: handle})
