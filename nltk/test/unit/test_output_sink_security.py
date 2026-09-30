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


class TestTreeSvgXss:
    def test_repr_svg_escapes_hostile_labels(self):
        pytest.importorskip("svgling", reason="svgling not installed")
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
