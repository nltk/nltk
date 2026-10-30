# Natural Language Toolkit: Toolbox settings helpers
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Behaviour and depth bound of the Toolbox settings helpers.

The GHSA-f2h2-f4fc-p978 bound (MAX_TOOLBOX_DEPTH) moved two blocks out of
place: ``add_blank_lines`` raised UnboundLocalError on an ordinary tree, and
``to_settings_string`` closed every leaf, so its output no longer parsed.
These tests pin the restored behaviour on small trees and on the real MDF
settings file, and pin the bound on every recursive helper: a tree deeper
than the bound is refused with ValueError, never RecursionError, a tree at
the bound is walked in full, and without the bound the same deep tree really
overflows the stack (the teeth). Nothing is mocked.
"""

import sys
from xml.etree.ElementTree import Element, ElementTree, SubElement, tostring

import pytest

import nltk.toolbox
from nltk.toolbox import (
    MAX_TOOLBOX_DEPTH,
    ToolboxSettings,
    _sort_fields,
    _to_settings_string,
    add_blank_lines,
    add_default_fields,
    remove_blanks,
    sort_fields,
    to_settings_string,
)

DEEP = 5000


def _small_lexicon():
    root = Element("toolbox_data")
    SubElement(root, "header")
    for word in ("kaa", "kae"):
        rec = SubElement(root, "record")
        SubElement(rec, "lx").text = word
        SubElement(rec, "ps").text = "V"
    return root


def _settings(text):
    ts = ToolboxSettings()
    ts.open_string(text)
    try:
        return ts.parse(unwrap=False)
    finally:
        ts.close()


def _chain(n):
    """A chain of ``n`` nested elements, built iteratively, leaf text "x"."""
    root = cur = Element("grp")
    for _ in range(n - 1):
        cur = SubElement(cur, "grp")
    cur.text = "x"
    return root


def _levels(tree):
    """Number of levels in ``tree``, counted without recursion."""
    deepest, frontier = 0, [tree]
    while frontier:
        deepest += 1
        frontier = [child for node in frontier for child in node]
    return deepest


def _real_mdf_settings_text():
    try:
        pointer = nltk.data.find("corpora/toolbox/MDF/MDF_AltH.typ")
    except LookupError:
        pytest.skip("the toolbox corpus is not installed")
    with pointer.open("cp1252") as stream:
        return stream.read()


# add_blank_lines on ordinary small trees (the UnboundLocalError regression).


def test_add_blank_lines_leaves_a_tree_with_unlisted_tags_unchanged():
    tree = _small_lexicon()
    before = tostring(tree)
    add_blank_lines(tree, {}, {})
    assert tostring(tree) == before


def test_add_blank_lines_inserts_before_and_between():
    tree = _small_lexicon()
    rules = {"toolbox_data": ("record",)}
    add_blank_lines(tree, rules, rules)
    header, first, second = tree
    # before: header -> record changes tag; between: record -> record.
    assert header.text == "\n"
    assert [field.text for field in first] == ["kaa", "V\n"]
    assert [field.text for field in second] == ["kae", "V"]


def test_add_blank_lines_reaches_listed_tags_below_an_unlisted_root():
    root = Element("db")
    tree = _small_lexicon()
    root.append(tree)
    add_blank_lines(root, {"toolbox_data": ("record",)}, {"toolbox_data": ()})
    assert tree[0].text == "\n"
    assert [rec[-1].text for rec in tree[1:]] == ["V", "V"]


def test_add_blank_lines_appends_to_the_last_element_of_the_previous_subtree():
    tree = _settings(
        "\\+set\n\\+mkr a\n\\+sub\n\\leaf x\n\\-sub\n\\-mkr\n\\mkr b\n\\-set\n"
    )
    add_blank_lines(tree, {"set": ()}, {"set": ("mkr",)})
    assert tree.find("mkr/sub/leaf").text == "x\n"
    assert tree[0].text == "a"


def test_add_blank_lines_first_child_in_blanks_between_is_skipped():
    tree = _settings("\\+set\n\\mkr a\n\\mkr b\n\\mkr c\n\\-set\n")
    add_blank_lines(tree, {"set": ()}, {"set": ("mkr",)})
    assert [field.text for field in tree] == ["a\n", "b\n", "c"]


# to_settings_string writes what ToolboxSettings.parse reads back.


def test_to_settings_string_closes_only_blocks():
    tree = _settings("\\+set top\n\\nam one\n\\+mkr a\n\\lng v\n\\-mkr\n\\-set\n")
    out = to_settings_string(ElementTree(tree))
    assert out == ("\\+set top\n\\nam one\n\\+mkr a\n\\lng v\n\\-mkr\n\\-set\n")
    assert tostring(_settings(out)) == tostring(tree)


def test_real_mdf_settings_round_trip_and_blank_lines():
    text = _real_mdf_settings_text()
    tree = _settings(text)
    assert len(list(tree.iter())) > 500
    plain = to_settings_string(ElementTree(tree))
    assert tostring(_settings(plain)) == tostring(tree)

    mkrs = tree.findall("mkrset/mkr")
    assert len(mkrs) > 100
    rules = {"mkrset": ("mkr",)}
    add_blank_lines(tree, rules, rules)
    spaced = to_settings_string(ElementTree(tree))
    # One blank line before the first mkr (after mkrRecord), one between each pair.
    assert spaced.count("\n\n") == len(mkrs)
    reread = _settings(spaced)
    assert [e.tag for e in reread.iter()] == [e.tag for e in tree.iter()]
    assert [(e.text or "").strip() for e in reread.iter()] == [
        (e.text or "").strip() for e in tree.iter()
    ]


# The depth bound on every recursive helper.


HELPERS = {
    "to_settings_string": lambda t: to_settings_string(ElementTree(t)),
    "remove_blanks": remove_blanks,
    "add_default_fields": lambda t: add_default_fields(t, {"grp": ("extra",)}),
    "sort_fields": lambda t: sort_fields(t, {"grp": ("grp",)}),
    "add_blank_lines.unlisted": lambda t: add_blank_lines(t, {}, {}),
    "add_blank_lines.listed": lambda t: add_blank_lines(
        t, {"grp": ("grp",)}, {"grp": ("grp",)}
    ),
}

#: The same walks with the bound lifted, for the teeth.
UNBOUNDED = {
    "to_settings_string": lambda t: _to_settings_string(t, [], max_depth=sys.maxsize),
    "remove_blanks": lambda t: remove_blanks(t, max_depth=sys.maxsize),
    "add_default_fields": lambda t: add_default_fields(
        t, {"grp": ("extra",)}, max_depth=sys.maxsize
    ),
    "sort_fields": lambda t: _sort_fields(
        t, {"grp": {"grp": 0}}, max_depth=sys.maxsize
    ),
    "add_blank_lines.unlisted": lambda t: add_blank_lines(
        t, {}, {}, max_depth=sys.maxsize
    ),
    "add_blank_lines.listed": lambda t: add_blank_lines(
        t, {"grp": ("grp",)}, {"grp": ("grp",)}, max_depth=sys.maxsize
    ),
}


@pytest.mark.parametrize("name", sorted(HELPERS))
@pytest.mark.parametrize("depth", [MAX_TOOLBOX_DEPTH + 3, DEEP])
def test_deeper_than_the_bound_is_refused(name, depth):
    with pytest.raises(ValueError, match="MAX_TOOLBOX_DEPTH") as caught:
        HELPERS[name](_chain(depth))
    assert not isinstance(caught.value, RecursionError)


@pytest.mark.parametrize("name", sorted(HELPERS))
def test_bound_holds_with_a_raised_recursion_limit(name):
    saved = sys.getrecursionlimit()
    sys.setrecursionlimit(DEEP * 4)
    try:
        with pytest.raises(ValueError, match="MAX_TOOLBOX_DEPTH"):
            HELPERS[name](_chain(DEEP))
    finally:
        sys.setrecursionlimit(saved)


@pytest.mark.parametrize("name", sorted(HELPERS))
def test_a_tree_at_the_bound_is_walked_in_full(name):
    # add_default_fields gives the leaf a child, so it starts one level up.
    grows = 1 if name == "add_default_fields" else 0
    tree = _chain(MAX_TOOLBOX_DEPTH + 1 - grows)
    HELPERS[name](tree)
    assert _levels(tree) == MAX_TOOLBOX_DEPTH + 1


def test_a_tree_at_the_bound_is_written_in_full():
    out = to_settings_string(ElementTree(_chain(MAX_TOOLBOX_DEPTH + 1)))
    assert out.count("\\+grp\n") == MAX_TOOLBOX_DEPTH
    assert out.count("\\-grp\n") == MAX_TOOLBOX_DEPTH
    assert "\\grp x\n" in out


def test_raising_the_module_bound_allows_a_deeper_tree(monkeypatch):
    depth = MAX_TOOLBOX_DEPTH + 100
    with pytest.raises(ValueError):
        remove_blanks(_chain(depth))
    monkeypatch.setattr(nltk.toolbox, "MAX_TOOLBOX_DEPTH", depth)
    tree = _chain(depth)
    remove_blanks(tree)
    add_blank_lines(tree, {}, {})
    assert len(list(tree.iter())) == depth


@pytest.mark.parametrize("name", sorted(UNBOUNDED))
def test_teeth_the_deep_tree_overflows_without_the_bound(name):
    assert sys.getrecursionlimit() < DEEP
    with pytest.raises(RecursionError):
        UNBOUNDED[name](_chain(DEEP))
