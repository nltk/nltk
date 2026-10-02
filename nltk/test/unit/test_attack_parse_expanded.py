# Natural Language Toolkit: expanded attack harness for the parse guards
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""The parse-package guards driven with the widest attack matrix, benign
neighbours included, judged by what the sink would have received: the CoNLL
rows taggedsent_to_conll hands to MaltParser, the DOT text DependencyGraph
renders, and the transition parser's buffer. Nothing is mocked."""

import unicodedata

import pytest

from nltk.pathsec import has_line_unsafe_char

NUL = chr(0)
# Every character class has_line_unsafe_char refuses, spelled with chr()
LINE_BREAKS = [chr(c) for c in (0x0A, 0x0D, 0x0B, 0x0C, 0x1C, 0x1D, 0x1E, 0x85)]
SEPARATORS = [chr(0x2028), chr(0x2029)]
CONTROLS = [chr(c) for c in (0x00, 0x01, 0x07, 0x08, 0x09, 0x1B, 0x7F, 0x9B)]
SURROGATE = chr(0xD800)
UNSAFE = LINE_BREAKS + SEPARATORS + CONTROLS + [SURROGATE]
# Ordinary multilingual content that must keep working
BENIGN = [
    "John",
    "New-York",
    "caf" + chr(0xE9),
    "مرحبا",  # Arabic letters, spelled as literals
    "x" + chr(0x200D) + "y",  # zero-width joiner
    "a" + chr(0x00A0) + "b",  # no-break space
    "\U0001f600",
    "'",
    '"',
    "\\",
    "<b>",
    "&amp;",
    "a" * 5000,
]


def _all_refused_classes_covered():
    # the matrix must agree with the shared rule it drives
    for ch in UNSAFE:
        assert has_line_unsafe_char(ch), hex(ord(ch))
    for text in BENIGN:
        assert not has_line_unsafe_char(text), text


# === 1. CoNLL rows handed to MaltParser ===
class TestConllMatrix:
    def test_matrix_matches_the_shared_rule(self):
        _all_refused_classes_covered()

    @pytest.mark.parametrize("bad", UNSAFE, ids=lambda c: "U+%04X" % ord(c))
    def test_every_unsafe_character_is_refused_in_word_and_tag(self, bad):
        from nltk.parse.util import taggedsent_to_conll

        for pair in (("a" + bad + "b", "NN"), ("ok", "N" + bad + "N")):
            with pytest.raises(ValueError):
                list(taggedsent_to_conll([pair]))

    @pytest.mark.parametrize("text", BENIGN, ids=lambda t: t[:8])
    def test_benign_content_builds_exactly_one_row(self, text):
        from nltk.parse.util import taggedsent_to_conll

        rows = list(taggedsent_to_conll([(text, "NN")]))
        assert len(rows) == 1 and rows[0].count("\n") == 1
        assert rows[0].split("\t")[1] == text and rows[0].count("\t") == 9

    def test_a_row_is_never_re_split_by_a_line_reader(self):
        # what a reader sees is exactly one record per token, whatever the
        # token: str.splitlines (the widest splitter) agrees with the count
        from nltk.parse.util import taggedsent_to_conll

        rows = list(taggedsent_to_conll([(t, "NN") for t in BENIGN]))
        assert len("".join(rows).splitlines()) == len(BENIGN)


# === 2. Graphviz DOT ===
def _unescaped_quotes(dot):
    count, i = 0, 0
    while i < len(dot):
        if dot[i] == "\\":
            i += 2
            continue
        if dot[i] == '"':
            count += 1
        i += 1
    return count


DOT_ATTACKS = [
    'x" ] ; evil -> 0 [ label="',
    'x"]\n9 [label="pwned"]\n8 [label="',
    "x\\",
    'x\\\\"',
    "x\r\n",
    "x\n" + "9 -> 0",
    "x" + chr(0x2028) + "9 -> 0",
    "x" + NUL + "y",
    "{x}",
    "<x>",
    "x'y",
    "x;y",
    "x" * 5000,
]


