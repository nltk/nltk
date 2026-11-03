"""
One smoothing interface for the translation metrics: smooth_counts() in
nltk.translate.api, its methods named the same in every metric that combines
granularities (BLEU, NIST, CHRF, GLEU), "none" only for the others.
"""

import math
import warnings

import pytest

from nltk.test.unit.translate._reference_scores_ter_wer_rouge import RAW, TOOLS
from nltk.translate.api import SMOOTHING, smooth_counts
from nltk.translate.bleu_score import SmoothingFunction, sentence_bleu
from nltk.translate.chrf_score import corpus_chrf, sentence_chrf
from nltk.translate.gleu_score import corpus_gleu, sentence_gleu
from nltk.translate.metrics import (
    BLEU,
    CHRF,
    GLEU,
    LEPOR,
    METEOR,
    NIST,
    RIBES,
    ROUGE,
    TER,
    WER,
)
from nltk.translate.nist_score import corpus_nist, sentence_nist

REFERENCE = "the cat sat on the mat".split()
SCRAMBLED = "mat the on sat cat the".split()  # unigrams match, nothing longer


def test_smooth_counts_touches_only_orders_without_matches():
    counts = [(1, 3, 4, 5), (2, 0, 3, 4), (3, 0, 0, 3), (4, 0, 2, None)]
    # an order without hypothesis n-grams has nothing to smooth
    assert smooth_counts(counts, "floor", 0.5) == [
        (1, 3, 4, 5),
        (2, 0.5, 3, 4),
        (3, 0, 0, 3),
        (4, 0.5, 2, None),
    ]
    assert smooth_counts(counts, "exp") == [
        (1, 3, 4, 5),
        (2, 0.5, 3, 4),
        (3, 0, 0, 3),
        (4, 0.25, 2, None),
    ]
    # add-k adds to every order above 1, matched or not, and keeps None
    assert smooth_counts(counts, "add-k", 2) == [
        (1, 3, 4, 5),
        (2, 2, 5, 6),
        (3, 2, 2, 5),
        (4, 2, 4, None),
    ]
    assert smooth_counts(counts, "none") == counts
    with pytest.raises(ValueError, match="smoothing is one of"):
        smooth_counts(counts, "laplace")


def test_bleu_names_are_its_smoothing_methods():
    warnings.simplefilter("ignore")
    hyp = "the cat sat in a mat".split()
    for name, method in (
        ("floor", SmoothingFunction().method1),
        ("add-k", SmoothingFunction().method2),
        ("exp", SmoothingFunction().method3),
    ):
        assert BLEU(smoothing=name).sentence_score([REFERENCE], hyp) == sentence_bleu(
            [REFERENCE], hyp, smoothing_function=method
        )
    floor = SmoothingFunction(epsilon=0.01).method1
    assert BLEU(smoothing="floor", smooth_value=0.01).sentence_score(
        [REFERENCE], hyp
    ) == sentence_bleu([REFERENCE], hyp, smoothing_function=floor)
    # add-k with another k, as sacrebleu's add-k
    assert BLEU(smoothing="add-k", smooth_value=2).sentence_score(
        [REFERENCE], hyp
    ) == pytest.approx(
        BLEU(mode="sacrebleu", smoothing="add-k", smooth_value=2).sentence_score(
            [REFERENCE], hyp
        )
    )
    with pytest.raises(ValueError, match='value of "floor" or "add-k"'):
        BLEU(smoothing="exp", smooth_value=2)


def test_smoothing_rescues_bleu_from_its_missing_orders():
    warnings.simplefilter("ignore")
    # without matches of orders 2 to 4 the geometric mean is all but 0
    # (NLTK takes the log of sys.float_info.min for a zero precision)
    assert BLEU().sentence_score([REFERENCE], SCRAMBLED) < 1e-200
    # 6 of 6 unigrams; orders 2 to 4 smoothed over 5, 4 and 3 n-grams
    p1, ngrams = 1.0, (5, 4, 3)
    expected = {
        "floor": [0.1 / n for n in ngrams],
        "add-k": [1 / (n + 1) for n in ngrams],
        "exp": [1 / (2**k * n) for k, n in enumerate(ngrams, 1)],
    }
    for name, precisions in expected.items():
        geometric = math.exp(sum(map(math.log, [p1] + precisions)) / 4)
        assert BLEU(smoothing=name).sentence_score(
            [REFERENCE], SCRAMBLED
        ) == pytest.approx(geometric)


def test_nist_smooths_each_order():
    plain = NIST().sentence_score([REFERENCE], SCRAMBLED)
    # orders 2 to 5 have 5, 4, 3 and 2 hypothesis n-grams and no matches
    assert NIST(smoothing="exp").sentence_score([REFERENCE], SCRAMBLED) == (
        pytest.approx(plain + 0.5 / 5 + 0.25 / 4 + 0.125 / 3 + 0.0625 / 2)
    )
    assert NIST(smoothing="floor", smooth_value=0.2).sentence_score(
        [REFERENCE], SCRAMBLED
    ) == pytest.approx(plain + 0.2 / 5 + 0.2 / 4 + 0.2 / 3 + 0.2 / 2)
    assert NIST(smoothing="none").sentence_score([REFERENCE], SCRAMBLED) == plain
    assert sentence_nist([REFERENCE], SCRAMBLED, smoothing="exp") == NIST(
        smoothing="exp"
    ).sentence_score([REFERENCE], SCRAMBLED)


