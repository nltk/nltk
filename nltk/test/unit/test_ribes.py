import pytest

from nltk.translate.ribes_score import corpus_ribes, sentence_ribes, word_rank_alignment


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

    assert round(score, 4) == 0.3597


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

    assert round(score, 4) == 0.1688


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
