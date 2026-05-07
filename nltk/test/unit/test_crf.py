"""
Regression tests for ``nltk.tag.crf.CRFTagger``.
"""

import pytest

pytest.importorskip("pycrfsuite")

from nltk.tag.crf import CRFTagger

_TRAIN = [
    [("the", "DT"), ("cat", "NN"), ("sat", "VBD")],
    [("a", "DT"), ("dog", "NN"), ("ran", "VBD")],
    [("the", "DT"), ("dog", "NN"), ("sat", "VBD")],
    [("a", "DT"), ("cat", "NN"), ("ran", "VBD")],
]

_SAMPLE_SENT = ["the", "cat", "sat"]
_TAGS = {"DT", "NN", "VBD"}


@pytest.mark.parametrize(
    ("method", "bad", "match"),
    [
        ("tag", "the cat sat", "list of tokens"),
        ("tag", b"the cat sat", "list of tokens"),
        ("tag_sents", "the cat sat", "tokenized sentences"),
        ("tag_sents", b"the cat sat", "tokenized sentences"),
        ("tag_sents", ["the", "cat", "sat"], "tokenized sentences"),
        ("tag_sents", ("the", "cat", "sat"), "tokenized sentences"),
    ],
)
def test_rejects_bad_input_shapes(method, bad, match):
    ct = CRFTagger()
    with pytest.raises(TypeError, match=match):
        getattr(ct, method)(bad)


def test_training_options_are_copied():
    opts = {"c1": 0.5, "c2": 1.0}
    ct = CRFTagger(training_opt=opts)

    opts["c1"] = 99.0

    assert ct._training_options == {"c1": 0.5, "c2": 1.0}


@pytest.mark.parametrize(
    ("token", "expected"),
    [
        (
            "University",
            ["CAPITALIZATION", "SUF_y", "SUF_ty", "SUF_ity", "WORD_University"],
        ),
        ("A1", ["CAPITALIZATION", "HAS_NUM", "SUF_1", "WORD_A1"]),
        ("...", ["PUNCTUATION", "SUF_.", "SUF_..", "WORD_..."]),
        ("", []),
    ],
)
def test_default_features_are_cached_as_tuples(token, expected):
    ct = CRFTagger()

    first = ct._get_features([token], 0)
    second = ct._get_features([token], 0)

    assert first == expected
    assert second == expected
    assert first is not second
    assert ct._feature_cache[token] == tuple(expected)


def test_custom_feature_function_bypasses_default_cache():
    def feature_func(tokens, idx):
        prev = "<BOS>" if idx == 0 else tokens[idx - 1]
        return [f"TOKEN={tokens[idx]}", f"PREV={prev}"]

    ct = CRFTagger(feature_func=feature_func)

    assert ct._feature_func is feature_func
    assert ct._feature_func(["a", "b"], 1) == ["TOKEN=b", "PREV=a"]
    assert ct._feature_cache == {}


def test_clear_feature_cache_drops_cached_entries():
    ct = CRFTagger()

    ct._get_features(["University"], 0)
    ct._get_features(["dog"], 0)
    assert ct._feature_cache

    ct.clear_feature_cache()
    assert ct._feature_cache == {}

    ct._get_features(["University"], 0)
    assert "University" in ct._feature_cache


def test_tag_sents_kwargs_compatibility():
    ct = CRFTagger()

    with pytest.warns(DeprecationWarning, match="sents=.*deprecated"):
        with pytest.raises(RuntimeError, match="No model file set"):
            ct.tag_sents(sents=[["a", "b"]])

    with pytest.raises(TypeError, match="both 'sentences' and 'sents'"):
        ct.tag_sents([["a"]], sents=[["b"]])

    with pytest.raises(TypeError, match="unexpected keyword"):
        ct.tag_sents([["a"]], extra=True)


def test_train_tag_round_trip(tmp_path):
    model_file = tmp_path / "model.crf.tagger"

    trained = CRFTagger()
    trained.train(_TRAIN, str(model_file))
    assert model_file.exists()

    tagged = trained.tag(_SAMPLE_SENT)
    assert [word for word, _ in tagged] == _SAMPLE_SENT
    assert all(tag in _TAGS for _, tag in tagged)

    reloaded = CRFTagger()
    reloaded.set_model_file(str(model_file))
    assert reloaded.tag(_SAMPLE_SENT) == tagged