class TestDotMatrix:
    @pytest.mark.parametrize("word", DOT_ATTACKS, ids=lambda w: repr(w)[:14])
    def test_dependencygraph_word_never_breaks_out(self, word):
        from nltk.parse.dependencygraph import DependencyGraph

        dg = DependencyGraph("John N 2\nloves V 0\nMary N 2")
        dg.nodes[1]["word"] = word
        if NUL in word:
            # a C string ends at NUL, so Graphviz would truncate the label:
            # the word is refused outright instead of rendered
            with pytest.raises(ValueError, match="NUL"):
                dg.to_dot()
            return
        dot = dg.to_dot()
        lines = dot.split("\n")
        # exactly the four node labels and three edge labels of the three-word
        # graph, one statement per line, no raw line break or separator
        # smuggled in, every quote balanced
        assert _unescaped_quotes(dot) == 2 * 7, dot
        assert len(lines) == 12, dot
        # DOT breaks lines on LF and CR only; a Unicode separator inside the
        # quotes is just a character to it, and the count above shows it
        # added no statement
        assert "\r" not in dot
        assert (
            word.replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", "\\n")
            .replace("\r", "\\r")
            in dot
        )

    @pytest.mark.parametrize(
        "address",
        ['1 [label="x"]; 9 -> 0', "1;2", "0x1", 1.0, None, True, b"1", "1"],
        ids=lambda a: repr(a)[:14],
    )
    def test_a_non_integer_address_is_refused_not_interpolated(self, address):
        from nltk.parse.dependencygraph import DependencyGraph

        dg = DependencyGraph("John N 2\nloves V 0\nMary N 2")
        dg.nodes[1]["address"] = address
        with pytest.raises((ValueError, TypeError)):
            dg.to_dot()
        dg = DependencyGraph("John N 2\nloves V 0\nMary N 2")
        dg.nodes[2]["deps"]["dep"] = [address]
        with pytest.raises((ValueError, TypeError)):
            dg.to_dot()

    def test_relation_labels_are_escaped_too(self):
        from nltk.parse.dependencygraph import DependencyGraph

        dg = DependencyGraph("John N 2\nloves V 0\nMary N 2")
        deps = dg.nodes[2]["deps"]
        deps['x" ] ; evil -> 0 [ label="'] = deps.pop(next(iter(deps)))
        dot = dg.to_dot()
        assert _unescaped_quotes(dot) == 2 * 7, dot
        assert len(dot.split("\n")) == 12, dot

    def test_legit_graph_renders_unchanged(self):
        from nltk.parse.dependencygraph import DependencyGraph

        dg = DependencyGraph("John N 2\nloves V 0\nMary N 2")
        assert '1 [label="1 (John)"]' in dg.to_dot()
        assert "2 -> 1" in dg.to_dot()


class TestConllInjection:
    def test_legit_sentence_builds(self):
        from nltk.parse.util import taggedsent_to_conll

        rows = list(taggedsent_to_conll([("John", "NN"), ("runs", "VB")]))
        assert len(rows) == 2 and all(r.endswith("\n") for r in rows)

    @pytest.mark.parametrize(
        "pair",
        [
            ("a\tb", "NN"),  # tab adds a CoNLL column
            ("a\nb", "NN"),  # newline injects a CoNLL row
            ("a\rb", "NN"),
            ("w", "N\tN"),
            ("w", "N\nN"),
            ("w", "N\x00N"),
        ],
    )
    def test_delimiter_in_field_refused(self, pair):
        from nltk.parse.util import taggedsent_to_conll

        with pytest.raises(ValueError, match="tab, newline or NUL"):
            list(taggedsent_to_conll([pair]))


# 3/5. Stanford tagger and Stanford segmenter: newline-per-sentence input.
# (senna's guard moved to #3858, which routes senna through pathsec.spawn_trusted
# and keeps a per-token CR/LF check.)
def _min(cls, **attrs):
    obj = object.__new__(cls)
    for k, v in attrs.items():
        setattr(obj, k, v)
    return obj


