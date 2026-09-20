"""Numerical lexical floors and initialization across the IBM models."""

from collections import defaultdict

import pytest

from nltk.translate import (
    AlignedSent,
    IBMModel,
    IBMModel1,
    IBMModel2,
    IBMModel3,
    IBMModel4,
    IBMModel5,
)
from nltk.translate.ibm_model import Counts

MODELS = (IBMModel1, IBMModel2, IBMModel3, IBMModel4, IBMModel5)


@pytest.fixture
def corpus():
    return [
        AlignedSent(["X", "."], ["a", "."]),
        AlignedSent(["Z", "."], ["b", "b", "."]),
    ]


def make_model(model_class, corpus, iterations, *args, **kwargs):
    if model_class in (IBMModel4, IBMModel5):
        args = ({"a": 0, "b": 0, ".": 0}, {"X": 0, "Z": 0, ".": 0}, *args)
    return model_class(corpus, iterations, *args, **kwargs)


@pytest.mark.parametrize("model_class", MODELS)
@pytest.mark.parametrize("floor", [None, 0.0, 1e-7])
def test_floor_survives_initialization_and_training(model_class, floor, corpus):
    model = make_model(model_class, corpus, 0, lexical_floor=floor)
    expected = IBMModel.MIN_PROB if floor is None else floor

    # Known target rows still have their uniform initialization. A new
    # target tests the default inherited through all lower-model constructors.
    assert model.translation_table["X"]["b"] == 1 / 3
    assert model.translation_table["new"]["b"] == expected
    assert model.alignment_table[99][99][99][99] == IBMModel.MIN_PROB
    assert model.fertility_table[99]["new"] == IBMModel.MIN_PROB

    for _ in range(2):
        model.train(corpus)
        assert model.translation_table["X"]["b"] == expected
        assert model.translation_table["Z"]["a"] == expected
        assert model.translation_table["new"]["new"] == expected
        if floor == 0.0:
            for source in model.src_vocab:
                assert sum(
                    model.translation_table[t][source] for t in model.trg_vocab
                ) == pytest.approx(1.0, rel=0, abs=1e-14)


@pytest.mark.parametrize("model_class", MODELS)
@pytest.mark.parametrize("iterations", [0, 1])
def test_omitted_none_and_explicit_default_agree(model_class, iterations, corpus):
    default = make_model(model_class, corpus, iterations)
    for floor in (None, IBMModel.MIN_PROB):
        explicit = make_model(model_class, corpus, iterations, lexical_floor=floor)
        for target in (*default.trg_vocab, "new"):
            for source in (*default.src_vocab, "new"):
                assert (
                    explicit.translation_table[target][source]
                    == default.translation_table[target][source]
                )


@pytest.mark.parametrize("floor", [None, 0.0, 1e-7])
def test_issue_corpus_first_step(floor, corpus):
    model = IBMModel1(corpus, 1, lexical_floor=floor)
    expected = IBMModel.MIN_PROB if floor is None else floor
    assert model.translation_table["X"]["b"] == expected
    assert model.translation_table["."]["b"] == 0.5
    assert model.translation_table["Z"]["b"] == 0.5
    assert sum(model.translation_table[t]["b"] for t in model.trg_vocab) == 1 + expected


@pytest.mark.parametrize("floor", [0.0, 1e-7, 0.5, 1.0])
def test_m_step_clamps_estimates_and_handles_zero_source_totals(floor):
    model = IBMModel([], lexical_floor=floor)
    model.translation_table["rare"]["unobserved"] = 0.9
    model.translation_table["absent"]["s"] = 0.2
    counts = Counts()
    counts.t_given_s["rare"]["s"] = 0.25
    counts.t_given_s["common"]["s"] = 0.75
    counts.any_t_given_s["s"] = 1.0
    counts.t_given_s["rare"]["zero_total"] = 0.0

    model.maximize_lexical_translation_probabilities(counts)

    assert model.translation_table["rare"]["s"] == max(0.25, floor)
    assert model.translation_table["common"]["s"] == max(0.75, floor)
    assert model.translation_table["rare"]["unobserved"] == floor
    assert model.translation_table["rare"]["zero_total"] == floor
    assert model.translation_table["common"]["zero_total"] == floor
    # A target absent from counts is outside this sparse update.
    assert model.translation_table["absent"]["s"] == 0.2


@pytest.mark.parametrize("model_class", MODELS)
@pytest.mark.parametrize("floor", [None, 0.0, 1e-7])
def test_custom_initialization_preserves_values_and_positional_api(
    model_class, floor, corpus
):
    template = make_model(model_class, corpus, 0)
    probabilities = {
        name: value
        for name, value in vars(template).items()
        if name.endswith("_table") or name == "p1"
    }
    table = defaultdict(lambda: defaultdict(lambda: 0.25))
    table["X"]["a"] = 0.8
    table["Z"]["b"] = 0.0
    probabilities["translation_table"] = table

    model = make_model(model_class, corpus, 0, probabilities, lexical_floor=floor)

    assert model.translation_table["X"]["a"] == 0.8
    assert model.translation_table["Z"]["b"] == 0.0
    if floor is None:
        assert model.translation_table is table
        assert model.translation_table["new"]["b"] == 0.25
    else:
        assert model.translation_table["X"]["new"] == floor
        assert model.translation_table["new"]["b"] == floor
        assert "new" not in table
        assert "new" not in table["X"]
        assert table["X"]["new"] == 0.25


@pytest.mark.parametrize("model_class", [IBMModel1, IBMModel2])
def test_zero_floor_does_not_hide_an_impossible_e_step(model_class, corpus):
    template = model_class(corpus, 0)
    probabilities = {
        "translation_table": defaultdict(lambda: defaultdict(float)),
        "alignment_table": template.alignment_table,
    }
    model = model_class(corpus, 0, probabilities, lexical_floor=0.0)

    with pytest.raises(ZeroDivisionError):
        model.train(corpus)


@pytest.mark.parametrize(
    "floor", [-1.0, 1.01, float("inf"), -float("inf"), float("nan")]
)
def test_invalid_floor_values(floor):
    with pytest.raises(ValueError, match="lexical_floor"):
        IBMModel([], lexical_floor=floor)


@pytest.mark.parametrize("floor", [True, False, "0", 0j, object()])
def test_invalid_floor_types(floor):
    with pytest.raises(TypeError, match="lexical_floor"):
        IBMModel([], lexical_floor=floor)
