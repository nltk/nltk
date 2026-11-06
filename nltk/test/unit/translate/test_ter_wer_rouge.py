"""
TER, WER, chrF++ and ROUGE give the scores of their canonical
implementations (_reference_scores_ter_wer_rouge.py says how they were made):
tercom and sacrebleu for TER, jiwer and sclite for WER, chrF++.py and
sacrebleu for chrF++, rouge-score and ROUGE-1.5.5.pl for ROUGE.
"""

import pytest

from nltk.metrics import distance
from nltk.test.unit.translate._reference_scores_ter_wer_rouge import (
    CASES,
    RAW,
    TOOLS,
)
from nltk.translate.chrf_score import CHRF, corpus_chrf, sentence_chrf
from nltk.translate.rouge_score import ROUGE, corpus_rouge, sentence_rouge
from nltk.translate.ter_score import TER, corpus_ter, sentence_ter
from nltk.translate.wer_score import WER, corpus_wer, sentence_wer

TOL = 1e-9
IDS = list(CASES)
SINGLE = [cid for cid in IDS if all(len(refs) == 1 for refs, _ in CASES[cid])]


def corpus(cid, first_only=False):
    references, hypotheses = zip(*CASES[cid])
    if first_only:
        references = [refs[:1] for refs in references]
    return list(references), list(hypotheses)


def raw(cid):
    references, hypotheses = zip(*RAW[cid])
    return list(references), list(hypotheses)


def check(metric, references, hypotheses, expected):
    assert metric.corpus_score(references, hypotheses) == pytest.approx(
        expected["corpus"], abs=TOL
    )
    for refs, hyp, value in zip(references, hypotheses, expected["segment"]):
        assert metric.sentence_score(refs, hyp) == pytest.approx(value, abs=TOL)


@pytest.mark.parametrize("cid", IDS)
def test_ter_is_tercom(cid):
    check(TER(), *corpus(cid), TOOLS[cid]["tercom"])


@pytest.mark.parametrize("cid", IDS)
def test_ter_sacrebleu_mode_is_sacrebleu(cid):
    check(TER(mode="sacrebleu"), *corpus(cid), TOOLS[cid]["sacrebleu.ter"])


@pytest.mark.parametrize("cid", IDS)
def test_wer_is_jiwer(cid):
    check(WER(), *corpus(cid, first_only=True), TOOLS[cid]["jiwer"])


@pytest.mark.parametrize("cid", IDS)
def test_wer_sclite_mode_is_sclite(cid):
    check(WER(mode="sclite"), *corpus(cid, first_only=True), TOOLS[cid]["sclite"])


@pytest.mark.parametrize("smoothing", ["effective-order", "eps"])
@pytest.mark.parametrize("cid", IDS)
def test_chrfpp_sacrebleu_mode_is_sacrebleu(cid, smoothing):
    key = "sacrebleu.chrf++.eps" if smoothing == "eps" else "sacrebleu.chrf++"
    metric = CHRF(word_order=2, smoothing=smoothing, mode="sacrebleu")
    check(metric, *raw(cid), TOOLS[cid][key])


@pytest.mark.parametrize("cid", [c for c in SINGLE if "chrf++.py" in TOOLS[c]])
def test_chrfpp_is_chrfpp_py(cid):
    # chrF++.py's sentence scores, and its "avgF" line, their mean
    references, hypotheses = raw(cid)
    expected = TOOLS[cid]["chrf++.py"]
    metric = CHRF(beta=2, word_order=2)
    assert metric.corpus_score(references, hypotheses) == pytest.approx(
        expected["corpus_avg"], abs=TOL
    )
    for refs, hyp, value in zip(references, hypotheses, expected["segment"]):
        assert metric.sentence_score(refs, hyp) == pytest.approx(value, abs=TOL)


@pytest.mark.parametrize("measure", ["f", "precision", "recall"])
@pytest.mark.parametrize("variant", [1, 2, "L"])
@pytest.mark.parametrize("cid", IDS)
def test_rouge_is_rouge_score(cid, variant, measure):
    expected = TOOLS[cid][f"rouge-score.{variant}.{measure}"]
    check(ROUGE(variant, measure), *corpus(cid), expected)


