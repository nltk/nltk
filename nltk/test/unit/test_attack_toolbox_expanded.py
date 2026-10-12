# Natural Language Toolkit: the Toolbox threat model, case by case
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""Every case of the re-audit of ``nltk.toolbox`` after PR 3958, hostile and
benign, driven through the real readers, writers and helpers.

1. Depth: ``ToolboxSettings.parse`` and the six helper walks at, under, just
   over and ten times ``MAX_TOOLBOX_DEPTH``; the stack the walks leave a
   caller; flat data files; the chunk parser.
2. Width and length: the ``add_blank_lines`` walk over a tree both deep and
   wide (the subtree listing PR 3958 put in made it depth times width), wide
   trees in every helper, long markers, values and continuation runs.
3. Markers and structure: regex metacharacters, unterminated, stray and
   mismatched blocks, NUL and every control character, bidi and zero width
   characters, duplicate backslashes, HTML names, a self referencing file,
   and a sanitised marker that must be a visible XML name.
4. Line breaks and BOMs through the four entry routes (a string, a filename,
   a PathPointer, the corpus reader), on planted and on real corpus files.
5. Writers: values and markers that would read back as other fields, round
   trips of hostile and real data, empty fields, encodings, and no XML
   parser, attribute or tail anywhere.
6. Paths: every entry route against outside, linked, special, shared and
   oddly spelled files, with every open checked to run inside pathsec.

