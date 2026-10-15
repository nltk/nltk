# Natural Language Toolkit: the PanLex readers on the corpora NLTK ships
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""The PanLex Swadesh and PanLex Lite readers on the real packages, every
public method, through the loaders in ``nltk.corpus``. Skipped where a
package is not installed (CI has neither); run locally after
``nltk.download("panlex_swadesh")`` and ``nltk.download("panlex_lite")``."""

import os

import pytest

import nltk
from nltk.corpus.reader.panlex_lite import PanLexLiteCorpusReader
from nltk.corpus.reader.panlex_swadesh import PanlexLanguage


def _swadesh(size="110"):
    from nltk.corpus import swadesh110, swadesh207

    reader = swadesh110 if size == "110" else swadesh207
    try:
        reader.fileids()
    except LookupError:
        pytest.skip("panlex_swadesh is not installed")
    return reader


def _lite():
    try:
        root = nltk.data.find("corpora/panlex_lite")
    except LookupError:
        pytest.skip("panlex_lite is not installed")
    return PanLexLiteCorpusReader(str(root))


def test_swadesh_reader_lists_the_shipped_languages():
    reader = _swadesh()
    assert reader.swadesh_size == "110"
    assert reader.license() == "CC0 1.0 Universal"
    languages = list(reader.get_languages())
    assert len(languages) > 1000
    assert all(isinstance(lang, PanlexLanguage) for lang in languages)
    assert "eng-000" in reader.language_codes()
    assert len(reader.fileids()) == len(languages)


def test_swadesh_reader_reads_words_entries_and_macrolanguages():
    reader = _swadesh()
    eng = reader.words_by_lang("eng-000")
    assert len(eng) == 110 and ["bark"] in eng and ["all", "every"] in eng
    fra = reader.words_by_iso639("fra")
    assert len(fra) >= 110 and ["\u00e9corce"] in fra
    entries = reader.entries(["swadesh110/eng-000.txt", "swadesh110/fra-000.txt"])
    # zip() stops at the shorter list: fra-000 has 107 concepts
    assert len(entries) == 107 and entries[0] == ("all\tevery", "chaque\ttous\ttout")
    assert "eng-000" in reader.get_macrolanguages()["eng"]
    big = _swadesh("207")
    assert big.swadesh_size == "207" and len(big.words_by_lang("eng-000")) == 207
    assert big.entries(["swadesh207/eng-000.txt", "swadesh207/fra-000.txt"])[0] == (
        "1 sg.\tI",
        "je\tmoi",
    )


def test_swadesh_reader_refuses_a_file_id_that_leaves_the_corpus():
    reader = _swadesh()
    with pytest.raises((ValueError, PermissionError, OSError)):
        reader.words_by_lang("../../../etc/passwd")


def test_lite_reader_is_a_corpus_reader_on_the_shipped_database():
    reader = _lite()
    assert reader.fileids() == ["db.sqlite"]
    assert os.path.isfile(os.path.join(str(reader.root), "db.sqlite"))
    # the shipped package is gone; a database rebuilt from PanLex's own data
    # (see its README.txt) holds at least the English and French varieties
    varieties = reader.language_varieties()
    assert len(varieties) >= 100
    assert ("eng-000", "English") in varieties
    assert ("fra-000", "fran\u00e7ais") in varieties
    assert reader.language_varieties("fra")[0][0].startswith("fra-")


def test_lite_reader_translates_and_lists_meanings_on_the_shipped_database():
    reader = _lite()
    translations = reader.translations("eng-000", "dog", "fra-000")
    assert translations and all(isinstance(q, int) for _, q in translations)
    assert any(text.lower() == "chien" for text, _ in translations)
    assert any(
        text == "Hund" for text, _ in reader.translations("eng-000", "dog", "deu-000")
    )
    back = [
        text.lower() for text, _ in reader.translations("fra-000", "chien", "eng-000")
    ]
    assert "dog" in back
    meanings = reader.meanings("eng-000", "dog")
    assert meanings
    first = meanings[0]
    assert first.id() == first["mn"] and 0 <= first.quality() <= 9
    assert first.source() == first["ap"] and first.source_group() == first["ui"]
    assert "eng-000" in first.expressions() and "dog" in first.expressions()["eng-000"]


def test_lite_reader_connection_is_read_only_on_the_shipped_database():
    import sqlite3

    reader = _lite()
    with pytest.raises(sqlite3.OperationalError):
        reader._c.execute("CREATE TABLE probe (x INTEGER)")
    with pytest.raises(sqlite3.DatabaseError, match="not authorized"):
        reader._c.execute("ATTACH DATABASE ':memory:' AS probe")


def test_lite_reader_binds_hostile_parameters_on_the_shipped_database():
    reader = _lite()
    for text in ["dog\0' OR 1=1 --", "d" * 10_000_000, b"dog", None]:
        assert reader.translations("eng-000", text, "fra-000") == []
        assert reader.meanings("eng-000", text) == []
        if text is not None:  # None is the documented "every variety"
            assert reader.language_varieties(text) == []
    # "%" is itself an English expression in PanLex; bound as text it finds
    # that one entry, where a spliced wildcard would match every expression
    for text in ["%", "_og", "%og%"]:
        assert len(reader.meanings("eng-000", text)) < 100
        assert len(reader.translations("eng-000", text, "fra-000")) < 100
        assert reader.language_varieties(text) == []
    injected = "dog' UNION SELECT name, 1 FROM sqlite_master --"
    assert reader.translations("eng-000", injected, "fra-000") == []
    with pytest.raises(KeyError):
        reader.meanings("xxx-999", "dog")


def test_lite_reader_connection_is_screened_and_budgeted_on_the_shipped_database():
    from nltk import pathsec

    reader = _lite()
    connection = reader._c.connection
    rows = connection.execute("SELECT type, rootpage FROM sqlite_master").fetchall()
    assert rows and all(pathsec._plain_schema_object(k, p) is None for k, p in rows)
    assert connection.execute("PRAGMA trusted_schema").fetchall() == [(0,)]
    # the most connected English expressions in the 20240301 data (found
    # offline: each has over 4000 denotations) stay far inside the budget
    for text in ["break", "cut", "light", "cover", "tree"]:
        if not reader.meanings("eng-000", text):
            continue
        used = connection._steps * pathsec._SQLITE_STEP_GRAIN
        assert 0 < used * 10 < pathsec.MAX_SQLITE_STEPS
        assert reader.translations("eng-000", text, "fra-000")
        used = connection._steps * pathsec._SQLITE_STEP_GRAIN
        assert 0 < used * 10 < pathsec.MAX_SQLITE_STEPS
    with pytest.raises(PermissionError, match="exceeded MAX_SQLITE_STEPS"):
        connection.execute(
            "WITH RECURSIVE n(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM n)"
            " SELECT count(*) FROM n"
        ).fetchone()
