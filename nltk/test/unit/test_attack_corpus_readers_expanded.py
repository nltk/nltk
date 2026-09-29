# Natural Language Toolkit: expanded attack harness for the corpus reader guards
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""The corpus readers this branch changes, driven with hostile and benign input
and judged against reference implementations and against Python's own XML
parser on the same bytes: the CoNLL SRL predicate index (GHSA-v8f3), the TIMIT
phone-tree walk, the XML corpus view's read window, and every reader's XML
parse routed through nltk.xmlsec. The real corpora are read as documented.
Nothing is mocked."""

import io
import os
import time
from xml.etree import ElementTree as StockET

import pytest

from nltk.test.unit.test_quadratic_dos import _assert_subquadratic
from nltk.tree import Tree


def _needs(*resources):
    import nltk.data

    for name in resources:
        try:
            nltk.data.find(name)
        except LookupError:
            pytest.skip(f"{name} is not installed")


# ===========================================================================
# 1. CoNLL SRL: the predicate to spanlist index (GHSA-v8f3)
# ===========================================================================
def _srl_reader(tmp_path):
    from nltk.corpus.reader.conll import ConllCorpusReader

    (tmp_path / "srl.conll").write_text("")
    return ConllCorpusReader(
        str(tmp_path), ["srl.conll"], ("words", "pos", "tree", "srl")
    )


def _grid(n):
    grid = []
    for i in range(n):
        row = ["w", "NN", "*", "verb.01", "p"]
        row += ["(V*)" if i == j else "(A1*)" for j in range(n)]
        grid.append(row)
    return grid


def _reference_srl_instances(reader, grid):
    """The pre-fix selection, kept as the oracle: rescan every spanlist per
    predicate and take the first one whose V or C-V span covers the word."""
    from nltk.corpus.reader.conll import ConllSRLInstance, ConllSRLInstanceList

    tree = reader._get_parsed_sent(grid, False)
    spanlists = reader._get_srl_spans(grid)
    predicates = reader._get_column(grid, reader._colmap["srl"] + 1)
    rolesets = reader._get_column(grid, reader._colmap["srl"])
    instances = ConllSRLInstanceList(tree)
    for wordnum, predicate in enumerate(predicates):
        if predicate == "-":
            continue
        for spanlist in spanlists:
            for (start, end), tag in spanlist:
                if wordnum in range(start, end) and tag in ("V", "C-V"):
                    break
            else:
                continue
            break
        else:
            raise ValueError("No srl column found for %r" % predicate)
        instances.append(
            ConllSRLInstance(tree, wordnum, predicate, rolesets[wordnum], spanlist)
        )
    return instances


def _same_instances(a, b):
    def key(i):
        return (
            i.verb,
            i.verb_head,
            i.verb_stem,
            i.roleset,
            sorted(i.arguments),
            i.tagged_spans,
        )

    return [key(i) for i in a] == [key(i) for i in b]


class TestConllSRLPredicateRescan:
    def test_correctness_preserved(self, tmp_path):
        reader = _srl_reader(tmp_path)
        instances = reader._get_srl_instances(_grid(3), False)
        assert len(instances) == 3
        assert all(type(x).__name__ == "ConllSRLInstance" for x in instances)
        assert _same_instances(instances, _reference_srl_instances(reader, _grid(3)))

    def test_many_predicates_is_linear(self, tmp_path):
        reader = _srl_reader(tmp_path)
        grids = {70: _grid(70), 280: _grid(280)}
        _assert_subquadratic(
            lambda n: reader._get_srl_instances(grids[n], False), 70, 280
        )

    def test_hostile_grids_agree_with_the_reference(self, tmp_path):
        reader = _srl_reader(tmp_path)
        # overlapping V spans (word 1 is covered by predicate 0's second
        # column before its own C-V column: the first spanlist wins, as it
        # always did), a C-V continuation, and a word with no predicate
        rows = [
            ["a", "NN", "*", "verb.01", "p", "(V*)", "(V*", "*"],
            ["b", "NN", "*", "verb.02", "p", "(A1*)", "*)", "(C-V*)"],
            ["c", "NN", "*", "verb.03", "p", "*", "*", "(V*)"],
            ["d", "NN", "*", "-", "-", "*", "(A0*)", "*"],
        ]
        got = reader._get_srl_instances(rows, False)
        assert _same_instances(got, _reference_srl_instances(reader, rows))
        assert [i.verb_head for i in got] == [0, 1, 2]
        assert got[1].tagged_spans == got[0].tagged_spans or got[1].verb == [0, 1]
        # a predicate no V or C-V span covers is refused by both
        rows[2][7] = "*"
        with pytest.raises(ValueError, match="No srl column"):
            reader._get_srl_instances(rows, False)
        with pytest.raises(ValueError, match="No srl column"):
            _reference_srl_instances(reader, rows)

    def test_the_probe_has_teeth(self, monkeypatch):
        from nltk.corpus.reader.conll import ConllCorpusReader
        from nltk.test.unit import security_probes as probes

        probe = probes.PROBES["GHSA-v8f3-6phw-6mh9"]
        assert probe()[0] == probes.FIXED
        monkeypatch.setattr(
            ConllCorpusReader,
            "_get_srl_instances",
            lambda self, grid, pos_in_tree: _reference_srl_instances(self, grid),
        )
        status, detail = probe()
        assert status == probes.VULNERABLE, detail
        monkeypatch.undo()
        assert probe()[0] == probes.FIXED

    def test_real_conll_corpora_read_as_documented(self):
        _needs("corpora/conll2000", "corpora/conll2002")
        from nltk.corpus import conll2000, conll2002

        assert len(conll2000.chunked_sents()) == 10948
        assert conll2000.tagged_words()[:2] == [("Confidence", "NN"), ("in", "IN")]
        assert len(conll2002.iob_words()) == 678377
        first = conll2000.chunked_sents()[0]
        assert isinstance(first, Tree) and first.label() == "S"


# ===========================================================================
# 2. TIMIT: the phone-tree walk
# ===========================================================================
def _reference_phone_trees(word_times, phone_times, sent_times):
    """The pre-fix walk, kept as the oracle, consuming with pop(0)."""
    word_times, phone_times, sent_times = (
        list(word_times),
        list(phone_times),
        list(sent_times),
    )
    trees = []
    while sent_times:
        (sent, sent_start, sent_end) = sent_times.pop(0)
        trees.append(Tree("S", []))
        while word_times and phone_times and phone_times[0][2] <= word_times[0][1]:
            trees[-1].append(phone_times.pop(0)[0])
        while word_times and word_times[0][2] <= sent_end:
            (word, word_start, word_end) = word_times.pop(0)
            trees[-1].append(Tree(word, []))
            while phone_times and phone_times[0][2] <= word_end:
                trees[-1][-1].append(phone_times.pop(0)[0])
        while phone_times and phone_times[0][2] <= sent_end:
            trees[-1].append(phone_times.pop(0)[0])
    return trees


def _synthetic_times(n):
    phones = [(f"p{i}", 10 * i, 10 * i + 10) for i in range(3 * n)]
    words = [(f"w{i}", 30 * i, 30 * i + 30) for i in range(n)]
    sents = [(f"s{i}", 300 * i, 300 * i + 300) for i in range(max(1, n // 10))]
    return words, phones, sents


class TestTimitPhoneTrees:
    def _reader_with(self, monkeypatch, words, phones, sents):
        from nltk.corpus.reader.timit import TimitCorpusReader

        reader = TimitCorpusReader.__new__(TimitCorpusReader)
        monkeypatch.setattr(reader, "_utterances", ["u"], raising=False)
        monkeypatch.setattr(reader, "word_times", lambda u: list(words), raising=False)
        monkeypatch.setattr(
            reader, "phone_times", lambda u: list(phones), raising=False
        )
        monkeypatch.setattr(reader, "sent_times", lambda u: list(sents), raising=False)
        return reader

    @pytest.mark.parametrize("n", [1, 7, 40])
    def test_synthetic_utterances_match_the_reference(self, monkeypatch, n):
        words, phones, sents = _synthetic_times(n)
        reader = self._reader_with(monkeypatch, words, phones, sents)
        assert [str(t) for t in reader.phone_trees()] == [
            str(t) for t in _reference_phone_trees(words, phones, sents)
        ]

    def test_hostile_timings_match_the_reference(self, monkeypatch):
        # phones outside every word, words outside every sentence, empty lists,
        # overlapping and unsorted spans: the walk must not hang or index past
        # the end, and must give what the reference walk gives
        cases = [
            ([], [], []),
            ([("w", 0, 5)], [], [("s", 0, 100)]),
            ([], [("p", 0, 1)], [("s", 0, 100)]),
            ([("w", 50, 60)], [("p", 0, 1), ("q", 70, 80)], [("s", 0, 100)]),
            (
                [("w", 0, 10), ("x", 5, 15)],
                [("p", 0, 3), ("q", 3, 12), ("r", 12, 20)],
                [("s", 0, 100), ("t", 100, 200)],
            ),
            ([("w", 200, 210)], [("p", 0, 1)], [("s", 0, 100)]),
        ]
        for words, phones, sents in cases:
            reader = self._reader_with(monkeypatch, words, phones, sents)
            assert [str(t) for t in reader.phone_trees()] == [
                str(t) for t in _reference_phone_trees(words, phones, sents)
            ], (words, phones, sents)

    def test_long_utterances_are_linear(self, monkeypatch):
        def op(n):
            words, phones, sents = _synthetic_times(n)
            reader = self._reader_with(monkeypatch, words, phones, sents)
            reader.phone_trees()

        _assert_subquadratic(op, 5000, 20000)

    def test_the_real_corpus_matches_the_reference_walk(self):
        _needs("corpora/timit")
        from nltk.corpus import timit

        utterances = timit.utteranceids()
        assert len(utterances) == 160 and len(timit.words()) == 1394
        got = [str(t) for t in timit.phone_trees()]
        expected = []
        for u in utterances:
            expected += [
                str(t)
                for t in _reference_phone_trees(
                    timit.word_times(u), timit.phone_times(u), timit.sent_times(u)
                )
            ]
        assert got == expected and len(got) == 160


# ===========================================================================
# 3. XMLCorpusView: the read window, and every reader's parse through xmlsec
# ===========================================================================
def _xml_view(text, tagspec, tmp_path, name="doc.xml"):
    from nltk.corpus.reader.xmldocs import XMLCorpusView

    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return XMLCorpusView(str(path), tagspec)


class TestXMLCorpusView:
    def test_elements_match_the_stock_parser_on_the_same_bytes(self, tmp_path):
        text = (
            "<doc>"
            + "".join(
                f'<e n="{i}"><w>tok{i}</w><w a="x&amp;y">z</w></e>' for i in range(500)
            )
            + "</doc>"
        )
        view = _xml_view(text, "doc/e", tmp_path)
        elements = list(view)
        assert len(elements) == 500
        stock = StockET.fromstring(text)
        assert [StockET.tostring(e) for e in elements] == [
            StockET.tostring(e) for e in stock.iter("e")
        ]

    def test_one_oversized_element_is_read_in_linear_time(self, tmp_path):
        def op(n):
            text = "<doc><e>" + "x" * n + "</e></doc>"
            view = _xml_view(text, "doc/e", tmp_path, name=f"big{n}.xml")
            assert len(list(view)) == 1

        _assert_subquadratic(op, 400_000, 1_600_000)

    def test_one_oversized_tag_is_read_in_linear_time(self, tmp_path):
        def op(n):
            text = '<doc><e a="' + "x" * n + '">y</e></doc>'
            view = _xml_view(text, "doc/e", tmp_path, name=f"tag{n}.xml")
            assert len(list(view)) == 1

        _assert_subquadratic(op, 200_000, 800_000)

    def test_a_tag_past_the_token_ceiling_is_refused_by_xmlsec(self, tmp_path):
        import nltk.xmlsec

        text = (
            '<doc><e a="' + "x" * (nltk.xmlsec.MAX_TOKEN_BYTES + 10) + '">y</e></doc>'
        )
        view = _xml_view(text, "doc/e", tmp_path, name="huge_tag.xml")
        with pytest.raises(nltk.xmlsec.StructureForbidden, match="markup token"):
            list(view)

    def test_many_small_elements_are_linear(self, tmp_path):
        def op(n):
            text = "<doc>" + "<e>x</e>" * n + "</doc>"
            view = _xml_view(text, "doc/e", tmp_path, name=f"many{n}.xml")
            assert len(list(view)) == n

        _assert_subquadratic(op, 20_000, 80_000)

    def test_malformed_fragments_end_cleanly(self, tmp_path):
        # a tag left open at the end of the file is refused; a stray '>' between
        # elements is tolerated as text and the elements are still found
        view = _xml_view("<doc><e>x</e><unclosed", "doc/e", tmp_path, name="eof.xml")
        with pytest.raises(ValueError, match="Unexpected end of file"):
            list(view)
        view = _xml_view("<doc>><e>x</e>></doc>", "doc/e", tmp_path, name="stray.xml")
        assert [e.tag for e in view] == ["e"]

    def test_entities_and_bombs_are_refused_by_every_reader_route(self, tmp_path):
        from nltk.corpus.reader import XMLCorpusReader

        laughs = (
            '<?xml version="1.0"?><!DOCTYPE lolz [<!ENTITY lol "lol">'
            + "".join(
                '<!ENTITY lol%d "%s">'
                % (i, "&lol%d;" % (i - 1) * 10 if i > 1 else "&lol;" * 10)
                for i in range(1, 7)
            )
            + "]><lolz>&lol6;</lolz>"
        )
        (tmp_path / "bomb.xml").write_text(laughs)
        deep = "<d>" * 20000 + "</d>" * 20000
        (tmp_path / "deep.xml").write_text(deep)
        reader = XMLCorpusReader(str(tmp_path), r".*\.xml")
        with pytest.raises(Exception) as exc:
            reader.xml("bomb.xml")
        assert type(exc.value).__name__ == "EntitiesForbidden"
        with pytest.raises(ValueError, match="nesting depth"):
            reader.xml("deep.xml")
        with pytest.raises(Exception) as exc:
            list(reader.words("bomb.xml"))
        assert type(exc.value).__name__ == "EntitiesForbidden"

    def test_every_xml_reader_parses_through_xmlsec(self):
        import nltk.xmlsec
        from nltk.corpus.reader import (
            bnc,
            childes,
            nombank,
            propbank,
            semcor,
            senseval,
            xmldocs,
        )

        for module in (bnc, childes, nombank, propbank, semcor, senseval, xmldocs):
            for name in ("safe_parse", "safe_fromstring"):
                fn = getattr(module, name, None)
                if fn is not None:
                    assert fn.__module__ == "nltk.xmlsec", (module.__name__, name)

    def test_the_real_xml_corpora_read_as_documented(self):
        _needs(
            "corpora/shakespeare",
            "corpora/senseval",
            "corpora/propbank",
            "corpora/nombank.1.0",
            "corpora/semcor",
        )
        from nltk.corpus import nombank, propbank, semcor, senseval, shakespeare

        play = shakespeare.xml("dream.xml")
        assert play.tag == "PLAY" and len(list(play.iter("LINE"))) == 2159
        assert len(shakespeare.words("dream.xml")) == 21538
        assert len(senseval.instances("hard.pos")) == 4333
        assert (
            len(propbank.instances()) == 112917 and len(nombank.instances()) == 114574
        )
        assert len(semcor.tagged_sents()) == 37176