Each hostile case has teeth: the behaviour before the fix is put back in
process, or the input is shown to be live, and the same assertion fails.
Control characters are built with chr().
"""

import builtins
import codecs
import importlib
import io
import os
import pathlib
import sys
import traceback
from xml.etree.ElementTree import (
    Element,
    ElementTree,
    ParseError,
    SubElement,
    tostring,
)

import pytest

import nltk.data
from nltk import redos
from nltk.corpus.reader.toolbox import ToolboxCorpusReader
from nltk.data import FileSystemPathPointer
from nltk.test.unit import timing

#: The module itself: ``import nltk.toolbox as tb`` binds the LazyModule that
#: nltk/__init__ puts in its place, on which monkeypatch restores a stale copy.
tb = importlib.import_module("nltk.toolbox")

BOUND = tb.MAX_TOOLBOX_DEPTH
POSIX = os.name == "posix"
posix_only = pytest.mark.skipif(not POSIX, reason="POSIX file semantics")


def settings(text, **kwargs):
    ts = tb.ToolboxSettings()
    ts.open_string(text)
    kwargs.setdefault("unwrap", False)
    try:
        return ts.parse(**kwargs)
    finally:
        ts.close()


def data(text, key="lx", **kwargs):
    td = tb.ToolboxData()
    td.open_string(text)
    try:
        return td.parse(key=key, **kwargs)
    finally:
        td.close()


def nested(n, leaf=True):
    """A settings file ``n`` blocks deep, with a leaf in the innermost."""
    parts = ["\\+m%d x\n" % i for i in range(n)]
    if leaf:
        parts.append("\\leaf v\n")
    parts += ["\\-m%d\n" % i for i in reversed(range(n))]
    return "".join(parts)


def chain(n, tag="grp", cls=Element):
    root = node = cls(tag)
    for _ in range(n - 1):
        child = cls(tag)
        node.append(child)
        node = child
    node.text = "x"
    return root


def levels(tree):
    deepest, frontier = 0, [tree]
    while frontier:
        deepest += 1
        frontier = [child for node in frontier for child in node]
    return deepest


def plant(directory, name, text, encoding="utf-8", mode=0o600):
    """Write ``text`` byte for byte (no newline translation) and return the path."""
    path = os.path.join(str(directory), name)
    with open(path, "wb") as handle:
        handle.write(text.encode(encoding))
    os.chmod(path, mode)
    return path


HELPERS = {
    "to_settings_string": lambda t: tb.to_settings_string(ElementTree(t)),
    "remove_blanks": tb.remove_blanks,
    "add_default_fields": lambda t: tb.add_default_fields(t, {"grp": ("extra",)}),
    "sort_fields": lambda t: tb.sort_fields(t, {"grp": ("grp",)}),
    "add_blank_lines": lambda t: tb.add_blank_lines(t, {}, {}),
    "add_blank_lines.listed": lambda t: tb.add_blank_lines(
        t, {"grp": ("grp",)}, {"grp": ("grp",)}
    ),
}

#: The same walks with rules naming the tags a parsed nested() tree has.
PARSED_HELPERS = {
    "to_settings_string": lambda t: tb.to_settings_string(ElementTree(t)),
    "remove_blanks": tb.remove_blanks,
    "add_default_fields": lambda t: tb.add_default_fields(
        t, {"m%d" % (BOUND - 1): ("e",)}
    ),
    "sort_fields": lambda t: tb.sort_fields(t, {"m0": ("m1",)}),
    "add_blank_lines": lambda t: tb.add_blank_lines(t, {}, {}),
    "add_blank_lines.listed": lambda t: tb.add_blank_lines(
        t, {"m0": ("m1",)}, {"m0": ("m1",)}
    ),
}


# 1. Depth.


@pytest.mark.parametrize(
    "n, refused",
    [(BOUND - 1, False), (BOUND, False), (BOUND + 1, True), (10 * BOUND, True)],
)
def test_parse_depth_under_at_over_and_ten_times_the_bound(n, refused):
    if refused:
        with pytest.raises(ValueError, match="MAX_TOOLBOX_DEPTH"):
            settings(nested(n))
    else:
        assert levels(settings(nested(n))) == n + 1


#: The longest chain each walk takes. A walk that never enters a leaf reaches
#: one level less (sort_fields, add_blank_lines); add_default_fields gives the
#: leaf a child, which it then enters, so it reaches one level more.
LONGEST = {
    "to_settings_string": BOUND + 1,
    "remove_blanks": BOUND + 1,
    "add_default_fields": BOUND,
    "sort_fields": BOUND + 2,
    "add_blank_lines": BOUND + 2,
    "add_blank_lines.listed": BOUND + 2,
}


@pytest.mark.parametrize("name", sorted(HELPERS))
def test_each_walk_takes_its_longest_chain_and_refuses_one_more(name):
    HELPERS[name](chain(LONGEST[name]))
    for n in (LONGEST[name] + 1, 10 * BOUND):
        with pytest.raises(ValueError, match="MAX_TOOLBOX_DEPTH"):
            HELPERS[name](chain(n))


@pytest.mark.parametrize("name", sorted(PARSED_HELPERS))
def test_each_walk_takes_the_deepest_tree_parse_accepts(name):
    tree = settings(nested(BOUND))
    PARSED_HELPERS[name](tree)
    assert levels(tree) >= BOUND + 1


def _from_a_deep_caller(frames, walk, tree):
    def dive(i):
        if i:
            return dive(i - 1)
        return walk(tree)

    return dive(frames)


@pytest.mark.parametrize("name", sorted(PARSED_HELPERS))
def test_the_walks_leave_a_caller_stack_headroom(name):
    """At the default recursion limit a caller 300 frames deep can still walk
    the deepest tree parse accepts: the bound keeps a walk near 500 frames."""
    assert sys.getrecursionlimit() >= 1000
    _from_a_deep_caller(300, PARSED_HELPERS[name], settings(nested(BOUND)))


def test_headroom_teeth(monkeypatch):
    """With the bound raised to 900 the same call overflows: the headroom
    test above measures the depth of the walk, not something else."""
    monkeypatch.setattr(tb, "MAX_TOOLBOX_DEPTH", 900)
    tree = settings(nested(900))
    with pytest.raises(RecursionError):
        _from_a_deep_caller(300, tb.remove_blanks, tree)


def test_a_data_file_stays_flat_whatever_its_markers():
    tree = data("\\lx a\n" + "\\+x v\n" * 5000 + "\\-x\n" * 5000)
    assert levels(tree) == 3
    assert len(tree[1]) == 10001


def test_to_sfm_string_reads_records_and_fields_only():
    root = Element("toolbox_data")
    field = SubElement(SubElement(root, "record"), "lx")
    field.text = "a"
    field.append(chain(10 * BOUND))
    assert tb.to_sfm_string(root) == "\\lx a\n"


def test_the_chunk_parser_nests_as_deep_as_its_grammar_only():
    td = tb.ToolboxData()
    td.open_string("\\_sh v3\n" + "\\lx a\n\\sn 1\n\\ps n\n\\ge g\n" * 50)
    tree = td.parse(grammar="sense: {<sn><ps><ge>*}\nrecord: {<lx><sense>+}", key="lx")
    assert levels(tree) == 5  # toolbox_data, record, record chunk, sense, field
    assert len(tree.findall("record")) == 50


# 2. Width and length.


class CountingElement(Element):
    """An Element counting every child read a walk makes (iteration, index,
    len and iter all pass through it): a cost measure no clock can skew."""

    reads = 0

    def __getitem__(self, index):
        CountingElement.reads += 1
        return super().__getitem__(index)

    def __len__(self):
        CountingElement.reads += 1
        return super().__len__()

    def iter(self, tag=None):
        for element in super().iter(tag):
            CountingElement.reads += 1
            yield element


def deep_wide(depth, width, cls=Element):
    """A chain ``depth`` deep, each level followed by a sibling, with
    ``width`` leaves at the bottom: every level's previous sibling holds the
    whole bottom, which is what a subtree listing pays for at every level."""
    root = node = cls("grp")
    for _ in range(depth - 1):
        deeper, sibling = cls("grp"), cls("grp")
        sibling.text = "s"
        node.append(deeper)
        node.append(sibling)
        node = deeper
    for _ in range(width):
        leaf = cls("grp")
        leaf.text = "v"
        node.append(leaf)
    return root


def _listed_reads(depth, width):
    tree = deep_wide(depth, width, CountingElement)
    CountingElement.reads = 0
    tb.add_blank_lines(tree, {"grp": ("grp",)}, {"grp": ("grp",)})
    return CountingElement.reads


def test_add_blank_lines_reads_each_element_a_bounded_number_of_times():
    small, big = _listed_reads(100, 2000), _listed_reads(400, 8000)
    assert big / small < 8, (small, big)


def test_add_blank_lines_reads_teeth(monkeypatch):
    """PR 3958's subtree listing, put back: four times the depth and the width
    costs about sixteen times the reads."""
    monkeypatch.setattr(tb, "_last_descendant", lambda e: list(e.iter())[-1])
    small, big = _listed_reads(100, 2000), _listed_reads(400, 8000)
    assert big / small >= 8, (small, big)


def test_add_blank_lines_on_a_deep_wide_tree_is_subquadratic():
    trees = {1: deep_wide(120, 30_000), 4: deep_wide(480, 120_000)}
    rules = {"grp": ("grp",)}
    timing.assert_subquadratic(
        lambda k: tb.add_blank_lines(trees[k], rules, rules), 1, 4, cpu_bound=True
    )


def test_add_blank_lines_appends_to_the_same_element_as_before():
    """The last element in document order, as the subtree listing found it."""
    tree = settings(
        "\\+set\n\\+mkr a\n\\+sub\n\\leaf x\n\\+deep\n\\last y\n\\-deep\n\\-sub\n"
        "\\-mkr\n\\mkr b\n\\-set\n"
    )
    expected = list(tree[0].iter())[-1]
    tb.add_blank_lines(tree, {"set": ()}, {"set": ("mkr",)})
    assert expected.tag == "last" and expected.text == "y\n"
    assert tree.find("mkr/sub/leaf").text == "x"


@pytest.mark.parametrize("name", sorted(HELPERS))
def test_every_walk_is_linear_on_a_wide_flat_tree(name):
    flat = {}
    for k, n in ((1, 50_000), (4, 200_000)):
        root = flat[k] = Element("grp")
        for _ in range(n):
            SubElement(root, "grp").text = "v"
    timing.assert_subquadratic(lambda k: HELPERS[name](flat[k]), 1, 4, cpu_bound=True)


def test_parsing_many_lines_is_linear():
    texts = {k: "\\+grp\n" + "\\grp v\n" * (5000 * k) + "\\-grp\n" for k in (1, 4)}
    timing.assert_subquadratic(lambda k: settings(texts[k]), 1, 4, cpu_bound=True)
    records = {k: "\\lx a\n" + "\\ge g\n" * (5000 * k) for k in (1, 4)}
    timing.assert_subquadratic(lambda k: data(records[k]), 1, 4, cpu_bound=True)
    runs = {k: "\\lx a\n" + "c\n" * (5000 * k) for k in (1, 4)}
    timing.assert_subquadratic(lambda k: data(runs[k]), 1, 4, cpu_bound=True)


@pytest.mark.parametrize("size", [100_000, 1_000_000])
def test_a_long_marker_is_kept_whole(size):
    marker = "m" * size
    assert data("\\%s value\n" % marker, key=marker)[1][0].tag == marker
    assert settings(f"\\+{marker} v\n\\-{marker}\n").tag == marker


def test_a_long_value_and_a_long_continuation_run_are_kept_whole():
    assert len(data("\\lx " + "v" * 1_000_000 + "\n")[1][0].text) == 1_000_000
    assert data("\\lx a\n" + "c\n" * 20_000)[1][0].text == "a" + " c" * 20_000


SENSES = "sense: {<sn><ps><ge>*}"


def _record_text(fields):
    """One ``lx`` record of exactly ``fields`` fields: lx, then sn/ps/ge runs."""
    groups, extra = divmod(fields - 1, 3)
    return "\\lx a\n" + "\\sn 1\n\\ps n\n\\ge g\n" * groups + "\\ge g\n" * extra


def _chunk(text):
    td = tb.ToolboxData()
    td.open_string(text)
    return td.parse(grammar=SENSES, key="lx")


def _spy_xform(monkeypatch):
    """Every pattern a chunk rule applies, as ChunkString.xform receives it."""
    from nltk.chunk.regexp import ChunkString

    seen, real = [], ChunkString.xform

    def xform(self, regexp, repl):
        seen.append(regexp)
        return real(self, regexp, repl)

    monkeypatch.setattr(ChunkString, "xform", xform)
    return seen


def test_a_record_wider_than_the_chunk_bound_is_refused_before_matching(monkeypatch):
    """The chunk rules rescan the rest of a record for every match (the
    slowest call took 0.05, 0.17, 0.70 and 2.8 CPU seconds as a record doubled
    from 7,500 fields), so a record past the bound never reaches them."""
    seen = _spy_xform(monkeypatch)
    wide = _record_text(tb.MAX_CHUNK_RECORD_FIELDS + 1)
    with pytest.raises(ValueError, match="MAX_CHUNK_RECORD_FIELDS"):
        _chunk(_record_text(5) + wide)
    assert seen == []


def test_a_record_at_the_chunk_bound_is_chunked(monkeypatch):
    seen = _spy_xform(monkeypatch)
    record = _chunk(_record_text(tb.MAX_CHUNK_RECORD_FIELDS))[1]
    assert record[0].tag == "lx"
    assert [e.tag for e in record[1:]] == ["sense"] * (
        (tb.MAX_CHUNK_RECORD_FIELDS - 1) // 3
    )
    assert seen


def test_chunk_bound_teeth(monkeypatch):
    """With the bound raised the same record reaches the chunk rules."""
    seen = _spy_xform(monkeypatch)
    fields = tb.MAX_CHUNK_RECORD_FIELDS + 1
    monkeypatch.setattr(tb, "MAX_CHUNK_RECORD_FIELDS", fields)
    # lx, then one sense per sn/ps/ge run; the odd trailing ge joins the last
    assert len(_chunk(_record_text(fields))[1]) == 1 + (fields - 1) // 3
    assert seen


def test_the_chunk_rules_run_through_redos_with_a_time_limit(monkeypatch):
    """Defence in depth under the bound: every pattern a rule applies is a
    redos TimedPattern carrying the module's finite time limit."""
    seen = _spy_xform(monkeypatch)
    _chunk(_record_text(31))
    assert seen and all(isinstance(r, redos.TimedPattern) for r in seen)
    limits = {r._resolve(redos._UNSET) for r in seen}
    assert limits == {redos.DEFAULT_TIMEOUT} and 0 < redos.DEFAULT_TIMEOUT < 60


