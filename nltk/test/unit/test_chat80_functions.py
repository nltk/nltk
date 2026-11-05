"""
Every function of ``nltk.sem.chat80`` on the Chat-80 world database. Expected
values are those of NLTK's "Sample usage for chat80" page, of Warren and Pereira
(1982), of the shipped ``city.db``, or of the Prolog files read here directly.
"""

import os
import shutil
import sqlite3
import sys

import pytest

import nltk
from nltk.grammar import FeatureGrammar
from nltk.sem import Assignment, Model, Valuation, chat80
from nltk.sem.logic import Expression

CITY_DB = "corpora/city_database/city.db"


@pytest.fixture
def stage(monkeypatch):
    nltk.data.clear_cache()
    directory = nltk.data.make_staging_dir(prefix="nltk_chat80_fn_")
    monkeypatch.chdir(directory)
    yield directory
    os.chdir(os.path.dirname(directory))
    shutil.rmtree(directory, ignore_errors=True)
    nltk.data.clear_cache()


@pytest.fixture(scope="module")
def valuation():
    try:
        return chat80.make_valuation(chat80.concepts(), read=True)
    except LookupError:
        pytest.skip("the chat80 corpus is not installed")


def _text(filename):
    try:
        return nltk.data.load(f"corpora/chat80/{filename}", format="text")
    except LookupError:
        pytest.skip("the chat80 corpus is not installed")


def _rows(query):
    try:
        return list(chat80.sql_query(CITY_DB, query))
    except LookupError:
        pytest.skip("the city database is not installed")


def test_items_name_every_bundle():
    assert chat80.items == tuple(sorted(chat80.item_metadata))
    assert "rivers" in chat80.items
    assert list(chat80.rels) == list(chat80.item_metadata.values())
    for bundle in chat80.rels:
        assert set(bundle) == {"rel_name", "closures", "schema", "filename"}


def test_a_concept_prints_as_the_howto_shows():
    c1 = chat80.Concept("dog", arity=1, extension={"d1", "d2"})
    assert str(c1) == "Label = 'dog'\nArity = 1\nExtension = ['d1', 'd2']"
    assert repr(c1) == "Concept('dog')"
    assert (c1.altLabels, c1.closures) == ([], [])
    assert chat80.Concept("cat", arity=1).extension == []


def test_augment_adds_to_the_extension():
    c = chat80.Concept("dog", arity=1, extension={"d2"})
    assert c.augment("d1") == {"d1", "d2"}
    assert c.extension == ["d1", "d2"]


def test_the_graph_helpers_of_a_concept():
    c = chat80.Concept("contain", arity=2)
    graph = c._make_graph({("a", "b"), ("b", "c"), ("a", "d")})
    assert {k: sorted(v) for k, v in graph.items()} == {"a": ["b", "d"], "b": ["c"]}
    closed = c._transclose({"a": ["b"], "b": ["c"], "c": ["d"]})
    assert sorted(closed["a"]) == ["b", "c", "d"] and sorted(closed["b"]) == ["c", "d"]
    assert c._make_pairs({"a": ["b", "c"]}) == {("a", "b"), ("a", "c")}


def test_close_makes_a_relation_symmetric_as_the_howto_shows():
    borders = {("a1", "a2"), ("a2", "a3")}
    c2 = chat80.Concept("borders", arity=2, extension=borders)
    assert c2.extension == [("a1", "a2"), ("a2", "a3")]
    c3 = chat80.Concept("borders", arity=2, closures=["symmetric"], extension=borders)
    c3.close()
    assert c3.extension == [("a1", "a2"), ("a2", "a1"), ("a2", "a3"), ("a3", "a2")]


def test_close_makes_a_relation_transitive():
    c = chat80.Concept(
        "contain", arity=2, closures=["transitive"], extension={("a", "b"), ("b", "c")}
    )
    c.close()
    assert c.extension == [("a", "b"), ("a", "c"), ("b", "c")]


def test_clause2concepts_reads_the_cities_as_the_howto_shows():
    _text("cities.pl")
    schema = ["city", "country", "population"]
    concepts = chat80.clause2concepts("cities.pl", "city", schema)
    assert repr(concepts) == (
        "[Concept('city'), Concept('country_of'), Concept('population_of')]"
    )
    assert [c.extension[:4] for c in concepts] == [
        ["athens", "bangkok", "barcelona", "berlin"],
        [
            ("athens", "greece"),
            ("bangkok", "thailand"),
            ("barcelona", "spain"),
            ("berlin", "east_germany"),
        ],
        [
            ("athens", "1368"),
            ("bangkok", "1178"),
            ("barcelona", "1280"),
            ("berlin", "3481"),
        ],
    ]


