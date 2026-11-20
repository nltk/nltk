from nltk.tree import Tree, TreePrettyPrinter


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


def _drawn_leaf_order(tree):
    # sort the leaves by the column they are drawn at
    leaves = set(tree.leaves())
    found = []
    for line in TreePrettyPrinter(tree).text().splitlines():
        start = 0
        for word in line.split():
            start = line.index(word, start)
            if word in leaves:
                found.append((2 * start + len(word), word))
            start += len(word)
    return [word for _, word in sorted(found)]


def test_pretty_print_leaf_order_mixed_leaves_and_subtrees():
    for source in (
        "(Div (Mult sixteen four) two)",
        "(Div two (Mult sixteen four))",
        "(A (B one (C two three) four) five (D (E six) seven))",
        "(S (NP a b) (VP c))",
    ):
        tree = Tree.fromstring(source)
        assert _drawn_leaf_order(tree) == tree.leaves()
