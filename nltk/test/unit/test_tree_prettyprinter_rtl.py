# Natural Language Toolkit: right-to-left tree drawing tests
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""Functional tests for ``TreePrettyPrinter(..., rtl=True)`` and
``Tree.pretty_print(rtl=True)`` (issue #2886, pull request #3472), and for
the ``highlight`` and ``maxwidth=None`` repairs made alongside.

``rtl`` mirrors the drawing grid, so the first child of every node is drawn
at the right as a tree of Arabic, Hebrew, Persian or Urdu is read, and puts an
invisible LEFT-TO-RIGHT MARK before every cell of right-to-left text so a
bidi-aware terminal keeps the columns. The tree is never rebuilt: each leaf
stays under its own preterminal, subclasses keep their state and
``highlight`` keeps naming the original nodes.

Every invisible character is built with ``chr(0x...)``: the tool layer that
writes these files decodes backslash escapes."""

import io
import warnings

import pytest

from nltk.termsec import _bidi_is_balanced
from nltk.tree import (
    ImmutableTree,
    ParentedTree,
    ProbabilisticTree,
    Tree,
    TreePrettyPrinter,
)
from nltk.tree.prettyprinter import LRM, _holds_rtl

ZWNJ = chr(0x200C)
ESC = chr(0x1B)
BLUE, RED, RESET = ESC + "[34;1m", ESC + "[31;1m", ESC + "[0m"

SMALL = "(S (NP Mary) (VP walks))"
ENGLISH = "(s (dp (d the) (np dog)) (vp (v chased) (dp (d the) (np cat))))"
ARABIC = (
    "(S (VP (V ذهب) (NP (DET ال) (N طفل)) (PP (PREP إلى) (NP (DET ال) (N حديقة)))))"
)
HEBREW = "(S (NP (NNP ישראל)) (VP (VBD אכל) (NP (NN תפוח))))"
# the Persian tree of issue #2886; its verb holds a ZWNJ, as Persian does
PERSIAN = (
    "(S (VPS (N آشپزها) (VP (PP (PREP_EZ برای) (N مهمانها)) "
    "(MV (N آشپزی) (V می" + ZWNJ + "کنند)))) (PUNC .))"
)

SMALL_LTR = (
    "      S       \n"
    "  ____|____    \n"
    " NP        VP \n"
    " |         |   \n"
    "Mary     walks\n"
)
SMALL_RTL = (
    "       S      \n"
    "   ____|___    \n"
    "  VP       NP \n"
    "  |        |   \n"
    "walks     Mary\n"
)
ENGLISH_RTL = """\
              s
          ____|_________
         vp             |
      ___|____          |
     dp       |         dp
  ___|___     |      ___|___
 np      d    v     np      d
 |       |    |     |       |
cat     the chased dog     the"""
ARABIC_RTL = """\
                    S
                    |
                    VP
            ________|___________
           PP           |       |
        ___|___         |       |
       NP      |        NP      |
   ____|___    |     ___|___    |
  N       DET PREP  N      DET  V
  |        |   |    |       |   |
حديقة      ال إلى  طفل      ال ذهب"""
HEBREW_RTL = """\
          S
       ___|____
      VP       |
  ____|___     |
 NP       |    NP
 |        |    |
 NN      VBD  NNP
 |        |    |
תפוח     אכל ישראל"""
DISCONTINUOUS_RTL = (
    "         S     \n"
    "      ___       \n"
    "     A   |     \n"
    "  ___|__ | __   \n"
    " |       B   | \n"
    " |       |   |  \n"
    " c       b   a \n"
)


def plain(text):
    """The drawing without its direction marks, as a character grid."""
    return text.replace(LRM, "")


def stripped(text):
    return [line.rstrip() for line in plain(text).rstrip("\n").split("\n")]


def printed(tree, **kwargs):
    buf = io.StringIO()
    tree.pretty_print(stream=buf, **kwargs)
    return buf.getvalue()


def svg_x(svg):
    """``{label: x}`` of the text elements of an SVG drawing."""
    found = {}
    for chunk in svg.split("<text ")[1:]:
        attrs, rest = chunk.split(">", 1)
        label = rest.split("</text>", 1)[0]
        found[label] = float(attrs.split('x="', 1)[1].split('"', 1)[0])
    return found


class TestMirroredGrid:
    @pytest.mark.parametrize("source", [SMALL, ENGLISH, ARABIC, HEBREW, PERSIAN])
    def test_rtl_reflects_every_column_and_nothing_else(self, source):
        tree = Tree.fromstring(source)
        ltr, rtl = TreePrettyPrinter(tree), TreePrettyPrinter(tree, rtl=True)
        maxcol = max(col for _, col in ltr.coords.values())
        assert rtl.coords == {
            n: (row, maxcol - col) for n, (row, col) in ltr.coords.items()
        }
        assert list(rtl.nodes.items()) == list(ltr.nodes.items())
        assert list(rtl.edges.items()) == list(ltr.edges.items())
        assert rtl.highlight == ltr.highlight
        assert rtl.rtl is True and ltr.rtl is False

    def test_small_tree_exact(self):
        tree = Tree.fromstring(SMALL)
        assert TreePrettyPrinter(tree).text() == SMALL_LTR
        assert TreePrettyPrinter(tree, rtl=False).text() == SMALL_LTR
        assert TreePrettyPrinter(tree, rtl=True).text() == SMALL_RTL
        assert LRM not in TreePrettyPrinter(tree, rtl=True).text()

    def test_english_tree_drawn_mirrored(self):
        tree = Tree.fromstring(ENGLISH)
        assert stripped(TreePrettyPrinter(tree, rtl=True).text()) == ENGLISH_RTL.split(
            "\n"
        )

    def test_arabic_tree_reads_from_the_right(self):
        tree = Tree.fromstring(ARABIC)
        text = TreePrettyPrinter(tree, rtl=True).text()
        assert stripped(text) == ARABIC_RTL.split("\n")
        assert text.count(LRM) == len(tree.leaves())
        assert tree.leaves() == ["ذهب", "ال", "طفل", "إلى", "ال", "حديقة"]
        assert stripped(text)[-1].split() == list(reversed(tree.leaves()))

    def test_hebrew_tree(self):
        tree = Tree.fromstring(HEBREW)
        text = TreePrettyPrinter(tree, rtl=True).text()
        assert stripped(text) == HEBREW_RTL.split("\n")
        assert text.count(LRM) == 3

    def test_persian_tree_of_the_issue(self):
        tree = Tree.fromstring(PERSIAN)
        text = TreePrettyPrinter(tree, rtl=True).text()
        verb = "می" + ZWNJ + "کنند"
        assert verb in text and text.count(LRM) == 5  # five words and a "."
        assert stripped(text)[-1].split() == list(reversed(tree.leaves()))
        assert stripped(text)[-3].split() == ["PUNC", "V", "N", "N", "PREP_EZ", "N"]

    def test_rtl_is_a_truth_value(self):
        tree = Tree.fromstring(SMALL)
        assert TreePrettyPrinter(tree, rtl=1).text() == SMALL_RTL
        assert TreePrettyPrinter(tree, rtl=0).text() == SMALL_LTR
        assert TreePrettyPrinter(tree, rtl=None).rtl is False

    def test_str_of_the_printer_is_its_text(self):
        assert str(TreePrettyPrinter(Tree.fromstring(SMALL), rtl=True)) == SMALL_RTL


class TestDirectionMarks:
    def test_mark_only_before_cells_of_right_to_left_text(self):
        tree = Tree(
            "S",
            [
                Tree("A", ["ذهب"]),
                Tree("B", ["2024"]),
                Tree("C", ["١٢٣"]),
                Tree("D", ["ال-NP"]),
                Tree("E", ["Mary"]),
                Tree("ض", ["x"]),
            ],
        )
        text = TreePrettyPrinter(tree, rtl=True).text()
        assert text.count(LRM) == 4  # the Arabic word, digits, mixed cell, label
        # the marked cell is the first token after each mark
        cells = [chunk.split("\n")[0].split()[0] for chunk in text.split(LRM)[1:]]
        assert all(_holds_rtl(cell) for cell in cells)
        # mirrored: the label row reads first, then the leaf row from the left
        assert cells == ["ض", "ال-NP", "١٢٣", "ذهب"]
        assert _bidi_is_balanced(text)
        assert LRM not in TreePrettyPrinter(tree).text()

    def test_latin_tree_gets_no_marks_even_mirrored(self):
        assert LRM not in TreePrettyPrinter(Tree.fromstring(ENGLISH), rtl=True).text()

    def test_each_wrapped_line_of_a_wide_cell_is_marked(self):
        tree = Tree("S", [Tree("N", ["حديقة" * 4])])
        text = TreePrettyPrinter(tree, rtl=True).text(maxwidth=8)
        assert text.count(LRM) == 3  # 20 letters wrap into 8 + 8 + 4
        lines = [line.strip() for line in stripped(text)[-3:]]
        assert lines == ["حديقةحدي", "قةحديقةح", "ديقة"]
        assert all(line.startswith(LRM) for line in text.split("\n")[-4:-1])

    def test_marks_are_independent_of_line_style_and_spacing(self):
        tree = Tree.fromstring(ARABIC)
        for options in (
            {"unicodelines": True},
            {"nodedist": 3},
            {"abbreviate": True},
            {"ansi": True},
            {"html": True},
        ):
            assert TreePrettyPrinter(tree, rtl=True).text(**options).count(LRM) == 6

    def test_stripping_the_marks_leaves_the_mirrored_grid(self):
        tree = Tree.fromstring(ARABIC)
        text = TreePrettyPrinter(tree, rtl=True).text()
        widths = {len(line) for line in plain(text).rstrip("\n").split("\n")}
        assert max(widths) - min(widths) <= 2  # the grid, give or take padding


class TestTreeIsNeverTouched:
    @pytest.mark.parametrize("source", [SMALL, ARABIC, PERSIAN])
    def test_tree_and_its_nodes_are_the_same_afterwards(self, source):
        tree = Tree.fromstring(source)
        before, ids = tree.copy(True), [id(n) for n in tree.subtrees()]
        printed(tree, rtl=True)
        TreePrettyPrinter(tree, rtl=True).svg()
        assert tree == before and [id(n) for n in tree.subtrees()] == ids

    def test_probabilistic_tree_keeps_its_probabilities(self):
        tree = ProbabilisticTree(
            "S",
            [
                ProbabilisticTree("NP", ["Mary"], prob=0.5),
                ProbabilisticTree("VP", ["walks"], prob=0.5),
            ],
            prob=0.25,
        )
        assert plain(printed(tree, rtl=True)) == SMALL_RTL + "\n"
        assert tree.prob() == 0.25 and [c.prob() for c in tree] == [0.5, 0.5]

    def test_parented_tree_keeps_its_parents(self):
        tree = ParentedTree.fromstring(SMALL)
        assert printed(tree, rtl=True) == SMALL_RTL + "\n"
        assert all(child.parent() is tree for child in tree)

    def test_immutable_tree_can_be_drawn(self):
        tree = ImmutableTree.fromstring(SMALL)
        assert printed(tree) == SMALL_LTR + "\n"
        assert printed(tree, rtl=True) == SMALL_RTL + "\n"

    def test_subclasses_draw_like_a_plain_tree(self):
        for cls in (ParentedTree, ImmutableTree):
            assert TreePrettyPrinter(cls.fromstring(ARABIC), rtl=True).text() == (
                TreePrettyPrinter(Tree.fromstring(ARABIC), rtl=True).text()
            )


class TestHighlight:
    def test_highlight_names_the_original_nodes_in_both_directions(self):
        tree = Tree.fromstring(SMALL)
        ltr = TreePrettyPrinter(tree, highlight=[tree[0]]).text(ansi=True)
        rtl = TreePrettyPrinter(tree, highlight=[tree[0]], rtl=True).text(ansi=True)
        assert ltr == SMALL_LTR.replace(" NP ", BLUE + " NP " + RESET)
        assert rtl == SMALL_RTL.replace(" NP ", BLUE + " NP " + RESET)

    def test_highlight_in_html_mode(self):
        tree = Tree.fromstring(SMALL)
        html = TreePrettyPrinter(tree, highlight=[tree[1]], rtl=True).text(html=True)
        assert html.count("<font color=blue>") == 1 and "VP" in html.split("</font>")[0]

    def test_highlight_a_leaf_by_its_index(self):
        tree = Tree.fromstring(ARABIC)
        text = TreePrettyPrinter(tree, highlight=[5], rtl=True).text(ansi=True)
        assert text.count(RED) == 1 and "حديقة" in text.split(RED)[1].split(RESET)[0]

    def test_highlight_a_subtree_of_a_discontinuous_tree(self):
        tree = Tree.fromstring("(S (A 0 2) (B 1))", read_leaf=int)
        text = TreePrettyPrinter(tree, ["a", "b", "c"], [tree[0]], rtl=True).text(
            ansi=True
        )
        assert text.count(BLUE) == 1 and " A " in text.split(BLUE)[1].split(RESET)[0]

    def test_highlight_of_a_parented_tree_node(self):
        tree = ParentedTree.fromstring(SMALL)
        text = TreePrettyPrinter(tree, highlight=[tree[1]], rtl=True).text(ansi=True)
        assert text.count(BLUE) == 1 and " VP " in text.split(BLUE)[1].split(RESET)[0]

    def test_highlighted_ids_are_direction_independent(self):
        tree = Tree.fromstring(ARABIC)
        nodes = [tree[0][1], tree[0][2][1][1], 0]
        assert (
            TreePrettyPrinter(tree, highlight=nodes).highlight
            == TreePrettyPrinter(tree, highlight=nodes, rtl=True).highlight
            != set()
        )

    def test_no_highlight_means_everything_is_coloured(self):
        tree = Tree.fromstring(SMALL)
        text = TreePrettyPrinter(tree, rtl=True).text(ansi=True)
        assert text.count(BLUE) == 3 and text.count(RED) == 2


class TestDiscontinuousAndSvg:
    def test_discontinuous_tree_is_mirrored(self):
        tree = Tree.fromstring("(S (A 0 2) (B 1))", read_leaf=int)
        assert TreePrettyPrinter(tree, ["a", "b", "c"], rtl=True).text() == (
            DISCONTINUOUS_RTL
        )

    def test_svg_is_mirrored_too(self):
        tree = Tree.fromstring(SMALL)
        ltr = svg_x(TreePrettyPrinter(tree).svg())
        rtl = svg_x(TreePrettyPrinter(tree, rtl=True).svg())
        assert ltr.keys() == rtl.keys() == {"S", "NP", "VP", "Mary", "walks"}
        assert ltr["NP"] < ltr["VP"] and rtl["NP"] > rtl["VP"]
        assert len({ltr[label] + rtl[label] for label in ltr}) == 1  # one mirror axis
        assert rtl["S"] == ltr["S"]


class TestPrettyPrintMethod:
    def test_pretty_print_forwards_rtl(self):
        tree = Tree.fromstring(ARABIC)
        assert (
            printed(tree, rtl=True) == TreePrettyPrinter(tree, rtl=True).text() + "\n"
        )
        assert printed(tree) == TreePrettyPrinter(tree).text() + "\n"

    def test_pretty_print_options_still_reach_text(self):
        tree = Tree.fromstring(SMALL)
        out = printed(tree, rtl=True, unicodelines=True, nodedist=2)
        assert chr(0x2500) in out and stripped(out)[-1] == "walks       Mary"

    def test_pretty_print_keeps_the_marks(self):
        assert printed(Tree.fromstring(ARABIC), rtl=True).count(LRM) == 6

    def test_deprecated_import_path_takes_rtl(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from nltk.treeprettyprinter import TreePrettyPrinter as Deprecated
        assert Deprecated(Tree.fromstring(SMALL), rtl=True).text() == SMALL_RTL


class TestMaxwidthNone:
    def test_none_disables_wrapping_as_documented(self):
        label = "plural-noun-phrase-with-a-very-long-name"
        tree = Tree.fromstring("(sentence (%s word))" % label)
        text = TreePrettyPrinter(tree).text(maxwidth=None)
        assert label in text and text.count("\n") == 5
        assert label not in TreePrettyPrinter(tree).text()  # the default wraps


class TestAbbreviate:
    def test_integer_is_the_width_as_documented(self):
        tree = Tree.fromstring("(sentence (plural-noun-phrase (plural-noun word)))")
        for width in (3, 5, 7):
            text = TreePrettyPrinter(tree, rtl=True).text(abbreviate=width)
            assert stripped(text)[0].strip() == "sentence"[:width] + "."
            assert stripped(text)[2].strip() == "plural-noun-phrase"[:width] + "."
        # only a label longer than the width is cut
        for width, cut in ((8, "plural-n."), (12, "plural-noun-.")):
            text = TreePrettyPrinter(tree).text(abbreviate=width)
            assert stripped(text)[0].strip() == "sentence" and "word" in text
            assert stripped(text)[2].strip() == cut

    def test_true_means_five_and_false_means_off(self):
        tree = Tree.fromstring("(sentence (plural-noun-phrase (plural-noun word)))")
        assert stripped(TreePrettyPrinter(tree).text(abbreviate=True))[0].strip() == (
            "sente."
        )
        for off in (False, None, 0):
            assert "sentence" in TreePrettyPrinter(tree).text(abbreviate=off)

    def test_none_with_rtl_and_an_arabic_label(self):
        tree = Tree("S", [Tree("N", ["حديقة" * 4])])
        text = TreePrettyPrinter(tree, rtl=True).text(maxwidth=None)
        assert "حديقة" * 4 in text and text.count(LRM) == 1
