from nltk.tree import Tree


def test_fromstring_allows_escaped_closing_parenthesis_leaf() -> None:
    tree = Tree.fromstring(r"(S \))")

    assert tree.label() == "S"
    assert tree.leaves() == [r"\)"]


def test_fromstring_allows_escaped_opening_parenthesis_leaf() -> None:
    tree = Tree.fromstring(r"(S \()")

    assert tree.label() == "S"
    assert tree.leaves() == [r"\("]