def test_chunking_bounded_records_is_linear_in_their_number():
    texts = {k: _record_text(31) * (100 * k) for k in (1, 4)}
    timing.assert_subquadratic(lambda k: _chunk(texts[k]), 1, 4, cpu_bound=True)


# 3. Markers and structure.

META = "a.*+?()[]{}|^$\\<>"


def test_regex_metacharacter_markers_are_inert():
    record = data("\\lx a\n\\%s v\n\\ge g\n" % META)[1]
    assert [e.tag for e in record] == ["lx", "a._______________", "ge"]
    assert settings(f"\\+{META} v\n\\{META} w\n\\-{META}\n").tag == (
        "a._______________"
    )
    td = tb.ToolboxData()
    td.open_string("\\lx a\n\\%s v\n\\ge g\n" % META)
    chunked = td.parse(grammar="x: {<lx><a.*>}", key="lx")
    assert [e.tag for e in chunked[1][0]] == ["lx", "a._______________"]


def test_the_record_key_is_compared_not_matched():
    assert len(data("\\l.x a\n\\lx b\n\\lyx c\n", key="l.x")) == 2


def test_an_unterminated_block_is_closed_by_the_writer():
    tree = settings("\\+a v\n\\b w\n")
    assert tostring(tree) == b"<a>v<b>w</b></a>"
    assert tb.to_settings_string(ElementTree(tree)) == "\\+a v\n\\b w\n\\-a\n"


def test_a_close_with_nothing_open_is_refused():
    with pytest.raises(IndexError):
        settings("\\-a\n")


def test_a_close_names_nothing_it_closes_the_open_block():
    assert tostring(settings("\\+a v\n\\-b\n")) == b"<a>v</a>"


@pytest.mark.parametrize("text", ["\\+a\n\\-a\n\\+b\n\\-b\n", "\\a x\n\\b y\n"])
def test_a_second_top_level_element_is_refused(text):
    with pytest.raises(ParseError, match="multiple elements on top level"):
        settings(text)