def _no_unescaped_breakout(dot):
    # After removing escaped backslashes and escaped quotes, every DOT line must
    # have balanced delimiter quotes and hold no raw newline injected mid-value.
    for line in dot.splitlines():
        stripped = line.replace("\\\\", "").replace('\\"', "")
        if stripped.count('"') % 2 != 0:
            return False
    return True


class TestDotEscaping:
    def test_dependencygraph_escapes_quote_and_newline(self):
        from nltk.parse.dependencygraph import DependencyGraph

        dg = DependencyGraph('ev"il N 2\nloves V 0\nMary N 2')
        dot = dg.to_dot()
        assert '\\"' in dot  # the quote is escaped
        assert _no_unescaped_breakout(dot)

    def test_dependencygraph_legit_still_renders(self):
        from nltk.parse.dependencygraph import DependencyGraph

        dg = DependencyGraph("John N 2\nloves V 0\nMary N 2")
        dot = dg.to_dot()
        assert 'label="0 (None)"' in dot and "John" in dot


class TestTransitionParserBuffer:  # GHSA-r53h family: O(n) front removal
    def test_transition_parser_buffer_is_deque(self):
        from collections import deque

        from nltk.parse.dependencygraph import DependencyGraph
        from nltk.parse.transitionparser import Configuration

        # The sibling fix: the parser buffer became a deque so shift/right-arc
        # consume the front in O(1); __str__ still renders it as a plain list.
        dg = DependencyGraph("the DT 2 det\ncat NN 0 root\n", top_relation_label="root")
        conf = Configuration(dg)
        assert isinstance(conf.buffer, deque)
        assert "Buffer : [1, 2]" in str(conf)


# === 4. What the consolidation review found: lying subclasses, NUL, integer types ===
class _LyingIter(str):
    """Real characters carry the delimiter; __iter__ and __contains__ deny it."""

    def __iter__(self):
        return iter("safe")

    def __contains__(self, item):
        return False


class TestConsolidationFindings:
    @pytest.mark.parametrize("bad", ["\t", "\n", "\r", NUL, chr(0x2028)])
    def test_a_lying_str_subclass_is_judged_on_its_real_characters(self, bad):
        from nltk.parse.util import taggedsent_to_conll

        token = _LyingIter("a" + bad + "b")
        assert has_line_unsafe_char(token) is True
        with pytest.raises(ValueError):
            list(taggedsent_to_conll([(token, "NN")]))
        with pytest.raises(ValueError):
            list(taggedsent_to_conll([("word", _LyingIter("N" + bad))]))

    def test_a_lying_str_subclass_with_safe_characters_still_builds(self):
        from nltk.parse.util import taggedsent_to_conll

        rows = list(taggedsent_to_conll([(_LyingIter("plain"), _LyingIter("NN"))]))
        assert rows == ["1\tplain\t_\tNN\tNN\t_\t0\ta\t_\t_\n"]

    def test_a_nul_in_a_word_or_relation_is_refused_not_rendered(self):
        from nltk.parse.dependencygraph import DependencyGraph

        dg = DependencyGraph("John N 2\nloves V 0\nMary N 2")
        dg.nodes[1]["word"] = "Jo" + NUL + "hn"
        with pytest.raises(ValueError, match="NUL"):
            dg.to_dot()
        dg = DependencyGraph("John N 2\nloves V 0\nMary N 2")
        dg.nodes[2]["deps"] = {"ro" + NUL + "ot": [1]}
        with pytest.raises(ValueError, match="NUL"):
            dg.to_dot()

    def test_integer_typed_addresses_render_and_bool_or_float_are_refused(self):
        numpy = pytest.importorskip("numpy")
        from nltk.parse.dependencygraph import DependencyGraph

        dg = DependencyGraph("John N 2\nloves V 0\nMary N 2")
        dg.nodes[1]["address"] = numpy.int64(1)
        dg.nodes[2]["deps"] = {"nsubj": [numpy.int32(1)], "dobj": [3]}
        dot = dg.to_dot()
        assert '1 [label="1 (John)"]' in dot and "2 -> 1" in dot
        for bad in (True, 1.0, "1", None, 1 + 0j):
            dg = DependencyGraph("John N 2\nloves V 0\nMary N 2")
            dg.nodes[1]["address"] = bad
            with pytest.raises(ValueError):
                dg.to_dot()

    def test_a_lying_word_is_escaped_from_its_real_characters(self):
        from nltk.parse.dependencygraph import DependencyGraph

        class LyingStr(str):
            def __str__(self):
                return "safe"

        dg = DependencyGraph("John N 2\nloves V 0\nMary N 2")
        dg.nodes[1]["word"] = LyingStr('x"] ; evil [label="')
        dot = dg.to_dot()
        assert 'x\\"] ; evil [label=\\"' in dot and "safe" not in dot
        assert _no_unescaped_breakout(dot)


