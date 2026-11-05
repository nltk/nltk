"""
nltk_data's chat80.fcfg, unchanged since 2012, is written in NLTK's logic syntax
from before July 2008, has seven stray parentheses, and includes its lexicon of
proper names with a directive NLTK's grammar reader never had. ``nltk.data.load``
repairs that exact file, by exact edits pinned to its SHA-256, as it reads it.

The repaired grammar's answers are checked in NLTK's Chat-80 model against the
paper (Warren and Pereira 1982) and against the Prolog files, read here directly.
"""

import hashlib
import os
import re

import pytest

import nltk
from nltk.data import Chat80Repair
from nltk.featstruct import TYPE, FeatStruct
from nltk.grammar import FeatureGrammar
from nltk.parse import FeatureChartParser
from nltk.sem import Assignment, Model, chat80
from nltk.sem.logic import ApplicationExpression
from nltk.test.unit import timing

from . import _mp_ctx

CHAT80 = "grammars/sample_grammars/chat80.fcfg"
PNAMES = "grammars/sample_grammars/chat_pnames.fcfg"


def _raw(resource):
    try:
        return nltk.data.load(resource, format="raw", cache=False)
    except LookupError:
        pytest.skip(f"{resource} is not installed")


def _facts(filename, relation):
    """The argument tuples of ``relation(a,b,...).`` lines in a Chat-80 file."""
    text = _raw(f"corpora/chat80/{filename}").decode("utf-8")
    return [
        tuple(line[len(relation) + 1 : -2].split(","))
        for line in text.splitlines()
        if line.startswith(relation + "(") and line.endswith(").")
    ]


@pytest.fixture(scope="module")
def answer():
    """Parse a question with chat80.fcfg and find its answers in the model."""
    parser = FeatureChartParser(nltk.data.load(CHAT80))
    valuation = chat80.make_valuation(chat80.concepts(), read=True)
    model = Model(valuation.domain, valuation)
    assignment = Assignment(valuation.domain)

    def ask(question):
        (tree,) = parser.parse(question.split())
        sem = tree.label()["SEM"].simplify()
        return sorted(model.satisfiers(sem.term, sem.variable.name, assignment))

    return ask


def test_the_shipped_files_are_the_ones_the_repairs_are_pinned_to():
    assert hashlib.sha256(_raw(CHAT80)).hexdigest() == Chat80Repair.GRAMMAR
    assert hashlib.sha256(_raw(PNAMES)).hexdigest() == Chat80Repair.LEXICON


def test_the_shipped_file_does_not_load_as_it_is():
    with pytest.raises(ValueError, match="line 19"):
        FeatureGrammar.fromstring(_raw(CHAT80).decode("utf-8"))


def test_each_edit_meets_its_text_as_often_as_the_file_has_it():
    # 1 + 7 + 2 + 2 + 1 + 1: the 14 productions that fail on their own
    text = _raw(CHAT80).decode("utf-8")
    counts = [text.count(old) for old, new in Chat80Repair.EDITS[Chat80Repair.GRAMMAR]]
    assert counts == [1, 7, 2, 2, 1, 1]
    lexicon = _raw(PNAMES).decode("utf-8")
    ((old, new),) = Chat80Repair.EDITS[Chat80Repair.LEXICON]
    assert lexicon.count(old) == lexicon.count("->") == 540
    line, resource = Chat80Repair.INCLUDE
    assert text.count(line) == 1 and resource == PNAMES


def test_the_repaired_text_has_no_old_form_left():
    repaired = Chat80Repair.repair(_raw(CHAT80), _raw(CHAT80).decode("utf-8"))
    for old, new in Chat80Repair.EDITS[Chat80Repair.GRAMMAR]:
        assert old not in repaired
    assert "% include" not in repaired
    assert "PropN[num=" not in repaired and repaired.count("PropN[NUM=sg") == 540


def test_chat80_loads_with_nltk_data_alone():
    grammar = nltk.data.load(CHAT80, cache=False)
    # its own 50 rules and words, and the 540 proper names it includes
    assert len(grammar.productions()) == 50 + 540
    assert grammar.start()[TYPE] == "S"