def test_an_empty_settings_file_parses_to_none():
    assert settings("") is None


def _is_xml_name(name):
    """XML 1.0 (Fifth Edition) Name, written out here, not taken from nltk."""
    start = [
        (0x41, 0x5A), (0x5F, 0x5F), (0x61, 0x7A), (0xC0, 0xD6), (0xD8, 0xF6),
        (0xF8, 0x2FF), (0x370, 0x37D), (0x37F, 0x1FFF), (0x200C, 0x200D),
        (0x2070, 0x218F), (0x2C00, 0x2FEF), (0x3001, 0xD7FF), (0xF900, 0xFDCF),
        (0xFDF0, 0xFFFD), (0x10000, 0xEFFFF),
    ]  # fmt: skip
    rest = start + [(0x2D, 0x2E), (0x30, 0x39), (0xB7, 0xB7), (0x300, 0x36F)]
    rest += [(0x203F, 0x2040)]

    def inside(ch, ranges):
        return any(a <= ord(ch) <= b for a, b in ranges)

    return bool(name) and inside(name[0], start) and all(inside(c, rest) for c in name)


_IGNORABLE = redos.compile(r"\p{Default_Ignorable_Code_Point}")

#: Every code point of the blocks that held a failure, and a stride over the rest.
SAMPLE = sorted(
    set(range(0x0, 0x400))
    | set(range(0x1100, 0x1200))
    | set(range(0x1780, 0x1810))
    | set(range(0x2000, 0x2500))
    | set(range(0x3130, 0x3190))
    | set(range(0xFE00, 0xFE70))
    | set(range(0xFF00, 0x10000))
    | set(range(0x1D170, 0x1D180))
    | set(range(0xE0000, 0xE01F0))
    | set(range(0x400, 0x110000, 251)) - set(range(0xD800, 0xE000))
)


def _bad(sanitize, marker):
    tag = sanitize(marker)
    return not _is_xml_name(tag) or bool(redos.search(_IGNORABLE, tag))


def _bad_markers(sanitize):
    markers = [m for cp in SAMPLE for m in (chr(cp) + "x", "x" + chr(cp))]
    return [m for m in markers if _bad(sanitize, m)]


def test_every_sanitised_marker_is_a_visible_xml_name():
    assert _bad_markers(tb._sanitize_marker) == []


def _pre_fix_sanitize(mkr):
    """_sanitize_marker before this change, step for step."""
    if not mkr:
        return "empty"
    safe = redos.sub(r"[^\w\-.]", "_", mkr)
    if redos.match(r"^[\d\-.]", safe):
        safe = "_" + safe
    if safe.lower() in {"script", "style", "iframe", "object", "embed", "link", "meta"}:
        safe = "tb_" + safe
    return safe


def test_sanitised_marker_teeth():
    assert _bad_markers(_pre_fix_sanitize)
    for marker in (
        "x" + chr(0xB5),  # MICRO SIGN: a letter, no XML name character
        chr(0x301) + "x",  # a combining mark cannot start a name
        "g" + chr(0x200D) + "e",  # ZERO WIDTH JOINER renders as nothing
        "ge" + chr(0xFE0F),  # a variation selector renders as nothing
        "x" + chr(0x24B6),  # CIRCLED LATIN CAPITAL LETTER A
    ):
        assert _bad(_pre_fix_sanitize, marker) and not _bad(tb._sanitize_marker, marker)


@pytest.mark.parametrize("cp", [cp for cp in range(0x100) if cp != 0x0A])
def test_nul_every_control_and_every_latin1_character_in_a_marker(cp):
    """White space ends a marker (the value keeps it); any other character
    stays in the marker, sanitised to an XML name with no control in it."""
    ch = chr(cp)
    record = data(f"\\lx a\n\\g{ch}e v{ch}w\n")[1]
    tag = record[1].tag
    assert _is_xml_name(tag) and ch in record[1].text
    if redos.match(r"\s", ch):
        assert tag == "g"
    elif cp < 0x20 or 0x7F <= cp < 0xA0:
        assert tag == "g_e"


@pytest.mark.parametrize(
    "cp",
    [0x202A, 0x202B, 0x202C, 0x202D, 0x202E, 0x2066, 0x2067, 0x2068, 0x2069]
    + [0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF, 0x034F, 0x180E, 0xFE0F, 0x3164],
)
def test_bidi_and_zero_width_characters_leave_markers_and_stay_in_values(cp):
    ch = chr(cp)
    record = data(f"\\lx a\n\\g{ch}e v{ch}w\n")[1]
    assert record[1].tag == "g_e"
    assert record[1].text == "v%sw" % ch


def test_duplicate_backslashes_name_an_inert_marker():
    record = data("\\lx a\n\\\\ge v\n\\\\\\+x w\n")[1]
    assert [e.tag for e in record] == ["lx", "_ge", "___x"]
    tree = settings("\\+\\\\set\n\\\\nam v\n\\-\\\\set\n")
    assert tostring(tree) == b"<__set><_nam>v</_nam></__set>"


def test_html_element_names_never_carry_attributes():
    names = ["script", "SCRIPT", "style", "iframe", "svg", "img", "math", "noscript"]
    tree = data("".join("\\%s v=1 onload=x\n" % n for n in ["lx"] + names))
    tags = [e.tag for e in tree[1]][1:]
    assert tags == ["tb_script", "tb_SCRIPT", "tb_style", "tb_iframe"] + names[4:]
    assert all(not e.attrib and e.tail is None for e in tree.iter())


class OpenSpy:
    """Records every open (builtins, io, os, codecs) and whether a pathsec
    frame was on the stack when it ran."""

    def __init__(self, monkeypatch):
        self.calls = []
        for owner, name in ((builtins, "open"), (io, "open"), (os, "open")):
            monkeypatch.setattr(owner, name, self._wrap(name, getattr(owner, name)))
        monkeypatch.setattr(codecs, "open", self._wrap("codecs.open", codecs.open))

    def _wrap(self, name, real):
        def spy(file, *args, **kwargs):
            if not isinstance(file, int):  # an int re-wraps a descriptor
                stack = "".join(traceback.format_stack(limit=15))
                self.calls.append((name, str(file), "pathsec.py" in stack))
            return real(file, *args, **kwargs)

        return spy

    def unguarded(self):
        return [c for c in self.calls if not c[2]]