# === 7. DependencyGraph.to_conll: the rows MaltParser trains on ===
CONLL_STYLE_FIELDS = {
    3: ("word", "tag", "head"),
    4: ("word", "tag", "head", "rel"),
    10: ("i", "word", "lemma", "ctag", "tag", "feats", "head", "rel"),
}
CONLL_ROWS = (
    "1\tJohn\tJohn\tNNP\tNNP\t_\t2\tnsubj\t_\t_\n"
    "2\tsees\tsee\tVBZ\tVBZ\t_\t0\tROOT\t_\t_\n"
    "3\tMary\tMary\tNNP\tNNP\t_\t2\tdobj\t_\t_\n"
)


def _conll_graph():
    from nltk.parse.dependencygraph import DependencyGraph

    return DependencyGraph(CONLL_ROWS, top_relation_label="ROOT")


class TestConllOutputInjection:
    def test_a_benign_graph_renders_every_style_exactly(self):
        dg = _conll_graph()
        assert dg.to_conll(10) == CONLL_ROWS
        assert dg.to_conll(4) == (
            "John\tNNP\t2\tnsubj\nsees\tVBZ\t0\tROOT\nMary\tNNP\t2\tdobj\n"
        )
        assert dg.to_conll(3) == "John\tNNP\t2\nsees\tVBZ\t0\nMary\tNNP\t2\n"

    @pytest.mark.parametrize("text", BENIGN)
    def test_benign_content_builds_one_row_per_node(self, text):
        for field in ("word", "lemma", "ctag", "tag", "feats", "rel"):
            dg = _conll_graph()
            dg.nodes[1][field] = text
            for style, fields in CONLL_STYLE_FIELDS.items():
                rows = dg.to_conll(style).split("\n")
                assert rows[-1] == "" and len(rows) == 4
                columns = len(fields) + (2 if style == 10 else 0)
                assert all(row.count("\t") == columns - 1 for row in rows[:3])

    @pytest.mark.parametrize("bad", UNSAFE)
    @pytest.mark.parametrize(
        "field", ["word", "lemma", "ctag", "tag", "feats", "head", "rel"]
    )
    def test_an_unsafe_character_in_an_emitted_field_is_refused(self, field, bad):
        _all_refused_classes_covered()
        for style, fields in CONLL_STYLE_FIELDS.items():
            dg = _conll_graph()
            dg.nodes[1][field] = "2" + bad + "9" if field == "head" else "a" + bad + "b"
            if field in fields:
                with pytest.raises(ValueError, match="to_conll"):
                    dg.to_conll(style)
            else:
                # a field this style never writes cannot inject into it
                assert dg.to_conll(style) == _conll_graph().to_conll(style)

    def test_an_injected_row_never_reaches_the_output(self):
        dg = _conll_graph()
        dg.nodes[1]["word"] = "John\t_\tNNP\tNNP\t_\t2\tnsubj\t_\t_\n9\tEVIL"
        for style in CONLL_STYLE_FIELDS:
            with pytest.raises(ValueError, match="to_conll"):
                dg.to_conll(style)

    def test_a_lying_str_subclass_is_judged_on_its_real_characters(self):
        dg = _conll_graph()
        dg.nodes[1]["word"] = _LyingIter("Jo\thn")
        with pytest.raises(ValueError, match="to_conll"):
            dg.to_conll(10)

    def test_a_lying_format_writes_the_real_characters(self):
        class LyingFormat(str):
            def __format__(self, spec):
                return "x\t9\tINJECTED\n"

        dg = _conll_graph()
        dg.nodes[1]["word"] = LyingFormat("John")
        assert dg.to_conll(10) == CONLL_ROWS

    def test_an_object_rendering_to_a_lying_subclass_is_judged_on_its_real_text(self):
        class Renders:
            def __str__(self):
                return _LyingIter("Jo\nhn")

        assert has_line_unsafe_char(Renders()) is True
        dg = _conll_graph()
        dg.nodes[1]["word"] = Renders()
        with pytest.raises(ValueError, match="to_conll"):
            dg.to_conll(4)

    def test_malt_train_refuses_before_writing_any_file(self, tmp_path):
        from nltk.parse.malt import MaltParser

        parser = _min(MaltParser, _working_dir=str(tmp_path))
        bad = _conll_graph()
        bad.nodes[1]["word"] = "John\t_\tNNP\tNNP\t_\t2\tnsubj\t_\t_\n9\tEVIL"
        with pytest.raises(ValueError, match="to_conll"):
            parser.train([_conll_graph(), bad])
        assert list(tmp_path.iterdir()) == []