def test_a_grammar_read_again_is_not_repaired_again():
    raw = _raw(CHAT80)
    first = Chat80Repair.repair(raw, raw.decode("utf-8"))
    # a fresh read of the file gets the kept text back, not a new repair of it
    assert Chat80Repair.repair(raw, raw.decode("utf-8")) is first
    assert nltk.data.load(CHAT80) is nltk.data.load(CHAT80)


def test_other_text_is_read_as_it_is():
    text = "% start S\nS -> 'a'\n"
    assert Chat80Repair.repair(text.encode(), text) == text
    # a file that differs from the shipped one by a byte is not touched
    changed = _raw(CHAT80) + b"\n"
    assert Chat80Repair.repair(changed, changed.decode("utf-8")) == changed.decode()


def test_app_reads_every_variable_name_the_reader_accepts():
    # chat80.fcfg writes <app(?v,?PRED)>; app was read only for ?[a-z]+ names
    for text, expected in [
        ("[SEM=<app(?subj,?vp)>]", "?subj(?vp)"),
        ("[SEM=<app(?v,?PRED)>]", "?v(?PRED)"),
        ("[SEM=<app(?x_1, ?Y2)>]", "?x_1(?Y2)"),
    ]:
        sem = FeatStruct(text)["SEM"]
        assert isinstance(sem, ApplicationExpression) and str(sem) == expected


_LONG = "a" * 200_000


def _long_app_worker():
    try:
        sem = FeatStruct(f"[SEM=<app(?{_LONG},?b)>]")["SEM"]
        os._exit(0 if str(sem) == f"?{_LONG}(?b)" else 4)
    except BaseException:
        os._exit(3)


def _near_miss_worker():
    # a long name that never closes: every handler must give up in linear time
    try:
        FeatStruct(f"[SEM=<app(?{_LONG} ,?b")
    except ValueError:
        os._exit(0)
    except BaseException:
        os._exit(3)
    os._exit(4)


@pytest.mark.parametrize("worker", [_long_app_worker, _near_miss_worker])
def test_app_runs_in_linear_time(worker):
    run = timing.run_in_process(
        worker, (), budget=20, context=_mp_ctx(), cpu_bound=True
    )
    assert run.within_budget, "reading app() did not finish in time -> ReDoS"
    assert run.exitcode == 0, f"worker failed (exit code {run.exitcode})"


def test_the_capital_of_upper_volta_is_ouagadougou(answer):
    # Warren and Pereira 1982, Appendix I: "Which country's capital is Ouagadougou?"
    assert answer("what is the capital of Upper_Volta") == ["ouagadougou"]


def test_paris_is_the_capital_of_france(answer):
    # section 2: "Paris is the capital of France. capital(france,paris)"
    assert answer("what is the capital of France") == ["paris"]


def test_three_oceans_border_the_united_states(answer):
    # section 2: Chat-80 "simply gives all three answers"
    oceans = {x for (x,) in _facts("world1.pl", "ocean")}
    borders = set(_facts("borders.pl", "borders"))
    expected = sorted(
        x
        for x in oceans
        if (x, "united_states") in borders or ("united_states", x) in borders
    )
    assert len(expected) == 3
    assert answer("which ocean borders United_States") == expected


def _neighbours(region):
    borders = set(_facts("borders.pl", "borders"))
    return {a for a, b in borders if b == region} | {
        b for a, b in borders if a == region
    }


def test_the_countries_bordering_china(answer):
    countries = {fact[0] for fact in _facts("countries.pl", "country")}
    expected = sorted(_neighbours("china") & countries)
    assert answer("which country borders China") == expected


def test_the_asian_countries_bordering_china(answer):
    contains = _facts("contain.pl", "contains0")
    asian, frontier = set(), {"asia"}
    while frontier:
        frontier = {b for a, b in contains if a in frontier} - asian
        asian |= frontier
    countries = {fact[0] for fact in _facts("countries.pl", "country")}
    expected = sorted(_neighbours("china") & countries & asian)
    assert answer("which Asian countries border China") == expected


def test_the_seas_bordering_turkey(answer):
    seas = {x for (x,) in _facts("world1.pl", "sea")}
    assert answer("which sea borders Turkey") == sorted(_neighbours("turkey") & seas)


def test_the_population_of_china(answer):
    (china,) = (
        fact for fact in _facts("countries.pl", "country") if fact[0] == "china"
    )
    assert answer("what is the population of China") == [china[5]]
