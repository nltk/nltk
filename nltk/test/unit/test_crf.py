"""
Regression tests for ``nltk.tag.crf.CRFTagger``.
"""

import pytest

pytest.importorskip("pycrfsuite")

from nltk.tag.crf import CRFTagger


@pytest.mark.parametrize("bad", ["the cat sat", b"the cat sat"])
def test_crf_tag_rejects_string_or_bytes_input(bad):
    ct = CRFTagger()
    with pytest.raises(TypeError, match="list of tokens"):
        ct.tag(bad)


@pytest.mark.parametrize(
    "bad",
    [
        "the cat sat",
        b"the cat sat",
        ["the", "cat", "sat"],
        ("the", "cat", "sat"),
    ],
)
def test_crf_tag_sents_rejects_non_batch_shapes(bad):
    ct = CRFTagger()
    with pytest.raises(TypeError, match="tokenized sentences"):
        ct.tag_sents(bad)


@pytest.mark.parametrize(
    ("token", "expected"),
    [
        (
            "University",
            ["CAPITALIZATION", "SUF_y", "SUF_ty", "SUF_ity", "WORD_University"],
        ),
        (
            "A1",
            ["CAPITALIZATION", "HAS_NUM", "SUF_1", "WORD_A1"],
        ),
        (
            "...",
            ["PUNCTUATION", "SUF_.", "SUF_..", "WORD_..."],
        ),
        (
            "",
            [],
        ),
    ],
)
def test_crf_default_features_are_cached_as_tuples(token, expected):
    ct = CRFTagger()

    first = ct._get_features([token], 0)
    second = ct._get_features([token], 0)

    assert first == expected
    assert second == expected
    assert first is not second
    assert ct._feature_cache[token] == tuple(expected)


def test_crf_training_options_are_copied():
    opts = {"c1": 0.5, "c2": 1.0}
    ct = CRFTagger(training_opt=opts)

    opts["c1"] = 99.0

    assert ct._training_options == {"c1": 0.5, "c2": 1.0}


def test_crf_custom_feature_function_bypasses_default_cache():
    def feature_func(tokens, idx):
        prev = "<BOS>" if idx == 0 else tokens[idx - 1]
        return [f"TOKEN={tokens[idx]}", f"PREV={prev}"]

    ct = CRFTagger(feature_func=feature_func)

    assert ct._feature_func is feature_func
    assert ct._feature_func(["a", "b"], 1) == ["TOKEN=b", "PREV=a"]
    assert ct._feature_cache == {}


def test_crf_clear_feature_cache_drops_cached_entries():
    ct = CRFTagger()

    ct._get_features(["University"], 0)
    ct._get_features(["dog"], 0)
    assert ct._feature_cache  # populated by the calls above

    ct.clear_feature_cache()
    assert ct._feature_cache == {}

    # Cache is rebuilt on the next call.
    ct._get_features(["University"], 0)
    assert "University" in ct._feature_cache
