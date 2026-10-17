# Natural Language Toolkit: YAML deserialization DoS regression tests
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""YAML-bomb attacks and benign look-alikes for the nltk.jsontags YAML chokepoint.

Before this guard, ``nltk.data.load(format="yaml")`` and
``CategorizedMarkdownCorpusReader.metadata()`` called PyYAML's bare
``yaml.safe_load`` on corpus content. PyYAML's safe loader composes the node
graph with ordinary Python recursion and runs the implicit-type resolver on
every node, with no bound on depth, node count or size, so a small deeply
nested document raises an uncaught ``RecursionError`` (CWE-674) and a flat
document of a few hundred thousand nodes runs for minutes (CWE-400). The sibling
JSON branch of ``nltk.data.load`` was already bounded by ``safe_json_load``; this
brings YAML to the same floor through ``safe_yaml_load`` / ``safe_yaml_loads``.

Every attack here runs against the real chokepoint and asserts the specific
bounded ``ValueError``; every benign look-alike loads real-shaped YAML and
checks the value, so the bounds do not over-block. The refusals are
deterministic (the cap is crossed at a fixed node, a fixed depth or a fixed byte
count), so no assertion depends on wall-clock time.
"""

import os

import pytest

from nltk.jsontags import (
    YAML_MAX_BYTES,
    YAML_MAX_DEPTH,
    YAML_MAX_NODES,
    safe_yaml_load,
    safe_yaml_loads,
)

pytest.importorskip("yaml", reason="PyYAML is an optional dependency")


def _deep(n):
    """A flow sequence nested n levels: the RecursionError primitive."""
    return "[" * n + "]" * n


def _flat(n):
    """A flat mapping of n keys: the node-count / resolver DoS."""
    return "\n".join(f"k{i}: v{i}" for i in range(n))


def test_deep_flow_sequence_is_refused_by_depth_cap():
    """A document nested far past YAML_MAX_DEPTH is refused during composition.

    Proves the recursion primitive (uncaught RecursionError in PyYAML's
    recursive composer, CWE-674) is converted to a bounded ValueError.
    """
    with pytest.raises(ValueError, match="nesting depth"):
        safe_yaml_loads(_deep(YAML_MAX_DEPTH + 500))


def test_depth_just_over_cap_is_refused_and_just_under_loads():
    """The depth boundary is exact: cap+1 refused, a legal shallow doc loads."""
    with pytest.raises(ValueError, match="nesting depth"):
        safe_yaml_loads(_deep(YAML_MAX_DEPTH + 1))
    # A shallow nested mapping is well under the cap and must load.
    value = safe_yaml_loads("a:\n  b:\n    c: 1\n")
    assert value == {"a": {"b": {"c": 1}}}


def test_flat_mapping_over_node_cap_is_refused():
    """A flat mapping with more than YAML_MAX_NODES nodes is refused by node count.

    Proves the resolver-per-node CPU DoS (CWE-400) is bounded: the loader stops
    after a fixed number of composed nodes rather than running unbounded. This
    document is small in bytes (well under the byte cap) and shallow (well under
    the depth cap), so only the node cap can catch it.
    """
    # Two nodes per key (the scalar key and the scalar value) plus the mapping,
    # so a key count just over half the node cap crosses it.
    keys = YAML_MAX_NODES // 2 + 50
    payload = _flat(keys)
    assert len(payload.encode("utf-8")) < YAML_MAX_BYTES
    with pytest.raises(ValueError, match="composes more than"):
        safe_yaml_loads(payload)


def test_oversized_document_is_refused_before_parsing_by_byte_cap():
    """A document over YAML_MAX_BYTES is refused instantly, before any parse.

    Proves the memory bound: a huge file is rejected on its byte length, so it
    is never read into the parser.
    """
    payload = "a: 1\n" * (YAML_MAX_BYTES // 5 + 100)
    assert len(payload.encode("utf-8")) > YAML_MAX_BYTES
    with pytest.raises(ValueError, match="over the"):
        safe_yaml_loads(payload)


def test_oversized_single_scalar_is_refused_by_byte_cap():
    """One gigantic scalar value is refused by the byte cap too."""
    payload = "x: " + "a" * (YAML_MAX_BYTES + 1000)
    with pytest.raises(ValueError, match="over the"):
        safe_yaml_loads(payload)


def test_non_string_input_is_a_type_error_at_the_chokepoint():
    """A non-str/bytes argument fails with a clear TypeError, not deep inside yaml."""
    with pytest.raises(TypeError, match="expected str or bytes"):
        safe_yaml_loads(12345)


def test_stream_reader_enforces_byte_cap():
    """safe_yaml_load reads at most the cap from a stream, refusing a huge file.

    Proves the stream entry point (what nltk.data.load uses) does not slurp a
    gigantic resource into memory before rejecting it.
    """
    import io

    payload = ("a: 1\n" * (YAML_MAX_BYTES // 5 + 100)).encode("utf-8")
    with pytest.raises(ValueError, match="exceeds the"):
        safe_yaml_load(io.BytesIO(payload))


def test_benign_front_matter_round_trips():
    """A realistic markdown front-matter block loads to the expected mapping."""
    text = "title: Hello World\ntags:\n  - nlp\n  - corpora\nauthor: nltk\ncount: 3\n"
    value = safe_yaml_loads(text)
    assert value == {
        "title": "Hello World",
        "tags": ["nlp", "corpora"],
        "author": "nltk",
        "count": 3,
    }


def test_benign_alias_shares_references_and_loads():
    """A moderate anchor/alias document loads: safe mode shares, does not copy.

    An alias expands to a shared reference, not a deep copy, so a bounded alias
    document (no per-node blow-up) is legitimate and must not be refused.
    """
    value = safe_yaml_loads("a: &a [x, y, z]\nb: [*a, *a, *a]\n")
    assert value["a"] == ["x", "y", "z"]
    assert value["b"] == [["x", "y", "z"]] * 3


def test_benign_stream_round_trips():
    """safe_yaml_load reads and parses a small YAML stream correctly."""
    import io

    value = safe_yaml_load(io.BytesIO(b"name: test\nvalues:\n  - 1\n  - 2\n"))
    assert value == {"name": "test", "values": [1, 2]}


def test_data_load_yaml_refuses_deep_resource(tmp_path, monkeypatch):
    """nltk.data.load(format="yaml") refuses a planted deep resource (end to end).

    Drives the real public loader on a real file, proving the routing reaches
    the chokepoint and not bare yaml.safe_load.
    """
    import nltk
    import nltk.data
    from nltk import pathsec

    monkeypatch.setattr(pathsec, "ENFORCE", False)
    resource = tmp_path / "deep.yaml"
    resource.write_text(_deep(YAML_MAX_DEPTH + 500), encoding="utf-8")
    nltk.data.path.insert(0, os.fspath(tmp_path))
    try:
        with pytest.raises(ValueError, match="nesting depth"):
            nltk.data.load("file://" + os.fspath(resource), format="yaml")
    finally:
        nltk.data.path.remove(os.fspath(tmp_path))


def test_data_load_yaml_loads_benign_resource(tmp_path, monkeypatch):
    """nltk.data.load(format="yaml") still loads a legitimate YAML resource."""
    import nltk
    import nltk.data
    from nltk import pathsec

    monkeypatch.setattr(pathsec, "ENFORCE", False)
    resource = tmp_path / "ok.yaml"
    resource.write_text("title: Hello\nn: 3\nlist:\n  - 1\n  - 2\n", encoding="utf-8")
    nltk.data.path.insert(0, os.fspath(tmp_path))
    try:
        value = nltk.data.load("file://" + os.fspath(resource), format="yaml")
    finally:
        nltk.data.path.remove(os.fspath(tmp_path))
    assert value == {"title": "Hello", "n": 3, "list": [1, 2]}


def test_markdown_metadata_reader_refuses_deep_front_matter():
    """CategorizedMarkdownCorpusReader.metadata_reader refuses a deep front matter.

    Skipped where the markdown toolchain (markdown_it / mdit_plain /
    mdit_py_plugins) is not installed, since the reader cannot be built without
    it. The sink is the identical safe_yaml_loads call.
    """
    pytest.importorskip("markdown_it")
    pytest.importorskip("mdit_plain")
    pytest.importorskip("mdit_py_plugins")

    import io

    from nltk.corpus.reader.markdown import CategorizedMarkdownCorpusReader

    reader = CategorizedMarkdownCorpusReader.__new__(CategorizedMarkdownCorpusReader)
    from markdown_it import MarkdownIt
    from mdit_py_plugins.front_matter import front_matter_plugin

    reader.parser = MarkdownIt("commonmark").use(front_matter_plugin)
    front = "---\n" + _deep(YAML_MAX_DEPTH + 500) + "\n---\n\nbody\n"
    with pytest.raises(ValueError, match="nesting depth"):
        reader.metadata_reader(io.StringIO(front))


def test_markdown_metadata_reader_loads_benign_front_matter():
    """The markdown reader still reads a legitimate front-matter block."""
    pytest.importorskip("markdown_it")
    pytest.importorskip("mdit_plain")
    pytest.importorskip("mdit_py_plugins")

    import io

    from markdown_it import MarkdownIt
    from mdit_py_plugins.front_matter import front_matter_plugin

    from nltk.corpus.reader.markdown import CategorizedMarkdownCorpusReader

    reader = CategorizedMarkdownCorpusReader.__new__(CategorizedMarkdownCorpusReader)
    reader.parser = MarkdownIt("commonmark").use(front_matter_plugin)
    front = "---\ntitle: Doc\ntags:\n  - a\n---\n\nbody\n"
    (meta,) = reader.metadata_reader(io.StringIO(front))
    assert meta == {"title": "Doc", "tags": ["a"]}
