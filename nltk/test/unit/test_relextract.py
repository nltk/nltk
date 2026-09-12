from copy import deepcopy
from types import SimpleNamespace

import pytest

from nltk import redos
from nltk.sem.relextract import extract_rels, semi_rel2reldict, tree2semi_rel
from nltk.tree import Tree


@pytest.mark.parametrize("entities", [[], [Tree("PER", ["Alice"])]])
def test_fewer_than_two_entities(entities):
    assert semi_rel2reldict(tree2semi_rel(Tree("S", entities))) == []


def test_single_relation():
    pairs = tree2semi_rel(
        Tree(
            "S", ["Today", Tree("PER", ["Alice"]), "works", "at", Tree("ORG", ["Acme"])]
        )
    )
    original = deepcopy(pairs)

    assert semi_rel2reldict(pairs) == [
        {
            "lcon": "Today",
            "subjclass": "PER",
            "subjtext": "Alice",
            "subjsym": "alice",
            "filler": "works at",
            "untagged_filler": "works at",
            "objclass": "ORG",
            "objtext": "Acme",
            "objsym": "acme",
            "rcon": "",
        }
    ]
    assert pairs == original


@pytest.mark.parametrize("window", [1, 2])
def test_all_adjacent_relations_keep_available_context(window):
    pairs = tree2semi_rel(
        Tree(
            "S",
            [
                "Early",
                "today",
                Tree("PER", ["Alice"]),
                "works",
                "at",
                Tree("ORG", ["Acme"]),
                "based",
                "in",
                Tree("LOC", ["London"]),
            ],
        )
    )
    relations = semi_rel2reldict(pairs, window=window)

    assert [(rel["subjtext"], rel["objtext"]) for rel in relations] == [
        ("Alice", "Acme"),
        ("Acme", "London"),
    ]
    assert relations[0]["lcon"] == " ".join(["Early", "today"][-window:])
    assert relations[0]["rcon"] == " ".join(["based", "in"][:window])
    assert relations[1]["lcon"] == " ".join(["works", "at"][-window:])
    assert relations[1]["rcon"] == ""


@pytest.mark.parametrize("corpus", ["ace", "conll2002", "ieer"])
def test_extract_only_relation(corpus):
    person, organization = (
        ("PER", "ORG") if corpus == "conll2002" else ("PERSON", "ORGANIZATION")
    )
    tree = Tree(
        "S", [Tree(person, ["Alice"]), "works", "at", Tree(organization, ["Acme"])]
    )
    doc = (
        SimpleNamespace(text=tree, headline=Tree("S", [])) if corpus == "ieer" else tree
    )

    relations = extract_rels(
        "PER", "ORG", doc, corpus=corpus, pattern=redos.compile("works at")
    )

    assert [(rel["subjtext"], rel["filler"], rel["objtext"]) for rel in relations] == [
        ("Alice", "works at", "Acme")
    ]


def test_extract_last_matching_relation():
    tree = Tree(
        "S",
        [Tree("LOC", ["London"]), Tree("PER", ["Alice"]), "at", Tree("ORG", ["Acme"])],
    )

    relations = extract_rels(
        "PER", "ORG", tree, corpus="conll2002", pattern=redos.compile("at")
    )

    assert [(rel["subjtext"], rel["objtext"]) for rel in relations] == [
        ("Alice", "Acme")
    ]


def test_tagged_relation():
    tree = Tree(
        "S",
        [
            Tree("PER", [("Alice", "NNP")]),
            ("works", "VBZ"),
            ("at", "IN"),
            Tree("ORG", [("Acme", "NNP")]),
        ],
    )
    relations = extract_rels(
        "PER", "ORG", tree, corpus="conll2002", pattern=redos.compile("works/VBZ at/IN")
    )

    assert len(relations) == 1
    assert relations[0]["filler"] == "works/VBZ at/IN"
    assert relations[0]["untagged_filler"] == "works at"
    assert relations[0]["subjsym"] == "alice"
    assert relations[0]["objsym"] == "acme"


@pytest.mark.parametrize(
    "subjclass,objclass,pattern,window",
    [
        ("LOC", "ORG", "works at", 10),
        ("PER", "LOC", "works at", 10),
        ("PER", "ORG", "lives at", 10),
        ("PER", "ORG", "works at", 1),
    ],
)
def test_last_relation_still_respects_filters(subjclass, objclass, pattern, window):
    tree = Tree("S", [Tree("PER", ["Alice"]), "works", "at", Tree("ORG", ["Acme"])])

    assert (
        extract_rels(
            subjclass,
            objclass,
            tree,
            corpus="conll2002",
            pattern=redos.compile(pattern),
            window=window,
        )
        == []
    )
