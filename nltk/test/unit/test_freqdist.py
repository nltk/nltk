from collections import Counter

import pytest

import nltk
from nltk.probability import ConditionalFreqDist, LaplaceProbDist, MLEProbDist


def test_iterating_returns_an_iterator_ordered_by_frequency():
    samples = ["one", "two", "two"]
    distribution = nltk.FreqDist(samples)
    assert list(distribution) == ["two", "one"]


@pytest.mark.parametrize("warm_cache", [False, True])
@pytest.mark.parametrize(
    "method, args, result, remaining",
    [
        ("pop", ("a",), 2, {"b": 1}),
        ("pop", ("a", None), 2, {"b": 1}),
        ("popitem", (), ("b", 1), {"a": 2}),
        ("clear", (), None, {}),
    ],
)
def test_removal_updates_totals_and_probabilities(
    warm_cache, method, args, result, remaining
):
    distribution = nltk.FreqDist("aab")
    probability = MLEProbDist(distribution)
    if warm_cache:
        assert distribution.N() == 3
    assert getattr(distribution, method)(*args) == result
    assert dict(distribution) == remaining
    total = sum(remaining.values())
    assert distribution.N() == total
    for sample in "ab":
        expected = remaining.get(sample, 0) / total if total else 0
        assert distribution.freq(sample) == expected
        assert probability.prob(sample) == expected
        assert LaplaceProbDist(distribution, bins=2).prob(sample) == (
            remaining.get(sample, 0) + 1
        ) / (total + 2)
    distribution.update("cc")
    assert distribution.N() == total + 2


@pytest.mark.parametrize("warm_cache", [False, True])
@pytest.mark.parametrize("default", [None, 0, object()])
def test_pop_missing_with_default(warm_cache, default):
    distribution = nltk.FreqDist("aab")
    if warm_cache:
        assert distribution.N() == 3
    assert distribution.pop("missing", default) is default
    assert dict(distribution) == {"a": 2, "b": 1}
    assert distribution.N() == 3


@pytest.mark.parametrize("warm_cache", [False, True])
def test_pop_missing_without_default(warm_cache):
    distribution = nltk.FreqDist("aab")
    if warm_cache:
        assert distribution.N() == 3
    with pytest.raises(KeyError) as error:
        distribution.pop("missing")
    assert error.value.args == ("missing",)
    assert dict(distribution) == {"a": 2, "b": 1}
    assert distribution.N() == 3


@pytest.mark.parametrize("warm_cache", [False, True])
def test_empty_removal_and_refill(warm_cache):
    distribution = nltk.FreqDist()
    if warm_cache:
        assert distribution.N() == 0
    with pytest.raises(KeyError) as error:
        distribution.popitem()
    assert error.value.args == ("popitem(): dictionary is empty",)
    assert distribution.clear() is None
    assert distribution.clear() is None
    assert distribution.N() == 0
    distribution["new"] = 2
    assert distribution.N() == 2
    assert distribution.popitem() == ("new", 2)
    assert distribution.N() == 0


@pytest.mark.parametrize(
    "method, args, kwargs",
    [
        ("pop", (), {}),
        ("pop", ("a", None, None), {}),
        ("pop", ([],), {}),
        ("pop", (), {"key": "a"}),
        ("pop", ("a",), {"default": None}),
        ("popitem", ("a",), {}),
        ("popitem", (), {"key": "a"}),
        ("clear", ("a",), {}),
        ("clear", (), {"key": "a"}),
    ],
)
def test_removal_argument_errors_match_counter(method, args, kwargs):
    distribution = nltk.FreqDist("aab")
    assert distribution.N() == 3
    for counter in (Counter("aab"), distribution):
        with pytest.raises(TypeError):
            getattr(counter, method)(*args, **kwargs)
        assert dict(counter) == {"a": 2, "b": 1}
    assert distribution.N() == 3


@pytest.mark.parametrize(
    "method, args", [("pop", ("b",)), ("popitem", ()), ("clear", ())]
)
def test_conditional_totals_after_removal(method, args):
    conditional = ConditionalFreqDist([("first", "a"), ("first", "b"), ("second", "c")])
    assert conditional.N() == 3
    getattr(conditional["first"], method)(*args)
    expected = 1 if method == "clear" else 2
    assert conditional.N() == expected
    assert conditional["second"].N() == 1


@pytest.mark.parametrize("count", [0, 2**256, -(2**256)])
@pytest.mark.parametrize(
    "method, args", [("pop", ("large",)), ("popitem", ()), ("clear", ())]
)
def test_removal_handles_large_and_signed_counts(count, method, args):
    distribution = nltk.FreqDist({"other": 1, "large": count})
    assert distribution.N() == count + 1
    result = getattr(distribution, method)(*args)
    assert result == {"pop": count, "popitem": ("large", count), "clear": None}[method]
    assert distribution.N() == (0 if method == "clear" else 1)


@pytest.mark.parametrize("method", ["pop", "popitem", "clear"])
def test_repeated_removal_from_large_distribution(method):
    distribution = nltk.FreqDist()
    size = 2048
    for _ in range(2):
        distribution.update(dict.fromkeys(range(size), 2**128))
        assert distribution.N() == size * 2**128
        if method == "clear":
            assert distribution.clear() is None
        else:
            for remaining in range(size - 1, -1, -1):
                if method == "pop":
                    assert distribution.pop(remaining) == 2**128
                else:
                    assert distribution.popitem() == (remaining, 2**128)
                if remaining % 256 == 0:
                    assert distribution.N() == remaining * 2**128
        assert distribution.N() == 0
        assert not distribution
