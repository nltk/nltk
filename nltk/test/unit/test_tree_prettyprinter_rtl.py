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
import random
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


CORNER_L, CORNER_R, VERTICAL = chr(0x250C), chr(0x2510), chr(0x2502)


def crossing_by_geometry(drawn):
    """Brute force over a drawing's coordinates, independent of the sweep in
    ``nodecoords``: the ids of the children whose vertical line up to their
    parent passes a row strictly between them in which the horizontal branch
    of another node spans the child's column."""
    children = {}
    for child, parent in drawn.edges.items():
        children.setdefault(parent, []).append(child)
    branches = []
    for parent, kids in children.items():
        if len(kids) > 1:
            cols = [drawn.coords[k][1] for k in kids]
            branches.append((drawn.coords[parent][0], min(cols), max(cols)))
    found = set()
    for child, parent in drawn.edges.items():
        (crow, col), prow = drawn.coords[child], drawn.coords[parent][0]
        if any(prow < brow < crow and lo < col < hi for brow, lo, hi in branches):
            found.add(child)
    return found


def drawn_crossings(text):
    """How many vertical lines a unicode drawing draws through a branch: a
    box vertical strictly inside an open corner pair of its row."""
    count = 0
    for line in text.split("\n"):
        depth = 0
        for ch in line:
            if ch == CORNER_L:
                depth += 1
            elif ch == CORNER_R:
                depth -= 1
            elif ch == VERTICAL and depth > 0:
                count += 1
    return count


def random_discontinuous(rng, n):
    """A random tree over ``n`` leaves whose leaves are a random permutation
    of ``0..n-1``, so most of its preterminals straddle one another."""

    def shape(k, depth):
        if k == 1 or (depth > 1 and rng.random() < 0.3):
            return Tree("N", [None] * k)
        cuts = sorted(rng.sample(range(1, k), min(k - 1, rng.randint(1, 3))))
        parts = [b - a for a, b in zip([0] + cuts, cuts + [k])]
        return Tree("S", [shape(p, depth + 1) for p in parts])

    leaves = iter(rng.sample(range(n), n))

    def fill(node):
        return Tree(
            node.label(),
            [fill(c) if isinstance(c, Tree) else next(leaves) for c in node],
        )

    return fill(shape(n, 0)), [str(i) for i in range(n)]


def svg_verticals(svg):
    """``[(x, y_from, y_to)]`` of the child-to-parent lines of an SVG drawing,
    in document order: the black vertical polylines longer than the four
    pixel stub every branching node draws under its own label."""
    found = []
    for line in svg.split("\n"):
        if "stroke:black" in line and "points=" in line:
            points = line.split('points="', 1)[1].split('"', 1)[0].split()
            (x1, y1), (x2, y2) = (map(float, p.split(",")) for p in points)
            if x1 == x2 and abs(y1 - y2) > 4:
                found.append((x1, y1, y2))
    return found


def svg_vertical_of(drawn, child):
    """The line ``svg()`` draws from ``child`` up to its parent."""
    (crow, col), prow = drawn.coords[child], drawn.coords[drawn.edges[child]][0]
    return (col * 40 + 20, crow * 25 + 20 - 12, prow * 25 + 20 + 6)


DISCO = "(S (A 0 2) (B 1))"
SAMETIER = "(S (X (A 1) (B 2)) (P 0 3))"
RIGHTMOST = "(S (A 0) (B 1 3) (C 2))"
DUTCH = (
    "(top (punct 8) (smain (noun 0) (verb 1) (inf (verb 5) (inf (verb 6) "
    "(conj (inf (pp (prep 2) (np (det 3) (noun 4))) (verb 7)) (inf (verb 9)) "
    "(vg 10) (inf (verb 11)))))) (punct 12))"
)
DUTCH_SENTENCE = (
    "Ze had met haar moeder kunnen gaan winkelen , zwemmen of terrassen .".split()
)
DISCO_UNICODE = (
    "     S         \n"
    "     ┌───┐      \n"
    "     │   A     \n"
    " ┌── │ ──┴───┐  \n"
    " │   B       │ \n"
    " │   │       │  \n"
    " a   b       c \n"
)
SAMETIER_UNICODE = (
    "         S         \n"
    "         ┌───┐      \n"
    "         │   X     \n"
    "     ┌── │ ──┐      \n"
    "     │   P   │     \n"
    " ┌── │ ──┴── │ ──┐  \n"
    " │   A       B   │ \n"
    " │   │       │   │  \n"
    " a   b       c   d \n"
)
# a layout in which S1 (id 9) was placed on the line from S2 (id 2) up to
# the other S1 (id 1), so one column carries two vertical lines at once
TWO_LINES_ONE_COLUMN = (
    "(S0 (S1 (S2 (N2 0) (N4 6))) (S1 (N1 7) (N2 5) (N2 2)) (N1 1) "
    "(S1 (N4 3) (S2 (S3 (N0 8 4)))))"
)