def test_a_settings_file_naming_itself_opens_nothing_else(pathsec_sandbox, monkeypatch):
    path = os.path.join(str(pathsec_sandbox.root), "self.typ")
    plant(
        pathsec_sandbox.root,
        "self.typ",
        "\\+DatabaseType self\n\\fil %s\n\\+mkrset\n\\+mkr lx\n\\lng %s\n"
        "\\-mkr\n\\-mkrset\n\\-DatabaseType\n" % (path, "/etc/passwd"),
    )
    spy = OpenSpy(monkeypatch)
    tree = tb.ToolboxSettings(path, encoding="utf8").parse(unwrap=False)
    assert tree.tag == "DatabaseType"
    assert {os.path.realpath(c[1]) for c in spy.calls} == {os.path.realpath(path)}
    assert spy.unguarded() == []


# 4. Line breaks and BOMs through every entry route.

BREAKS = {
    "VT": chr(0x0B),
    "FF": chr(0x0C),
    "FS": chr(0x1C),
    "GS": chr(0x1D),
    "RS": chr(0x1E),
    "NEL": chr(0x85),
    "LS": chr(0x2028),
    "PS": chr(0x2029),
}


def _fields_by_route(root, text, encoding="utf-8", **kwargs):
    path = plant(root, "route.db", text, encoding)
    kwargs.setdefault("unwrap", False)
    routes = {}
    sf = tb.StandardFormat()
    sf.open_string(text)
    routes["string"] = list(sf.fields(**kwargs))
    routes["filename"] = list(tb.StandardFormat(path, encoding).fields(**kwargs))
    pointer = FileSystemPathPointer(path)
    routes["pointer"] = list(tb.StandardFormat(pointer, encoding).fields(**kwargs))
    reader = ToolboxCorpusReader(str(root), ["route.db"], encoding=encoding)
    routes["corpus reader"] = reader.fields("route.db", encoding=encoding, **kwargs)
    return routes


@pytest.mark.parametrize("label", sorted(BREAKS))
def test_a_unicode_line_break_starts_no_field_on_any_route(pathsec_sandbox, label):
    text = "\\lx a\n\\ge gloss%s\\lx smuggled\n" % BREAKS[label]
    for route, fields in _fields_by_route(pathsec_sandbox.root, text).items():
        assert fields == [("lx", "a"), ("ge", "gloss%s\\lx smuggled" % BREAKS[label])]


def _develop_line_iteration(monkeypatch):
    """Put back the line iteration of develop: the stream's own readline."""
    monkeypatch.setattr(tb.StandardFormat, "_lines", lambda self: iter(self._file))


@pytest.mark.parametrize("label", sorted(BREAKS))
def test_unicode_line_break_teeth(pathsec_sandbox, label, monkeypatch):
    """The PathPointer reader's own line iteration splits there."""
    text = "\\lx a\n\\ge gloss%s\\lx smuggled\n" % BREAKS[label]
    pointer = FileSystemPathPointer(plant(pathsec_sandbox.root, "t.db", text))
    _develop_line_iteration(monkeypatch)
    sf = tb.StandardFormat(pointer, "utf-8")
    assert [m for m, _ in sf.fields(unwrap=False)] == ["lx", "ge", "lx"]


def test_crlf_and_cr_read_the_same_on_every_file_route(pathsec_sandbox):
    text = "\\lx a\r\nmore\r\n\\ge b\rtail\n\\gp c\r\n"
    routes = _fields_by_route(pathsec_sandbox.root, text)
    expected = [("lx", "a\nmore"), ("ge", "b\ntail"), ("gp", "c")]
    for route in ("filename", "pointer", "corpus reader"):
        assert routes[route] == expected
    # open_string keeps a lone CR inside a line (toolbox.doctest pins it)
    assert routes["string"] == [("lx", "a\r\nmore"), ("ge", "b\rtail"), ("gp", "c")]


def test_a_utf8_bom_is_dropped_on_every_route(pathsec_sandbox):
    text = chr(0xFEFF) + "\\lx a\n\\ge b\n"
    for route, fields in _fields_by_route(pathsec_sandbox.root, text).items():
        assert fields == [("lx", "a"), ("ge", "b")], route
    sf = tb.StandardFormat()
    sf.open_string("\xef\xbb\xbf\\lx a\n")
    assert list(sf.fields()) == [("lx", "a")]


def test_bom_teeth(pathsec_sandbox):
    """The planted file really starts with the three BOM bytes, which decode
    to U+FEFF ahead of the first marker."""
    path = plant(pathsec_sandbox.root, "bom.db", chr(0xFEFF) + "\\lx a\n")
    with open(path, "rb") as handle:
        raw = handle.read()
    assert raw[:3] == b"\xef\xbb\xbf"
    assert raw.decode("utf-8")[0] == chr(0xFEFF)


def test_a_pathpointer_without_an_encoding_reads_text(pathsec_sandbox):
    pointer = FileSystemPathPointer(plant(pathsec_sandbox.root, "p.db", "\\lx a\n"))
    assert tostring(tb.ToolboxData(pointer).parse(key="lx")[1]) == (
        b"<record><lx>a</lx></record>"
    )
    with pointer.open() as handle:  # teeth: the pointer itself hands out bytes
        assert isinstance(handle.read(), bytes)


def _real(resource):
    try:
        return str(nltk.data.find(resource))
    except LookupError:
        pytest.skip("the toolbox corpus is not installed")


REAL_CRLF = {
    "MDF/MDFSampl.db": "cp1252",
    "MDF/English.lng": "cp1252",
    "rotokas/how_kika_galuc_mountain_got_its_name.txt": "utf8",
}


