# Natural Language Toolkit: tree pretty-printer attack harness
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""Drive the REAL tree pretty-printer (``TreePrettyPrinter`` and
``Tree.pretty_print``, with and without ``rtl``) with every hostile and
benign input its channels accept, and assert the refusal, the neutralised
output or the bounded cost. Nothing is mocked and no guard is patched.

Channels: the labels and leaves of the tree (untrusted whenever the tree was
parsed from, or produced by a parser over, attacker text), the ``sentence``
list of a discontinuous tree, the ``highlight`` sequence, and the shape of the
tree itself (width, depth, label length). Sinks: the terminal through
``Tree.pretty_print`` (``nltk.termsec.safe_print``; CWE-150, CVE-2021-42574,
CWE-1236), the HTML and SVG renderings (CWE-79) and CPU/memory through the
layout and the label-wrapping regex (CWE-400, CWE-407, CWE-1333).

The reference for the attachment property is a local copy of the algorithm
pull request #3472 first proposed, which rebuilt the tree and poured the
leaves back in reading order; it is kept here as the oracle of what the
shipped code must NOT do.

Every invisible character is built with ``chr(0x...)``: the tool layer that
writes these files decodes backslash escapes."""

import io

import pytest

from nltk.termsec import _bidi_is_balanced, sanitize_terminal
from nltk.test.unit.test_termsec_attack_matrix import _dangerous_cp
from nltk.test.unit.test_tree_prettyprinter_rtl import (
    crossing_by_geometry,
    drawn_crossings,
)
from nltk.test.unit.timing import assert_subquadratic, budget
from nltk.tree import ProbabilisticTree, Tree, TreePrettyPrinter
from nltk.tree.prettyprinter import LRM
from nltk.tree.tree import MAX_TREE_DEPTH
from nltk.xmlsec import fromstring as xml_fromstring

ESC = chr(0x1B)
BEL = chr(0x07)
CSI8 = chr(0x9B)
OSC8 = chr(0x9D)
RLO, LRO = chr(0x202E), chr(0x202D)
RLE, LRE, PDF = chr(0x202B), chr(0x202A), chr(0x202C)
LRI, PDI = chr(0x2066), chr(0x2069)
FSI = chr(0x2068)
RLM, ALM = chr(0x200F), chr(0x061C)
ZWSP, ZWNJ, WJ = chr(0x200B), chr(0x200C), chr(0x2060)
SHY, BOM = chr(0xAD), chr(0xFEFF)
LSEP, PSEP = chr(0x2028), chr(0x2029)
TAG_A, NONCHAR, SURROGATE = chr(0xE0041), chr(0xFFFE), chr(0xD800)
MARKS = frozenset((ord(LRM), ord(RLM), ord(ALM)))
BACKSLASH = chr(0x5C)

ARABIC = (
    "(S (VP (V ذهب) (NP (DET ال) (N طفل)) (PP (PREP إلى) (NP (DET ال) (N حديقة)))))"
)
ARABIC_POS = {"ذهب": "V", "ال": "DET", "طفل": "N", "إلى": "PREP", "حديقة": "N"}


def _live(text):
    """A control a terminal would act on: everything the chokepoint escapes
    except the three direction marks it keeps when the nesting balances."""
    return any(_dangerous_cp(ord(c)) and ord(c) not in MARKS for c in text)


def _printed(tree, **kwargs):
    buf = io.StringIO()
    tree.pretty_print(stream=buf, **kwargs)
    return buf.getvalue()


def _spans(row):
    """``[(token, start, end)]`` of the non-blank runs of one drawn row."""
    found, start = [], None
    for i, ch in enumerate(row + " "):
        if ch != " " and start is None:
            start = i
        elif ch == " " and start is not None:
            found.append((row[start:i], start, i))
            start = None
    return found


def _attachments(text):
    """``{leaf: label}`` read off a drawing whose leaves all sit under unary
    preterminals: the label two rows above a leaf, centred on its column."""
    grid = text.replace(LRM, "").rstrip("\n").split("\n")
    labels = _spans(grid[-3])
    found = {}
    for leaf, start, end in _spans(grid[-1]):
        centre = (start + end - 1) / 2
        over = [lab for lab, a, b in labels if abs((a + b - 1) / 2 - centre) <= 1]
        assert len(over) == 1, (leaf, grid)
        found[leaf] = over[0]
    return found


def _pr3472_mirror(tree):
    """The algorithm #3472 first proposed, kept as the oracle of the defect:
    mirror the structure, then pour the original leaves back in reading
    order, which moves leaves between parents and rebuilds every node."""

    def mirror(node):
        return type(node)(
            node.label(),
            [mirror(c) if isinstance(c, Tree) else c for c in reversed(node)],
        )

    leaves = iter(tree.leaves())

    def restore(node):
        if isinstance(node, Tree):
            return type(node)(node.label(), [restore(c) for c in node])
        return next(leaves)

    return restore(mirror(tree))


class TestAttachmentOracle:
    """The property the review found broken in the first approach: a drawing
    must attach every leaf to its own preterminal, in both directions."""

    def test_pr3472_rebuild_moved_leaves_between_parents(self):
        tree = Tree.fromstring("(S (NP Mary) (VP walks))")
        rebuilt = _pr3472_mirror(tree)
        assert rebuilt == Tree.fromstring("(S (VP Mary) (NP walks))")
        assert _attachments(TreePrettyPrinter(rebuilt).text()) == {
            "Mary": "VP",
            "walks": "NP",
        }
        arabic = _pr3472_mirror(Tree.fromstring(ARABIC))
        assert _attachments(TreePrettyPrinter(arabic).text()) != ARABIC_POS

    def test_shipped_rtl_keeps_every_leaf_under_its_preterminal(self):
        tree = Tree.fromstring(ARABIC)
        for rtl in (False, True):
            for options in ({}, {"unicodelines": True}, {"nodedist": 3}):
                drawn = TreePrettyPrinter(tree, rtl=rtl).text(**options)
                assert _attachments(drawn) == ARABIC_POS, (rtl, options)
        small = Tree.fromstring("(S (NP Mary) (VP walks))")
        assert _attachments(TreePrettyPrinter(small, rtl=True).text()) == {
            "Mary": "NP",
            "walks": "VP",
        }

    def test_pr3472_rebuild_dropped_subclass_state_the_shipped_code_keeps(self):
        tree = ProbabilisticTree(
            "S", [ProbabilisticTree("NP", ["Mary"], prob=0.5)], prob=0.25
        )
        assert _pr3472_mirror(tree).prob() is None
        TreePrettyPrinter(tree, rtl=True).text()
        assert tree.prob() == 0.25 and tree[0].prob() == 0.5

    def test_shipped_rtl_never_touches_the_tree(self):
        tree = Tree.fromstring(ARABIC)
        children = [id(c) for c in tree.subtrees()]
        before = tree.copy(True)
        for rtl in (False, True):
            _printed(tree, rtl=rtl)
            TreePrettyPrinter(tree, rtl=rtl).svg()
        assert tree == before and [id(c) for c in tree.subtrees()] == children


class TestTerminalSink:
    HOSTILE = {
        "csi-clear-screen": "evil" + ESC + "[2Jx",
        "csi-cursor-up-rewrite": "evil" + ESC + "[2A" + ESC + "[K" + "ok",
        "osc-window-title": "evil" + ESC + "]0;pwned" + BEL + "x",
        "osc52-clipboard": "evil" + ESC + "]52;c;cHduZWQ=" + BEL,
        "osc8-hyperlink": "evil" + ESC + "]8;;http://x" + ESC + BACKSLASH + "x",
        "dcs-query": "evil" + ESC + "P$q" + ESC + BACKSLASH,
        "c1-8bit-csi": "evil" + CSI8 + "31mx",
        "c1-8bit-osc": "evil" + OSC8 + "0;t" + BEL,
        "bel": "evil" + BEL,
        "cr-overwrite": "evil" + chr(0x0D) + "good",
        "backspace-erase": "evil" + chr(0x08) * 4 + "good",
        "nul": "evil" + chr(0) + "x",
        "del": "evil" + chr(0x7F),
        "vt-ff": "evil" + chr(0x0B) + chr(0x0C),
        "rlo": "evil" + RLO + "x",
        "lro": "evil" + LRO + "x",
        "rle-unbalanced": "evil" + RLE + "x",
        "pdf-stray": "evil" + PDF,
        "fsi-unbalanced": "evil" + FSI + "x",
        "crossed-nesting": LRE + LRI + PDF + PDI + "evil",
        "override-closed": RLO + "evil" + PDF,
        "zwsp": "evil" + ZWSP + "x",
        "word-joiner": "evil" + WJ + "x",
        "soft-hyphen": "evil" + SHY + "x",
        "line-separator": "evil" + LSEP + "x",
        "paragraph-separator": "evil" + PSEP + "x",
        "bom": BOM + "evil",
        "unicode-tag": "evil" + TAG_A,
        "noncharacter": "evil" + NONCHAR,
        "lone-surrogate": "evil" + SURROGATE,
    }

    @pytest.mark.parametrize("rtl", [False, True])
    @pytest.mark.parametrize("name", sorted(HOSTILE))
    def test_hostile_label_and_leaf_never_reach_the_terminal_live(self, name, rtl):
        payload = self.HOSTILE[name]
        tree = Tree(
            "S", [Tree(payload, ["leaf"]), Tree("NP", [payload]), Tree("VP", ["ذهب"])]
        )
        for options in ({}, {"unicodelines": True}, {"ansi": True}, {"html": True}):
            out = _printed(tree, rtl=rtl, **options)
            assert "evil" in out and not _live(out), (name, options, out)
            assert sanitize_terminal(out) == out, (name, options)

    @pytest.mark.parametrize("name", sorted(HOSTILE))
    def test_hostile_sentence_token_is_neutralised(self, name):
        tree = Tree.fromstring("(S (A 0 2) (B 1))", read_leaf=int)
        sentence = [self.HOSTILE[name], "b", "ذهب"]
        out = _printed(tree, sentence=sentence, rtl=True)
        assert "evil" in out and not _live(out) and sanitize_terminal(out) == out

    def test_direction_marks_of_a_clean_rtl_tree_survive_and_balance(self):
        out = _printed(Tree.fromstring(ARABIC), rtl=True)
        assert out.count(LRM) == 6 and _bidi_is_balanced(out)
        assert sanitize_terminal(out) == out and not _live(out)

    def test_one_hostile_cell_escapes_every_mark_too(self):
        tree = Tree.fromstring(ARABIC)
        tree[0][0][0] = "ذهب" + RLE
        out = _printed(tree, rtl=True)
        assert LRM not in out and (BACKSLASH + "u200e") in out and not _live(out)
        assert (BACKSLASH + "u202b") in out

    def test_legit_balanced_bidi_and_persian_zwnj_pass_through(self):
        verb = "می" + ZWNJ + "کنند"
        tree = Tree(
            "S",
            [
                Tree("V", [verb]),
                Tree("N", [RLE + "abc" + PDF]),
                Tree("P", [LRI + "x" + PDI]),
            ],
        )
        out = _printed(tree, rtl=True)
        assert verb in out and RLE + "abc" + PDF in out and LRI + "x" + PDI in out
        # nothing was escaped: the sink passed the balanced text through as is
        assert out == TreePrettyPrinter(tree, rtl=True).text() + "\n"
        assert out.count(LRM) == 1 and ESC not in out and RLO not in out

    def test_ansi_colour_request_cannot_smuggle_a_live_escape(self):
        tree = Tree.fromstring(ARABIC)
        tree[0][0].set_label("V" + ESC + "[2J")
        out = _printed(tree, rtl=True, ansi=True, highlight=[tree[0][0]])
        assert not _live(out) and "V" in out

    def test_newline_and_tab_inside_a_leaf_stay_within_the_grid(self):
        tree = Tree(
            "S", [Tree("A", ["one\ntwo"]), Tree("B", ["x\ty"]), Tree("C", ["ذهب"])]
        )
        for rtl in (False, True):
            out = _printed(tree, rtl=rtl)
            lines = out.rstrip("\n").split("\n")
            assert "one" in out and "two" in out and "y" in out and not _live(out)
            assert all("\n" not in line for line in lines)


class TestHighlightChannel:
    def test_foreign_highlight_objects_do_not_crash_or_match(self):
        tree = Tree.fromstring(ARABIC)
        for foreign in ([None], ["ذهب"], [object()], [3.5], [()], [Tree("X", ["y"])]):
            text = TreePrettyPrinter(tree, highlight=foreign, rtl=True).text(ansi=True)
            assert "ذهب" in text and ESC not in text

    def test_terminal_index_highlight_colours_exactly_that_leaf(self):
        tree = Tree.fromstring(ARABIC)
        for rtl in (False, True):
            text = TreePrettyPrinter(tree, highlight=[2], rtl=rtl).text(ansi=True)
            assert text.count(ESC + "[31;1m") == 1
            coloured = text.split(ESC + "[31;1m")[1].split(ESC + "[0m")[0]
            assert coloured.replace(LRM, "").strip() == "طفل"

    @pytest.mark.parametrize("rtl", [False, True])
    def test_index_guards_hold(self, rtl):
        for source, sentence in (
            ("(S (A 0) (B 5))", ["a", "b"]),
            ("(S (A 0) (B 0))", ["a"]),
            ("(S (A -1) (B 0))", ["a", "b"]),
        ):
            with pytest.raises(ValueError):
                TreePrettyPrinter(
                    Tree.fromstring(source, read_leaf=int), sentence, rtl=rtl
                )
        with pytest.raises(ValueError):
            TreePrettyPrinter(Tree.fromstring("(S (A x))"), ["x"], rtl=rtl)


class TestHtmlAndSvgSinks:
    PAYLOADS = [
        "<script>alert(1)</script>",
        "</pre><b>x",
        '" onload="evil',
        "&amp;&lt;",
        "]]><!--",
        "<svg onload=x>",
    ]

    @pytest.mark.parametrize("rtl", [False, True])
    @pytest.mark.parametrize("payload", PAYLOADS)
    def test_svg_escapes_labels_and_stays_well_formed(self, payload, rtl):
        tree = Tree("S", [Tree(payload, [payload]), Tree("N", ["ذهب"])])
        svg = TreePrettyPrinter(tree, highlight=[tree[0]], rtl=rtl).svg()
        assert "<script" not in svg and "<b>" not in svg and "]]>" not in svg
        assert (
            "onload="
            not in svg.replace("&quot;", "")[svg.find("<text") :].split(">")[0]
        )
        texts = [
            el.text
            for el in xml_fromstring(svg).iter("{http://www.w3.org/2000/svg}text")
        ]
        assert texts.count(payload) == 2 and "ذهب" in texts

    @pytest.mark.parametrize("payload", PAYLOADS)
    def test_html_mode_escapes_labels_and_keeps_marks(self, payload):
        tree = Tree("S", [Tree(payload, [payload]), Tree("N", ["ذهب"])])
        html = TreePrettyPrinter(tree, highlight=[tree[0]], rtl=True).text(html=True)
        assert "<script" not in html and "<b>" not in html and "<svg" not in html
        assert "<font color=blue>" in html
        assert html.count("<font") == html.count("</font>") and LRM in html

    def test_control_characters_in_svg_text_are_the_callers_to_strip(self):
        # the SVG is a document for a viewer, not a terminal: an ESC inside a
        # label is not well-formed XML 1.0, so a parser refuses the document
        svg = TreePrettyPrinter(Tree("S", [Tree("A" + ESC + "[2J", ["x"])])).svg()
        with pytest.raises(Exception):
            xml_fromstring(svg)


class TestShapeCost:
    """CWE-400 / CWE-407: the layout is linear in the width of the tree, and
    the cost in depth is bounded by Tree.fromstring's MAX_TREE_DEPTH."""

    @staticmethod
    def _flat(n, leaf="w"):
        return Tree("S", [Tree("N", [leaf + str(i)]) for i in range(n)])

    @staticmethod
    def _balanced(leaves):
        if leaves == 1:
            return Tree("N", ["w"])
        half = TestShapeCost._balanced(leaves // 2)
        return Tree("S", [half, half.copy(True)])

    @staticmethod
    def _comb(depth):
        tree = Tree("X", ["w"])
        for i in range(depth):
            tree = Tree("S%d" % i, [tree, Tree("N", ["w"])])
        return tree

    @pytest.mark.parametrize("rtl", [False, True])
    def test_width_is_linear(self, rtl):
        trees = {n: self._flat(n, "ذهب") for n in (2000, 8000)}
        assert_subquadratic(
            lambda n: TreePrettyPrinter(trees[n], rtl=rtl).text(),
            2000,
            8000,
            cpu_bound=True,
        )

    def test_balanced_width_is_subquadratic(self):
        trees = {n: self._balanced(n) for n in (1024, 4096)}
        assert_subquadratic(
            lambda n: TreePrettyPrinter(trees[n], rtl=True).text(),
            1024,
            4096,
            cpu_bound=True,
        )

    def test_depth_at_the_fromstring_cap_is_bounded(self):
        tree = Tree.fromstring(str(self._comb(MAX_TREE_DEPTH - 2)))
        with budget(10, "the deepest tree fromstring accepts", cpu_bound=True):
            drawn = TreePrettyPrinter(tree, rtl=True)
            text, svg = drawn.text(), drawn.svg()
        assert text.count("\n") > MAX_TREE_DEPTH and "<svg" in svg

    def test_deeper_than_the_cap_fails_closed_fast(self):
        tree = self._comb(3000)
        with budget(10, "a tree far deeper than any fromstring accepts"):
            with pytest.raises(RecursionError):
                TreePrettyPrinter(tree)

    @pytest.mark.parametrize("rtl", [False, True])
    def test_long_label_wrapping_is_linear(self, rtl):
        def op(n):
            tree = Tree("S", [Tree("x" * n, ["ذهب" * (n // 3)])])
            TreePrettyPrinter(tree, rtl=rtl).text(maxwidth=16)

        assert_subquadratic(op, 50_000, 200_000, cpu_bound=True)

    def test_huge_label_unwrapped_and_abbreviated(self):
        label = "x" * 1_000_000
        tree = Tree(label, [label])
        with budget(5, "a megabyte label", cpu_bound=True):
            text = TreePrettyPrinter(tree).text(maxwidth=None)
            short = TreePrettyPrinter(tree).text(abbreviate=True)
        assert label in text and len(short) < 100

    def test_many_leaves_under_one_node_with_marks(self):
        n = 20_000
        tree = Tree("S", ["ذهب%d" % i for i in range(n)])
        with budget(5, "twenty thousand marked leaves", cpu_bound=True):
            text = TreePrettyPrinter(tree, rtl=True).text()
        assert text.count(LRM) == n


class TestBenignParameters:
    def test_non_string_labels_and_leaves_render(self):
        from nltk.grammar import Nonterminal

        # integer LEAVES are sentence indices by the printer's contract, so the
        # Tree docstring's own example takes string leaves here
        tree = Tree(1, ["two", Tree(3, ["four"]), 5.5])
        for rtl in (False, True):
            text = TreePrettyPrinter(tree, rtl=rtl).text(ansi=True)
            assert "1" in text and "four" in text and "5.5" in text
            assert ">3<" in TreePrettyPrinter(tree, rtl=rtl).svg()
        grammar = Tree(Nonterminal("S"), [Tree(Nonterminal("-NP"), ["x"])])
        text = TreePrettyPrinter(grammar).text(ansi=True)
        assert "-NP" in text and ESC + "[32;1m" in text  # funccolor for a "-" label

    @pytest.mark.parametrize("nodedist", [0, -1, 7])
    def test_odd_nodedist_values_do_not_crash(self, nodedist):
        tree = Tree.fromstring(ARABIC)
        for rtl in (False, True):
            text = TreePrettyPrinter(tree, rtl=rtl).text(nodedist=nodedist)
            assert "ذهب" in text

    @pytest.mark.parametrize("maxwidth", [1, 2, 3, 4, 5, 16, None])
    def test_small_and_disabled_maxwidth(self, maxwidth):
        tree = Tree.fromstring("(sentence (plural-noun-phrase Superconductors))")
        text = TreePrettyPrinter(tree, rtl=True).text(maxwidth=maxwidth)
        assert "".join(text.split()).count("Superconductors") == 1

    def test_empty_frontier_tuple_leaf_and_single_leaf(self):
        for source in (
            Tree.fromstring("(S (NP ) (VP x))"),
            Tree("S", [("w", "POS")]),
            Tree("S", ["x"]),
        ):
            for rtl in (False, True):
                assert TreePrettyPrinter(source, rtl=rtl).text()


class TestCrossingCost:
    """CWE-400 / CWE-407 for the crossing-edge sweep of ``nodecoords``: the
    check that marks the edges drawn through another node's branch must not
    bring back a rescan of the grid per node. Shapes with thousands of
    crossing lines in one row stay linear, a discontinuous comb at the depth
    cap and a nest of branches over the same lines stay inside a budget, and
    right-to-left, hostile, empty and huge text on crossing trees is drawn
    with every crossing edge still found and moved last."""

    @staticmethod
    def _chain(n):
        """Every preterminal straddles the next: n/2 - 1 lines, each crossing
        one branch, all in one row."""
        kids = [Tree("P%d" % i, [2 * i, 2 * i + 3]) for i in range(n // 2 - 1)]
        kids.append(Tree("Q", [1]))
        return Tree("S", kids), [str(i) for i in range(n)]

    @staticmethod
    def _interleaved(n):
        """Two preterminals whose leaves alternate: one branch over n/2 lines."""
        tree = Tree(
            "S", [Tree("A", list(range(0, n, 2))), Tree("B", list(range(1, n, 2)))]
        )
        return tree, [str(i) for i in range(n)]

    @staticmethod
    def _nested(n):
        """Every preterminal contains the next, one per row: the line of each
        inner one crosses every outer branch, (n/2 - 1)(n/2)/2 crossings on
        n/2 - 1 lines, each of which must be retired at its first branch."""
        kids = [Tree("P%d" % i, [i, n - 1 - i]) for i in range(n // 2)]
        return Tree("S", kids), [str(i) for i in range(n)]

    @staticmethod
    def _disco_comb(depth):
        """A comb whose every level holds a preterminal straddling the next."""
        node = Tree("Q", [1])
        for i in reversed(range(depth)):
            node = Tree("S%d" % i, [Tree("P%d" % i, [2 * i, 2 * i + 3]), node])
        return node, [str(j) for j in range(2 * depth + 2)]

    @staticmethod
    def _crossing_last(drawn):
        crossing = crossing_by_geometry(drawn)
        order = list(drawn.edges)
        assert set(order[len(order) - len(crossing) :]) == crossing
        return len(crossing)

    @pytest.mark.parametrize("rtl", [False, True])
    def test_thousands_of_crossing_lines_in_one_row_are_linear(self, rtl):
        trees = {n: self._chain(n) for n in (5000, 20000)}
        assert_subquadratic(
            lambda n: TreePrettyPrinter(*trees[n], rtl=rtl).text(),
            5000,
            20000,
            cpu_bound=True,
        )
        small = TreePrettyPrinter(*self._chain(400), rtl=rtl)
        assert self._crossing_last(small) == 199
        assert drawn_crossings(small.text(unicodelines=True)) == 199
        big = TreePrettyPrinter(*trees[20000], rtl=rtl)
        assert drawn_crossings(big.text(unicodelines=True)) == 9999

    def test_one_branch_over_thousands_of_lines_is_linear(self):
        trees = {n: self._interleaved(n) for n in (5000, 20000)}
        assert_subquadratic(
            lambda n: TreePrettyPrinter(*trees[n], rtl=True).text(),
            5000,
            20000,
            cpu_bound=True,
        )
        small = TreePrettyPrinter(*self._interleaved(400))
        assert self._crossing_last(small) == 200
        assert (
            drawn_crossings(TreePrettyPrinter(*trees[20000]).text(unicodelines=True))
            == 10000
        )

    def test_nested_branches_retire_each_line_once(self):
        tree, sentence = self._nested(400)
        with budget(
            10, "two hundred nested branches over the same lines", cpu_bound=True
        ):
            drawn = TreePrettyPrinter(tree, sentence, rtl=True)
            text = drawn.text(unicodelines=True)
        assert self._crossing_last(drawn) == 199
        assert drawn_crossings(text) == 199 * 200 // 2

    def test_a_discontinuous_comb_at_the_depth_cap_is_bounded(self):
        tree, sentence = self._disco_comb(MAX_TREE_DEPTH - 2)
        tree = Tree.fromstring(str(tree), read_leaf=int)
        with budget(
            10, "a discontinuous comb at the fromstring depth cap", cpu_bound=True
        ):
            drawn = TreePrettyPrinter(tree, sentence, rtl=True)
            text, svg = drawn.text(), drawn.svg()
        assert self._crossing_last(drawn) == 2 * (MAX_TREE_DEPTH - 2) - 1
        assert text.count("\n") > MAX_TREE_DEPTH and "<svg" in svg

    def test_hostile_and_right_to_left_tokens_on_crossing_lines(self):
        tree, _ = self._chain(2000)
        hostile = sorted(TestTerminalSink.HOSTILE.values())
        sentence = [
            ("ذهب", "ישראל", "٣", hostile[i % len(hostile)])[i % 4] for i in range(2000)
        ]
        with budget(10, "two thousand hostile and bidi tokens on crossing lines"):
            out = _printed(tree, sentence=sentence, rtl=True, unicodelines=True)
        assert "evil" in out and not _live(out) and sanitize_terminal(out) == out
        assert drawn_crossings(out) == 999
        clean = [("ذهب", "ישראל")[i % 2] for i in range(2000)]
        out = _printed(tree, sentence=clean, rtl=True)
        # one mark per drawn leaf; the chain leaves one token unattached
        assert out.count(LRM) == len(tree.leaves()) == 1999
        assert _bidi_is_balanced(out) and not _live(out)
        assert self._crossing_last(TreePrettyPrinter(tree, clean, rtl=True)) == 999

    def test_empty_and_huge_labels_on_crossing_nodes(self):
        tree, sentence = self._chain(200)
        for i, kid in enumerate(tree):
            if kid.label().startswith("P"):
                kid.set_label("" if i % 2 else "x" * 5000)
        with budget(5, "a hundred crossing nodes labelled empty or five thousand wide"):
            drawn = TreePrettyPrinter(tree, sentence, rtl=True)
            wrapped, unwrapped, svg = (
                drawn.text(maxwidth=16),
                drawn.text(maxwidth=None),
                drawn.svg(),
            )
        assert self._crossing_last(drawn) == 99
        assert "x" * 5000 in unwrapped and "x" * 5000 not in wrapped
        assert svg.count("x" * 5000) == 50 and "<script" not in svg