def test_nist_add_k_gives_every_order_above_1_something_to_divide_by():
    short = ["the", "cat"]
    with pytest.raises(ValueError, match="no 3-grams"):
        NIST().sentence_score([REFERENCE], short)
    with pytest.raises(ValueError, match="no 3-grams"):
        NIST(smoothing="exp").sentence_score([REFERENCE], short)
    assert NIST(smoothing="add-k").sentence_score([REFERENCE], short) > 0
    with pytest.raises(ValueError, match="does not smooth NIST"):
        NIST(mode="mteval", smoothing="exp")


def test_gleu_smooths_each_order_before_pooling():
    # 6 unigram matches; 1/2, 1/4 and 1/8 for orders 2 to 4; 6 + 5 + 4 + 3 n-grams
    assert GLEU(smoothing="exp").sentence_score([REFERENCE], SCRAMBLED) == (
        pytest.approx((6 + 0.5 + 0.25 + 0.125) / 18)
    )
    assert GLEU(smoothing="add-k").sentence_score([REFERENCE], SCRAMBLED) == (
        pytest.approx((6 + 3) / (18 + 3))
    )
    assert GLEU(smoothing="none").sentence_score([REFERENCE], SCRAMBLED) == 6 / 18
    refs, hyps = [[REFERENCE], [REFERENCE]], [SCRAMBLED, REFERENCE]
    assert corpus_gleu(refs, hyps, smoothing="floor") == GLEU(
        smoothing="floor"
    ).corpus_score(refs, hyps)
    assert sentence_gleu([REFERENCE], SCRAMBLED, smoothing="exp") == GLEU(
        smoothing="exp"
    ).sentence_score([REFERENCE], SCRAMBLED)


@pytest.mark.parametrize(
    "cid",
    [
        c
        for c in TOOLS
        if "chrf++.py" in TOOLS[c] and all(len(refs) == 1 for refs, _ in RAW[c])
    ],
)
def test_chrf_without_smoothing_is_chrfpp_py(cid):
    # chrF++.py scores an order without matches 0, the "none" smoothing
    references, hypotheses = zip(*RAW[cid])
    metric = CHRF(beta=2, word_order=2, smoothing="none")
    expected = TOOLS[cid]["chrf++.py"]
    assert metric.corpus_score(list(references), list(hypotheses)) == pytest.approx(
        expected["corpus_avg"], abs=1e-12
    )
    for refs, hyp, value in zip(references, hypotheses, expected["segment"]):
        assert metric.sentence_score(refs, hyp) == pytest.approx(value, abs=1e-12)


def test_chrf_smooths_each_character_and_word_order():
    beta = 3.0
    # the word bigrams of the scrambled sentence: 5 hypothesis, 5 reference,
    # none matched; "floor" lets them match 0.1
    floor = CHRF(word_order=2, smoothing="floor").sentence_score([REFERENCE], SCRAMBLED)
    plain = CHRF(word_order=2, smoothing="none").sentence_score([REFERENCE], SCRAMBLED)
    p = r = 0.1 / 5
    word_bigram = (1 + beta**2) * p * r / (beta**2 * p + r)
    # the character orders without matches are smoothed too: floor >= plain + that
    assert floor >= plain + word_bigram / 8 - 1e-12
    assert CHRF().sentence_score([REFERENCE], SCRAMBLED) == CHRF(
        smoothing="eps"
    ).sentence_score([REFERENCE], SCRAMBLED)
    assert sentence_chrf(REFERENCE, SCRAMBLED, smoothing="exp") == CHRF(
        smoothing="exp"
    ).sentence_score([REFERENCE], SCRAMBLED)
    assert corpus_chrf([REFERENCE], [SCRAMBLED], smoothing="add-k") == CHRF(
        smoothing="add-k"
    ).corpus_score([[REFERENCE]], [SCRAMBLED])
    with pytest.raises(ValueError, match="nltk mode smooths"):
        CHRF(smoothing="laplace")


@pytest.mark.parametrize(
    "make",
    [
        lambda **kw: BLEU(**kw),
        lambda **kw: NIST(**kw),
        lambda **kw: CHRF(**kw),
        lambda **kw: GLEU(**kw),
        lambda **kw: ROUGE(**kw),
        lambda **kw: METEOR(**kw),
        lambda **kw: LEPOR(**kw),
        lambda **kw: RIBES(**kw),
        lambda **kw: TER(**kw),
        lambda **kw: WER(**kw),
    ],
    ids=[
        "BLEU",
        "NIST",
        "CHRF",
        "GLEU",
        "ROUGE",
        "METEOR",
        "LEPOR",
        "RIBES",
        "TER",
        "WER",
    ],
)
def test_every_metric_takes_the_smoothing_keyword(make):
    make(smoothing="none")
    make(smoothing=None)


@pytest.mark.parametrize(
    "make", [ROUGE, METEOR, LEPOR, RIBES, TER, WER], ids=lambda m: m.__name__
)
@pytest.mark.parametrize("smoothing", [s for s in SMOOTHING if s != "none"])
def test_metrics_of_one_granularity_refuse_smoothing(make, smoothing):
    with pytest.raises(ValueError, match='takes smoothing "none"'):
        make(smoothing=smoothing)


@pytest.mark.parametrize("smoothing", SMOOTHING)
def test_smoothing_is_never_worse_than_none_on_a_scrambled_sentence(smoothing):
    # smoothing only adds matches, so it never lowers a score of matches
    for make in (NIST, GLEU, lambda **kw: CHRF(word_order=2, **kw)):
        smoothed = make(smoothing=smoothing).sentence_score([REFERENCE], SCRAMBLED)
        plain = make(smoothing="none").sentence_score([REFERENCE], SCRAMBLED)
        assert smoothed >= plain or math.isclose(smoothed, plain)
