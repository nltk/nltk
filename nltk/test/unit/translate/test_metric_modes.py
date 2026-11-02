"""
The "mteval" and "sacrebleu" modes of the translation metrics give the scores
of the reference implementations (_reference_scores.py says how they were
made), and the "nltk" mode and the empty-input rule behave as MetricI says.
"""

import pytest

from nltk.test.unit.translate._reference_scores import CASES, MTEVAL, SACREBLEU
from nltk.translate.bleu_score import SmoothingFunction, corpus_bleu, sentence_bleu
from nltk.translate.chrf_score import corpus_chrf, sentence_chrf
from nltk.translate.gleu_score import corpus_gleu, sentence_gleu
from nltk.translate.metrics import BLEU, CHRF, GLEU, NIST, RIBES
from nltk.translate.nist_score import corpus_nist, sentence_nist
from nltk.translate.ribes_score import corpus_ribes, sentence_ribes

TOL = 1e-9
IDS = list(CASES)
BLEU_SMOOTHING = [
    (s, e) for s in ("none", "exp", "floor", "add-k") for e in (False, True)
]
CHRF_SETTINGS = [(b, s) for b in (2, 3) for s in ("effective-order", "eps")]


def corpus(cid):
    references, hypotheses = zip(*CASES[cid])
    return list(references), list(hypotheses)


@pytest.mark.parametrize("cid", IDS)
@pytest.mark.parametrize("smoothing", ["exp", "none"])
def test_bleu_mteval(cid, smoothing):
    refs, hyps = corpus(cid)
    bleu = BLEU(mode="mteval", smoothing=smoothing)
    expected = MTEVAL[cid]
    assert bleu.corpus_score(refs, hyps) == pytest.approx(
        expected[f"bleu.corpus.{smoothing}"], abs=TOL
    )
    for (r, h), score in zip(CASES[cid], expected[f"bleu.sentence.{smoothing}"]):
        assert bleu.sentence_score(r, h) == pytest.approx(score, abs=TOL)


@pytest.mark.parametrize("cid", IDS)
@pytest.mark.parametrize("smoothing,effective_order", BLEU_SMOOTHING)
def test_bleu_sacrebleu(cid, smoothing, effective_order):
    refs, hyps = corpus(cid)
    bleu = BLEU(mode="sacrebleu", smoothing=smoothing, effective_order=effective_order)
    key = f"{smoothing}.eff" if effective_order else smoothing
    expected = SACREBLEU[cid]
    assert bleu.corpus_score(refs, hyps) == pytest.approx(
        expected[f"bleu.corpus.{key}"], abs=TOL
    )
    for (r, h), score in zip(CASES[cid], expected[f"bleu.sentence.{key}"]):
        assert bleu.sentence_score(r, h) == pytest.approx(score, abs=TOL)


@pytest.mark.parametrize("cid", IDS)
def test_bleu_sacrebleu_defaults_follow_sacrebleu(cid):
    # sacrebleu.corpus_bleu() smooths with exp without effective order,
    # sacrebleu.sentence_bleu() with it
    refs, hyps = corpus(cid)
    bleu, expected = BLEU(mode="sacrebleu"), SACREBLEU[cid]
    assert bleu.corpus_score(refs, hyps) == pytest.approx(
        expected["bleu.corpus.exp"], abs=TOL
    )
    for (r, h), score in zip(CASES[cid], expected["bleu.sentence.exp.eff"]):
        assert bleu.sentence_score(r, h) == pytest.approx(score, abs=TOL)


@pytest.mark.parametrize("cid", IDS)
def test_nist_mteval(cid):
    refs, hyps = corpus(cid)
    expected = MTEVAL[cid]
    for n in (4, 5):
        assert NIST(n, mode="mteval").corpus_score(refs, hyps) == pytest.approx(
            expected[f"nist.corpus.{n}"], abs=TOL
        )
    for (r, h), score in zip(CASES[cid], expected["nist.sentence.5"]):
        assert NIST(mode="mteval").sentence_score(r, h) == pytest.approx(score, abs=TOL)


@pytest.mark.parametrize("cid", IDS)
@pytest.mark.parametrize("beta,smoothing", CHRF_SETTINGS)
def test_chrf_sacrebleu(cid, beta, smoothing):
    refs, hyps = corpus(cid)
    chrf = CHRF(beta=beta, smoothing=smoothing, mode="sacrebleu")
    key = f"beta{beta}.{smoothing}"
    expected = SACREBLEU[cid]
    assert chrf.corpus_score(refs, hyps) == pytest.approx(
        expected[f"chrf.corpus.{key}"], abs=TOL
    )
    for (r, h), score in zip(CASES[cid], expected[f"chrf.sentence.{key}"]):
        assert chrf.sentence_score(r, h) == pytest.approx(score, abs=TOL)


