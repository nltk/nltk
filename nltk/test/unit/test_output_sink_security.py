# Natural Language Toolkit: output-sink injection tests
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Untrusted data reaches several output sinks besides the terminal print sites:
concordance/similar output of a loaded (possibly hostile) corpus, the WordNet
browser's served HTML (CWE-79), the downloader's Unzipping status line, and the
Jupyter tree SVG. These tests drive the real code paths (no mocks) and confirm a
control sequence or markup payload cannot survive to the sink."""

import re

import pytest


class TestTextTerminalSanitisation:
    def _text(self, tokens):
        from nltk.text import Text

        return Text(tokens)

    def test_concordance_escapes_control_sequences(self, capsys):
        # a corpus token carrying an ANSI/OSC sequence must not drive the TTY
        toks = "the quick \x1b[2Kwiped fox and the lazy dog and the end".split()
        toks[2] = "\x1b[2Kwiped"
        self._text(toks * 3).concordance("the", width=79, lines=5)
        out = capsys.readouterr().out
        assert "\x1b" not in out

    def test_similar_escapes_control_sequences(self, capsys):
        a = "\x1b]0;title\x07evil"
        toks = ["the", a, "fox", "the", a, "dog", "the", a, "cat"]
        self._text(toks).similar("the")
        out = capsys.readouterr().out
        assert "\x1b" not in out and "\x07" not in out

    def test_benign_concordance_is_unchanged(self, capsys):
        toks = "a b c the word here and the word there end stop now go".split()
        self._text(toks * 3).concordance("word", width=79, lines=2)
        out = capsys.readouterr().out
        assert "word" in out  # legit text prints normally, no escaping noise
        assert "\\x" not in out


class TestWordnetAppXss:
    def test_make_lookup_link_escapes(self):
        from nltk.app.wordnet_app import make_lookup_link

        class Ref:
            def encode(self):
                return 'a"onmouseover=alert(1)'

        import html

        out = make_lookup_link(Ref(), html.escape("<script>x</script>"))
        assert "<script>" not in out  # element-content payload neutralised
        assert '"onmouseover=alert(1)"' not in out  # attribute breakout neutralised
        assert "&lt;script&gt;" in out and "&quot;" in out


svgling = pytest.importorskip("svgling", reason="svgling not installed")


class TestTreeSvgXss:
    def test_repr_svg_escapes_hostile_labels(self):
        from nltk.tree import Tree

        t = Tree(
            "S", [Tree("NP", ["<script>alert(1)</script>"]), Tree("VP", ["a & b"])]
        )
        svg = t._repr_svg_()
        # every SVG <text> node must have the payload XML-escaped, not raw
        assert "<script>alert" not in svg
        assert "&lt;script&gt;" in svg
        for node in re.findall(r"<text[^>]*>(.*?)</text>", svg):
            assert "<script" not in node
