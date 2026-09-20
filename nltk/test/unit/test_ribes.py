import pytest

from nltk.translate.ribes_score import (
    corpus_ribes,
    kendall_tau,
    sentence_ribes,
    word_rank_alignment,
)


def test_ribes_empty_worder():  # worder as in word order
    # Verifies that these two sentences have no alignment,
    # and hence have the lowest possible RIBES score.
    hyp = "This is a nice sentence which I quite like".split()
    ref = "Okay well that's neat and all but the reference's different".split()

    assert word_rank_alignment(ref, hyp) == []

    list_of_refs = [[ref]]
    hypotheses = [hyp]
    assert corpus_ribes(list_of_refs, hypotheses) == 0.0


def test_ribes_empty_hypothesis():
    refs = [["a"], ["b"]]

    assert sentence_ribes(refs, []) == 0.0
    assert corpus_ribes([refs], [[]]) == 0.0


def test_ribes_empty_references():
    assert sentence_ribes([], ["a"]) == 0.0


def test_ribes_empty_corpus():
    assert corpus_ribes([], []) == 0.0


def test_ribes_rejects_mismatched_corpus_lengths():
    with pytest.raises(ValueError, match="number of reference sets"):
        corpus_ribes([[["a"]]], [["a"], ["b"]])


def test_ribes_one_worder():
    # Verifies that these two sentences have just one match,
    # and the RIBES score for this sentence with very little
    # correspondence is 0.
    hyp = "This is a nice sentence which I quite like".split()
    ref = "Okay well that's nice and all but the reference's different".split()

    assert word_rank_alignment(ref, hyp) == [3]

    list_of_refs = [[ref]]
    hypotheses = [hyp]
    assert corpus_ribes(list_of_refs, hypotheses) == 0.0


def test_ribes_two_worder():
    # Verifies that these two sentences have two matches,
    # but still get the lowest possible RIBES score due
    # to the lack of similarity.
    hyp = "This is a nice sentence which I quite like".split()
    ref = "Okay well that's nice and all but the reference is different".split()

    assert word_rank_alignment(ref, hyp) == [9, 3]

    list_of_refs = [[ref]]
    hypotheses = [hyp]
    assert corpus_ribes(list_of_refs, hypotheses) == 0.0


def test_ribes():
    # Based on the doctest of the corpus_ribes function
    hyp1 = [
        "It",
        "is",
        "a",
        "guide",
        "to",
        "action",
        "which",
        "ensures",
        "that",
        "the",
        "military",
        "always",
        "obeys",
        "the",
        "commands",
        "of",
        "the",
        "party",
    ]
    ref1a = [
        "It",
        "is",
        "a",
        "guide",
        "to",
        "action",
        "that",
        "ensures",
        "that",
        "the",
        "military",
        "will",
        "forever",
        "heed",
        "Party",
        "commands",
    ]
    ref1b = [
        "It",
        "is",
        "the",
        "guiding",
        "principle",
        "which",
        "guarantees",
        "the",
        "military",
        "forces",
        "always",
        "being",
        "under",
        "the",
        "command",
        "of",
        "the",
        "Party",
    ]
    ref1c = [
        "It",
        "is",
        "the",
        "practical",
        "guide",
        "for",
        "the",
        "army",
        "always",
        "to",
        "heed",
        "the",
        "directions",
        "of",
        "the",
        "party",
    ]

    hyp2 = [
        "he",
        "read",
        "the",
        "book",
        "because",
        "he",
        "was",
        "interested",
        "in",
        "world",
        "history",
    ]
    ref2a = [
        "he",
        "was",
        "interested",
        "in",
        "world",
        "history",
        "because",
        "he",
        "read",
        "the",
        "book",
    ]

    list_of_refs = [[ref1a, ref1b, ref1c], [ref2a]]
    hypotheses = [hyp1, hyp2]

    score = corpus_ribes(list_of_refs, hypotheses)

    assert round(score, 4) == 0.633


