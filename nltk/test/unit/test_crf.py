"""
Regression tests for ``nltk.tag.crf.CRFTagger``.
"""

import os

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


@pytest.mark.skipif(not hasattr(os, "getuid"), reason="POSIX ownership model")
def test_set_model_file_refuses_group_or_world_writable_model(tmp_path):
    """A group/world-writable model another local user could swap is refused
    before crfsuite (C) parses it (require_private, CWE-426/CWE-732)."""
    model = tmp_path / "model.crf.tagger"
    CRFTagger().train(_TRAIN, str(model))
    os.chmod(model, 0o666)
    with pytest.raises(PermissionError):
        CRFTagger().set_model_file(str(model))


def test_set_model_file_refuses_oversize_model(tmp_path, monkeypatch):
    """A model over MAX_TOOL_MODEL_BYTES is refused (a memory bomb crfsuite would
    load whole, CWE-400); a tiny monkeypatched cap avoids needing a giant file."""
    import nltk.tag.crf as crf_mod

    model = tmp_path / "model.crf.tagger"
    CRFTagger().train(_TRAIN, str(model))
    assert model.stat().st_size > 8
    monkeypatch.setattr(crf_mod, "MAX_TOOL_MODEL_BYTES", 8)
    with pytest.raises(PermissionError):
        CRFTagger().set_model_file(str(model))


def test_legit_private_model_still_loads_and_tags(tmp_path):
    """Control: a normal (private, in-size) trained model still loads through the
    guard and tags, so the new checks do not over-block real usage."""
    model = tmp_path / "model.crf.tagger"
    CRFTagger().train(_TRAIN, str(model))
    ct = CRFTagger()
    ct.set_model_file(str(model))
    tagged = ct.tag_sents([_SAMPLE_SENT])[0]
    assert [w for w, _ in tagged] == _SAMPLE_SENT
    assert all(t in _TAGS for _, t in tagged)
