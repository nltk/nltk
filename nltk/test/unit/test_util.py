import pytest

from nltk.util import everygrams, ngrams, transitive_closure


@pytest.fixture
def everygram_input():
    """Form test data for tests."""
    return iter(["a", "b", "c"])


def test_everygrams_without_padding(everygram_input):
    expected_output = [
        ("a",),
        ("a", "b"),
        ("a", "b", "c"),
        ("b",),
        ("b", "c"),
        ("c",),
    ]
    output = list(everygrams(everygram_input))
    assert output == expected_output


def test_everygrams_max_len(everygram_input):
    expected_output = [
        ("a",),
        ("a", "b"),
        ("b",),
        ("b", "c"),
        ("c",),
    ]
    output = list(everygrams(everygram_input, max_len=2))
    assert output == expected_output


def test_everygrams_min_len(everygram_input):
    expected_output = [
        ("a", "b"),
        ("a", "b", "c"),
        ("b", "c"),
    ]
    output = list(everygrams(everygram_input, min_len=2))
    assert output == expected_output


def test_everygrams_pad_right(everygram_input):
    expected_output = [
        ("a",),
        ("a", "b"),
        ("a", "b", "c"),
        ("b",),
        ("b", "c"),
        ("b", "c", None),
        ("c",),
        ("c", None),
        ("c", None, None),
        (None,),
        (None, None),
        (None,),
    ]
    output = list(everygrams(everygram_input, max_len=3, pad_right=True))
    assert output == expected_output


def test_everygrams_pad_left(everygram_input):
    expected_output = [
        (None,),
        (None, None),
        (None, None, "a"),
        (None,),
        (None, "a"),
        (None, "a", "b"),
        ("a",),
        ("a", "b"),
        ("a", "b", "c"),
        ("b",),
        ("b", "c"),
        ("c",),
    ]
    output = list(everygrams(everygram_input, max_len=3, pad_left=True))
    assert output == expected_output


@pytest.mark.parametrize("n", [0, -1])
def test_ngrams_rejects_non_positive_order(n):
    """A non-positive order has no meaningful n-gram, so it is refused."""
    with pytest.raises(ValueError, match="n must be positive"):
        list(ngrams(["a", "b", "c"], n))


@pytest.mark.parametrize("n", [1, 2, 3])
def test_ngrams_accepts_positive_order(n):
    output = list(ngrams(["a", "b", "c"], n))
    assert all(len(gram) == n for gram in output)


@pytest.mark.parametrize("min_len", [0, -1])
def test_everygrams_rejects_non_positive_min_len(everygram_input, min_len):
    """min_len below one would emit empty tuples alongside the real n-grams."""
    with pytest.raises(ValueError, match="min_len must be positive"):
        list(everygrams(everygram_input, min_len=min_len, max_len=2))


def test_transitive_closure_chain():
    graph = {"a": {"b"}, "b": {"c"}, "c": set()}
    expected = {"a": {"b", "c"}, "b": {"c"}, "c": set()}
    assert transitive_closure(graph) == expected


def test_transitive_closure_reflexive():
    graph = {"a": {"b"}, "b": {"c"}, "c": set()}
    expected = {"a": {"a", "b", "c"}, "b": {"b", "c"}, "c": {"c"}}
    assert transitive_closure(graph, reflexive=True) == expected


def test_transitive_closure_cycle():
    graph = {"a": {"b"}, "b": {"a"}}
    expected = {"a": {"a", "b"}, "b": {"a", "b"}}
    assert transitive_closure(graph) == expected


def test_transitive_closure_empty():
    assert transitive_closure({}) == {}


def test_transitive_closure_does_not_mutate_input():
    graph = {"a": {"b"}, "b": set()}
    original_sets = {k: v for k, v in graph.items()}
    snapshot = {k: set(v) for k, v in graph.items()}

    transitive_closure(graph)

    assert graph == snapshot
    assert set(graph) == set(snapshot)
    # the same set objects, not new-but-equal ones
    assert all(graph[k] is original_sets[k] for k in snapshot)