def test_str2records_reads_every_fact_of_a_file():
    facts = [
        line for line in _text("borders.pl").splitlines() if line.startswith("borders(")
    ]
    records = chat80._str2records("borders.pl", "borders")
    assert len(records) == len(facts) == 856
    assert records[0] == ["albania", "greece"]


def test_unary_and_binary_concepts():
    records = [["athens", "greece", "1368"], ["bangkok", "thailand", "1178"]]
    unary = chat80.unary_concept("city", 0, records)
    assert (unary.prefLabel, unary.arity, unary.extension) == (
        "city",
        1,
        ["athens", "bangkok"],
    )
    binary = chat80.binary_concept("population", [], 0, 2, records)
    assert binary.prefLabel == "population_of"
    assert binary.extension == [("athens", "1368"), ("bangkok", "1178")]
    border = chat80.binary_concept("border", ["symmetric"], 0, 1, [["a", "b"]])
    assert border.prefLabel == "border" and border.extension == [("a", "b"), ("b", "a")]
    contain = chat80.binary_concept(
        "contain", ["transitive"], 0, 1, [["a", "b"], ["b", "c"]]
    )
    assert contain.prefLabel == "contain" and ("a", "c") in contain.extension


def test_process_bundle_merges_the_concepts_of_its_relations():
    _text("borders.pl")
    concepts = chat80.process_bundle([chat80.city, chat80.borders])
    assert set(concepts) == {"city", "country_of", "population_of", "border"}
    # borders.pl's 856 facts, closed under symmetry
    assert len(concepts["border"].extension) == 858


def test_make_valuation_as_the_howto_shows(valuation):
    pairs = chat80.make_valuation(chat80.concepts("city"))
    assert sorted(label for label, extension in pairs) == [
        "city",
        "country_of",
        "population_of",
    ]
    assert "calcutta" in valuation["city"]
    assert [
        town for (town, country) in valuation["country_of"] if country == "india"
    ] == [
        "bombay",
        "calcutta",
        "delhi",
        "hyderabad",
        "madras",
    ]
    model = Model(valuation.domain, valuation)
    assert model.evaluate(r"population_of(jakarta, 533)", Assignment(valuation.domain))


def test_the_valuation_answers_its_one_place_predicates(valuation):
    model = Model(valuation.domain, valuation)
    g = Assignment(valuation.domain)
    assert model.evaluate("country(france)", g) is True
    assert model.evaluate("country(paris)", g) is False
    formula = Expression.fromstring("country(x) & capital_of(x, ouagadougou)")
    assert model.satisfiers(formula, "x", g) == {"upper_volta"}
    # a city is one individual, not the letters of its name
    assert not {name for name in valuation.domain if len(name) == 1 and name.isalpha()}


def test_label_indivs_names_every_individual():
    v = Valuation([("dog", {"d1", "d2"}), ("see", {("d1", "d2")})])
    labelled = chat80.label_indivs(v)
    assert labelled["d1"] == "d1" and labelled["d2"] == "d2"


def test_make_lex_writes_a_rule_for_each_name():
    lex = chat80.make_lex(["zloty", "upper_volta"])
    assert "chat80.py -x" in lex[0]
    # the howto's rule, in the logic syntax and feature names chat80.fcfg reads
    assert lex[1:] == [
        "PropN[NUM=sg, SEM=<\\P.P(zloty)>] -> 'Zloty'\n",
        "PropN[NUM=sg, SEM=<\\P.P(upper_volta)>] -> 'Upper_Volta'\n",
    ]


def test_the_written_lexicon_loads_as_a_grammar(stage, valuation):
    chat80.make_valuation(chat80.concepts(), lexicon=True)
    with open(os.path.join(stage, "chat_pnames.fcfg")) as f:
        text = f.read()
    grammar = FeatureGrammar.fromstring("% start PropN\n" + text)
    assert len(grammar.productions()) == len(valuation.domain)
    assert "PropN[NUM=sg, SEM=<\\P.P(zloty)>] -> 'Zloty'\n" in text


def test_concepts_takes_one_item_or_many():
    labels = {c.prefLabel for c in chat80.concepts("city")}
    assert labels == {"city", "country_of", "population_of"}
    every = {c.prefLabel for c in chat80.concepts()}
    assert {"river", "drains", "rises", "flows", "border", "capital_of"} <= every


def test_river_courses_reads_every_river():
    text = _text("rivers.pl")
    courses = chat80.river_courses()
    assert len(courses) == text.count("\nriver(") == 41
    assert courses["nile"] == ["mediterranean", "egypt", "sudan", "uganda"]
    # the danube's record runs over two lines
    assert courses["danube"] == [
        "black_sea",
        "romania",
        "yugoslavia",
        "hungary",
        "czechoslovakia",
        "austria",
        "west_germany",
    ]