@pytest.mark.parametrize("measure", ["f", "precision", "recall"])
@pytest.mark.parametrize("variant", [1, 2, "L"])
@pytest.mark.parametrize("cid", IDS)
def test_rouge_155_mode_is_rouge_155(cid, variant, measure):
    expected = TOOLS[cid][f"rouge-1.5.5.{variant}.{measure}"]
    check(ROUGE(variant, measure, mode="rouge-1.5.5"), *corpus(cid), expected)


def test_tercom_and_sacrebleu_find_different_shifts():
    # a long scrambled segment: sacrebleu's beam and shift ranking find
    # shifts that tercom's do not
    references, hypotheses = corpus("T06_long_scrambled")
    nltk_ter = TER().corpus_score(references, hypotheses)
    sacrebleu_ter = TER(mode="sacrebleu").corpus_score(references, hypotheses)
    assert nltk_ter == pytest.approx(TOOLS["T06_long_scrambled"]["tercom"]["corpus"])
    assert sacrebleu_ter < nltk_ter


def test_sclite_counts_more_edits_than_the_fewest():
    reference, hypothesis = "a a a b b".split(), "b b c c c".split()
    assert WER().sentence_score([reference], hypothesis) == 1.0
    assert WER(mode="sclite").sentence_score([reference], hypothesis) == 1.2


def test_the_functions_are_the_nltk_mode():
    references, hypotheses = corpus("T08_corpus_mix")
    for function, metric in (
        (corpus_ter, TER()),
        (corpus_wer, WER()),
        (corpus_rouge, ROUGE()),
    ):
        assert function(references, hypotheses) == metric.corpus_score(
            references, hypotheses
        )
    refs, hyp = references[1], hypotheses[1]
    assert sentence_ter(refs, hyp) == TER().sentence_score(refs, hyp)
    assert sentence_wer(refs, hyp) == WER().sentence_score(refs, hyp)
    assert sentence_rouge(refs, hyp, "L") == ROUGE("L").sentence_score(refs, hyp)
    raw_refs, raw_hyps = raw("T08_corpus_mix")
    assert corpus_chrf([r[0] for r in raw_refs], raw_hyps, word_order=2) == CHRF(
        word_order=2
    ).corpus_score(raw_refs, raw_hyps)
    assert sentence_chrf(raw_refs[0][0], raw_hyps[0], word_order=2) == CHRF(
        word_order=2
    ).sentence_score(raw_refs[0], raw_hyps[0])


def test_error_rates_score_an_empty_hypothesis_one():
    # every reference word is deleted
    for metric in (TER(), TER(mode="sacrebleu"), WER(), WER(mode="sclite")):
        assert metric.sentence_score([["the", "cat"]], []) == 1.0
    assert ROUGE().sentence_score([["the", "cat"]], []) == 0.0


@pytest.mark.parametrize(
    "make", [TER, lambda: TER(mode="sacrebleu"), WER, lambda: WER(mode="sclite")]
)
def test_references_without_words_have_nothing_to_divide_by(make):
    metric = make()
    if getattr(metric, "mode", None) == "sacrebleu":
        assert metric.sentence_score([[]], ["a"]) == 1.0
        assert metric.sentence_score([[]], []) == 0.0
    else:
        with pytest.raises(ValueError, match="no"):
            metric.sentence_score([[]], ["a"])


@pytest.mark.parametrize(
    "score",
    [
        lambda r, h: TER().sentence_score([r], h),
        lambda r, h: TER(mode="sacrebleu").sentence_score([r], h),
        lambda r, h: WER().sentence_score([r], h),
        lambda r, h: WER(mode="sclite").sentence_score([r], h),
        lambda r, h: ROUGE("L").sentence_score([r], h),
    ],
    ids=["ter", "ter-sacrebleu", "wer", "wer-sclite", "rouge-l"],
)
def test_quadratic_metrics_refuse_inputs_past_the_distance_bound(score):
    # the edit distances and the LCS are quadratic in the lengths: they keep
    # the bound of nltk.metrics.distance
    long = ["w"] * (distance.MAX_DISTANCE_INPUT_LEN + 1)
    with pytest.raises(ValueError, match="MAX_DISTANCE_INPUT_LEN"):
        score(["a", "b"], long)
    with pytest.raises(ValueError, match="MAX_DISTANCE_INPUT_LEN"):
        score(long, ["a", "b"])