@pytest.mark.parametrize("rel", sorted(REAL_CRLF))
def test_real_crlf_files_read_the_same_through_the_corpus_reader(rel, monkeypatch):
    root = _real("corpora/toolbox")
    enc = REAL_CRLF[rel]
    reader = ToolboxCorpusReader(root, [rel], encoding=enc)
    by_reader = reader.fields(rel, unwrap=False, encoding=enc)
    sf = tb.StandardFormat(os.path.join(root, rel), enc)
    assert by_reader == list(sf.fields(unwrap=False))
    assert not any("\r" in value for _, value in by_reader)
    _develop_line_iteration(monkeypatch)  # teeth: the reader's own lines keep CR
    old = tb.StandardFormat(FileSystemPathPointer(os.path.join(root, rel)), enc)
    assert any("\r" in value for _, value in old.fields(unwrap=False))


def test_demo_runs(capsys):
    _real("corpora/toolbox/rotokas.dic")
    _real("corpora/toolbox/MDF/MDF_AltH.typ")
    tb.demo()
    out = capsys.readouterr().out
    assert "kaa" in out and "letter" in out and "\\\\+DatabaseType MDF" in out


# 5. Writers.


def _record(**fields):
    root = Element("toolbox_data")
    SubElement(root, "header")
    record = SubElement(root, "record")
    for tag, text in fields.items():
        SubElement(record, tag).text = text
    return root


@pytest.mark.parametrize(
    "value",
    ["gloss\n\\lx injected", "gloss\r\\lx injected", "gloss\r\n\\lx x", "\n\\-set"],
)
def test_a_value_line_that_is_a_marker_is_refused_by_both_writers(value):
    with pytest.raises(ValueError, match="separate field"):
        tb.to_sfm_string(_record(lx="a", ge=value))
    block = Element("set")
    SubElement(block, "nam").text = value
    with pytest.raises(ValueError, match="separate field"):
        tb.to_settings_string(ElementTree(block))


@pytest.mark.parametrize("value", ["a\n\\ b", "a\n\\", "a\n b", "a\\lx", "\\lx"])
def test_a_value_line_that_is_no_marker_is_written_and_read_back(value):
    tree = _record(lx="a", ge=value)
    assert tb.to_sfm_string(tree) == "\\lx a\n\\ge %s\n" % value
    block = Element("set")
    SubElement(block, "nam").text = value
    out = tb.to_settings_string(ElementTree(block))
    assert tostring(settings(out)) == tostring(block)


@pytest.mark.parametrize(
    "tag", ["", "a b", "a\n\\-set", "a\tb", chr(0x2028).join("ab")]
)
def test_a_marker_that_would_split_is_refused_by_both_writers(tag):
    root = Element("toolbox_data")
    SubElement(SubElement(root, "record"), tag).text = "v"
    with pytest.raises(ValueError, match="cannot write marker"):
        tb.to_sfm_string(root)
    block = Element("set")
    SubElement(block, tag).text = "v"
    with pytest.raises(ValueError, match="cannot write marker"):
        tb.to_settings_string(ElementTree(block))


@pytest.mark.parametrize("tag", ["+x", "-x"])
def test_a_block_sign_is_refused_in_settings_and_written_in_data(tag):
    block = Element("set")
    SubElement(block, tag).text = "v"
    with pytest.raises(ValueError, match="cannot write marker"):
        tb.to_settings_string(ElementTree(block))
    assert tb.to_sfm_string(_record(**{"lx": "a", tag: "v"})).endswith("\\%s v\n" % tag)


def test_a_comment_node_is_refused():
    from xml.etree.ElementTree import Comment

    block = Element("set")
    block.append(Comment("c"))
    with pytest.raises(ValueError, match="cannot write marker"):
        tb.to_settings_string(ElementTree(block))


def test_writer_teeth(monkeypatch):
    """Without the check the same trees read back as other trees, or not at all."""
    monkeypatch.setattr(tb, "_check_writable", lambda *args, **kwargs: None)
    out = tb.to_sfm_string(_record(lx="a", ge="gloss\n\\lx injected"))
    assert len(data(out)) == 3  # header and two records, one injected
    block = Element("set")
    SubElement(block, "nam").text = "x\n\\-set\n\\+evil y"
    with pytest.raises(ParseError):
        settings(tb.to_settings_string(ElementTree(block)))
    block = Element("set")
    SubElement(block, "a b").text = "v"
    assert tostring(settings(tb.to_settings_string(ElementTree(block)))) == (
        b"<set><a>b v</a></set>"
    )


HOSTILE_SETTINGS = [
    nested(BOUND),
    f"\\+{META} v\n\\{META} w\n\\-{META}\n",
    "\\+a v\n\\b w\n",
    "\\+a v\n\\-b\n",
    "\\+a\n\\g" + chr(0) + "e v" + chr(0) + "al\n\\-a\n",
    "\\+a\n\\g" + chr(0x202E) + "e v" + chr(0x202E) + "w\n\\-a\n",
    "\\+a\n\\b x\n\\\n\\ y\n\\-a\n",
    "\\+set\n\\b x\r\ny\r\n\\c \\-z\n\\-set\n",
    "\\+set\n\\b x" + chr(0x2028) + "\\-set\n\\-set\n",
]

HOSTILE_DATA = [
    "\\lx a\n\\%s v\n" % META,
    "\\lx a\n\\g" + chr(0) + "e v" + chr(0) + "al\n",
    "\\lx a\n\\ge \\\n\\lx b\n\\ge  x \n",
    "\\_sh v3\n\\lx a\n\\script s\n\\lx b\n",
    "\\lx a\n\\ge b" + chr(0x85) + "\\lx c\n",
    "\\lx header-less\n\\ge g\n",
]


@pytest.mark.parametrize("text", HOSTILE_SETTINGS)
@pytest.mark.parametrize("unwrap", [False, True])
def test_parsed_hostile_settings_write_back_unchanged(text, unwrap):
    tree = settings(text, unwrap=unwrap)
    out = tb.to_settings_string(ElementTree(tree))
    assert tostring(settings(out, unwrap=unwrap)) == tostring(tree)


@pytest.mark.parametrize("text", HOSTILE_DATA)
def test_parsed_hostile_data_writes_back_unchanged(text):
    tree = data(text)
    assert tostring(data(tb.to_sfm_string(tree))) == tostring(tree)