class TestCrossingEdges:
    """``nodecoords`` orders ``edges`` bottom up with the crossing edges last.
    An edge crosses when the vertical line from the child up to its parent
    is drawn through the horizontal branch of a third node: a row strictly
    between the two whose branch spans the child's column. Pinned here
    against a brute-force reading of the coordinates and against the
    drawing itself, in both directions."""

    @pytest.mark.parametrize("source", [SMALL, ENGLISH, ARABIC, HEBREW, PERSIAN])
    @pytest.mark.parametrize("rtl", [False, True])
    def test_a_continuous_tree_has_no_crossing_edge(self, source, rtl):
        drawn = TreePrettyPrinter(Tree.fromstring(source), rtl=rtl)
        assert crossing_by_geometry(drawn) == set()
        assert drawn_crossings(plain(drawn.text(unicodelines=True))) == 0

    def test_continuous_edges_keep_the_bottom_up_order(self):
        # ids follow the tree positions: S 0, NP 1, Mary 2, VP 3, walks 4
        ltr, rtl = TreePrettyPrinter(Tree.fromstring(SMALL)), TreePrettyPrinter(
            Tree.fromstring(SMALL), rtl=True
        )
        assert list(ltr.edges.items()) == [(4, 3), (2, 1), (1, 0), (3, 0)]
        assert list(rtl.edges.items()) == list(ltr.edges.items())

    def test_the_crossing_edge_of_a_discontinuous_tree_comes_last(self):
        # ids: S 0, A 1, a 2, c 3, B 4, b 5: B's line up to S crosses A's branch
        drawn = TreePrettyPrinter(Tree.fromstring(DISCO, read_leaf=int), list("abc"))
        assert crossing_by_geometry(drawn) == {4}
        assert list(drawn.edges.items()) == [(2, 1), (3, 1), (5, 4), (1, 0), (4, 0)]
        assert drawn.text(unicodelines=True) == DISCO_UNICODE
        assert drawn_crossings(DISCO_UNICODE) == 1
        assert (
            TreePrettyPrinter(
                Tree.fromstring(DISCO, read_leaf=int), list("abc"), rtl=True
            ).text()
            == DISCONTINUOUS_RTL
        )

    def test_crossing_edges_are_moved_not_merely_found(self):
        # P sits between X and X's children: the lines of A, B and P cross,
        # and X's own edge (id 4) now precedes them, which bottom up it did not
        tree = Tree.fromstring(SAMETIER, read_leaf=int)
        drawn = TreePrettyPrinter(tree, list("abcd"))
        assert crossing_by_geometry(drawn) == {1, 5, 7}
        assert list(drawn.edges.items()) == [
            (2, 1),
            (3, 1),
            (8, 7),
            (6, 5),
            (4, 0),
            (5, 4),
            (7, 4),
            (1, 0),
        ]
        assert [drawn.nodes[c].label() for c in list(drawn.edges)[-3:]] == [
            "A",
            "B",
            "P",
        ]
        assert drawn.text(unicodelines=True) == SAMETIER_UNICODE
        assert drawn_crossings(SAMETIER_UNICODE) == 3

    def test_a_child_that_is_not_the_leftmost_crosses_too(self):
        tree = Tree.fromstring(RIGHTMOST, read_leaf=int)
        drawn = TreePrettyPrinter(tree, list("abcd"))
        assert crossing_by_geometry(drawn) == {6}
        assert list(drawn.edges)[-1] == 6 and drawn.nodes[6].label() == "C"
        assert drawn.edges[6] == 0 and drawn.nodes[0].label() == "S"
        assert drawn_crossings(drawn.text(unicodelines=True)) == 1

    def test_the_dutch_tree_of_the_doctest(self):
        drawn = TreePrettyPrinter(Tree.fromstring(DUTCH, read_leaf=int), DUTCH_SENTENCE)
        crossing = crossing_by_geometry(drawn)
        tail = list(drawn.edges)[-3:]
        assert crossing == set(tail) and len(crossing) == 3
        assert [
            (drawn.nodes[c].label(), drawn.nodes[drawn.edges[c]].label()) for c in tail
        ] == [("verb", "inf"), ("verb", "inf"), ("punct", "top")]
        assert [DUTCH_SENTENCE[drawn.nodes[c][0]] for c in tail] == [
            "gaan",
            "kunnen",
            ",",
        ]
        # the verbs cross the branches of conj and inf, the comma that of conj
        assert drawn_crossings(drawn.text(unicodelines=True)) == 5

    @pytest.mark.parametrize(
        "source, sentence",
        [
            (DISCO, list("abc")),
            (SAMETIER, list("abcd")),
            (RIGHTMOST, list("abcd")),
            (DUTCH, DUTCH_SENTENCE),
            (TWO_LINES_ONE_COLUMN, [str(i) for i in range(9)]),
        ],
    )
    def test_same_edges_and_crossings_in_both_directions(self, source, sentence):
        tree = Tree.fromstring(source, read_leaf=int)
        ltr = TreePrettyPrinter(tree, sentence)
        rtl = TreePrettyPrinter(tree, sentence, rtl=True)
        assert list(ltr.edges.items()) == list(rtl.edges.items())
        assert crossing_by_geometry(ltr) == crossing_by_geometry(rtl) != set()
        assert drawn_crossings(ltr.text(unicodelines=True)) == drawn_crossings(
            plain(rtl.text(unicodelines=True))
        )

    def test_two_lines_in_one_column_are_both_found(self):
        tree = Tree.fromstring(TWO_LINES_ONE_COLUMN, read_leaf=int)
        drawn = TreePrettyPrinter(tree, [str(i) for i in range(9)])
        assert drawn.coords[1][1] == drawn.coords[9][1] == drawn.coords[2][1]
        crossing = crossing_by_geometry(drawn)
        assert crossing == {1, 2, 5, 7, 9, 10, 12, 14, 17, 20}
        assert set(list(drawn.edges)[-10:]) == crossing

    def test_svg_draws_the_crossing_lines_last(self):
        tree = Tree.fromstring(SAMETIER, read_leaf=int)
        for rtl in (False, True):
            drawn = TreePrettyPrinter(tree, list("abcd"), rtl=rtl)
            verticals = svg_verticals(drawn.svg())
            assert verticals == [svg_vertical_of(drawn, child) for child in drawn.edges]
            assert verticals[-3:] == [svg_vertical_of(drawn, c) for c in (5, 7, 1)]

    def test_highlight_and_the_sentence_channel_leave_the_order_alone(self):
        tree = Tree.fromstring(SAMETIER, read_leaf=int)
        plain_order = list(TreePrettyPrinter(tree, list("abcd")).edges.items())
        # the drawing sorts S's children by first leaf: P (tree[1]) gets id 1
        lit = TreePrettyPrinter(tree, list("abcd"), highlight=[tree[1], 0], rtl=True)
        assert list(lit.edges.items()) == plain_order and lit.highlight == {1, 2}
        assert lit.text(ansi=True).count(BLUE) == 1
        words = TreePrettyPrinter(tree, ["ذهب", "ال", "طفل", "إلى"], rtl=True)
        assert list(words.edges.items()) == plain_order
        assert words.text().count(LRM) == 4

    def test_an_empty_label_on_a_crossing_node(self):
        tree = Tree("S", [Tree("A", [0, 2]), Tree("", [1])])
        drawn = TreePrettyPrinter(tree, list("abc"))
        assert crossing_by_geometry(drawn) == {4} and list(drawn.edges)[-1] == 4
        assert drawn_crossings(drawn.text(unicodelines=True)) == 1

    def test_random_discontinuous_trees_agree_with_the_geometry(self):
        rng = random.Random(2886)
        with_crossings = 0
        for _ in range(300):
            tree, sentence = random_discontinuous(rng, rng.randint(2, 8))
            for rtl in (False, True):
                drawn = TreePrettyPrinter(tree, sentence, rtl=rtl)
                assert set(drawn.nodes) == set(drawn.coords), tree
                crossing = crossing_by_geometry(drawn)
                order = list(drawn.edges)
                assert set(order[len(order) - len(crossing) :]) == crossing, tree
                text = plain(drawn.text(unicodelines=True))
                assert (drawn_crossings(text) > 0) == bool(crossing), tree
                with_crossings += bool(crossing)
        assert with_crossings > 200