def test_river_concepts_follow_world0():
    courses = chat80.river_courses()
    concepts = {c.prefLabel: c for c in chat80.river_concepts()}
    assert {label: c.arity for label, c in concepts.items()} == {
        "river": 1,
        "drains": 2,
        "rises": 2,
        "flows": 2,
    }
    assert len(concepts["river"].extension) == 41
    # drains(R,S) :- first(L,S); rises(R,C) :- last(L,C); flows(R,C) past the mouth
    assert ("nile", "mediterranean") in concepts["drains"].extension
    assert ("nile", "uganda") in concepts["rises"].extension
    assert len(concepts["flows"].extension) == sum(len(c) - 1 for c in courses.values())


def test_the_rivers_round_trip_through_a_store(stage):
    base = os.path.join(stage, "rivers")
    chat80.val_dump([chat80.rivers], base)
    loaded = chat80.val_load(base)
    expected = chat80.make_valuation(chat80.river_concepts(), read=True)
    assert loaded == expected
    assert ("danube", "black_sea") in loaded["drains"]


def test_cities2table_builds_the_shipped_city_table(stage):
    shipped = _rows("SELECT * FROM city_table")
    db = os.path.join(stage, "city.db")
    chat80.cities2table("cities.pl", "city", db, setup=True)
    with sqlite3.connect(db) as connection:
        built = connection.execute("SELECT * FROM city_table").fetchall()
    assert sorted(built) == sorted(shipped)
    assert len(built) == _text("cities.pl").count("\ncity(")


def test_sql_query_as_the_howto_shows():
    q = (
        "SELECT City, Population FROM city_table "
        "WHERE Country = 'china' and Population > 1000"
    )
    assert ["%-10s %4s" % answer for answer in _rows(q)] == [
        "canton     1496",
        "chungking  1100",
        "mukden     1551",
        "peking     2031",
        "shanghai   5407",
        "tientsin   1795",
    ]


def test_the_sql0_grammar_queries_the_city_table_as_the_howto_shows():
    cp = nltk.parse.load_parser("grammars/book_grammars/sql0.fcfg")
    (tree,) = cp.parse("What cities are in China".split())
    q = " ".join(tree.label()["SEM"])
    assert q == 'SELECT City FROM city_table WHERE   Country="china"'
    assert " ".join("%s" % r for r in _rows(q)) == (
        "canton chungking dairen harbin kowloon mukden peking shanghai sian tientsin"
    )


def _main(monkeypatch, *argv):
    monkeypatch.setattr(sys, "argv", ["chat80", *argv])
    chat80.main()


def test_main_prints_the_vocabulary(monkeypatch, capsys):
    with pytest.raises(SystemExit) as exit:
        _main(monkeypatch, "-v")
    assert exit.value.code == 0
    lines = capsys.readouterr().out.splitlines()
    assert {"river 1", "drains 2", "border 2", "capital_of 2"} <= set(lines)


def test_main_prints_one_relation(monkeypatch, capsys):
    with pytest.raises(SystemExit) as exit:
        _main(monkeypatch, "-r", "capital_of")
    assert exit.value.code == 0
    out = capsys.readouterr().out
    assert out.startswith("Label = 'capital_of'\nArity = 2\n")
    assert "('upper_volta', 'ouagadougou')" in out


def test_main_stores_and_loads_a_valuation(stage, monkeypatch, capsys):
    store = os.path.join(stage, "world")
    with pytest.raises(SystemExit) as exit:
        _main(monkeypatch, "-s", store)
    assert exit.value.code == 0
    assert "Dumping a valuation to" in capsys.readouterr().out
    _main(monkeypatch, "-q", "-l", store)
    assert chat80.val_load(store) == chat80.make_valuation(chat80.concepts(), read=True)


def test_main_prints_the_concepts_and_the_valuation(monkeypatch, capsys):
    _main(monkeypatch, "-q", "-c")
    out = capsys.readouterr().out
    assert (
        "Label = 'river'\nArity = 1\n" in out and "'upper_volta': 'upper_volta'" in out
    )


def test_main_writes_the_lexicon(stage, monkeypatch, capsys):
    _main(monkeypatch, "-x")
    assert "Writing out lexical rules" in capsys.readouterr().out
    with open(os.path.join(stage, "chat_pnames.fcfg")) as f:
        assert "-> 'Upper_Volta'\n" in f.read()


def test_main_refuses_to_store_and_load_at_once(monkeypatch, capsys):
    with pytest.raises(SystemExit) as exit:
        _main(monkeypatch, "-s", "a", "-l", "b")
    assert exit.value.code == 2
    assert "mutually exclusive" in capsys.readouterr().err


def test_sql_demo_prints_every_row(capsys):
    shipped = _rows("SELECT * FROM city_table")
    chat80.sql_demo()
    lines = capsys.readouterr().out.splitlines()
    assert lines[:2] == ["", "Using SQL to extract rows from 'city.db' RDB."]
    assert lines[2:] == [str(row) for row in shipped]
