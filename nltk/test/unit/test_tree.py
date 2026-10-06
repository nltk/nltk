from nltk.tree import Tree


def test_fromstring_allows_escaped_brackets():
    for source in (r"(S \))", r"(S \()", r"(S (NP \)) (VP ok))"):
        tree = Tree.fromstring(source)
        assert str(tree) == source


def test_fromstring_escaped_bracket_leaf_and_label():
    tree = Tree.fromstring(r"(S (\( x))")
    assert tree[0].label() == r"\("
    assert tree.leaves() == ["x"]


def test_fromstring_roundtrips_escaped_bracket_leaf():
    # a real-world case: a leaf holding a smiley whose close paren is escaped
    source = r"(EMOJI :\))"
    tree = Tree.fromstring(source)
    assert tree.label() == "EMOJI"
    assert tree.leaves() == [r":\)"]
    assert str(tree) == source


def test_fromstring_normal_parsing_unaffected():
    tree = Tree.fromstring("(S (NP the cat) (VP sat))")
    assert tree.label() == "S"
    assert tree.leaves() == ["the", "cat", "sat"]