def test_a_lone_cr_marker_line_parsed_from_a_string_is_refused_on_write():
    """open_string keeps it in one value; a file would split it, so it is
    refused rather than written."""
    tree = data("\\lx a\n\\ge gloss\r\\lx smuggled\n")
    assert tree[1][1].text == "gloss\r\\lx smuggled"
    with pytest.raises(ValueError, match="separate field"):
        tb.to_sfm_string(tree)


def test_empty_header_round_trips():
    tree = data("\\lx a\n\\ge g\n")
    assert len(tree[0]) == 0
    out = tb.to_sfm_string(tree)
    assert out == "\\lx a\n\\ge g\n"
    assert tostring(data(out)) == tostring(tree)


def test_default_fields_are_written_as_empty_markers():
    tree = data("\\_sh v3\n\\lx a\n\\ge g\n")
    tb.add_default_fields(tree, {"record": ("ps", "ge")})
    assert tb.to_sfm_string(tree) == "\\_sh v3\n\n\\lx a\n\\ge g\n\\ps\n"


def test_to_sfm_string_with_an_encoding_returns_bytes():
    tree = data("\\_sh v3\n\\lx caf" + chr(0xE9) + "\n\\ge g\n")
    assert tb.to_sfm_string(tree, encoding="cp1252") == (
        b"\\_sh v3\n\n\\lx caf\xe9\n\\ge g\n"
    )
    assert tb.to_sfm_string(tree, encoding="cp1252", unicode_fields={"lx"}) == (
        b"\\_sh v3\n\n\\lx caf\xc3\xa9\n\\ge g\n"
    )


#: file -> (encoding, record key)
REAL_DATA = {
    "rotokas.dic": ("utf8", "lx"),
    "iu_mien_samp.db": ("utf8", "lx"),
    "test.dic": ("utf8", None),  # keyed by its first marker, f1
    "MDF/MDF_AltH.db": ("cp1252", "lx"),
    "MDF/MDFSampl.db": ("cp1252", "lx"),
    "rotokas/river.txt": ("utf8", "ref"),
}
REAL_SETTINGS = {
    "MDF/MDF_AltH.typ": "cp1252",
    "MDF/MDF.typ": "cp1252",
    "MDF/English.lng": "cp1252",
    "MDF/Date.lng": "cp1252",
}


@pytest.mark.parametrize("rel", sorted(REAL_DATA))
def test_real_data_reads_the_same_by_route_and_writes_back_unchanged(rel):
    root = _real("corpora/toolbox")
    (enc, key), path = REAL_DATA[rel], os.path.join(root, rel)
    by_name = tb.ToolboxData(path, enc).parse(key=key)
    by_pointer = tb.ToolboxData(FileSystemPathPointer(path), enc).parse(key=key)
    assert tostring(by_name) == tostring(by_pointer)
    assert len(by_name) > 1
    assert tostring(data(tb.to_sfm_string(by_name), key=key)) == tostring(by_name)


@pytest.mark.parametrize("rel", sorted(REAL_SETTINGS))
@pytest.mark.parametrize("unwrap", [False, True])
def test_real_settings_read_the_same_by_route_and_write_back_unchanged(rel, unwrap):
    root = _real("corpora/toolbox")
    enc, path = REAL_SETTINGS[rel], os.path.join(root, rel)
    by_name = tb.ToolboxSettings(path, enc).parse(unwrap=unwrap)
    pointer = FileSystemPathPointer(path)
    by_pointer = tb.ToolboxSettings(pointer, enc).parse(unwrap=unwrap)
    assert tostring(by_name) == tostring(by_pointer)
    out = tb.to_settings_string(ElementTree(by_name))
    assert tostring(settings(out, unwrap=unwrap)) == tostring(by_name)


def test_no_input_yields_an_attribute_or_a_tail_and_no_xml_parser_runs(monkeypatch):
    import pyexpat
    import xml.etree.ElementTree as ET

    hits = []
    real_create, real_parser = pyexpat.ParserCreate, ET.XMLParser
    monkeypatch.setattr(
        pyexpat, "ParserCreate", lambda *a, **k: hits.append(1) or real_create(*a, **k)
    )
    monkeypatch.setattr(
        ET, "XMLParser", lambda *a, **k: hits.append(2) or real_parser(*a, **k)
    )
    trees = [settings(t) for t in HOSTILE_SETTINGS] + [data(t) for t in HOSTILE_DATA]
    for tree in trees:
        assert all(not e.attrib and e.tail is None for e in tree.iter())
        tb.to_settings_string(ElementTree(tree))
    assert hits == []


# 6. Paths.


def _settings_by_name(path):
    return tb.ToolboxSettings(path, "utf8").parse(unwrap=False)


ENTRIES = {
    "StandardFormat": lambda p: list(tb.StandardFormat(p, "utf8").fields()),
    "ToolboxData": lambda p: tb.ToolboxData(p, "utf8").parse(key="lx"),
    "ToolboxSettings": _settings_by_name,
    "corpus reader": lambda p: ToolboxCorpusReader(
        os.path.dirname(str(p)), [os.path.basename(str(p))]
    ).fields(os.path.basename(str(p))),
}
CANARY = "OUTSIDE-ROOT-CANARY"


def _refused(entry, path, monkeypatch):
    """The entry refuses ``path`` and every open it made ran inside pathsec."""
    spy = OpenSpy(monkeypatch)
    try:
        got = ENTRIES[entry](path)
    except PermissionError:
        pass
    except ValueError as exc:  # the corpus reader refuses a root this way
        assert "Security Violation" in str(exc)
    else:
        raise AssertionError(f"{entry} read {path!r}: {got!r}")
    assert spy.unguarded() == []


def _outside(sandbox):
    return plant(sandbox.outside, "secret.db", "\\lx %s\n" % CANARY)


def _reads(entry, path):
    got = ENTRIES[entry](path)
    text = tostring(got).decode() if hasattr(got, "iter") else repr(got)
    assert "inside" in text
    return got


@pytest.mark.parametrize("entry", sorted(ENTRIES))
def test_an_outside_file_is_refused(pathsec_sandbox, entry, monkeypatch):
    _refused(entry, _outside(pathsec_sandbox), monkeypatch)
    _reads(entry, plant(pathsec_sandbox.root, "in.db", "\\lx inside\n"))


