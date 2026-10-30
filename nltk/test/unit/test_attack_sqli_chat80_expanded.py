# Natural Language Toolkit: SQL-injection attack tests (chat80)
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""SQL-injection attack tests for the parameterized sqlite sink in
``nltk.sem.chat80.cities2table``.

Corpus field values reach sqlite only through a bound-parameter INSERT
(``insert into city_table values (?,?,?)``), so a crafted field value such as
``' OR 1=1 --`` or ``;DROP TABLE city_table;--`` is stored as a literal string
and cannot alter the statement. These tests drive the REAL ``cities2table``
end-to-end: a crafted Prolog corpus file is placed under a sandbox data root,
parsed by the real ``_str2records``, and inserted by the real sqlite cursor;
the resulting database is then inspected to prove the payloads were bound, the
table survived, and a benign row still returns the right answer.
"""

import inspect
import os
import sqlite3

import pytest

from nltk.sem import chat80

# The ``restricted_sandbox`` fixture is provided by nltk/test/unit/conftest.py:
# it enforces pathsec against a single throwaway data root and points
# nltk.data.path at it, so both the crafted corpus file and the db live inside
# the sandbox (cities2table validate_path()s the db path).

# Every payload is a single Chat-80 field value. Chat-80 uses the comma as its
# field delimiter, so payloads are deliberately comma-free (a comma would just
# be parsed as a field boundary, never reaching SQL); each still carries the
# quote / semicolon / comment / UNION / backslash tricks that a naive string
# concat would honour.
SQLI_PAYLOADS = {
    "or_1_eq_1": "z' OR 1=1 --",
    "stacked_drop": "z';DROP TABLE city_table;--",
    "stacked_delete": "z'); DELETE FROM city_table; --",
    "union_select": "z' UNION SELECT name FROM sqlite_master --",
    "comment_inline": "z'/**/OR/**/'1'='1",
    "quote_backslash": "z' \" \\ --",
    "double_quote": 'z" OR "1"="1',
    "unicode_quote": "z’ OR 1=1 --",  # U+2019 right single quote
    "null_byte_ish": "z'||(SELECT sqlite_version())||'",
}

BENIGN = ("athens", "greece", 1368)


def _write_corpus(root, records, relfile):
    """Write ``records`` as a Chat-80 ``city(...)`` Prolog file under the
    sandbox data root's ``corpora/chat80`` dir, where nltk.data.load finds it."""
    chat80_dir = os.path.join(root, "corpora", "chat80")
    os.makedirs(chat80_dir, exist_ok=True)
    path = os.path.join(chat80_dir, relfile)
    with open(path, "w", encoding="utf8") as f:
        for city, country, pop in records:
            f.write(f"city({city},{country},{pop}).\n")
    return path


def _build_table(root, records, relfile="sqli.pl", dbname="cities_sqli.db"):
    """Drive the REAL cities2table over a crafted corpus, returning the db path."""
    _write_corpus(root, records, relfile)
    db = os.path.join(root, dbname)
    chat80.cities2table(relfile, "city", db, setup=True)
    return db


def test_cities2table_binds_values_no_concat_source():
    """Static guard: the sink uses placeholder binding, never a value spliced
    into the SQL text. The only ``%`` formatting is the fixed table name."""
    src = inspect.getsource(chat80.cities2table)
    assert "values (?,?,?)" in src
    # The record tuple is passed as the 2nd arg to execute(), i.e. bound.
    assert "execute(" in src and "% table_name, t)" in src


def test_all_payloads_are_bound_and_roundtrip(restricted_sandbox):
    """Every SQLi payload is stored verbatim (proving it was a bound parameter,
    not interpreted as SQL) and the table survives the DROP/DELETE payloads."""
    root = restricted_sandbox
    # population index lets us look each crafted row back up unambiguously
    records = [BENIGN]
    payload_pop = {}
    for i, (name, payload) in enumerate(SQLI_PAYLOADS.items(), start=1):
        pop = 1000 + i
        payload_pop[name] = (payload, pop)
        records.append((payload, "france", pop))

    db = _build_table(root, records)

    con = sqlite3.connect(db)
    try:
        cur = con.cursor()
        # 1. table survived every stacked DROP/DELETE payload
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='city_table'"
        )
        assert cur.fetchone() is not None, "city_table was dropped by a payload"

        # 2. no row was deleted: every record we wrote is present
        cur.execute("SELECT COUNT(*) FROM city_table")
        assert cur.fetchone()[0] == len(records)

        # 3. each payload round-trips byte-for-byte -> it was bound, not parsed
        for name, (payload, pop) in payload_pop.items():
            cur.execute("SELECT City FROM city_table WHERE Population = ?", (pop,))
            stored = cur.fetchone()
            assert stored is not None, f"payload row missing: {name}"
            assert stored[0] == payload, f"payload mutated for {name}: {stored[0]!r}"
    finally:
        con.close()


def test_benign_query_returns_right_answer(restricted_sandbox):
    """A legitimate field value is inserted and read back correctly (BENIGN)."""
    root = restricted_sandbox
    db = _build_table(root, [BENIGN, ("paris_city", "france", 999)])
    con = sqlite3.connect(db)
    try:
        cur = con.cursor()
        cur.execute(
            "SELECT Country, Population FROM city_table WHERE City = ?", ("athens",)
        )
        row = cur.fetchone()
        assert row == ("greece", 1368)
    finally:
        con.close()


def test_sql_query_benign_reads_installed_corpus():
    """Drive the real sql_query() against the installed city.db (BENIGN)."""
    import nltk.data

    try:
        nltk.data.find("corpora/city_database/city.db")
    except LookupError:
        pytest.skip("city_database corpus not installed")

    cur = chat80.sql_query(
        "corpora/city_database/city.db",
        "SELECT Country FROM city_table WHERE City = 'athens'",
    )
    assert cur.fetchall() == [("greece",)]
