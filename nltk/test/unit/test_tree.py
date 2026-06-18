# Natural Language Toolkit: Tree Unit Tests
#
# Copyright (C) 2001-2026 NLTK Project
# Author: The NLTK Project contributors
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

import pytest

from nltk.tree import Tree


@pytest.mark.parametrize(
    "escaped,expected",
    [
        (r"\)", [r"\)"]),
        (r"\(", [r"\("]),
    ],
)
def test_fromstring_allows_escaped_parenthesis_leaf(escaped, expected) -> None:
    tree = Tree.fromstring(f"(S {escaped})")

    assert tree.label() == "S"
    assert tree.leaves() == expected