@pytest.mark.parametrize("cid", IDS)
def test_chrf_sentences_agree_across_modes(cid):
    # one reference, beta 3 and eps: sentence_chrf() is sacrebleu's sentence chrF
    for refs, hyp in CASES[cid]:
        assert sentence_chrf(refs[0], hyp) == pytest.approx(
            CHRF(beta=3, smoothing="eps", mode="sacrebleu").sentence_score(
                refs[:1], hyp
            ),
            abs=TOL,
        )


def test_the_functions_are_the_nltk_mode():
    refs, hyps = corpus("C03_paper_corpus")
    method3 = SmoothingFunction().method3
    assert corpus_bleu(refs, hyps, smoothing_function=method3) == BLEU(
        smoothing="exp"
    ).corpus_score(refs, hyps)
    assert sentence_bleu(refs[0], hyps[0]) == BLEU().sentence_score(refs[0], hyps[0])
    assert corpus_nist(refs, hyps) == NIST().corpus_score(refs, hyps)
    assert sentence_nist(refs[0], hyps[0]) == NIST().sentence_score(refs[0], hyps[0])
    firsts = [r[0] for r in refs]
    assert corpus_chrf(firsts, hyps) == CHRF().corpus_score([[f] for f in firsts], hyps)
    assert corpus_gleu(refs, hyps) == GLEU().corpus_score(refs, hyps)
    assert sentence_gleu(refs[0], hyps[0]) == GLEU().sentence_score(refs[0], hyps[0])
    assert corpus_ribes(refs, hyps) == RIBES().corpus_score(refs, hyps)
    assert sentence_ribes(refs[0], hyps[0]) == RIBES().sentence_score(refs[0], hyps[0])


def test_nltk_bleu_names_its_smoothing_methods():
    refs, hyps = corpus("C08_no_4gram_match")
    sf = SmoothingFunction()
    for name, method in (
        ("none", sf.method0),
        ("floor", sf.method1),
        ("add-k", sf.method2),
        ("exp", sf.method3),
    ):
        assert BLEU(smoothing=name).corpus_score(refs, hyps) == corpus_bleu(
            refs, hyps, smoothing_function=method
        )
    assert BLEU(smoothing="method7").corpus_score(refs, hyps) == corpus_bleu(
        refs, hyps, smoothing_function=sf.method7
    )


METRICS = {
    "BLEU-nltk": lambda **kw: BLEU(**kw),
    "BLEU-mteval": lambda **kw: BLEU(mode="mteval", **kw),
    "BLEU-sacrebleu": lambda **kw: BLEU(mode="sacrebleu", **kw),
    "NIST-nltk": lambda **kw: NIST(**kw),
    "NIST-mteval": lambda **kw: NIST(mode="mteval", **kw),
    "CHRF-nltk": lambda **kw: CHRF(**kw),
    "CHRF-sacrebleu": lambda **kw: CHRF(mode="sacrebleu", **kw),
    "GLEU-nltk": lambda **kw: GLEU(**kw),
    "RIBES-nltk": lambda **kw: RIBES(**kw),
}


@pytest.mark.parametrize("make", METRICS.values(), ids=METRICS.keys())
def test_an_empty_corpus_raises_unless_asked_for_zero(make):
    with pytest.raises(ValueError, match="the corpus is empty"):
        make().corpus_score([], [])
    assert make(on_empty="zero").corpus_score([], []) == 0.0


@pytest.mark.parametrize("make", METRICS.values(), ids=METRICS.keys())
def test_a_hypothesis_without_references_raises_unless_asked_for_zero(make):
    with pytest.raises(ValueError, match="a hypothesis has no references"):
        make().sentence_score([], ["a", "cat"])
    assert make(on_empty="zero").sentence_score([], ["a", "cat"]) == 0.0


@pytest.mark.parametrize("make", METRICS.values(), ids=METRICS.keys())
def test_different_numbers_of_references_and_hypotheses_raise(make):
    with pytest.raises(ValueError, match="number of reference sets"):
        make().corpus_score([[["a"]]], [["a"], ["b"]])


@pytest.mark.parametrize(
    "function",
    [corpus_bleu, corpus_nist, corpus_chrf, corpus_gleu, corpus_ribes],
    ids=lambda f: f.__name__,
)
def test_the_functions_take_on_empty(function):
    with pytest.raises(ValueError, match="the corpus is empty"):
        function([], [])
    assert function([], [], on_empty="zero") == 0.0


