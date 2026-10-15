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
that; their honest stores and the real packages still load.

Found by planting these files as ``corpora/panlex_lite/db.sqlite``: a view
with an endless recursive CTE hung ``__init__`` (1.2 GB in 15 s), a view of
``zeroblob(900 MB)`` rows took 4 GB from a 12 KB file, a self-joining view
hung ``translations()``, fts4/fts5/rtree tables were read as ``lv``.
"""

import os
import sqlite3

import pytest

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