class TestLineUnsafeFastPath:
    def test_the_printable_fast_path_agrees_with_the_category_rule_everywhere(self):
        refused = {"Cc", "Cs", "Zl", "Zp"}
        wrong = [
            hex(cp)
            for cp in range(0x110000)
            if has_line_unsafe_char(chr(cp))
            != (unicodedata.category(chr(cp)) in refused)
        ]
        assert wrong == []

    def test_allow_tab_still_exempts_only_the_tab(self):
        assert has_line_unsafe_char("a\tb", allow_tab=True) is False
        assert has_line_unsafe_char("a\tb") is True
        assert has_line_unsafe_char("a\t\nb", allow_tab=True) is True


class TestDotEscapeOfRenderedValues:
    def test_a_value_rendering_to_a_lying_subclass_is_escaped_from_its_real_text(self):
        from nltk.parse.dependencygraph import DependencyGraph

        class LyingReplace(str):
            def replace(self, old, new, count=-1):
                return str.__str__(self)  # refuses to escape anything

        class Renders:
            def __str__(self):
                return LyingReplace('x"] ; evil [label="')

        dg = DependencyGraph("John N 2\nloves V 0\nMary N 2")
        dg.nodes[1]["word"] = Renders()
        dot = dg.to_dot()
        assert 'x\\"] ; evil [label=\\"' in dot
        assert _no_unescaped_breakout(dot)


class TestTransitionParserLabels:
    def test_a_colon_in_a_relation_label_survives_training_and_parsing(
        self, pathsec_sandbox
    ):
        numpy = pytest.importorskip("numpy")
        pytest.importorskip("sklearn")
        from nltk.parse.dependencygraph import DependencyGraph
        from nltk.parse.transitionparser import TransitionParser

        rows = (
            "1\tthe\t_\tDT\tDT\t_\t2\tnmod:det\t_\t_\n"
            "2\tdog\t_\tNN\tNN\t_\t3\tnmod:nsubj\t_\t_\n"
            "3\tsleeps\t_\tVBZ\tVBZ\t_\t0\tROOT\t_\t_\n"
        )
        gold = DependencyGraph(rows, top_relation_label="ROOT")
        model = pathsec_sandbox.root / "ud.model"
        for algorithm in ("arc-standard", "arc-eager"):
            numpy.random.seed(0)
            parser = TransitionParser(algorithm)
            parser.train([gold] * 4, str(model), verbose=False)
            learned = set(parser._match_transition.values())
            assert {"LEFTARC:nmod:det", "LEFTARC:nmod:nsubj"} <= learned, learned
            (parsed,) = parser.parse([gold], str(model))
            rels = {node["rel"] for node in parsed.nodes.values() if node["rel"]}
            assert rels and rels <= {"nmod:det", "nmod:nsubj", "ROOT"}, rels
            assert "nmod" not in rels