@pytest.mark.parametrize(
    "metric",
    [
        BLEU(mode="mteval"),
        BLEU(mode="sacrebleu"),
        NIST(mode="mteval"),
        CHRF(mode="sacrebleu"),
        GLEU(),
        RIBES(),
    ],
    ids=lambda m: f"{type(m).__name__}-{m.mode}",
)
def test_an_empty_hypothesis_is_scored_zero(metric):
    assert metric.sentence_score([["the", "cat"]], []) == 0.0


def test_nltk_nist_names_the_order_it_cannot_score():
    with pytest.raises(ValueError, match="no 3-grams to score.*mode='mteval'"):
        sentence_nist([["the", "cat", "sat"]], ["the", "cat"])
    assert (
        NIST(mode="mteval").sentence_score([["the", "cat", "sat"]], ["the", "cat"]) > 0
    )


@pytest.mark.parametrize(
    "make",
    [
        lambda: BLEU(mode="moses"),
        lambda: BLEU(on_empty="maybe"),
        lambda: BLEU(effective_order=True),
        lambda: BLEU(smoothing="method8"),
        lambda: BLEU(mode="mteval", weights=(0.5, 0.3, 0.2)),
        lambda: BLEU(mode="mteval", weights=[(0.5, 0.5), (1,)]),
        lambda: BLEU(mode="mteval", smoothing="floor"),
        lambda: BLEU(mode="mteval", effective_order=True),
        lambda: BLEU(mode="sacrebleu", smoothing="method4"),
        lambda: BLEU(mode="sacrebleu", brevity_penalty="shortest"),
        lambda: BLEU(mode="sacrebleu", auto_reweigh=True),
        lambda: BLEU(mode="mteval", brevity_penalty="longest"),
        lambda: NIST(mode="sacrebleu"),
        lambda: CHRF(min_len=4, max_len=3),
        lambda: CHRF(smoothing="effective-order"),
        lambda: CHRF(mode="sacrebleu", min_len=2),
        lambda: CHRF(mode="sacrebleu", smoothing="exp"),
        lambda: GLEU(mode="sacrebleu"),
        lambda: RIBES(mode="mteval"),
    ],
)
def test_settings_a_mode_does_not_have_are_refused(make):
    with pytest.raises(ValueError):
        make()


def test_nltk_chrf_takes_one_reference():
    with pytest.raises(ValueError, match="one reference per hypothesis"):
        CHRF().sentence_score([["a", "cat"], ["the", "cat"]], ["a", "cat"])


def test_mteval_brevity_penalty_closest_and_shortest():
    # mteval-v14.pl -c -b with --brevity-penalty closest gives 0.846481724891
    # (the 7-word reference), with shortest 1.0 (the 4-word one)
    refs = ["the cat sat on".split(), "the cat sat on the mat today".split()]
    hyp = "the cat sat on the mat".split()
    assert BLEU(mode="mteval").sentence_score(refs, hyp) == pytest.approx(
        0.846481724891, abs=TOL
    )
    assert BLEU(mode="mteval", brevity_penalty="shortest").sentence_score(
        refs, hyp
    ) == pytest.approx(1.0, abs=TOL)


def test_mteval_nist_divides_a_single_ngram_order_by_one():
    # "the cat sat" is the only trigram of the hypothesis and carries one bit
    # ("the cat" occurs twice in the references, "the cat sat" once);
    # mteval-v14.pl -c gives 3.418295834054 from order 3 on
    refs = ["the cat sat".split(), "the cat ran".split()]
    for n in (3, 5):
        assert NIST(n, mode="mteval").sentence_score(
            refs, "the cat sat".split()
        ) == pytest.approx(3.418295834054, abs=TOL)


def test_sacrebleu_chrf_reference_without_ngrams_of_an_order():
    # "cat" has no character 4- to 6-grams, so sacrebleu counts none for the
    # hypothesis either, which shows in the corpus totals; sacrebleu 2.6.0
    # CHRF().sentence_score and corpus_score give these
    hyp, refs = "the cat sat on the mat".split(), [["cat"]]
    for kwargs, score in (
        ({}, 0.41155195089872865),
        ({"smoothing": "eps"}, 0.19951099011897558),
        ({"beta": 3, "smoothing": "eps"}, 0.28112002376708256),
    ):
        assert CHRF(mode="sacrebleu", **kwargs).sentence_score(
            refs, hyp
        ) == pytest.approx(score, abs=TOL)
    hyps = [hyp, "a dog ran in the park".split()]
    list_of_refs = [refs, ["the dog ran in a park".split()]]
    for kwargs, score in (
        ({}, 0.5431847160208403),
        ({"smoothing": "eps"}, 0.5346711934177145),
    ):
        assert CHRF(mode="sacrebleu", **kwargs).corpus_score(
            list_of_refs, hyps
        ) == pytest.approx(score, abs=TOL)
