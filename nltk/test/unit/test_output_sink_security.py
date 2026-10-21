# Natural Language Toolkit: output-sink injection tests
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""The Jupyter tree SVG is an output sink reached by untrusted labels (a tree
built from a hostile corpus): every <text> node must carry the label XML-escaped,
never raw markup (CWE-79). The real svgling renderer runs; nothing is mocked.
The concordance sink this file once pinned is driven by
test_print_routing_end_to_end.py; the terminal and CSV matrices are in
test_termsec_attack_matrix.py and test_csv_injection_security.py."""

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