def test_no_zero_div():
    # Regression test for Issue 2529, assure that no ZeroDivisionError is thrown.
    hyp1 = [
        "It",
        "is",
        "a",
        "guide",
        "to",
        "action",
        "which",
        "ensures",
        "that",
        "the",
        "military",
        "always",
        "obeys",
        "the",
        "commands",
        "of",
        "the",
        "party",
    ]
    ref1a = [
        "It",
        "is",
        "a",
        "guide",
        "to",
        "action",
        "that",
        "ensures",
        "that",
        "the",
        "military",
        "will",
        "forever",
        "heed",
        "Party",
        "commands",
    ]
    ref1b = [
        "It",
        "is",
        "the",
        "guiding",
        "principle",
        "which",
        "guarantees",
        "the",
        "military",
        "forces",
        "always",
        "being",
        "under",
        "the",
        "command",
        "of",
        "the",
        "Party",
    ]
    ref1c = [
        "It",
        "is",
        "the",
        "practical",
        "guide",
        "for",
        "the",
        "army",
        "always",
        "to",
        "heed",
        "the",
        "directions",
        "of",
        "the",
        "party",
    ]

    hyp2 = ["he", "read", "the"]
    ref2a = ["he", "was", "interested", "in", "world", "history", "because", "he"]

    list_of_refs = [[ref1a, ref1b, ref1c], [ref2a]]
    hypotheses = [hyp1, hyp2]

    score = corpus_ribes(list_of_refs, hypotheses)

    assert round(score, 4) == 0.4421


def test_word_rank_alignment_unhashable_tokens():
    # Tokens need not be hashable: word_rank_alignment must still work when
    # tokens are e.g. lists (the previous list.count implementation relied only
    # on equality). Regression for the memoisation introduced with the KMP
    # rewrite, which must fall back to an uncached count for unhashable tokens
    # rather than raise TypeError.
    ref = [["b"], ["a"], ["b"], ["a"]]
    hyp = [["a"], ["b"], ["a"], ["b"]]
    # Should not raise; result matches the equivalent hashable (string) tokens.
    assert word_rank_alignment(ref, hyp) == word_rank_alignment(
        ["b", "a", "b", "a"], ["a", "b", "a", "b"]
    )


def test_kendall_tau_counts_all_increasing_pairs():
    # (H1, R1) from Isozaki et al. 2010. "Bob hit John yesterday" against
    # "John hit Bob yesterday" gives the ranks [2, 1, 0, 3]. The pairs (2, 3),
    # (1, 3) and (0, 3) are increasing, so tau = 2 * 3 / 6 - 1 = 0.0 and the
    # normalised score is 0.5. The ranks 2 and 3 are not adjacent in the list,
    # so this used to be scored as if no pair were increasing.
    assert kendall_tau([2, 1, 0, 3], normalize=False) == 0.0
    assert kendall_tau([2, 1, 0, 3]) == 0.5


def test_kendall_tau_increasing_ranks_with_gaps():
    # Words in the right order are fully ordered even when their ranks are not
    # consecutive integers.
    assert kendall_tau([0, 2]) == 1.0
    assert kendall_tau([0, 2, 4, 6]) == 1.0
    # 4 of the 6 pairs are increasing.
    assert kendall_tau([1, 0, 3, 2]) == pytest.approx(2 / 3)


def test_kendall_tau_extremes():
    assert kendall_tau([0, 1, 2, 3]) == 1.0
    assert kendall_tau([0, 1, 2, 3], normalize=False) == 1.0
    assert kendall_tau([3, 2, 1, 0]) == 0.0
    assert kendall_tau([3, 2, 1, 0], normalize=False) == -1.0


def test_ribes_paper_h1_example():
    # NKT is 0.5, the unigram precision is 1.0 and there is no brevity penalty,
    # so the sentence level RIBES is 0.5.
    ref = "John hit Bob yesterday".split()
    hyp = "Bob hit John yesterday".split()
    assert sentence_ribes([ref], hyp) == 0.5
