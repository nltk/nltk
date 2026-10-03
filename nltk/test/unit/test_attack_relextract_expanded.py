# Natural Language Toolkit: expanded attack harness for the relation extractor
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""nltk.sem.relextract driven with hostile and benign chunk structures and
judged against a reference implementation of the previous pair walk on the
same input, in linear time, and on the real IEER corpus as documented.
Nothing is mocked."""

import random
import re
from collections import defaultdict

import pytest

from nltk.sem.relextract import (
    _join,
    class_abbrev,
    clause,
    extract_rels,
    list2sym,
    rtuple,
    semi_rel2reldict,
    tree2semi_rel,
)
from nltk.test.unit.test_quadratic_dos import _assert_subquadratic
from nltk.tree import Tree

ESC = chr(0x1B)


def _reference_reldicts(pairs, window=5):
    """The pre-fix walk, kept as the oracle: re-slice the list off its head
    for every relation."""
    pairs = list(pairs)
    result = []
    while len(pairs) > 2:
        reldict = defaultdict(str)
        reldict["lcon"] = _join(pairs[0][0][-window:])
        reldict["subjclass"] = pairs[0][1].label()
        reldict["subjtext"] = _join(pairs[0][1].leaves())
        reldict["subjsym"] = list2sym(pairs[0][1].leaves())
        reldict["filler"] = _join(pairs[1][0])
        reldict["untagged_filler"] = _join(pairs[1][0], untag=True)
        reldict["objclass"] = pairs[1][1].label()
        reldict["objtext"] = _join(pairs[1][1].leaves())
        reldict["objsym"] = list2sym(pairs[1][1].leaves())
        reldict["rcon"] = _join(pairs[2][0][:window])
        result.append(reldict)
        pairs = pairs[1:]
    return result


def _chunk_tree(
    rng, n_entities, words=("the", "old", "man", "sat", "in", "&amp;", "x'y", 'q"z')
):
    labels = ["ORG", "LOC", "PER", "GPE"]
    children = []
    for i in range(n_entities):
        for _ in range(rng.randint(0, 4)):
            children.append((rng.choice(words), "NN"))
        leaves = [(rng.choice(words), "NNP") for _ in range(rng.randint(1, 3))]
        children.append(Tree(rng.choice(labels), leaves))
    for _ in range(rng.randint(0, 3)):
        children.append((rng.choice(words), "NN"))
    return Tree("S", children)


class TestAgainstTheReference:
    @pytest.mark.parametrize("seed", range(25))
    def test_random_chunk_trees_give_the_same_relations(self, seed):
        rng = random.Random(seed)
        pairs = tree2semi_rel(_chunk_tree(rng, rng.randint(0, 12)))
        for window in (0, 1, 5, 100):
            assert semi_rel2reldict(pairs, window=window) == _reference_reldicts(
                pairs, window
            )

    def test_fewer_than_three_pairs_give_nothing(self):
        for n in (0, 1, 2):
            pairs = tree2semi_rel(_chunk_tree(random.Random(n), n))
            assert semi_rel2reldict(pairs) == [] == _reference_reldicts(pairs)

    def test_a_pair_that_is_not_a_tree_fails_the_same_way(self):
        pairs = [
            ([("a", "NN")], Tree("ORG", [("x", "NNP")])),
            ([("b", "NN")], "not a tree"),
            ([("c", "NN")], Tree("LOC", [("y", "NNP")])),
        ]
        with pytest.raises(AttributeError):
            semi_rel2reldict(pairs)
        with pytest.raises(AttributeError):
            _reference_reldicts(pairs)

    def test_many_entities_are_linear(self):
        rng = random.Random(0)

        def op(n):
            pairs = tree2semi_rel(_chunk_tree(rng, n))
            assert len(semi_rel2reldict(pairs)) == max(0, len(pairs) - 2)

        _assert_subquadratic(op, 3000, 12000)


class TestHostileText:
    def _pairs(self, word):
        tree = Tree(
            "S",
            [
                (word, "NN"),
                Tree("ORG", [(word, "NNP")]),
                ("in", "IN"),
                Tree("LOC", [("Rome", "NNP")]),
                (word, "NN"),
                Tree("PER", [("Ann", "NNP")]),
            ],
        )
        return tree2semi_rel(tree)

    @pytest.mark.parametrize(
        "word",
        [
            "x" + ESC + "]0;evil" + chr(7) + "y",
            "a\nb",
            "c\rd",
            "&amp;",
            "&lt;script&gt;",
            " ",
            "it's",
            'q"z',
            "\\",
        ],
    )
    def test_trace_output_and_the_printers_never_carry_a_raw_control(
        self, word, capsys
    ):
        rels = semi_rel2reldict(self._pairs(word), trace=True)
        assert rels == _reference_reldicts(self._pairs(word))
        out = capsys.readouterr().out
        assert ESC not in out and chr(7) not in out
        for rel in rels:
            for text in (rtuple(rel, lcon=True, rcon=True), clause(rel, "REL")):
                assert ESC not in text and chr(7) not in text and "\r" not in text
                assert text.count("\n") == 0

    def test_symbols_decode_entities_and_normalise(self):
        assert list2sym(["A", "&amp;", "B."]) == "a_&_b"
        assert _join([("a", "NN"), ("b", "VB")]) == "a/NN b/VB"
        assert _join([("a", "NN"), ("b", "VB")], untag=True) == "a b"
        assert (
            class_abbrev("ORGANIZATION") == "ORG"
            and class_abbrev("NOTATYPE") == "NOTATYPE"
        )


class TestRealIeer:
    def _needs(self):
        import nltk.data

        try:
            nltk.data.find("corpora/ieer")
        except LookupError:
            pytest.skip("ieer is not installed")

    def test_the_documented_extraction(self):
        self._needs()
        from nltk.corpus import ieer

        IN = re.compile(r".*\bin\b(?!\b.+ing)")
        lines = []
        for doc in ieer.parsed_docs("NYT_19980315"):
            for rel in extract_rels("ORG", "LOC", doc, corpus="ieer", pattern=IN):
                lines.append(rtuple(rel))
        assert lines[:2] == [
            "[ORG: 'WHYY'] 'in' [LOC: 'Philadelphia']",
            "[ORG: 'McGlashan &AMP; Sarrail'] 'firm in' [LOC: 'San Mateo']",
        ]
        assert len(lines) == 13

    def test_a_verbose_pattern_finds_the_documented_roles(self):
        """The documented ROLES pattern is re.VERBOSE; the extractor re-derives a
        caller's pattern under the regex cap, and doing so without the flags
        found none of the 40 relations the raw regex finds."""
        self._needs()
        from nltk.corpus import ieer

        roles = r"""
        (.*(analyst|chair(wo)?man|commissioner|counsel|director|economist|editor|
        executive|foreman|governor|head|lawyer|leader|librarian).*)|
        manager|partner|president|producer|professor|researcher|spokes(wo)?man|writer|
        ,\sof\sthe?\s*  # "X, of (the) Y"
        """
        ROLES = re.compile(roles, re.VERBOSE)
        found, raw = [], 0
        for fileid in ieer.fileids():
            for doc in ieer.parsed_docs(fileid):
                found += [
                    rtuple(r)
                    for r in extract_rels(
                        "PER", "ORG", doc, corpus="ieer", pattern=ROLES
                    )
                ]
                for r in _reference_reldicts(tree2semi_rel(doc.text), 10):
                    if (
                        r["subjclass"] == "PERSON"
                        and r["objclass"] == "ORGANIZATION"
                        and len(r["filler"].split()) <= 10
                        and ROLES.match(r["filler"])
                    ):
                        raw += 1
        assert len(found) == raw == 40
        assert (
            "[PER: 'Kivutha Kibwana'] ', of the' [ORG: 'National Convention Assembly']"
            in found
        )

    def test_every_document_matches_the_reference_walk(self):
        self._needs()
        from nltk.corpus import ieer

        IN = re.compile(r".*\bin\b(?!\b.+ing)")
        total = 0
        for fileid in ieer.fileids():
            for doc in ieer.parsed_docs(fileid):
                pairs = tree2semi_rel(doc.text)
                got = semi_rel2reldict(pairs, window=10)
                assert got == _reference_reldicts(pairs, window=10)
                rels = extract_rels(
                    "ORG", "LOC", doc, corpus="ieer", pattern=IN, window=10
                )
                expected = [
                    r
                    for r in _reference_reldicts(pairs, 10)
                    if r["subjclass"] == "ORGANIZATION"
                    and r["objclass"] == "LOCATION"
                    and len(r["filler"].split()) <= 10
                    and IN.match(r["filler"])
                ]
                assert [rtuple(r) for r in rels] == [rtuple(r) for r in expected]
                total += len(rels)
        assert total == 45

    def test_the_demos_run_on_the_real_corpus(self, capsys):
        self._needs()
        from nltk.sem.relextract import in_demo, roles_demo

        in_demo(trace=0, sql=True)
        out = capsys.readouterr().out
        assert "IN(" in out and "Extract data from SQL table" in out
        roles_demo(trace=0)
        assert (
            "[PER: 'Kivutha Kibwana'] ', of the' [ORG: 'National Convention Assembly']"
            in capsys.readouterr().out
        )