@posix_only
@pytest.mark.parametrize("entry", sorted(ENTRIES))
def test_links_inside_a_root_are_refused(pathsec_sandbox, entry, monkeypatch):
    root = str(pathsec_sandbox.root)
    os.symlink(_outside(pathsec_sandbox), os.path.join(root, "out.db"))
    real = plant(root, "real.db", "\\lx inside\n")
    os.symlink(real, os.path.join(root, "in.db"))
    os.symlink(str(pathsec_sandbox.outside), os.path.join(root, "outdir"))
    for name in ("out.db", "in.db", os.path.join("outdir", "secret.db")):
        _refused(entry, os.path.join(root, name), monkeypatch)
    _reads(entry, real)


@posix_only
@pytest.mark.parametrize("entry", sorted(ENTRIES))
def test_a_hard_link_to_an_outside_file_is_refused(pathsec_sandbox, entry, monkeypatch):
    link = os.path.join(str(pathsec_sandbox.root), "hard.db")
    try:
        os.link(_outside(pathsec_sandbox), link)
    except OSError as exc:
        pytest.skip("no hard link across these directories: %s" % exc)
    _refused(entry, link, monkeypatch)


@posix_only
@pytest.mark.parametrize("entry", sorted(ENTRIES))
def test_a_fifo_is_refused_without_blocking(pathsec_sandbox, entry, monkeypatch):
    fifo = os.path.join(str(pathsec_sandbox.root), "pipe.db")
    os.mkfifo(fifo)
    _refused(entry, fifo, monkeypatch)


@pytest.mark.parametrize("entry", sorted(ENTRIES))
def test_a_directory_is_not_read(pathsec_sandbox, entry):
    directory = os.path.join(str(pathsec_sandbox.root), "dir.db")
    os.makedirs(directory)
    with pytest.raises((PermissionError, IsADirectoryError, ValueError)):
        ENTRIES[entry](directory)


@posix_only
@pytest.mark.parametrize("entry", sorted(ENTRIES))
@pytest.mark.parametrize("mode", [0o620, 0o602, 0o666])
def test_a_file_another_account_can_write_is_refused(
    pathsec_sandbox, entry, mode, monkeypatch
):
    path = plant(pathsec_sandbox.root, "shared.db", "\\lx inside\n", mode=mode)
    _refused(entry, path, monkeypatch)
    os.chmod(path, 0o600)  # teeth: the write bit alone decides
    _reads(entry, path)


@posix_only
def test_shared_file_teeth(pathsec_sandbox, monkeypatch):
    """Before this change a bare filename read the file the corpus reader refused."""
    path = plant(pathsec_sandbox.root, "shared.db", "\\lx inside\n", mode=0o666)
    monkeypatch.setattr(tb, "_refuse_file_not_ours", lambda stream, path: stream)
    _reads("StandardFormat", path)
    with pytest.raises(PermissionError):
        ENTRIES["corpus reader"](path)


@pytest.mark.parametrize("entry", ["StandardFormat", "ToolboxData", "ToolboxSettings"])
def test_odd_spellings_of_an_outside_file_are_refused(
    pathsec_sandbox, entry, monkeypatch
):
    outside = _outside(pathsec_sandbox)
    root = str(pathsec_sandbox.root)
    rel = os.path.relpath(outside, root)
    for spelling in (
        "file://" + pathlib.Path(outside).as_posix(),
        os.path.join(root, rel),
        pathlib.Path(outside),
        os.fsencode(outside),
    ):
        _refused(entry, spelling, monkeypatch)
    for spelling in (
        "file://" + pathlib.Path(outside).as_posix().replace("/", "%2F"),
        os.path.join(root, rel.replace("..", "%2e%2e")),
    ):
        with pytest.raises((PermissionError, FileNotFoundError)):
            ENTRIES[entry](spelling)


def test_a_pathpointer_built_on_an_outside_path_is_refused(pathsec_sandbox):
    pointer = FileSystemPathPointer(_outside(pathsec_sandbox))
    with pytest.raises(PermissionError):
        tb.ToolboxData(pointer, "utf8").parse()
    with pytest.raises(PermissionError):
        tb.ToolboxSettings(pointer, "utf8").parse()


def test_the_corpus_reader_refuses_an_outside_root_and_a_dotdot_fileid(pathsec_sandbox):
    _outside(pathsec_sandbox)
    with pytest.raises((PermissionError, ValueError)):
        ToolboxCorpusReader(str(pathsec_sandbox.outside), ["secret.db"]).fields(
            "secret.db"
        )
    rel = os.path.relpath(
        os.path.join(str(pathsec_sandbox.outside), "secret.db"),
        str(pathsec_sandbox.root),
    )
    with pytest.raises(ValueError):
        ToolboxCorpusReader(str(pathsec_sandbox.root), [rel]).fields(rel)


def test_a_file_descriptor_passes_through_pathsec_by_design(pathsec_sandbox):
    """pathsec.open hands an int to the kernel unchecked: a caller who passes a
    descriptor has already opened the file. Pinned so a change is deliberate."""
    fd = os.open(_outside(pathsec_sandbox), os.O_RDONLY)
    sf = tb.StandardFormat(fd)
    try:
        assert list(sf.fields()) == [("lx", CANARY)]
    finally:
        sf.close()


def test_the_cr8c_shape_is_refused(pathsec_sandbox, monkeypatch):
    """GHSA-cr8c-r94v-fmcm: a plain filename outside every root."""
    outside = _outside(pathsec_sandbox)
    for entry in ("StandardFormat", "ToolboxData", "ToolboxSettings"):
        _refused(entry, outside, monkeypatch)


@pytest.mark.parametrize("entry", sorted(ENTRIES))
def test_every_open_of_an_inside_file_runs_inside_pathsec(
    pathsec_sandbox, entry, monkeypatch
):
    path = plant(pathsec_sandbox.root, "in.db", "\\lx inside\n")
    spy = OpenSpy(monkeypatch)
    _reads(entry, path)
    assert spy.calls and spy.unguarded() == []
