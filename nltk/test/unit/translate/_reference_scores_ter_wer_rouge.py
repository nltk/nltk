# Natural Language Toolkit: reference scores of TER, WER, chrF++ and ROUGE
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Scores of 33 small corpora by the canonical implementations of TER,
WER, chrF++ and ROUGE, for the modes of the metrics in nltk.translate. The
M_ corpora are random pairs on which a wider or narrower beam (tercom's 20,
sacrebleu's 25) or sacrebleu's ranking of shifts decides the score.

  tercom        tercom 0.8.0 (github.com/jhclark/tercom e413d077, the 0.7.25
                algorithm), java ter.TER -s
  sacrebleu.*   sacrebleu 2.6.0: TER(case_sensitive=True); CHRF(word_order=2),
                with eps_smoothing=True for ".eps"
  chrf++.py     chrF++.py (github.com/m-popovic/chrF 6d3c384c), -nc 6 -nw 2 -b 2,
                printing 12 decimals; it fails on C09 and C10, where a segment
                scores 0 against every reference, so they have no entry
  jiwer         jiwer 4.0.0, the first reference
  sclite        sclite 2.10 (SCTK 2.4.12), the first reference
  rouge-score   rouge-score 0.1.2, score_multi, the tokens as given
  rouge-1.5.5   ROUGE-1.5.5.pl -n 2 -f A -p 0.5, printing 17 significant digits
                instead of five decimals; "corpus" is the mean of its per-
                evaluation scores (the script prints a bootstrap estimate)

tercom, sclite and ROUGE-1.5.5.pl read each distinct token as an ASCII id,
so their lowercasing and ASCII-only token filters do not change what they
compare. Scores are on the 0 to 1 scale.

CASES: each corpus as (references, hypothesis) pairs of tokens; RAW: the same
as text, which chrF++ reads.
"""

CASES = {
    "C01_paper_h1_3refs": [
        (
            [
                [
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
                ],
                [
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
                ],
                [
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
                ],
            ],
            [
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
            ],
        )
    ],
    "C02_paper_h2_3refs": [
        (
            [
                [
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
                ],
                [
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
                ],
                [
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
                ],
            ],
            [
                "It",
                "is",
                "to",
                "insure",
                "the",
                "troops",
                "forever",
                "hearing",
                "the",
                "activity",
                "guidebook",
                "that",
                "party",
                "direct",
            ],
        )
    ],
    "C03_paper_corpus": [
        (
            [
                [
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
                ],
                [
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
                ],
                [
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
                ],
            ],
            [
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
            ],
        ),
        (
            [
                [
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
                ],
                [
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
                ],
                [
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
                ],
            ],
            [
                "It",
                "is",
                "to",
                "insure",
                "the",
                "troops",
                "forever",
                "hearing",
                "the",
                "activity",
                "guidebook",
                "that",
                "party",
                "direct",
            ],
        ),
    ],
    "C04_split_matches": [
        ([["A", "B", "x", "y"], ["x", "y", "C", "D"]], ["A", "B", "C", "D"])
    ],
    "C05_short_hyp": [
        ([["the", "cat", "sat", "on", "the", "mat"]], ["the", "cat", "sat"])
    ],
    "C06_corpus_all_short": [
        ([["the", "cat", "sat", "on", "the", "mat"]], ["the", "cat", "sat"]),
        ([["a", "dog", "ran", "in", "the", "park"]], ["a", "dog", "ran"]),
    ],
    "C07_corpus_one_short": [
        (
            [
                [
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
            ],
            [
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
            ],
        ),
        ([["the", "party"]], ["the", "party"]),
    ],
    "C08_no_4gram_match": [
        (
            [["the", "cat", "sat", "under", "the", "mat"]],
            ["the", "cat", "sat", "on", "a", "mat"],
        )
    ],
    "C09_no_match": [([["a", "b", "c", "d", "e"]], ["w", "x", "y", "z", "q"])],
    "C10_empty_hyp": [([["the", "cat", "sat", "on", "the", "mat"]], [])],
    "C11_perfect_corpus": [
        (
            [["the", "cat", "sat", "on", "the", "mat"]],
            ["the", "cat", "sat", "on", "the", "mat"],
        ),
        (
            [["a", "quick", "brown", "fox", "jumps", "over", "the", "lazy", "dog"]],
            ["a", "quick", "brown", "fox", "jumps", "over", "the", "lazy", "dog"],
        ),
    ],
    "C12a_order_ab": [
        (
            [["the", "cat", "sat", "on", "the", "red", "mat", "today"]],
            ["the", "cat", "sat", "on", "the", "mat", "today"],
        ),
        (
            [["the", "dog", "was", "in", "a", "park"]],
            ["a", "dog", "is", "in", "the", "park", "now"],
        ),
    ],
    "C12b_order_ba": [
        (
            [["the", "dog", "was", "in", "a", "park"]],
            ["a", "dog", "is", "in", "the", "park", "now"],
        ),
        (
            [["the", "cat", "sat", "on", "the", "red", "mat", "today"]],
            ["the", "cat", "sat", "on", "the", "mat", "today"],
        ),
    ],
    "C13_bp_tie": [
        (
            [["the", "cat", "sat", "on"], ["the", "cat", "sat", "on", "the", "mat"]],
            ["the", "cat", "sat", "on", "mat"],
        )
    ],
    "C14_long_hyp": [
        (
            [["the", "cat", "sat", "on", "the", "mat"]],
            ["the", "cat", "sat", "on", "the", "mat", "and", "then", "it", "slept"],
        )
    ],
    "C15_clipping": [
        (
            [
                ["the", "cat", "is", "on", "the", "mat"],
                ["there", "is", "a", "cat", "on", "the", "mat"],
            ],
            ["the", "the", "the", "the", "the", "the", "the"],
        )
    ],
    "T01_phrase_shift": [
        (
            [["the", "cat", "sat", "on", "the", "mat", "today"]],
            ["on", "the", "mat", "today", "the", "cat", "sat"],
        )
    ],
    "T02_shift_beyond_50": [
        (
            [
                [
                    "w0",
                    "w1",
                    "w2",
                    "w3",
                    "w4",
                    "w5",
                    "w6",
                    "w7",
                    "w8",
                    "w9",
                    "w10",
                    "w11",
                    "w12",
                    "w13",
                    "w14",
                    "w15",
                    "w16",
                    "w17",
                    "w18",
                    "w19",
                    "w20",
                    "w21",
                    "w22",
                    "w23",
                    "w24",
                    "w25",
                    "w26",
                    "w27",
                    "w28",
                    "w29",
                    "w30",
                    "w31",
                    "w32",
                    "w33",
                    "w34",
                    "w35",
                    "w36",
                    "w37",
                    "w38",
                    "w39",
                    "w40",
                    "w41",
                    "w42",
                    "w43",
                    "w44",
                    "w45",
                    "w46",
                    "w47",
                    "w48",
                    "w49",
                    "w50",
                    "w51",
                    "w52",
                    "w53",
                    "w54",
                    "w55",
                    "w56",
                    "w57",
                    "w58",
                    "w59",
                    "w60",
                    "w61",
                    "w62",
                    "w63",
                    "w64",
                    "w65",
                    "w66",
                    "w67",
                    "w68",
                    "w69",
                ]
            ],
            [
                "w60",
                "w61",
                "w62",
                "w63",
                "w64",
                "w65",
                "w66",
                "w67",
                "w68",
                "w69",
                "w0",
                "w1",
                "w2",
                "w3",
                "w4",
                "w5",
                "w6",
                "w7",
                "w8",
                "w9",
                "w10",
                "w11",
                "w12",
                "w13",
                "w14",
                "w15",
                "w16",
                "w17",
                "w18",
                "w19",
                "w20",
                "w21",
                "w22",
                "w23",
                "w24",
                "w25",
                "w26",
                "w27",
                "w28",
                "w29",
                "w30",
                "w31",
                "w32",
                "w33",
                "w34",
                "w35",
                "w36",
                "w37",
                "w38",
                "w39",
                "w40",
                "w41",
                "w42",
                "w43",
                "w44",
                "w45",
                "w46",
                "w47",
                "w48",
                "w49",
                "w50",
                "w51",
                "w52",
                "w53",
                "w54",
                "w55",
                "w56",
                "w57",
                "w58",
                "w59",
            ],
        )
    ],
    "T03_repeated_words": [
        (
            [["the", "the", "cat", "and", "the", "dog", "and", "the", "bird"]],
            ["the", "cat", "the", "dog", "the", "and", "bird", "the", "and"],
        )
    ],
    "T04_case": [
        (
            [["The", "Cat", "sat", "on", "the", "Mat"]],
            ["the", "cat", "sat", "on", "the", "mat"],
        )
    ],
    "T05_punctuation": [
        (
            [["Hello,", "world!", "It's", "(finally)", "here."]],
            ["Hello", "world", ",", "it's", "finally", "here", "!"],
        )
    ],
    "T06_long_scrambled": [
        (
            [
                [
                    "mike",
                    "alpha",
                    "golf",
                    "juliet",
                    "papa",
                    "bravo",
                    "india",
                    "bravo",
                    "juliet",
                    "sierra",
                    "november",
                    "delta",
                    "sierra",
                    "delta",
                    "sierra",
                    "golf",
                    "quebec",
                    "tango",
                    "kilo",
                    "foxtrot",
                    "romeo",
                    "lima",
                    "quebec",
                    "papa",
                    "quebec",
                    "delta",
                    "delta",
                    "tango",
                    "sierra",
                    "lima",
                    "november",
                    "lima",
                    "golf",
                    "foxtrot",
                    "tango",
                    "oscar",
                    "charlie",
                    "charlie",
                    "mike",
                    "sierra",
                    "charlie",
                    "quebec",
                    "echo",
                    "bravo",
                    "romeo",
                    "foxtrot",
                    "charlie",
                    "sierra",
                    "hotel",
                    "november",
                    "romeo",
                    "oscar",
                    "november",
                    "papa",
                    "tango",
                    "quebec",
                    "papa",
                    "oscar",
                    "bravo",
                    "papa",
                    "juliet",
                    "foxtrot",
                    "bravo",
                    "november",
                    "mike",
                    "oscar",
                    "alpha",
                    "papa",
                    "hotel",
                    "november",
                    "tango",
                    "sierra",
                    "lima",
                    "charlie",
                    "echo",
                    "delta",
                    "charlie",
                    "hotel",
                    "foxtrot",
                    "echo",
                    "hotel",
                    "echo",
                    "lima",
                    "golf",
                    "foxtrot",
                    "sierra",
                    "tango",
                    "romeo",
                    "quebec",
                    "oscar",
                    "lima",
                    "juliet",
                    "lima",
                    "papa",
                    "papa",
                    "oscar",
                    "oscar",
                    "november",
                    "oscar",
                    "mike",
                    "lima",
                    "quebec",
                    "delta",
                    "india",
                    "november",
                    "kilo",
                    "alpha",
                    "sierra",
                    "tango",
                    "hotel",
                    "sierra",
                    "alpha",
                    "foxtrot",
                    "tango",
                    "india",
                    "quebec",
                    "delta",
                    "india",
                    "sierra",
                    "bravo",
                ]
            ],
            [
                "bravo",
                "foxtrot",
                "bravo",
                "november",
                "mike",
                "oscar",
                "alpha",
                "quebec",
                "hotel",
                "november",
                "tango",
                "sierra",
                "lima",
                "charlie",
                "foxtrot",
                "delta",
                "charlie",
                "hotel",
                "foxtrot",
                "echo",
                "hotel",
                "bravo",
                "lima",
                "golf",
                "foxtrot",
                "sierra",
                "tango",
                "romeo",
                "india",
                "oscar",
                "lima",
                "juliet",
                "lima",
                "papa",
                "papa",
                "foxtrot",
                "oscar",
                "november",
                "oscar",
                "mike",
                "lima",
                "quebec",
                "tango",
                "india",
                "november",
                "kilo",
                "alpha",
                "sierra",
                "tango",
                "kilo",
                "sierra",
                "alpha",
                "foxtrot",
                "tango",
                "india",
                "quebec",
                "charlie",
                "india",
                "sierra",
                "bravo",
                "mike",
                "alpha",
                "golf",
                "delta",
                "papa",
                "bravo",
                "india",
                "bravo",
                "juliet",
                "sierra",
                "november",
                "delta",
                "sierra",
                "delta",
                "sierra",
                "golf",
                "quebec",
                "tango",
                "kilo",
                "foxtrot",
                "romeo",
                "lima",
                "quebec",
                "papa",
                "echo",
                "delta",
                "delta",
                "tango",
                "sierra",
                "lima",
                "november",
                "romeo",
                "golf",
                "foxtrot",
                "tango",
                "oscar",
                "charlie",
                "charlie",
                "lima",
                "sierra",
                "charlie",
                "quebec",
                "echo",
                "bravo",
                "romeo",
                "echo",
                "charlie",
                "sierra",
                "hotel",
                "november",
                "romeo",
                "oscar",
                "india",
                "papa",
                "tango",
                "quebec",
                "papa",
                "oscar",
                "bravo",
                "charlie",
            ],
        )
    ],
    "T07_multi_ref_shift": [
        (
            [["a", "b", "c", "d", "e", "f", "g"], ["e", "f", "g", "a", "b", "c", "d"]],
            ["e", "f", "g", "d", "c", "b", "a"],
        )
    ],
    "T08_corpus_mix": [
        (
            [["the", "cat", "sat", "on", "the", "mat"]],
            ["the", "cat", "sat", "on", "the", "mat"],
        ),
        (
            [["there", "is", "a", "cat", "on", "the", "mat"]],
            ["on", "the", "mat", "there", "is", "a", "cat"],
        ),
        ([["it", "is", "raining"]], ["rain", "it", "is"]),
    ],
    "M_tercom_beam_1": [
        (
            [
                [
                    "t3",
                    "t1",
                    "t1",
                    "t0",
                    "t2",
                    "t3",
                    "t2",
                    "t2",
                    "t1",
                    "t0",
                    "t1",
                    "t0",
                    "t4",
                    "t4",
                    "t4",
                    "t4",
                    "t4",
                    "t3",
                    "t0",
                    "t1",
                    "t0",
                    "t0",
                    "t1",
                    "t0",
                    "t3",
                    "t0",
                    "t2",
                    "t4",
                    "t3",
                    "t4",
                ]
            ],
            ["t1", "t4", "t3", "t4", "t2", "t0"],
        )
    ],
    "M_tercom_beam_2": [
        (
            [
                [
                    "t15",
                    "t8",
                    "t1",
                    "t9",
                    "t10",
                    "t17",
                    "t13",
                    "t11",
                    "t6",
                    "t12",
                    "t4",
                    "t6",
                    "t14",
                    "t1",
                    "t12",
                    "t17",
                    "t2",
                    "t11",
                    "t11",
                    "t13",
                    "t7",
                    "t16",
                    "t3",
                    "t4",
                    "t15",
                    "t3",
                    "t17",
                    "t8",
                    "t7",
                    "t10",
                    "t0",
                    "t17",
                    "t19",
                    "t6",
                    "t7",
                    "t19",
                    "t4",
                ]
            ],
            ["t19", "t15", "t17", "t19"],
        )
    ],
    "M_tercom_beam_3": [
        (
            [
                [
                    "t10",
                    "t11",
                    "t10",
                    "t5",
                    "t4",
                    "t1",
                    "t5",
                    "t13",
                    "t4",
                    "t7",
                    "t6",
                    "t7",
                    "t12",
                    "t19",
                    "t6",
                    "t17",
                    "t1",
                    "t0",
                    "t19",
                    "t1",
                    "t15",
                    "t2",
                    "t17",
                    "t13",
                    "t6",
                    "t13",
                    "t16",
                    "t14",
                    "t9",
                    "t4",
                    "t16",
                    "t1",
                    "t6",
                    "t1",
                    "t6",
                    "t12",
                ]
            ],
            ["t16", "t15", "t9", "t11", "t7", "t1", "t6", "t10", "t1"],
        )
    ],
    "M_sacrebleu_beam_1": [
        (
            [
                [
                    "t7",
                    "t16",
                    "t11",
                    "t53",
                    "t3",
                    "t19",
                    "t29",
                    "t47",
                    "t29",
                    "t1",
                    "t49",
                    "t22",
                    "t47",
                    "t31",
                    "t36",
                    "t18",
                    "t31",
                    "t28",
                    "t16",
                    "t59",
                    "t52",
                    "t27",
                    "t21",
                    "t31",
                    "t48",
                    "t20",
                    "t2",
                    "t20",
                    "t53",
                    "t29",
                    "t40",
                    "t17",
                    "t26",
                    "t16",
                ]
            ],
            ["t56", "t49"],
        )
    ],
    "M_sacrebleu_beam_2": [
        (
            [
                [
                    "t12",
                    "t16",
                    "t0",
                    "t19",
                    "t18",
                    "t13",
                    "t13",
                    "t14",
                    "t17",
                    "t9",
                    "t8",
                    "t6",
                    "t9",
                    "t8",
                    "t0",
                    "t11",
                    "t7",
                    "t12",
                    "t3",
                    "t0",
                    "t14",
                    "t9",
                    "t4",
                    "t8",
                    "t15",
                    "t1",
                    "t1",
                    "t9",
                    "t19",
                    "t0",
                    "t7",
                    "t11",
                    "t5",
                    "t5",
                    "t2",
                    "t5",
                    "t0",
                    "t7",
                    "t18",
                    "t14",
                    "t3",
                    "t18",
                    "t4",
                    "t4",
                    "t12",
                    "t1",
                    "t14",
                    "t14",
                    "t2",
                    "t5",
                    "t5",
                    "t6",
                    "t1",
                    "t12",
                    "t0",
                    "t15",
                    "t14",
                    "t8",
                    "t14",
                    "t6",
                    "t8",
                    "t15",
                    "t4",
                    "t2",
                    "t7",
                    "t18",
                    "t5",
                    "t13",
                    "t12",
                    "t19",
                    "t18",
                    "t12",
                    "t14",
                    "t18",
                    "t6",
                    "t5",
                    "t1",
                    "t4",
                    "t10",
                    "t14",
                    "t12",
                    "t12",
                    "t13",
                    "t9",
                    "t9",
                    "t11",
                    "t0",
                    "t14",
                    "t15",
                    "t4",
                    "t7",
                    "t6",
                    "t19",
                    "t1",
                    "t19",
                    "t3",
                    "t4",
                    "t14",
                    "t5",
                    "t8",
                ]
            ],
            [
                "t12",
                "t16",
                "t15",
                "t4",
                "t7",
                "t6",
                "t19",
                "t1",
                "t19",
                "t3",
                "t4",
                "t14",
                "t5",
                "t5",
                "t8",
                "t0",
                "t19",
                "t18",
                "t13",
                "t13",
                "t5",
                "t1",
                "t4",
                "t10",
                "t14",
                "t12",
                "t2",
                "t12",
                "t2",
                "t13",
                "t9",
                "t14",
                "t17",
                "t9",
                "t8",
                "t6",
                "t9",
                "t12",
                "t0",
                "t7",
                "t12",
                "t3",
                "t0",
                "t14",
                "t9",
                "t4",
                "t8",
                "t1",
                "t1",
                "t9",
                "t19",
                "t7",
                "t7",
                "t11",
                "t5",
                "t8",
                "t2",
                "t5",
                "t0",
                "t14",
                "t14",
                "t3",
                "t18",
                "t4",
                "t4",
                "t12",
                "t14",
                "t14",
                "t2",
                "t5",
                "t5",
                "t6",
                "t1",
                "t12",
                "t0",
                "t15",
                "t14",
                "t8",
                "t14",
                "t6",
                "t8",
                "t15",
                "t2",
                "t7",
                "t18",
                "t5",
                "t13",
                "t12",
                "t19",
                "t18",
                "t12",
                "t14",
                "t18",
                "t6",
                "t15",
                "t9",
                "t11",
                "t0",
                "t14",
            ],
        )
    ],
    "M_sacrebleu_beam_3": [
        (
            [
                [
                    "t4",
                    "t24",
                    "t25",
                    "t39",
                    "t1",
                    "t32",
                    "t12",
                    "t37",
                    "t56",
                    "t28",
                    "t3",
                    "t4",
                    "t48",
                    "t50",
                    "t33",
                    "t15",
                    "t20",
                    "t21",
                    "t56",
                    "t25",
                    "t5",
                    "t39",
                    "t23",
                    "t33",
                    "t55",
                    "t7",
                    "t30",
                    "t10",
                    "t24",
                    "t52",
                    "t21",
                    "t3",
                    "t4",
                    "t55",
                    "t10",
                    "t9",
                    "t7",
                    "t40",
                    "t1",
                    "t15",
                    "t26",
                    "t0",
                    "t51",
                    "t50",
                    "t24",
                    "t59",
                    "t32",
                    "t56",
                    "t37",
                    "t1",
                    "t27",
                    "t14",
                    "t22",
                    "t13",
                    "t7",
                    "t25",
                    "t52",
                    "t12",
                    "t59",
                    "t47",
                    "t32",
                    "t8",
                    "t53",
                    "t19",
                    "t15",
                    "t39",
                    "t28",
                    "t44",
                    "t42",
                    "t6",
                    "t26",
                    "t31",
                    "t31",
                    "t56",
                    "t56",
                    "t38",
                    "t5",
                    "t46",
                    "t58",
                    "t23",
                    "t8",
                    "t54",
                    "t27",
                    "t56",
                    "t41",
                    "t16",
                    "t54",
                    "t24",
                    "t43",
                    "t20",
                    "t14",
                    "t41",
                    "t54",
                    "t35",
                    "t47",
                    "t55",
                    "t28",
                    "t50",
                    "t45",
                    "t42",
                ]
            ],
            [
                "t4",
                "t24",
                "t25",
                "t39",
                "t1",
                "t32",
                "t12",
                "t37",
                "t56",
                "t28",
                "t3",
                "t4",
                "t48",
                "t9",
                "t7",
                "t1",
                "t19",
                "t15",
                "t39",
                "t28",
                "t44",
                "t42",
                "t6",
                "t26",
                "t31",
                "t31",
                "t15",
                "t26",
                "t0",
                "t40",
                "t51",
                "t50",
                "t24",
                "t59",
                "t32",
                "t56",
                "t37",
                "t1",
                "t27",
                "t14",
                "t22",
                "t13",
                "t7",
                "t25",
                "t52",
                "t12",
                "t59",
                "t47",
                "t32",
                "t8",
                "t53",
                "t56",
                "t56",
                "t38",
                "t5",
                "t46",
                "t58",
                "t23",
                "t56",
                "t25",
                "t5",
                "t39",
                "t33",
                "t55",
                "t7",
                "t30",
                "t10",
                "t24",
                "t8",
                "t54",
                "t27",
                "t56",
                "t41",
                "t16",
                "t54",
                "t24",
                "t43",
                "t20",
                "t14",
                "t41",
                "t54",
                "t35",
                "t47",
                "t55",
                "t50",
                "t33",
                "t15",
                "t20",
                "t21",
                "t52",
                "t21",
                "t3",
                "t4",
                "t55",
                "t10",
                "t28",
                "t50",
                "t45",
                "t42",
            ],
        )
    ],
    "M_sacrebleu_ranking_1": [
        ([["t10", "t19", "t8", "t8", "t1"]], ["t8", "t1", "t19", "t8", "t10"])
    ],
    "M_sacrebleu_ranking_2": [
        (
            [["t6", "t6", "t0", "t7", "t1", "t1", "t5", "t4", "t0", "t2"]],
            ["t5", "t6", "t4", "t0", "t2", "t6", "t1", "t1", "t0", "t7"],
        )
    ],
    "M_sacrebleu_ranking_3": [
        (
            [["t2", "t4", "t0", "t6", "t0", "t3", "t5", "t1", "t4", "t4", "t5", "t5"]],
            ["t2", "t5", "t4", "t5", "t0", "t6", "t0", "t3", "t5", "t1", "t4", "t4"],
        )
    ],
}

RAW = {
    "C01_paper_h1_3refs": [
        (
            [
                "It is a guide to action that ensures that the military will "
                "forever heed Party commands",
                "It is the guiding principle which guarantees the military "
                "forces always being under the command of the Party",
                "It is the practical guide for the army always to heed the "
                "directions of the party",
            ],
            "It is a guide to action which ensures that the military "
            "always obeys the commands of the party",
        )
    ],
    "C02_paper_h2_3refs": [
        (
            [
                "It is a guide to action that ensures that the military will "
                "forever heed Party commands",
                "It is the guiding principle which guarantees the military "
                "forces always being under the command of the Party",
                "It is the practical guide for the army always to heed the "
                "directions of the party",
            ],
            "It is to insure the troops forever hearing the activity "
            "guidebook that party direct",
        )
    ],
    "C03_paper_corpus": [
        (
            [
                "It is a guide to action that ensures that the military will "
                "forever heed Party commands",
                "It is the guiding principle which guarantees the military "
                "forces always being under the command of the Party",
                "It is the practical guide for the army always to heed the "
                "directions of the party",
            ],
            "It is a guide to action which ensures that the military always "
            "obeys the commands of the party",
        ),
        (
            [
                "It is a guide to action that ensures that the military will "
                "forever heed Party commands",
                "It is the guiding principle which guarantees the military "
                "forces always being under the command of the Party",
                "It is the practical guide for the army always to heed the "
                "directions of the party",
            ],
            "It is to insure the troops forever hearing the activity "
            "guidebook that party direct",
        ),
    ],
    "C04_split_matches": [(["A B x y", "x y C D"], "A B C D")],
    "C05_short_hyp": [(["the cat sat on the mat"], "the cat sat")],
    "C06_corpus_all_short": [
        (["the cat sat on the mat"], "the cat sat"),
        (["a dog ran in the park"], "a dog ran"),
    ],
    "C07_corpus_one_short": [
        (
            [
                "It is a guide to action that ensures that the military "
                "will forever heed Party commands"
            ],
            "It is a guide to action which ensures that the military "
            "always obeys the commands of the party",
        ),
        (["the party"], "the party"),
    ],
    "C08_no_4gram_match": [(["the cat sat under the mat"], "the cat sat on a mat")],
    "C09_no_match": [(["a b c d e"], "w x y z q")],
    "C10_empty_hyp": [(["the cat sat on the mat"], "")],
    "C11_perfect_corpus": [
        (["the cat sat on the mat"], "the cat sat on the mat"),
        (
            ["a quick brown fox jumps over the lazy dog"],
            "a quick brown fox jumps over the lazy dog",
        ),
    ],
    "C12a_order_ab": [
        (["the cat sat on the red mat today"], "the cat sat on the mat today"),
        (["the dog was in a park"], "a dog is in the park now"),
    ],
    "C12b_order_ba": [
        (["the dog was in a park"], "a dog is in the park now"),
        (["the cat sat on the red mat today"], "the cat sat on the mat today"),
    ],
    "C13_bp_tie": [
        (["the cat sat on", "the cat sat on the mat"], "the cat sat on mat")
    ],
    "C14_long_hyp": [
        (["the cat sat on the mat"], "the cat sat on the mat and then it slept")
    ],
    "C15_clipping": [
        (
            ["the cat is on the mat", "there is a cat on the mat"],
            "the the the the the the the",
        )
    ],
    "T01_phrase_shift": [
        (["the cat sat on the mat today"], "on the mat today the cat sat")
    ],
    "T02_shift_beyond_50": [
        (
            [
                "w0 w1 w2 w3 w4 w5 w6 w7 w8 w9 w10 w11 w12 w13 w14 w15 w16 "
                "w17 w18 w19 w20 w21 w22 w23 w24 w25 w26 w27 w28 w29 w30 "
                "w31 w32 w33 w34 w35 w36 w37 w38 w39 w40 w41 w42 w43 w44 "
                "w45 w46 w47 w48 w49 w50 w51 w52 w53 w54 w55 w56 w57 w58 "
                "w59 w60 w61 w62 w63 w64 w65 w66 w67 w68 w69"
            ],
            "w60 w61 w62 w63 w64 w65 w66 w67 w68 w69 w0 w1 w2 w3 w4 w5 "
            "w6 w7 w8 w9 w10 w11 w12 w13 w14 w15 w16 w17 w18 w19 w20 w21 "
            "w22 w23 w24 w25 w26 w27 w28 w29 w30 w31 w32 w33 w34 w35 w36 "
            "w37 w38 w39 w40 w41 w42 w43 w44 w45 w46 w47 w48 w49 w50 w51 "
            "w52 w53 w54 w55 w56 w57 w58 w59",
        )
    ],
    "T03_repeated_words": [
        (
            ["the the cat and the dog and the bird"],
            "the cat the dog the and bird the and",
        )
    ],
    "T04_case": [(["The Cat sat on the Mat"], "the cat sat on the mat")],
    "T05_punctuation": [
        (["Hello, world! It's (finally) here."], "Hello world , it's finally here !")
    ],
    "T06_long_scrambled": [
        (
            [
                "mike alpha golf juliet papa bravo india bravo juliet sierra "
                "november delta sierra delta sierra golf quebec tango kilo "
                "foxtrot romeo lima quebec papa quebec delta delta tango "
                "sierra lima november lima golf foxtrot tango oscar charlie "
                "charlie mike sierra charlie quebec echo bravo romeo foxtrot "
                "charlie sierra hotel november romeo oscar november papa "
                "tango quebec papa oscar bravo papa juliet foxtrot bravo "
                "november mike oscar alpha papa hotel november tango sierra "
                "lima charlie echo delta charlie hotel foxtrot echo hotel "
                "echo lima golf foxtrot sierra tango romeo quebec oscar lima "
                "juliet lima papa papa oscar oscar november oscar mike lima "
                "quebec delta india november kilo alpha sierra tango hotel "
                "sierra alpha foxtrot tango india quebec delta india sierra "
                "bravo"
            ],
            "bravo foxtrot bravo november mike oscar alpha quebec hotel "
            "november tango sierra lima charlie foxtrot delta charlie "
            "hotel foxtrot echo hotel bravo lima golf foxtrot sierra "
            "tango romeo india oscar lima juliet lima papa papa foxtrot "
            "oscar november oscar mike lima quebec tango india november "
            "kilo alpha sierra tango kilo sierra alpha foxtrot tango "
            "india quebec charlie india sierra bravo mike alpha golf "
            "delta papa bravo india bravo juliet sierra november delta "
            "sierra delta sierra golf quebec tango kilo foxtrot romeo "
            "lima quebec papa echo delta delta tango sierra lima november "
            "romeo golf foxtrot tango oscar charlie charlie lima sierra "
            "charlie quebec echo bravo romeo echo charlie sierra hotel "
            "november romeo oscar india papa tango quebec papa oscar "
            "bravo charlie",
        )
    ],
    "T07_multi_ref_shift": [(["a b c d e f g", "e f g a b c d"], "e f g d c b a")],
    "T08_corpus_mix": [
        (["the cat sat on the mat"], "the cat sat on the mat"),
        (["there is a cat on the mat"], "on the mat there is a cat"),
        (["it is raining"], "rain it is"),
    ],
    "M_tercom_beam_1": [
        (
            [
                "t3 t1 t1 t0 t2 t3 t2 t2 t1 t0 t1 t0 t4 t4 t4 t4 t4 t3 t0 t1 t0 "
                "t0 t1 t0 t3 t0 t2 t4 t3 t4"
            ],
            "t1 t4 t3 t4 t2 t0",
        )
    ],
    "M_tercom_beam_2": [
        (
            [
                "t15 t8 t1 t9 t10 t17 t13 t11 t6 t12 t4 t6 t14 t1 t12 t17 t2 "
                "t11 t11 t13 t7 t16 t3 t4 t15 t3 t17 t8 t7 t10 t0 t17 t19 t6 t7 "
                "t19 t4"
            ],
            "t19 t15 t17 t19",
        )
    ],
    "M_tercom_beam_3": [
        (
            [
                "t10 t11 t10 t5 t4 t1 t5 t13 t4 t7 t6 t7 t12 t19 t6 t17 t1 t0 "
                "t19 t1 t15 t2 t17 t13 t6 t13 t16 t14 t9 t4 t16 t1 t6 t1 t6 "
                "t12"
            ],
            "t16 t15 t9 t11 t7 t1 t6 t10 t1",
        )
    ],
    "M_sacrebleu_beam_1": [
        (
            [
                "t7 t16 t11 t53 t3 t19 t29 t47 t29 t1 t49 t22 t47 t31 t36 "
                "t18 t31 t28 t16 t59 t52 t27 t21 t31 t48 t20 t2 t20 t53 t29 "
                "t40 t17 t26 t16"
            ],
            "t56 t49",
        )
    ],
    "M_sacrebleu_beam_2": [
        (
            [
                "t12 t16 t0 t19 t18 t13 t13 t14 t17 t9 t8 t6 t9 t8 t0 t11 t7 "
                "t12 t3 t0 t14 t9 t4 t8 t15 t1 t1 t9 t19 t0 t7 t11 t5 t5 t2 "
                "t5 t0 t7 t18 t14 t3 t18 t4 t4 t12 t1 t14 t14 t2 t5 t5 t6 t1 "
                "t12 t0 t15 t14 t8 t14 t6 t8 t15 t4 t2 t7 t18 t5 t13 t12 t19 "
                "t18 t12 t14 t18 t6 t5 t1 t4 t10 t14 t12 t12 t13 t9 t9 t11 "
                "t0 t14 t15 t4 t7 t6 t19 t1 t19 t3 t4 t14 t5 t8"
            ],
            "t12 t16 t15 t4 t7 t6 t19 t1 t19 t3 t4 t14 t5 t5 t8 t0 t19 "
            "t18 t13 t13 t5 t1 t4 t10 t14 t12 t2 t12 t2 t13 t9 t14 t17 t9 "
            "t8 t6 t9 t12 t0 t7 t12 t3 t0 t14 t9 t4 t8 t1 t1 t9 t19 t7 t7 "
            "t11 t5 t8 t2 t5 t0 t14 t14 t3 t18 t4 t4 t12 t14 t14 t2 t5 t5 "
            "t6 t1 t12 t0 t15 t14 t8 t14 t6 t8 t15 t2 t7 t18 t5 t13 t12 "
            "t19 t18 t12 t14 t18 t6 t15 t9 t11 t0 t14",
        )
    ],
    "M_sacrebleu_beam_3": [
        (
            [
                "t4 t24 t25 t39 t1 t32 t12 t37 t56 t28 t3 t4 t48 t50 t33 t15 "
                "t20 t21 t56 t25 t5 t39 t23 t33 t55 t7 t30 t10 t24 t52 t21 "
                "t3 t4 t55 t10 t9 t7 t40 t1 t15 t26 t0 t51 t50 t24 t59 t32 "
                "t56 t37 t1 t27 t14 t22 t13 t7 t25 t52 t12 t59 t47 t32 t8 "
                "t53 t19 t15 t39 t28 t44 t42 t6 t26 t31 t31 t56 t56 t38 t5 "
                "t46 t58 t23 t8 t54 t27 t56 t41 t16 t54 t24 t43 t20 t14 t41 "
                "t54 t35 t47 t55 t28 t50 t45 t42"
            ],
            "t4 t24 t25 t39 t1 t32 t12 t37 t56 t28 t3 t4 t48 t9 t7 t1 t19 "
            "t15 t39 t28 t44 t42 t6 t26 t31 t31 t15 t26 t0 t40 t51 t50 "
            "t24 t59 t32 t56 t37 t1 t27 t14 t22 t13 t7 t25 t52 t12 t59 "
            "t47 t32 t8 t53 t56 t56 t38 t5 t46 t58 t23 t56 t25 t5 t39 t33 "
            "t55 t7 t30 t10 t24 t8 t54 t27 t56 t41 t16 t54 t24 t43 t20 "
            "t14 t41 t54 t35 t47 t55 t50 t33 t15 t20 t21 t52 t21 t3 t4 "
            "t55 t10 t28 t50 t45 t42",
        )
    ],
    "M_sacrebleu_ranking_1": [(["t10 t19 t8 t8 t1"], "t8 t1 t19 t8 t10")],
    "M_sacrebleu_ranking_2": [
        (["t6 t6 t0 t7 t1 t1 t5 t4 t0 t2"], "t5 t6 t4 t0 t2 t6 t1 t1 t0 t7")
    ],
    "M_sacrebleu_ranking_3": [
        (["t2 t4 t0 t6 t0 t3 t5 t1 t4 t4 t5 t5"], "t2 t5 t4 t5 t0 t6 t0 t3 t5 t1 t4 t4")
    ],
}

TOOLS = {
    "C01_paper_h1_3refs": {
        "tercom": {"corpus": 0.48, "segment": [0.48]},
        "sacrebleu.ter": {"corpus": 0.48, "segment": [0.48]},
        "sacrebleu.chrf++": {
            "corpus": 0.6217075369473655,
            "segment": [0.6217075369473655],
        },
        "sacrebleu.chrf++.eps": {
            "corpus": 0.6216559699394644,
            "segment": [0.6216559699394644],
        },
        "jiwer": {"corpus": 0.5, "segment": [0.5]},
        "sclite": {"corpus": 0.5, "segment": [0.5]},
        "chrf++.py": {
            "corpus": 0.6216559699394599,
            "corpus_avg": 0.6216559699394599,
            "segment": [0.6216559699394599],
        },
        "rouge-score.1.f": {
            "corpus": 0.6470588235294118,
            "segment": [0.6470588235294118],
        },
        "rouge-score.1.precision": {
            "corpus": 0.6111111111111112,
            "segment": [0.6111111111111112],
        },
        "rouge-score.1.recall": {"corpus": 0.6875, "segment": [0.6875]},
        "rouge-score.2.f": {"corpus": 0.5, "segment": [0.5]},
        "rouge-score.2.precision": {
            "corpus": 0.47058823529411764,
            "segment": [0.47058823529411764],
        },
        "rouge-score.2.recall": {
            "corpus": 0.5333333333333333,
            "segment": [0.5333333333333333],
        },
        "rouge-score.L.f": {
            "corpus": 0.6470588235294118,
            "segment": [0.6470588235294118],
        },
        "rouge-score.L.precision": {
            "corpus": 0.6111111111111112,
            "segment": [0.6111111111111112],
        },
        "rouge-score.L.recall": {"corpus": 0.6875, "segment": [0.6875]},
        "rouge-1.5.5.1.f": {
            "corpus": 0.576923076923077,
            "segment": [0.576923076923077],
        },
        "rouge-1.5.5.1.precision": {
            "corpus": 0.5555555555555556,
            "segment": [0.5555555555555556],
        },
        "rouge-1.5.5.1.recall": {"corpus": 0.6, "segment": [0.6]},
        "rouge-1.5.5.2.f": {
            "corpus": 0.28571428571428575,
            "segment": [0.28571428571428575],
        },
        "rouge-1.5.5.2.precision": {
            "corpus": 0.27450980392156865,
            "segment": [0.27450980392156865],
        },
        "rouge-1.5.5.2.recall": {
            "corpus": 0.2978723404255319,
            "segment": [0.2978723404255319],
        },
        "rouge-1.5.5.L.f": {
            "corpus": 0.5576923076923077,
            "segment": [0.5576923076923077],
        },
        "rouge-1.5.5.L.precision": {
            "corpus": 0.5370370370370371,
            "segment": [0.5370370370370371],
        },
        "rouge-1.5.5.L.recall": {"corpus": 0.58, "segment": [0.58]},
    },
    "C02_paper_h2_3refs": {
        "tercom": {"corpus": 0.72, "segment": [0.72]},
        "sacrebleu.ter": {"corpus": 0.72, "segment": [0.72]},
        "sacrebleu.chrf++": {
            "corpus": 0.30718916147543046,
            "segment": [0.30718916147543046],
        },
        "sacrebleu.chrf++.eps": {
            "corpus": 0.30710791974756346,
            "segment": [0.30710791974756346],
        },
        "jiwer": {"corpus": 0.8125, "segment": [0.8125]},
        "sclite": {"corpus": 0.8125, "segment": [0.8125]},
        "chrf++.py": {
            "corpus": 0.30710791974755997,
            "corpus_avg": 0.30710791974755997,
            "segment": [0.30710791974755997],
        },
        "rouge-score.1.f": {
            "corpus": 0.39999999999999997,
            "segment": [0.39999999999999997],
        },
        "rouge-score.1.precision": {
            "corpus": 0.42857142857142855,
            "segment": [0.42857142857142855],
        },
        "rouge-score.1.recall": {"corpus": 0.375, "segment": [0.375]},
        "rouge-score.2.f": {
            "corpus": 0.07142857142857144,
            "segment": [0.07142857142857144],
        },
        "rouge-score.2.precision": {
            "corpus": 0.07692307692307693,
            "segment": [0.07692307692307693],
        },
        "rouge-score.2.recall": {
            "corpus": 0.06666666666666667,
            "segment": [0.06666666666666667],
        },
        "rouge-score.L.f": {
            "corpus": 0.39999999999999997,
            "segment": [0.39999999999999997],
        },
        "rouge-score.L.precision": {
            "corpus": 0.42857142857142855,
            "segment": [0.42857142857142855],
        },
        "rouge-score.L.recall": {"corpus": 0.375, "segment": [0.375]},
        "rouge-1.5.5.1.f": {
            "corpus": 0.34782608695652173,
            "segment": [0.34782608695652173],
        },
        "rouge-1.5.5.1.precision": {
            "corpus": 0.38095238095238093,
            "segment": [0.38095238095238093],
        },
        "rouge-1.5.5.1.recall": {"corpus": 0.32, "segment": [0.32]},
        "rouge-1.5.5.2.f": {
            "corpus": 0.06976744186046513,
            "segment": [0.06976744186046513],
        },
        "rouge-1.5.5.2.precision": {
            "corpus": 0.07692307692307693,
            "segment": [0.07692307692307693],
        },
        "rouge-1.5.5.2.recall": {
            "corpus": 0.06382978723404255,
            "segment": [0.06382978723404255],
        },
        "rouge-1.5.5.L.f": {
            "corpus": 0.32608695652173914,
            "segment": [0.32608695652173914],
        },
        "rouge-1.5.5.L.precision": {
            "corpus": 0.35714285714285715,
            "segment": [0.35714285714285715],
        },
        "rouge-1.5.5.L.recall": {"corpus": 0.3, "segment": [0.3]},
    },
    "C03_paper_corpus": {
        "tercom": {"corpus": 0.6, "segment": [0.48, 0.72]},
        "sacrebleu.ter": {"corpus": 0.6, "segment": [0.48, 0.72]},
        "sacrebleu.chrf++": {
            "corpus": 0.46671353667972054,
            "segment": [0.6217075369473655, 0.30718916147543046],
        },
        "sacrebleu.chrf++.eps": {
            "corpus": 0.4667076744328732,
            "segment": [0.6216559699394644, 0.30710791974756346],
        },
        "jiwer": {"corpus": 0.65625, "segment": [0.5, 0.8125]},
        "sclite": {"corpus": 0.65625, "segment": [0.5, 0.8125]},
        "chrf++.py": {
            "corpus": 0.46670767443287,
            "corpus_avg": 0.46438194484351003,
            "segment": [0.6216559699394599, 0.30710791974755997],
        },
        "rouge-score.1.f": {
            "corpus": 0.5235294117647059,
            "segment": [0.6470588235294118, 0.39999999999999997],
        },
        "rouge-score.1.precision": {
            "corpus": 0.5198412698412699,
            "segment": [0.6111111111111112, 0.42857142857142855],
        },
        "rouge-score.1.recall": {"corpus": 0.53125, "segment": [0.6875, 0.375]},
        "rouge-score.2.f": {
            "corpus": 0.2857142857142857,
            "segment": [0.5, 0.07142857142857144],
        },
        "rouge-score.2.precision": {
            "corpus": 0.2737556561085973,
            "segment": [0.47058823529411764, 0.07692307692307693],
        },
        "rouge-score.2.recall": {
            "corpus": 0.3,
            "segment": [0.5333333333333333, 0.06666666666666667],
        },
        "rouge-score.L.f": {
            "corpus": 0.5235294117647059,
            "segment": [0.6470588235294118, 0.39999999999999997],
        },
        "rouge-score.L.precision": {
            "corpus": 0.5198412698412699,
            "segment": [0.6111111111111112, 0.42857142857142855],
        },
        "rouge-score.L.recall": {"corpus": 0.53125, "segment": [0.6875, 0.375]},
        "rouge-1.5.5.1.f": {
            "corpus": 0.46237458193979936,
            "segment": [0.576923076923077, 0.34782608695652173],
        },
        "rouge-1.5.5.1.precision": {
            "corpus": 0.46825396825396826,
            "segment": [0.5555555555555556, 0.38095238095238093],
        },
        "rouge-1.5.5.1.recall": {"corpus": 0.45999999999999996, "segment": [0.6, 0.32]},
        "rouge-1.5.5.2.f": {
            "corpus": 0.17774086378737544,
            "segment": [0.28571428571428575, 0.06976744186046513],
        },
        "rouge-1.5.5.2.precision": {
            "corpus": 0.1757164404223228,
            "segment": [0.27450980392156865, 0.07692307692307693],
        },
        "rouge-1.5.5.2.recall": {
            "corpus": 0.18085106382978722,
            "segment": [0.2978723404255319, 0.06382978723404255],
        },
        "rouge-1.5.5.L.f": {
            "corpus": 0.4418896321070234,
            "segment": [0.5576923076923077, 0.32608695652173914],
        },
        "rouge-1.5.5.L.precision": {
            "corpus": 0.4470899470899471,
            "segment": [0.5370370370370371, 0.35714285714285715],
        },
        "rouge-1.5.5.L.recall": {"corpus": 0.43999999999999995, "segment": [0.58, 0.3]},
    },
    "C04_split_matches": {
        "tercom": {"corpus": 0.5, "segment": [0.5]},
        "sacrebleu.ter": {"corpus": 0.5, "segment": [0.5]},
        "sacrebleu.chrf++": {
            "corpus": 0.27777777777777773,
            "segment": [0.27777777777777773],
        },
        "sacrebleu.chrf++.eps": {
            "corpus": 0.20833333333333337,
            "segment": [0.20833333333333337],
        },
        "jiwer": {"corpus": 0.5, "segment": [0.5]},
        "sclite": {"corpus": 0.5, "segment": [0.5]},
        "chrf++.py": {
            "corpus": 0.20833333333333,
            "corpus_avg": 0.20833333333333,
            "segment": [0.20833333333333],
        },
        "rouge-score.1.f": {"corpus": 0.5, "segment": [0.5]},
        "rouge-score.1.precision": {"corpus": 0.5, "segment": [0.5]},
        "rouge-score.1.recall": {"corpus": 0.5, "segment": [0.5]},
        "rouge-score.2.f": {
            "corpus": 0.3333333333333333,
            "segment": [0.3333333333333333],
        },
        "rouge-score.2.precision": {
            "corpus": 0.3333333333333333,
            "segment": [0.3333333333333333],
        },
        "rouge-score.2.recall": {
            "corpus": 0.3333333333333333,
            "segment": [0.3333333333333333],
        },
        "rouge-score.L.f": {"corpus": 0.5, "segment": [0.5]},
        "rouge-score.L.precision": {"corpus": 0.5, "segment": [0.5]},
        "rouge-score.L.recall": {"corpus": 0.5, "segment": [0.5]},
        "rouge-1.5.5.1.f": {"corpus": 0.5, "segment": [0.5]},
        "rouge-1.5.5.1.precision": {"corpus": 0.5, "segment": [0.5]},
        "rouge-1.5.5.1.recall": {"corpus": 0.5, "segment": [0.5]},
        "rouge-1.5.5.2.f": {
            "corpus": 0.3333333333333333,
            "segment": [0.3333333333333333],
        },
        "rouge-1.5.5.2.precision": {
            "corpus": 0.3333333333333333,
            "segment": [0.3333333333333333],
        },
        "rouge-1.5.5.2.recall": {
            "corpus": 0.3333333333333333,
            "segment": [0.3333333333333333],
        },
        "rouge-1.5.5.L.f": {"corpus": 0.5, "segment": [0.5]},
        "rouge-1.5.5.L.precision": {"corpus": 0.5, "segment": [0.5]},
        "rouge-1.5.5.L.recall": {"corpus": 0.5, "segment": [0.5]},
    },
    "C05_short_hyp": {
        "tercom": {"corpus": 0.5, "segment": [0.5]},
        "sacrebleu.ter": {"corpus": 0.5, "segment": [0.5]},
        "sacrebleu.chrf++": {
            "corpus": 0.4983595347043889,
            "segment": [0.4983595347043889],
        },
        "sacrebleu.chrf++.eps": {
            "corpus": 0.49744288166987904,
            "segment": [0.49744288166987904],
        },
        "jiwer": {"corpus": 0.5, "segment": [0.5]},
        "sclite": {"corpus": 0.5, "segment": [0.5]},
        "chrf++.py": {
            "corpus": 0.49744288166988,
            "corpus_avg": 0.49744288166988,
            "segment": [0.49744288166988],
        },
        "rouge-score.1.f": {
            "corpus": 0.6666666666666666,
            "segment": [0.6666666666666666],
        },
        "rouge-score.1.precision": {"corpus": 1.0, "segment": [1.0]},
        "rouge-score.1.recall": {"corpus": 0.5, "segment": [0.5]},
        "rouge-score.2.f": {
            "corpus": 0.5714285714285715,
            "segment": [0.5714285714285715],
        },
        "rouge-score.2.precision": {"corpus": 1.0, "segment": [1.0]},
        "rouge-score.2.recall": {"corpus": 0.4, "segment": [0.4]},
        "rouge-score.L.f": {
            "corpus": 0.6666666666666666,
            "segment": [0.6666666666666666],
        },
        "rouge-score.L.precision": {"corpus": 1.0, "segment": [1.0]},
        "rouge-score.L.recall": {"corpus": 0.5, "segment": [0.5]},
        "rouge-1.5.5.1.f": {
            "corpus": 0.6666666666666666,
            "segment": [0.6666666666666666],
        },
        "rouge-1.5.5.1.precision": {"corpus": 1.0, "segment": [1.0]},
        "rouge-1.5.5.1.recall": {"corpus": 0.5, "segment": [0.5]},
        "rouge-1.5.5.2.f": {
            "corpus": 0.5714285714285715,
            "segment": [0.5714285714285715],
        },
        "rouge-1.5.5.2.precision": {"corpus": 1.0, "segment": [1.0]},
        "rouge-1.5.5.2.recall": {"corpus": 0.4, "segment": [0.4]},
        "rouge-1.5.5.L.f": {
            "corpus": 0.6666666666666666,
            "segment": [0.6666666666666666],
        },
        "rouge-1.5.5.L.precision": {"corpus": 1.0, "segment": [1.0]},
        "rouge-1.5.5.L.recall": {"corpus": 0.5, "segment": [0.5]},
    },
    "C06_corpus_all_short": {
        "tercom": {"corpus": 0.5, "segment": [0.5, 0.5]},
        "sacrebleu.ter": {"corpus": 0.5, "segment": [0.5, 0.5]},
        "sacrebleu.chrf++": {
            "corpus": 0.4547384250602592,
            "segment": [0.4983595347043889, 0.4068066931969275],
        },
        "sacrebleu.chrf++.eps": {
            "corpus": 0.4533574450453037,
            "segment": [0.49744288166987904, 0.4045115106560769],
        },
        "jiwer": {"corpus": 0.5, "segment": [0.5, 0.5]},
        "sclite": {"corpus": 0.5, "segment": [0.5, 0.5]},
        "chrf++.py": {
            "corpus": 0.45335744504529996,
            "corpus_avg": 0.45097719616298,
            "segment": [0.49744288166988, 0.40451151065608004],
        },
        "rouge-score.1.f": {
            "corpus": 0.6666666666666666,
            "segment": [0.6666666666666666, 0.6666666666666666],
        },
        "rouge-score.1.precision": {"corpus": 1.0, "segment": [1.0, 1.0]},
        "rouge-score.1.recall": {"corpus": 0.5, "segment": [0.5, 0.5]},
        "rouge-score.2.f": {
            "corpus": 0.5714285714285715,
            "segment": [0.5714285714285715, 0.5714285714285715],
        },
        "rouge-score.2.precision": {"corpus": 1.0, "segment": [1.0, 1.0]},
        "rouge-score.2.recall": {"corpus": 0.4, "segment": [0.4, 0.4]},
        "rouge-score.L.f": {
            "corpus": 0.6666666666666666,
            "segment": [0.6666666666666666, 0.6666666666666666],
        },
        "rouge-score.L.precision": {"corpus": 1.0, "segment": [1.0, 1.0]},
        "rouge-score.L.recall": {"corpus": 0.5, "segment": [0.5, 0.5]},
        "rouge-1.5.5.1.f": {
            "corpus": 0.6666666666666666,
            "segment": [0.6666666666666666, 0.6666666666666666],
        },
        "rouge-1.5.5.1.precision": {"corpus": 1.0, "segment": [1.0, 1.0]},
        "rouge-1.5.5.1.recall": {"corpus": 0.5, "segment": [0.5, 0.5]},
        "rouge-1.5.5.2.f": {
            "corpus": 0.5714285714285715,
            "segment": [0.5714285714285715, 0.5714285714285715],
        },
        "rouge-1.5.5.2.precision": {"corpus": 1.0, "segment": [1.0, 1.0]},
        "rouge-1.5.5.2.recall": {"corpus": 0.4, "segment": [0.4, 0.4]},
        "rouge-1.5.5.L.f": {
            "corpus": 0.6666666666666666,
            "segment": [0.6666666666666666, 0.6666666666666666],
        },
        "rouge-1.5.5.L.precision": {"corpus": 1.0, "segment": [1.0, 1.0]},
        "rouge-1.5.5.L.recall": {"corpus": 0.5, "segment": [0.5, 0.5]},
    },
    "C07_corpus_one_short": {
        "tercom": {"corpus": 0.4444444444444444, "segment": [0.5, 0.0]},
        "sacrebleu.ter": {"corpus": 0.4444444444444444, "segment": [0.5, 0.0]},
        "sacrebleu.chrf++": {
            "corpus": 0.6478442052807519,
            "segment": [0.6217075369473655, 1.0],
        },
        "sacrebleu.chrf++.eps": {
            "corpus": 0.6477992363161934,
            "segment": [0.6216559699394644, 1.0],
        },
        "jiwer": {"corpus": 0.4444444444444444, "segment": [0.5, 0.0]},
        "sclite": {"corpus": 0.4444444444444444, "segment": [0.5, 0.0]},
        "chrf++.py": {
            "corpus": 0.64779923631619,
            "corpus_avg": 0.81082798496973,
            "segment": [0.6216559699394599, 1.0],
        },
        "rouge-score.1.f": {
            "corpus": 0.8235294117647058,
            "segment": [0.6470588235294118, 1.0],
        },
        "rouge-score.1.precision": {
            "corpus": 0.8055555555555556,
            "segment": [0.6111111111111112, 1.0],
        },
        "rouge-score.1.recall": {"corpus": 0.84375, "segment": [0.6875, 1.0]},
        "rouge-score.2.f": {"corpus": 0.75, "segment": [0.5, 1.0]},
        "rouge-score.2.precision": {
            "corpus": 0.7352941176470589,
            "segment": [0.47058823529411764, 1.0],
        },
        "rouge-score.2.recall": {
            "corpus": 0.7666666666666666,
            "segment": [0.5333333333333333, 1.0],
        },
        "rouge-score.L.f": {
            "corpus": 0.8235294117647058,
            "segment": [0.6470588235294118, 1.0],
        },
        "rouge-score.L.precision": {
            "corpus": 0.8055555555555556,
            "segment": [0.6111111111111112, 1.0],
        },
        "rouge-score.L.recall": {"corpus": 0.84375, "segment": [0.6875, 1.0]},
        "rouge-1.5.5.1.f": {
            "corpus": 0.8235294117647058,
            "segment": [0.6470588235294118, 1.0],
        },
        "rouge-1.5.5.1.precision": {
            "corpus": 0.8055555555555556,
            "segment": [0.6111111111111112, 1.0],
        },
        "rouge-1.5.5.1.recall": {"corpus": 0.84375, "segment": [0.6875, 1.0]},
        "rouge-1.5.5.2.f": {"corpus": 0.75, "segment": [0.5, 1.0]},
        "rouge-1.5.5.2.precision": {
            "corpus": 0.7352941176470589,
            "segment": [0.47058823529411764, 1.0],
        },
        "rouge-1.5.5.2.recall": {
            "corpus": 0.7666666666666666,
            "segment": [0.5333333333333333, 1.0],
        },
        "rouge-1.5.5.L.f": {
            "corpus": 0.8235294117647058,
            "segment": [0.6470588235294118, 1.0],
        },
        "rouge-1.5.5.L.precision": {
            "corpus": 0.8055555555555556,
            "segment": [0.6111111111111112, 1.0],
        },
        "rouge-1.5.5.L.recall": {"corpus": 0.84375, "segment": [0.6875, 1.0]},
    },
    "C08_no_4gram_match": {
        "tercom": {"corpus": 0.3333333333333333, "segment": [0.3333333333333333]},
        "sacrebleu.ter": {
            "corpus": 0.33333333333333326,
            "segment": [0.33333333333333326],
        },
        "sacrebleu.chrf++": {
            "corpus": 0.4728831719351453,
            "segment": [0.4728831719351453],
        },
        "sacrebleu.chrf++.eps": {
            "corpus": 0.47138357535996855,
            "segment": [0.47138357535996855],
        },
        "jiwer": {"corpus": 0.3333333333333333, "segment": [0.3333333333333333]},
        "sclite": {"corpus": 0.3333333333333333, "segment": [0.3333333333333333]},
        "chrf++.py": {
            "corpus": 0.47138357535997,
            "corpus_avg": 0.47138357535997,
            "segment": [0.47138357535997],
        },
        "rouge-score.1.f": {
            "corpus": 0.6666666666666666,
            "segment": [0.6666666666666666],
        },
        "rouge-score.1.precision": {
            "corpus": 0.6666666666666666,
            "segment": [0.6666666666666666],
        },
        "rouge-score.1.recall": {
            "corpus": 0.6666666666666666,
            "segment": [0.6666666666666666],
        },
        "rouge-score.2.f": {
            "corpus": 0.4000000000000001,
            "segment": [0.4000000000000001],
        },
        "rouge-score.2.precision": {"corpus": 0.4, "segment": [0.4]},
        "rouge-score.2.recall": {"corpus": 0.4, "segment": [0.4]},
        "rouge-score.L.f": {
            "corpus": 0.6666666666666666,
            "segment": [0.6666666666666666],
        },
        "rouge-score.L.precision": {
            "corpus": 0.6666666666666666,
            "segment": [0.6666666666666666],
        },
        "rouge-score.L.recall": {
            "corpus": 0.6666666666666666,
            "segment": [0.6666666666666666],
        },
        "rouge-1.5.5.1.f": {
            "corpus": 0.6666666666666666,
            "segment": [0.6666666666666666],
        },
        "rouge-1.5.5.1.precision": {
            "corpus": 0.6666666666666666,
            "segment": [0.6666666666666666],
        },
        "rouge-1.5.5.1.recall": {
            "corpus": 0.6666666666666666,
            "segment": [0.6666666666666666],
        },
        "rouge-1.5.5.2.f": {
            "corpus": 0.4000000000000001,
            "segment": [0.4000000000000001],
        },
        "rouge-1.5.5.2.precision": {"corpus": 0.4, "segment": [0.4]},
        "rouge-1.5.5.2.recall": {"corpus": 0.4, "segment": [0.4]},
        "rouge-1.5.5.L.f": {
            "corpus": 0.6666666666666666,
            "segment": [0.6666666666666666],
        },
        "rouge-1.5.5.L.precision": {
            "corpus": 0.6666666666666666,
            "segment": [0.6666666666666666],
        },
        "rouge-1.5.5.L.recall": {
            "corpus": 0.6666666666666666,
            "segment": [0.6666666666666666],
        },
    },
    "C09_no_match": {
        "tercom": {"corpus": 1.0, "segment": [1.0]},
        "sacrebleu.ter": {"corpus": 1.0, "segment": [1.0]},
        "sacrebleu.chrf++": {"corpus": 0.0, "segment": [0.0]},
        "sacrebleu.chrf++.eps": {
            "corpus": 1.0000000000000001e-16,
            "segment": [1.0000000000000001e-16],
        },
        "jiwer": {"corpus": 1.0, "segment": [1.0]},
        "sclite": {"corpus": 1.0, "segment": [1.0]},
        "rouge-score.1.f": {"corpus": 0.0, "segment": [0.0]},
        "rouge-score.1.precision": {"corpus": 0.0, "segment": [0.0]},
        "rouge-score.1.recall": {"corpus": 0.0, "segment": [0.0]},
        "rouge-score.2.f": {"corpus": 0.0, "segment": [0.0]},
        "rouge-score.2.precision": {"corpus": 0.0, "segment": [0.0]},
        "rouge-score.2.recall": {"corpus": 0.0, "segment": [0.0]},
        "rouge-score.L.f": {"corpus": 0.0, "segment": [0.0]},
        "rouge-score.L.precision": {"corpus": 0.0, "segment": [0.0]},
        "rouge-score.L.recall": {"corpus": 0.0, "segment": [0.0]},
        "rouge-1.5.5.1.f": {"corpus": 0.0, "segment": [0.0]},
        "rouge-1.5.5.1.precision": {"corpus": 0.0, "segment": [0.0]},
        "rouge-1.5.5.1.recall": {"corpus": 0.0, "segment": [0.0]},
        "rouge-1.5.5.2.f": {"corpus": 0.0, "segment": [0.0]},
        "rouge-1.5.5.2.precision": {"corpus": 0.0, "segment": [0.0]},
        "rouge-1.5.5.2.recall": {"corpus": 0.0, "segment": [0.0]},
        "rouge-1.5.5.L.f": {"corpus": 0.0, "segment": [0.0]},
        "rouge-1.5.5.L.precision": {"corpus": 0.0, "segment": [0.0]},
        "rouge-1.5.5.L.recall": {"corpus": 0.0, "segment": [0.0]},
    },
    "C10_empty_hyp": {
        "tercom": {"corpus": 1.0, "segment": [1.0]},
        "sacrebleu.ter": {"corpus": 1.0, "segment": [1.0]},
        "sacrebleu.chrf++": {"corpus": 0.0, "segment": [0.0]},
        "sacrebleu.chrf++.eps": {"corpus": 0.0, "segment": [0.0]},
        "jiwer": {"corpus": 1.0, "segment": [1.0]},
        "sclite": {"corpus": 1.0, "segment": [1.0]},
        "rouge-score.1.f": {"corpus": 0.0, "segment": [0.0]},
        "rouge-score.1.precision": {"corpus": 0.0, "segment": [0.0]},
        "rouge-score.1.recall": {"corpus": 0.0, "segment": [0.0]},
        "rouge-score.2.f": {"corpus": 0.0, "segment": [0.0]},
        "rouge-score.2.precision": {"corpus": 0.0, "segment": [0.0]},
        "rouge-score.2.recall": {"corpus": 0.0, "segment": [0.0]},
        "rouge-score.L.f": {"corpus": 0.0, "segment": [0]},
        "rouge-score.L.precision": {"corpus": 0.0, "segment": [0]},
        "rouge-score.L.recall": {"corpus": 0.0, "segment": [0]},
        "rouge-1.5.5.1.f": {"corpus": 0.0, "segment": [0.0]},
        "rouge-1.5.5.1.precision": {"corpus": 0.0, "segment": [0.0]},
        "rouge-1.5.5.1.recall": {"corpus": 0.0, "segment": [0.0]},
        "rouge-1.5.5.2.f": {"corpus": 0.0, "segment": [0.0]},
        "rouge-1.5.5.2.precision": {"corpus": 0.0, "segment": [0.0]},
        "rouge-1.5.5.2.recall": {"corpus": 0.0, "segment": [0.0]},
        "rouge-1.5.5.L.f": {"corpus": 0.0, "segment": [0.0]},
        "rouge-1.5.5.L.precision": {"corpus": 0.0, "segment": [0.0]},
        "rouge-1.5.5.L.recall": {"corpus": 0.0, "segment": [0.0]},
    },
    "C11_perfect_corpus": {
        "tercom": {"corpus": 0.0, "segment": [0.0, 0.0]},
        "sacrebleu.ter": {"corpus": 0.0, "segment": [0.0, 0.0]},
        "sacrebleu.chrf++": {"corpus": 1.0, "segment": [1.0, 1.0]},
        "sacrebleu.chrf++.eps": {"corpus": 1.0, "segment": [1.0, 1.0]},
        "jiwer": {"corpus": 0.0, "segment": [0.0, 0.0]},
        "sclite": {"corpus": 0.0, "segment": [0.0, 0.0]},
        "chrf++.py": {"corpus": 1.0, "corpus_avg": 1.0, "segment": [1.0, 1.0]},
        "rouge-score.1.f": {"corpus": 1.0, "segment": [1.0, 1.0]},
        "rouge-score.1.precision": {"corpus": 1.0, "segment": [1.0, 1.0]},
        "rouge-score.1.recall": {"corpus": 1.0, "segment": [1.0, 1.0]},
        "rouge-score.2.f": {"corpus": 1.0, "segment": [1.0, 1.0]},
        "rouge-score.2.precision": {"corpus": 1.0, "segment": [1.0, 1.0]},
        "rouge-score.2.recall": {"corpus": 1.0, "segment": [1.0, 1.0]},
        "rouge-score.L.f": {"corpus": 1.0, "segment": [1.0, 1.0]},
        "rouge-score.L.precision": {"corpus": 1.0, "segment": [1.0, 1.0]},
        "rouge-score.L.recall": {"corpus": 1.0, "segment": [1.0, 1.0]},
        "rouge-1.5.5.1.f": {"corpus": 1.0, "segment": [1.0, 1.0]},
        "rouge-1.5.5.1.precision": {"corpus": 1.0, "segment": [1.0, 1.0]},
        "rouge-1.5.5.1.recall": {"corpus": 1.0, "segment": [1.0, 1.0]},
        "rouge-1.5.5.2.f": {"corpus": 1.0, "segment": [1.0, 1.0]},
        "rouge-1.5.5.2.precision": {"corpus": 1.0, "segment": [1.0, 1.0]},
        "rouge-1.5.5.2.recall": {"corpus": 1.0, "segment": [1.0, 1.0]},
        "rouge-1.5.5.L.f": {"corpus": 1.0, "segment": [1.0, 1.0]},
        "rouge-1.5.5.L.precision": {"corpus": 1.0, "segment": [1.0, 1.0]},
        "rouge-1.5.5.L.recall": {"corpus": 1.0, "segment": [1.0, 1.0]},
    },
    "C12a_order_ab": {
        "tercom": {
            "corpus": 0.35714285714285715,
            "segment": [0.125, 0.6666666666666666],
        },
        "sacrebleu.ter": {
            "corpus": 0.35714285714285715,
            "segment": [0.125, 0.6666666666666665],
        },
        "sacrebleu.chrf++": {
            "corpus": 0.6072697113671581,
            "segment": [0.7806565863267049, 0.340932108927379],
        },
        "sacrebleu.chrf++.eps": {
            "corpus": 0.6072550442936804,
            "segment": [0.7806420506067817, 0.3409188039442672],
        },
        "jiwer": {
            "corpus": 0.35714285714285715,
            "segment": [0.125, 0.6666666666666666],
        },
        "sclite": {
            "corpus": 0.35714285714285715,
            "segment": [0.125, 0.6666666666666666],
        },
        "chrf++.py": {
            "corpus": 0.60725504429368,
            "corpus_avg": 0.56078042727552,
            "segment": [0.78064205060678, 0.34091880394427],
        },
        "rouge-score.1.f": {
            "corpus": 0.8512820512820513,
            "segment": [0.9333333333333333, 0.7692307692307692],
        },
        "rouge-score.1.precision": {
            "corpus": 0.8571428571428572,
            "segment": [1.0, 0.7142857142857143],
        },
        "rouge-score.1.recall": {
            "corpus": 0.8541666666666667,
            "segment": [0.875, 0.8333333333333334],
        },
        "rouge-score.2.f": {
            "corpus": 0.3846153846153846,
            "segment": [0.7692307692307692, 0.0],
        },
        "rouge-score.2.precision": {
            "corpus": 0.4166666666666667,
            "segment": [0.8333333333333334, 0.0],
        },
        "rouge-score.2.recall": {
            "corpus": 0.35714285714285715,
            "segment": [0.7142857142857143, 0.0],
        },
        "rouge-score.L.f": {
            "corpus": 0.6974358974358974,
            "segment": [0.9333333333333333, 0.4615384615384615],
        },
        "rouge-score.L.precision": {
            "corpus": 0.7142857142857143,
            "segment": [1.0, 0.42857142857142855],
        },
        "rouge-score.L.recall": {"corpus": 0.6875, "segment": [0.875, 0.5]},
        "rouge-1.5.5.1.f": {
            "corpus": 0.8512820512820513,
            "segment": [0.9333333333333333, 0.7692307692307692],
        },
        "rouge-1.5.5.1.precision": {
            "corpus": 0.8571428571428572,
            "segment": [1.0, 0.7142857142857143],
        },
        "rouge-1.5.5.1.recall": {
            "corpus": 0.8541666666666667,
            "segment": [0.875, 0.8333333333333334],
        },
        "rouge-1.5.5.2.f": {
            "corpus": 0.3846153846153846,
            "segment": [0.7692307692307692, 0.0],
        },
        "rouge-1.5.5.2.precision": {
            "corpus": 0.4166666666666667,
            "segment": [0.8333333333333334, 0.0],
        },
        "rouge-1.5.5.2.recall": {
            "corpus": 0.35714285714285715,
            "segment": [0.7142857142857143, 0.0],
        },
        "rouge-1.5.5.L.f": {
            "corpus": 0.6974358974358974,
            "segment": [0.9333333333333333, 0.4615384615384615],
        },
        "rouge-1.5.5.L.precision": {
            "corpus": 0.7142857142857143,
            "segment": [1.0, 0.42857142857142855],
        },
        "rouge-1.5.5.L.recall": {"corpus": 0.6875, "segment": [0.875, 0.5]},
    },
    "C12b_order_ba": {
        "tercom": {
            "corpus": 0.35714285714285715,
            "segment": [0.6666666666666666, 0.125],
        },
        "sacrebleu.ter": {
            "corpus": 0.35714285714285715,
            "segment": [0.6666666666666665, 0.125],
        },
        "sacrebleu.chrf++": {
            "corpus": 0.6072697113671581,
            "segment": [0.340932108927379, 0.7806565863267049],
        },
        "sacrebleu.chrf++.eps": {
            "corpus": 0.6072550442936804,
            "segment": [0.3409188039442672, 0.7806420506067817],
        },
        "jiwer": {
            "corpus": 0.35714285714285715,
            "segment": [0.6666666666666666, 0.125],
        },
        "sclite": {
            "corpus": 0.35714285714285715,
            "segment": [0.6666666666666666, 0.125],
        },
        "chrf++.py": {
            "corpus": 0.60725504429368,
            "corpus_avg": 0.56078042727552,
            "segment": [0.34091880394427, 0.78064205060678],
        },
        "rouge-score.1.f": {
            "corpus": 0.8512820512820513,
            "segment": [0.7692307692307692, 0.9333333333333333],
        },
        "rouge-score.1.precision": {
            "corpus": 0.8571428571428572,
            "segment": [0.7142857142857143, 1.0],
        },
        "rouge-score.1.recall": {
            "corpus": 0.8541666666666667,
            "segment": [0.8333333333333334, 0.875],
        },
        "rouge-score.2.f": {
            "corpus": 0.3846153846153846,
            "segment": [0.0, 0.7692307692307692],
        },
        "rouge-score.2.precision": {
            "corpus": 0.4166666666666667,
            "segment": [0.0, 0.8333333333333334],
        },
        "rouge-score.2.recall": {
            "corpus": 0.35714285714285715,
            "segment": [0.0, 0.7142857142857143],
        },
        "rouge-score.L.f": {
            "corpus": 0.6974358974358974,
            "segment": [0.4615384615384615, 0.9333333333333333],
        },
        "rouge-score.L.precision": {
            "corpus": 0.7142857142857143,
            "segment": [0.42857142857142855, 1.0],
        },
        "rouge-score.L.recall": {"corpus": 0.6875, "segment": [0.5, 0.875]},
        "rouge-1.5.5.1.f": {
            "corpus": 0.8512820512820513,
            "segment": [0.7692307692307692, 0.9333333333333333],
        },
        "rouge-1.5.5.1.precision": {
            "corpus": 0.8571428571428572,
            "segment": [0.7142857142857143, 1.0],
        },
        "rouge-1.5.5.1.recall": {
            "corpus": 0.8541666666666667,
            "segment": [0.8333333333333334, 0.875],
        },
        "rouge-1.5.5.2.f": {
            "corpus": 0.3846153846153846,
            "segment": [0.0, 0.7692307692307692],
        },
        "rouge-1.5.5.2.precision": {
            "corpus": 0.4166666666666667,
            "segment": [0.0, 0.8333333333333334],
        },
        "rouge-1.5.5.2.recall": {
            "corpus": 0.35714285714285715,
            "segment": [0.0, 0.7142857142857143],
        },
        "rouge-1.5.5.L.f": {
            "corpus": 0.6974358974358974,
            "segment": [0.4615384615384615, 0.9333333333333333],
        },
        "rouge-1.5.5.L.precision": {
            "corpus": 0.7142857142857143,
            "segment": [0.42857142857142855, 1.0],
        },
        "rouge-1.5.5.L.recall": {"corpus": 0.6875, "segment": [0.5, 0.875]},
    },
    "C13_bp_tie": {
        "tercom": {"corpus": 0.2, "segment": [0.2]},
        "sacrebleu.ter": {"corpus": 0.2, "segment": [0.2]},
        "sacrebleu.chrf++": {
            "corpus": 0.9354904589346682,
            "segment": [0.9354904589346682],
        },
        "sacrebleu.chrf++.eps": {
            "corpus": 0.9349286424593005,
            "segment": [0.9349286424593005],
        },
        "jiwer": {"corpus": 0.25, "segment": [0.25]},
        "sclite": {"corpus": 0.25, "segment": [0.25]},
        "chrf++.py": {
            "corpus": 0.9349286424593,
            "corpus_avg": 0.9349286424593,
            "segment": [0.9349286424593],
        },
        "rouge-score.1.f": {
            "corpus": 0.9090909090909091,
            "segment": [0.9090909090909091],
        },
        "rouge-score.1.precision": {"corpus": 1.0, "segment": [1.0]},
        "rouge-score.1.recall": {
            "corpus": 0.8333333333333334,
            "segment": [0.8333333333333334],
        },
        "rouge-score.2.f": {
            "corpus": 0.8571428571428571,
            "segment": [0.8571428571428571],
        },
        "rouge-score.2.precision": {"corpus": 0.75, "segment": [0.75]},
        "rouge-score.2.recall": {"corpus": 1.0, "segment": [1.0]},
        "rouge-score.L.f": {
            "corpus": 0.9090909090909091,
            "segment": [0.9090909090909091],
        },
        "rouge-score.L.precision": {"corpus": 1.0, "segment": [1.0]},
        "rouge-score.L.recall": {
            "corpus": 0.8333333333333334,
            "segment": [0.8333333333333334],
        },
        "rouge-1.5.5.1.f": {"corpus": 0.9, "segment": [0.9]},
        "rouge-1.5.5.1.precision": {"corpus": 0.9, "segment": [0.9]},
        "rouge-1.5.5.1.recall": {"corpus": 0.9, "segment": [0.9]},
        "rouge-1.5.5.2.f": {"corpus": 0.75, "segment": [0.75]},
        "rouge-1.5.5.2.precision": {"corpus": 0.75, "segment": [0.75]},
        "rouge-1.5.5.2.recall": {"corpus": 0.75, "segment": [0.75]},
        "rouge-1.5.5.L.f": {"corpus": 0.9, "segment": [0.9]},
        "rouge-1.5.5.L.precision": {"corpus": 0.9, "segment": [0.9]},
        "rouge-1.5.5.L.recall": {"corpus": 0.9, "segment": [0.9]},
    },
    "C14_long_hyp": {
        "tercom": {"corpus": 0.6666666666666666, "segment": [0.6666666666666666]},
        "sacrebleu.ter": {
            "corpus": 0.6666666666666665,
            "segment": [0.6666666666666665],
        },
        "sacrebleu.chrf++": {
            "corpus": 0.8466139652317082,
            "segment": [0.8466139652317082],
        },
        "sacrebleu.chrf++.eps": {
            "corpus": 0.8454621473188767,
            "segment": [0.8454621473188767],
        },
        "jiwer": {"corpus": 0.6666666666666666, "segment": [0.6666666666666666]},
        "sclite": {"corpus": 0.6666666666666666, "segment": [0.6666666666666666]},
        "chrf++.py": {
            "corpus": 0.84546214731888,
            "corpus_avg": 0.84546214731888,
            "segment": [0.84546214731888],
        },
        "rouge-score.1.f": {
            "corpus": 0.7499999999999999,
            "segment": [0.7499999999999999],
        },
        "rouge-score.1.precision": {"corpus": 0.6, "segment": [0.6]},
        "rouge-score.1.recall": {"corpus": 1.0, "segment": [1.0]},
        "rouge-score.2.f": {
            "corpus": 0.7142857142857143,
            "segment": [0.7142857142857143],
        },
        "rouge-score.2.precision": {
            "corpus": 0.5555555555555556,
            "segment": [0.5555555555555556],
        },
        "rouge-score.2.recall": {"corpus": 1.0, "segment": [1.0]},
        "rouge-score.L.f": {
            "corpus": 0.7499999999999999,
            "segment": [0.7499999999999999],
        },
        "rouge-score.L.precision": {"corpus": 0.6, "segment": [0.6]},
        "rouge-score.L.recall": {"corpus": 1.0, "segment": [1.0]},
        "rouge-1.5.5.1.f": {
            "corpus": 0.7499999999999999,
            "segment": [0.7499999999999999],
        },
        "rouge-1.5.5.1.precision": {"corpus": 0.6, "segment": [0.6]},
        "rouge-1.5.5.1.recall": {"corpus": 1.0, "segment": [1.0]},
        "rouge-1.5.5.2.f": {
            "corpus": 0.7142857142857143,
            "segment": [0.7142857142857143],
        },
        "rouge-1.5.5.2.precision": {
            "corpus": 0.5555555555555556,
            "segment": [0.5555555555555556],
        },
        "rouge-1.5.5.2.recall": {"corpus": 1.0, "segment": [1.0]},
        "rouge-1.5.5.L.f": {
            "corpus": 0.7499999999999999,
            "segment": [0.7499999999999999],
        },
        "rouge-1.5.5.L.precision": {"corpus": 0.6, "segment": [0.6]},
        "rouge-1.5.5.L.recall": {"corpus": 1.0, "segment": [1.0]},
    },
    "C15_clipping": {
        "tercom": {"corpus": 0.7692307692307693, "segment": [0.7692307692307693]},
        "sacrebleu.ter": {
            "corpus": 0.7692307692307694,
            "segment": [0.7692307692307694],
        },
        "sacrebleu.chrf++": {
            "corpus": 0.1471532900200283,
            "segment": [0.1471532900200283],
        },
        "sacrebleu.chrf++.eps": {
            "corpus": 0.14706277672359272,
            "segment": [0.14706277672359272],
        },
        "jiwer": {"corpus": 0.8333333333333334, "segment": [0.8333333333333334]},
        "sclite": {"corpus": 0.8333333333333334, "segment": [0.8333333333333334]},
        "chrf++.py": {
            "corpus": 0.14706277672359,
            "corpus_avg": 0.14706277672359,
            "segment": [0.14706277672359],
        },
        "rouge-score.1.f": {
            "corpus": 0.30769230769230765,
            "segment": [0.30769230769230765],
        },
        "rouge-score.1.precision": {
            "corpus": 0.2857142857142857,
            "segment": [0.2857142857142857],
        },
        "rouge-score.1.recall": {
            "corpus": 0.3333333333333333,
            "segment": [0.3333333333333333],
        },
        "rouge-score.2.f": {"corpus": 0.0, "segment": [0.0]},
        "rouge-score.2.precision": {"corpus": 0.0, "segment": [0.0]},
        "rouge-score.2.recall": {"corpus": 0.0, "segment": [0.0]},
        "rouge-score.L.f": {
            "corpus": 0.30769230769230765,
            "segment": [0.30769230769230765],
        },
        "rouge-score.L.precision": {
            "corpus": 0.2857142857142857,
            "segment": [0.2857142857142857],
        },
        "rouge-score.L.recall": {
            "corpus": 0.3333333333333333,
            "segment": [0.3333333333333333],
        },
        "rouge-1.5.5.1.f": {
            "corpus": 0.22222222222222224,
            "segment": [0.22222222222222224],
        },
        "rouge-1.5.5.1.precision": {
            "corpus": 0.21428571428571427,
            "segment": [0.21428571428571427],
        },
        "rouge-1.5.5.1.recall": {
            "corpus": 0.23076923076923078,
            "segment": [0.23076923076923078],
        },
        "rouge-1.5.5.2.f": {"corpus": 0.0, "segment": [0.0]},
        "rouge-1.5.5.2.precision": {"corpus": 0.0, "segment": [0.0]},
        "rouge-1.5.5.2.recall": {"corpus": 0.0, "segment": [0.0]},
        "rouge-1.5.5.L.f": {
            "corpus": 0.22222222222222224,
            "segment": [0.22222222222222224],
        },
        "rouge-1.5.5.L.precision": {
            "corpus": 0.21428571428571427,
            "segment": [0.21428571428571427],
        },
        "rouge-1.5.5.L.recall": {
            "corpus": 0.23076923076923078,
            "segment": [0.23076923076923078],
        },
    },
    "T01_phrase_shift": {
        "tercom": {"corpus": 0.14285714285714285, "segment": [0.14285714285714285]},
        "sacrebleu.ter": {
            "corpus": 0.14285714285714285,
            "segment": [0.14285714285714285],
        },
        "sacrebleu.chrf++": {
            "corpus": 0.876434959948892,
            "segment": [0.876434959948892],
        },
        "sacrebleu.chrf++.eps": {
            "corpus": 0.876434959948892,
            "segment": [0.876434959948892],
        },
        "jiwer": {"corpus": 0.8571428571428571, "segment": [0.8571428571428571]},
        "sclite": {"corpus": 0.8571428571428571, "segment": [0.8571428571428571]},
        "chrf++.py": {
            "corpus": 0.87643495994889,
            "corpus_avg": 0.87643495994889,
            "segment": [0.87643495994889],
        },
        "rouge-score.1.f": {"corpus": 1.0, "segment": [1.0]},
        "rouge-score.1.precision": {"corpus": 1.0, "segment": [1.0]},
        "rouge-score.1.recall": {"corpus": 1.0, "segment": [1.0]},
        "rouge-score.2.f": {
            "corpus": 0.8333333333333334,
            "segment": [0.8333333333333334],
        },
        "rouge-score.2.precision": {
            "corpus": 0.8333333333333334,
            "segment": [0.8333333333333334],
        },
        "rouge-score.2.recall": {
            "corpus": 0.8333333333333334,
            "segment": [0.8333333333333334],
        },
        "rouge-score.L.f": {
            "corpus": 0.5714285714285714,
            "segment": [0.5714285714285714],
        },
        "rouge-score.L.precision": {
            "corpus": 0.5714285714285714,
            "segment": [0.5714285714285714],
        },
        "rouge-score.L.recall": {
            "corpus": 0.5714285714285714,
            "segment": [0.5714285714285714],
        },
        "rouge-1.5.5.1.f": {"corpus": 1.0, "segment": [1.0]},
        "rouge-1.5.5.1.precision": {"corpus": 1.0, "segment": [1.0]},
        "rouge-1.5.5.1.recall": {"corpus": 1.0, "segment": [1.0]},
        "rouge-1.5.5.2.f": {
            "corpus": 0.8333333333333334,
            "segment": [0.8333333333333334],
        },
        "rouge-1.5.5.2.precision": {
            "corpus": 0.8333333333333334,
            "segment": [0.8333333333333334],
        },
        "rouge-1.5.5.2.recall": {
            "corpus": 0.8333333333333334,
            "segment": [0.8333333333333334],
        },
        "rouge-1.5.5.L.f": {
            "corpus": 0.5714285714285714,
            "segment": [0.5714285714285714],
        },
        "rouge-1.5.5.L.precision": {
            "corpus": 0.5714285714285714,
            "segment": [0.5714285714285714],
        },
        "rouge-1.5.5.L.recall": {
            "corpus": 0.5714285714285714,
            "segment": [0.5714285714285714],
        },
    },
    "T02_shift_beyond_50": {
        "tercom": {"corpus": 0.2857142857142857, "segment": [0.2857142857142857]},
        "sacrebleu.ter": {
            "corpus": 0.2857142857142857,
            "segment": [0.2857142857142857],
        },
        "sacrebleu.chrf++": {
            "corpus": 0.9892660776216914,
            "segment": [0.9892660776216914],
        },
        "sacrebleu.chrf++.eps": {
            "corpus": 0.9892660776216914,
            "segment": [0.9892660776216914],
        },
        "jiwer": {"corpus": 0.2857142857142857, "segment": [0.2857142857142857]},
        "sclite": {"corpus": 0.2857142857142857, "segment": [0.2857142857142857]},
        "chrf++.py": {
            "corpus": 0.9892660776216899,
            "corpus_avg": 0.9892660776216899,
            "segment": [0.9892660776216899],
        },
        "rouge-score.1.f": {"corpus": 1.0, "segment": [1.0]},
        "rouge-score.1.precision": {"corpus": 1.0, "segment": [1.0]},
        "rouge-score.1.recall": {"corpus": 1.0, "segment": [1.0]},
        "rouge-score.2.f": {
            "corpus": 0.9855072463768116,
            "segment": [0.9855072463768116],
        },
        "rouge-score.2.precision": {
            "corpus": 0.9855072463768116,
            "segment": [0.9855072463768116],
        },
        "rouge-score.2.recall": {
            "corpus": 0.9855072463768116,
            "segment": [0.9855072463768116],
        },
        "rouge-score.L.f": {
            "corpus": 0.8571428571428571,
            "segment": [0.8571428571428571],
        },
        "rouge-score.L.precision": {
            "corpus": 0.8571428571428571,
            "segment": [0.8571428571428571],
        },
        "rouge-score.L.recall": {
            "corpus": 0.8571428571428571,
            "segment": [0.8571428571428571],
        },
        "rouge-1.5.5.1.f": {"corpus": 1.0, "segment": [1.0]},
        "rouge-1.5.5.1.precision": {"corpus": 1.0, "segment": [1.0]},
        "rouge-1.5.5.1.recall": {"corpus": 1.0, "segment": [1.0]},
        "rouge-1.5.5.2.f": {
            "corpus": 0.9855072463768116,
            "segment": [0.9855072463768116],
        },
        "rouge-1.5.5.2.precision": {
            "corpus": 0.9855072463768116,
            "segment": [0.9855072463768116],
        },
        "rouge-1.5.5.2.recall": {
            "corpus": 0.9855072463768116,
            "segment": [0.9855072463768116],
        },
        "rouge-1.5.5.L.f": {
            "corpus": 0.8571428571428571,
            "segment": [0.8571428571428571],
        },
        "rouge-1.5.5.L.precision": {
            "corpus": 0.8571428571428571,
            "segment": [0.8571428571428571],
        },
        "rouge-1.5.5.L.recall": {
            "corpus": 0.8571428571428571,
            "segment": [0.8571428571428571],
        },
    },
    "T03_repeated_words": {
        "tercom": {"corpus": 0.3333333333333333, "segment": [0.3333333333333333]},
        "sacrebleu.ter": {
            "corpus": 0.33333333333333326,
            "segment": [0.33333333333333326],
        },
        "sacrebleu.chrf++": {
            "corpus": 0.5269201350179611,
            "segment": [0.5269201350179611],
        },
        "sacrebleu.chrf++.eps": {
            "corpus": 0.5269201350179611,
            "segment": [0.5269201350179611],
        },
        "jiwer": {"corpus": 0.5555555555555556, "segment": [0.5555555555555556]},
        "sclite": {"corpus": 0.5555555555555556, "segment": [0.5555555555555556]},
        "chrf++.py": {
            "corpus": 0.52692013501796,
            "corpus_avg": 0.52692013501796,
            "segment": [0.52692013501796],
        },
        "rouge-score.1.f": {"corpus": 1.0, "segment": [1.0]},
        "rouge-score.1.precision": {"corpus": 1.0, "segment": [1.0]},
        "rouge-score.1.recall": {"corpus": 1.0, "segment": [1.0]},
        "rouge-score.2.f": {"corpus": 0.25, "segment": [0.25]},
        "rouge-score.2.precision": {"corpus": 0.25, "segment": [0.25]},
        "rouge-score.2.recall": {"corpus": 0.25, "segment": [0.25]},
        "rouge-score.L.f": {
            "corpus": 0.6666666666666666,
            "segment": [0.6666666666666666],
        },
        "rouge-score.L.precision": {
            "corpus": 0.6666666666666666,
            "segment": [0.6666666666666666],
        },
        "rouge-score.L.recall": {
            "corpus": 0.6666666666666666,
            "segment": [0.6666666666666666],
        },
        "rouge-1.5.5.1.f": {"corpus": 1.0, "segment": [1.0]},
        "rouge-1.5.5.1.precision": {"corpus": 1.0, "segment": [1.0]},
        "rouge-1.5.5.1.recall": {"corpus": 1.0, "segment": [1.0]},
        "rouge-1.5.5.2.f": {"corpus": 0.25, "segment": [0.25]},
        "rouge-1.5.5.2.precision": {"corpus": 0.25, "segment": [0.25]},
        "rouge-1.5.5.2.recall": {"corpus": 0.25, "segment": [0.25]},
        "rouge-1.5.5.L.f": {
            "corpus": 0.6666666666666666,
            "segment": [0.6666666666666666],
        },
        "rouge-1.5.5.L.precision": {
            "corpus": 0.6666666666666666,
            "segment": [0.6666666666666666],
        },
        "rouge-1.5.5.L.recall": {
            "corpus": 0.6666666666666666,
            "segment": [0.6666666666666666],
        },
    },
    "T04_case": {
        "tercom": {"corpus": 0.5, "segment": [0.5]},
        "sacrebleu.ter": {"corpus": 0.5, "segment": [0.5]},
        "sacrebleu.chrf++": {
            "corpus": 0.540320984162896,
            "segment": [0.540320984162896],
        },
        "sacrebleu.chrf++.eps": {
            "corpus": 0.540320984162896,
            "segment": [0.540320984162896],
        },
        "jiwer": {"corpus": 0.5, "segment": [0.5]},
        "sclite": {"corpus": 0.5, "segment": [0.5]},
        "chrf++.py": {
            "corpus": 0.5403209841629,
            "corpus_avg": 0.5403209841629,
            "segment": [0.5403209841629],
        },
        "rouge-score.1.f": {"corpus": 0.5, "segment": [0.5]},
        "rouge-score.1.precision": {"corpus": 0.5, "segment": [0.5]},
        "rouge-score.1.recall": {"corpus": 0.5, "segment": [0.5]},
        "rouge-score.2.f": {
            "corpus": 0.4000000000000001,
            "segment": [0.4000000000000001],
        },
        "rouge-score.2.precision": {"corpus": 0.4, "segment": [0.4]},
        "rouge-score.2.recall": {"corpus": 0.4, "segment": [0.4]},
        "rouge-score.L.f": {"corpus": 0.5, "segment": [0.5]},
        "rouge-score.L.precision": {"corpus": 0.5, "segment": [0.5]},
        "rouge-score.L.recall": {"corpus": 0.5, "segment": [0.5]},
        "rouge-1.5.5.1.f": {"corpus": 0.5, "segment": [0.5]},
        "rouge-1.5.5.1.precision": {"corpus": 0.5, "segment": [0.5]},
        "rouge-1.5.5.1.recall": {"corpus": 0.5, "segment": [0.5]},
        "rouge-1.5.5.2.f": {
            "corpus": 0.4000000000000001,
            "segment": [0.4000000000000001],
        },
        "rouge-1.5.5.2.precision": {"corpus": 0.4, "segment": [0.4]},
        "rouge-1.5.5.2.recall": {"corpus": 0.4, "segment": [0.4]},
        "rouge-1.5.5.L.f": {"corpus": 0.5, "segment": [0.5]},
        "rouge-1.5.5.L.precision": {"corpus": 0.5, "segment": [0.5]},
        "rouge-1.5.5.L.recall": {"corpus": 0.5, "segment": [0.5]},
    },
    "T05_punctuation": {
        "tercom": {"corpus": 1.4, "segment": [1.4]},
        "sacrebleu.ter": {"corpus": 1.4, "segment": [1.4]},
        "sacrebleu.chrf++": {
            "corpus": 0.40835375545016434,
            "segment": [0.40835375545016434],
        },
        "sacrebleu.chrf++.eps": {
            "corpus": 0.40817984720937145,
            "segment": [0.40817984720937145],
        },
        "jiwer": {"corpus": 1.4, "segment": [1.4]},
        "sclite": {"corpus": 1.4, "segment": [1.4]},
        "chrf++.py": {
            "corpus": 0.40817984720937,
            "corpus_avg": 0.40817984720937,
            "segment": [0.40817984720937],
        },
        "rouge-score.1.f": {"corpus": 0.0, "segment": [0.0]},
        "rouge-score.1.precision": {"corpus": 0.0, "segment": [0.0]},
        "rouge-score.1.recall": {"corpus": 0.0, "segment": [0.0]},
        "rouge-score.2.f": {"corpus": 0.0, "segment": [0.0]},
        "rouge-score.2.precision": {"corpus": 0.0, "segment": [0.0]},
        "rouge-score.2.recall": {"corpus": 0.0, "segment": [0.0]},
        "rouge-score.L.f": {"corpus": 0.0, "segment": [0.0]},
        "rouge-score.L.precision": {"corpus": 0.0, "segment": [0.0]},
        "rouge-score.L.recall": {"corpus": 0.0, "segment": [0.0]},
        "rouge-1.5.5.1.f": {"corpus": 0.0, "segment": [0.0]},
        "rouge-1.5.5.1.precision": {"corpus": 0.0, "segment": [0.0]},
        "rouge-1.5.5.1.recall": {"corpus": 0.0, "segment": [0.0]},
        "rouge-1.5.5.2.f": {"corpus": 0.0, "segment": [0.0]},
        "rouge-1.5.5.2.precision": {"corpus": 0.0, "segment": [0.0]},
        "rouge-1.5.5.2.recall": {"corpus": 0.0, "segment": [0.0]},
        "rouge-1.5.5.L.f": {"corpus": 0.0, "segment": [0.0]},
        "rouge-1.5.5.L.precision": {"corpus": 0.0, "segment": [0.0]},
        "rouge-1.5.5.L.recall": {"corpus": 0.0, "segment": [0.0]},
    },
    "T06_long_scrambled": {
        "tercom": {"corpus": 1.0, "segment": [1.0]},
        "sacrebleu.ter": {"corpus": 0.85, "segment": [0.85]},
        "sacrebleu.chrf++": {
            "corpus": 0.8515632641496748,
            "segment": [0.8515632641496748],
        },
        "sacrebleu.chrf++.eps": {
            "corpus": 0.8515630193692602,
            "segment": [0.8515630193692602],
        },
        "jiwer": {"corpus": 0.8583333333333333, "segment": [0.8583333333333333]},
        "sclite": {"corpus": 1.0416666666666667, "segment": [1.0416666666666667]},
        "chrf++.py": {
            "corpus": 0.85156301936926,
            "corpus_avg": 0.85156301936926,
            "segment": [0.85156301936926],
        },
        "rouge-score.1.f": {
            "corpus": 0.9166666666666666,
            "segment": [0.9166666666666666],
        },
        "rouge-score.1.precision": {
            "corpus": 0.9166666666666666,
            "segment": [0.9166666666666666],
        },
        "rouge-score.1.recall": {
            "corpus": 0.9166666666666666,
            "segment": [0.9166666666666666],
        },
        "rouge-score.2.f": {
            "corpus": 0.7478991596638656,
            "segment": [0.7478991596638656],
        },
        "rouge-score.2.precision": {
            "corpus": 0.7478991596638656,
            "segment": [0.7478991596638656],
        },
        "rouge-score.2.recall": {
            "corpus": 0.7478991596638656,
            "segment": [0.7478991596638656],
        },
        "rouge-score.L.f": {
            "corpus": 0.4583333333333333,
            "segment": [0.4583333333333333],
        },
        "rouge-score.L.precision": {
            "corpus": 0.4583333333333333,
            "segment": [0.4583333333333333],
        },
        "rouge-score.L.recall": {
            "corpus": 0.4583333333333333,
            "segment": [0.4583333333333333],
        },
        "rouge-1.5.5.1.f": {
            "corpus": 0.9166666666666666,
            "segment": [0.9166666666666666],
        },
        "rouge-1.5.5.1.precision": {
            "corpus": 0.9166666666666666,
            "segment": [0.9166666666666666],
        },
        "rouge-1.5.5.1.recall": {
            "corpus": 0.9166666666666666,
            "segment": [0.9166666666666666],
        },
        "rouge-1.5.5.2.f": {
            "corpus": 0.7478991596638656,
            "segment": [0.7478991596638656],
        },
        "rouge-1.5.5.2.precision": {
            "corpus": 0.7478991596638656,
            "segment": [0.7478991596638656],
        },
        "rouge-1.5.5.2.recall": {
            "corpus": 0.7478991596638656,
            "segment": [0.7478991596638656],
        },
        "rouge-1.5.5.L.f": {
            "corpus": 0.4583333333333333,
            "segment": [0.4583333333333333],
        },
        "rouge-1.5.5.L.precision": {
            "corpus": 0.4583333333333333,
            "segment": [0.4583333333333333],
        },
        "rouge-1.5.5.L.recall": {
            "corpus": 0.4583333333333333,
            "segment": [0.4583333333333333],
        },
    },
    "T07_multi_ref_shift": {
        "tercom": {"corpus": 0.42857142857142855, "segment": [0.42857142857142855]},
        "sacrebleu.ter": {
            "corpus": 0.42857142857142855,
            "segment": [0.42857142857142855],
        },
        "sacrebleu.chrf++": {
            "corpus": 0.35833333333333334,
            "segment": [0.35833333333333334],
        },
        "sacrebleu.chrf++.eps": {
            "corpus": 0.35833333333333334,
            "segment": [0.35833333333333334],
        },
        "jiwer": {"corpus": 0.8571428571428571, "segment": [0.8571428571428571]},
        "sclite": {"corpus": 0.8571428571428571, "segment": [0.8571428571428571]},
        "chrf++.py": {
            "corpus": 0.35833333333333,
            "corpus_avg": 0.35833333333333,
            "segment": [0.35833333333333],
        },
        "rouge-score.1.f": {"corpus": 1.0, "segment": [1.0]},
        "rouge-score.1.precision": {"corpus": 1.0, "segment": [1.0]},
        "rouge-score.1.recall": {"corpus": 1.0, "segment": [1.0]},
        "rouge-score.2.f": {
            "corpus": 0.3333333333333333,
            "segment": [0.3333333333333333],
        },
        "rouge-score.2.precision": {
            "corpus": 0.3333333333333333,
            "segment": [0.3333333333333333],
        },
        "rouge-score.2.recall": {
            "corpus": 0.3333333333333333,
            "segment": [0.3333333333333333],
        },
        "rouge-score.L.f": {
            "corpus": 0.5714285714285714,
            "segment": [0.5714285714285714],
        },
        "rouge-score.L.precision": {
            "corpus": 0.5714285714285714,
            "segment": [0.5714285714285714],
        },
        "rouge-score.L.recall": {
            "corpus": 0.5714285714285714,
            "segment": [0.5714285714285714],
        },
        "rouge-1.5.5.1.f": {"corpus": 1.0, "segment": [1.0]},
        "rouge-1.5.5.1.precision": {"corpus": 1.0, "segment": [1.0]},
        "rouge-1.5.5.1.recall": {"corpus": 1.0, "segment": [1.0]},
        "rouge-1.5.5.2.f": {
            "corpus": 0.3333333333333333,
            "segment": [0.3333333333333333],
        },
        "rouge-1.5.5.2.precision": {
            "corpus": 0.3333333333333333,
            "segment": [0.3333333333333333],
        },
        "rouge-1.5.5.2.recall": {
            "corpus": 0.3333333333333333,
            "segment": [0.3333333333333333],
        },
        "rouge-1.5.5.L.f": {"corpus": 0.5, "segment": [0.5]},
        "rouge-1.5.5.L.precision": {"corpus": 0.5, "segment": [0.5]},
        "rouge-1.5.5.L.recall": {"corpus": 0.5, "segment": [0.5]},
    },
    "T08_corpus_mix": {
        "tercom": {
            "corpus": 0.1875,
            "segment": [0.0, 0.14285714285714285, 0.6666666666666666],
        },
        "sacrebleu.ter": {
            "corpus": 0.1875,
            "segment": [0.0, 0.14285714285714285, 0.6666666666666665],
        },
        "sacrebleu.chrf++": {
            "corpus": 0.8398692731255015,
            "segment": [1.0, 0.8561026493930907, 0.4819218515170614],
        },
        "sacrebleu.chrf++.eps": {
            "corpus": 0.8396997950572697,
            "segment": [1.0, 0.8561026493930904, 0.47968397345059577],
        },
        "jiwer": {
            "corpus": 0.5,
            "segment": [0.0, 0.8571428571428571, 0.6666666666666666],
        },
        "sclite": {
            "corpus": 0.5,
            "segment": [0.0, 0.8571428571428571, 0.6666666666666666],
        },
        "chrf++.py": {
            "corpus": 0.83969979505727,
            "corpus_avg": 0.7785955409479,
            "segment": [1.0, 0.85610264939309, 0.4796839734506],
        },
        "rouge-score.1.f": {
            "corpus": 0.8888888888888888,
            "segment": [1.0, 1.0, 0.6666666666666666],
        },
        "rouge-score.1.precision": {
            "corpus": 0.8888888888888888,
            "segment": [1.0, 1.0, 0.6666666666666666],
        },
        "rouge-score.1.recall": {
            "corpus": 0.8888888888888888,
            "segment": [1.0, 1.0, 0.6666666666666666],
        },
        "rouge-score.2.f": {
            "corpus": 0.7777777777777778,
            "segment": [1.0, 0.8333333333333334, 0.5],
        },
        "rouge-score.2.precision": {
            "corpus": 0.7777777777777778,
            "segment": [1.0, 0.8333333333333334, 0.5],
        },
        "rouge-score.2.recall": {
            "corpus": 0.7777777777777778,
            "segment": [1.0, 0.8333333333333334, 0.5],
        },
        "rouge-score.L.f": {
            "corpus": 0.746031746031746,
            "segment": [1.0, 0.5714285714285714, 0.6666666666666666],
        },
        "rouge-score.L.precision": {
            "corpus": 0.746031746031746,
            "segment": [1.0, 0.5714285714285714, 0.6666666666666666],
        },
        "rouge-score.L.recall": {
            "corpus": 0.746031746031746,
            "segment": [1.0, 0.5714285714285714, 0.6666666666666666],
        },
        "rouge-1.5.5.1.f": {
            "corpus": 0.8888888888888888,
            "segment": [1.0, 1.0, 0.6666666666666666],
        },
        "rouge-1.5.5.1.precision": {
            "corpus": 0.8888888888888888,
            "segment": [1.0, 1.0, 0.6666666666666666],
        },
        "rouge-1.5.5.1.recall": {
            "corpus": 0.8888888888888888,
            "segment": [1.0, 1.0, 0.6666666666666666],
        },
        "rouge-1.5.5.2.f": {
            "corpus": 0.7777777777777778,
            "segment": [1.0, 0.8333333333333334, 0.5],
        },
        "rouge-1.5.5.2.precision": {
            "corpus": 0.7777777777777778,
            "segment": [1.0, 0.8333333333333334, 0.5],
        },
        "rouge-1.5.5.2.recall": {
            "corpus": 0.7777777777777778,
            "segment": [1.0, 0.8333333333333334, 0.5],
        },
        "rouge-1.5.5.L.f": {
            "corpus": 0.746031746031746,
            "segment": [1.0, 0.5714285714285714, 0.6666666666666666],
        },
        "rouge-1.5.5.L.precision": {
            "corpus": 0.746031746031746,
            "segment": [1.0, 0.5714285714285714, 0.6666666666666666],
        },
        "rouge-1.5.5.L.recall": {
            "corpus": 0.746031746031746,
            "segment": [1.0, 0.5714285714285714, 0.6666666666666666],
        },
    },
    "M_tercom_beam_1": {
        "tercom": {"corpus": 0.8333333333333334, "segment": [0.8333333333333334]},
        "sacrebleu.ter": {
            "corpus": 0.8666666666666667,
            "segment": [0.8666666666666667],
        },
        "sacrebleu.chrf++": {
            "corpus": 0.13188029299255455,
            "segment": [0.13188029299255455],
        },
        "sacrebleu.chrf++.eps": {
            "corpus": 0.13181953593437015,
            "segment": [0.13181953593437015],
        },
        "jiwer": {"corpus": 0.8666666666666667, "segment": [0.8666666666666667]},
        "sclite": {"corpus": 0.8666666666666667, "segment": [0.8666666666666667]},
        "chrf++.py": {
            "corpus": 0.13181953593436999,
            "corpus_avg": 0.13181953593436999,
            "segment": [0.13181953593436999],
        },
        "rouge-score.1.f": {
            "corpus": 0.33333333333333337,
            "segment": [0.33333333333333337],
        },
        "rouge-score.1.precision": {"corpus": 1.0, "segment": [1.0]},
        "rouge-score.1.recall": {"corpus": 0.2, "segment": [0.2]},
        "rouge-score.2.f": {
            "corpus": 0.1176470588235294,
            "segment": [0.1176470588235294],
        },
        "rouge-score.2.precision": {"corpus": 0.4, "segment": [0.4]},
        "rouge-score.2.recall": {
            "corpus": 0.06896551724137931,
            "segment": [0.06896551724137931],
        },
        "rouge-score.L.f": {
            "corpus": 0.2222222222222222,
            "segment": [0.2222222222222222],
        },
        "rouge-score.L.precision": {
            "corpus": 0.6666666666666666,
            "segment": [0.6666666666666666],
        },
        "rouge-score.L.recall": {
            "corpus": 0.13333333333333333,
            "segment": [0.13333333333333333],
        },
        "rouge-1.5.5.1.f": {
            "corpus": 0.33333333333333337,
            "segment": [0.33333333333333337],
        },
        "rouge-1.5.5.1.precision": {"corpus": 1.0, "segment": [1.0]},
        "rouge-1.5.5.1.recall": {"corpus": 0.2, "segment": [0.2]},
        "rouge-1.5.5.2.f": {
            "corpus": 0.1176470588235294,
            "segment": [0.1176470588235294],
        },
        "rouge-1.5.5.2.precision": {"corpus": 0.4, "segment": [0.4]},
        "rouge-1.5.5.2.recall": {
            "corpus": 0.06896551724137931,
            "segment": [0.06896551724137931],
        },
        "rouge-1.5.5.L.f": {
            "corpus": 0.2222222222222222,
            "segment": [0.2222222222222222],
        },
        "rouge-1.5.5.L.precision": {
            "corpus": 0.6666666666666666,
            "segment": [0.6666666666666666],
        },
        "rouge-1.5.5.L.recall": {
            "corpus": 0.13333333333333333,
            "segment": [0.13333333333333333],
        },
    },
    "M_tercom_beam_2": {
        "tercom": {"corpus": 0.972972972972973, "segment": [0.972972972972973]},
        "sacrebleu.ter": {"corpus": 0.918918918918919, "segment": [0.918918918918919]},
        "sacrebleu.chrf++": {
            "corpus": 0.08708952413653898,
            "segment": [0.08708952413653898],
        },
        "sacrebleu.chrf++.eps": {
            "corpus": 0.08705411543947247,
            "segment": [0.08705411543947247],
        },
        "jiwer": {"corpus": 0.918918918918919, "segment": [0.918918918918919]},
        "sclite": {"corpus": 0.918918918918919, "segment": [0.918918918918919]},
        "chrf++.py": {
            "corpus": 0.08705411543946999,
            "corpus_avg": 0.08705411543946999,
            "segment": [0.08705411543946999],
        },
        "rouge-score.1.f": {
            "corpus": 0.1951219512195122,
            "segment": [0.1951219512195122],
        },
        "rouge-score.1.precision": {"corpus": 1.0, "segment": [1.0]},
        "rouge-score.1.recall": {
            "corpus": 0.10810810810810811,
            "segment": [0.10810810810810811],
        },
        "rouge-score.2.f": {
            "corpus": 0.05128205128205128,
            "segment": [0.05128205128205128],
        },
        "rouge-score.2.precision": {
            "corpus": 0.3333333333333333,
            "segment": [0.3333333333333333],
        },
        "rouge-score.2.recall": {
            "corpus": 0.027777777777777776,
            "segment": [0.027777777777777776],
        },
        "rouge-score.L.f": {
            "corpus": 0.14634146341463414,
            "segment": [0.14634146341463414],
        },
        "rouge-score.L.precision": {"corpus": 0.75, "segment": [0.75]},
        "rouge-score.L.recall": {
            "corpus": 0.08108108108108109,
            "segment": [0.08108108108108109],
        },
        "rouge-1.5.5.1.f": {
            "corpus": 0.1951219512195122,
            "segment": [0.1951219512195122],
        },
        "rouge-1.5.5.1.precision": {"corpus": 1.0, "segment": [1.0]},
        "rouge-1.5.5.1.recall": {
            "corpus": 0.10810810810810811,
            "segment": [0.10810810810810811],
        },
        "rouge-1.5.5.2.f": {
            "corpus": 0.05128205128205128,
            "segment": [0.05128205128205128],
        },
        "rouge-1.5.5.2.precision": {
            "corpus": 0.3333333333333333,
            "segment": [0.3333333333333333],
        },
        "rouge-1.5.5.2.recall": {
            "corpus": 0.027777777777777776,
            "segment": [0.027777777777777776],
        },
        "rouge-1.5.5.L.f": {
            "corpus": 0.14634146341463414,
            "segment": [0.14634146341463414],
        },
        "rouge-1.5.5.L.precision": {"corpus": 0.75, "segment": [0.75]},
        "rouge-1.5.5.L.recall": {
            "corpus": 0.08108108108108109,
            "segment": [0.08108108108108109],
        },
    },
    "M_tercom_beam_3": {
        "tercom": {"corpus": 0.8888888888888888, "segment": [0.8888888888888888]},
        "sacrebleu.ter": {
            "corpus": 0.8611111111111112,
            "segment": [0.8611111111111112],
        },
        "sacrebleu.chrf++": {
            "corpus": 0.1722525771054744,
            "segment": [0.1722525771054744],
        },
        "sacrebleu.chrf++.eps": {
            "corpus": 0.17223147950084133,
            "segment": [0.17223147950084133],
        },
        "jiwer": {"corpus": 0.8888888888888888, "segment": [0.8888888888888888]},
        "sclite": {"corpus": 0.8888888888888888, "segment": [0.8888888888888888]},
        "chrf++.py": {
            "corpus": 0.17223147950084003,
            "corpus_avg": 0.17223147950084003,
            "segment": [0.17223147950084003],
        },
        "rouge-score.1.f": {"corpus": 0.4, "segment": [0.4]},
        "rouge-score.1.precision": {"corpus": 1.0, "segment": [1.0]},
        "rouge-score.1.recall": {"corpus": 0.25, "segment": [0.25]},
        "rouge-score.2.f": {
            "corpus": 0.04651162790697674,
            "segment": [0.04651162790697674],
        },
        "rouge-score.2.precision": {"corpus": 0.125, "segment": [0.125]},
        "rouge-score.2.recall": {
            "corpus": 0.02857142857142857,
            "segment": [0.02857142857142857],
        },
        "rouge-score.L.f": {
            "corpus": 0.22222222222222227,
            "segment": [0.22222222222222227],
        },
        "rouge-score.L.precision": {
            "corpus": 0.5555555555555556,
            "segment": [0.5555555555555556],
        },
        "rouge-score.L.recall": {
            "corpus": 0.1388888888888889,
            "segment": [0.1388888888888889],
        },
        "rouge-1.5.5.1.f": {"corpus": 0.4, "segment": [0.4]},
        "rouge-1.5.5.1.precision": {"corpus": 1.0, "segment": [1.0]},
        "rouge-1.5.5.1.recall": {"corpus": 0.25, "segment": [0.25]},
        "rouge-1.5.5.2.f": {
            "corpus": 0.04651162790697674,
            "segment": [0.04651162790697674],
        },
        "rouge-1.5.5.2.precision": {"corpus": 0.125, "segment": [0.125]},
        "rouge-1.5.5.2.recall": {
            "corpus": 0.02857142857142857,
            "segment": [0.02857142857142857],
        },
        "rouge-1.5.5.L.f": {
            "corpus": 0.22222222222222227,
            "segment": [0.22222222222222227],
        },
        "rouge-1.5.5.L.precision": {
            "corpus": 0.5555555555555556,
            "segment": [0.5555555555555556],
        },
        "rouge-1.5.5.L.recall": {
            "corpus": 0.1388888888888889,
            "segment": [0.1388888888888889],
        },
    },
    "M_sacrebleu_beam_1": {
        "tercom": {"corpus": 0.9705882352941176, "segment": [0.9705882352941176]},
        "sacrebleu.ter": {
            "corpus": 0.9705882352941176,
            "segment": [0.9705882352941176],
        },
        "sacrebleu.chrf++": {
            "corpus": 0.021926937055406027,
            "segment": [0.021926937055406027],
        },
        "sacrebleu.chrf++.eps": {
            "corpus": 0.02192324395749458,
            "segment": [0.02192324395749458],
        },
        "jiwer": {"corpus": 0.9705882352941176, "segment": [0.9705882352941176]},
        "sclite": {"corpus": 0.9705882352941176, "segment": [0.9705882352941176]},
        "chrf++.py": {
            "corpus": 0.02192324395749,
            "corpus_avg": 0.02192324395749,
            "segment": [0.02192324395749],
        },
        "rouge-score.1.f": {
            "corpus": 0.05555555555555555,
            "segment": [0.05555555555555555],
        },
        "rouge-score.1.precision": {"corpus": 0.5, "segment": [0.5]},
        "rouge-score.1.recall": {
            "corpus": 0.029411764705882353,
            "segment": [0.029411764705882353],
        },
        "rouge-score.2.f": {"corpus": 0.0, "segment": [0.0]},
        "rouge-score.2.precision": {"corpus": 0.0, "segment": [0.0]},
        "rouge-score.2.recall": {"corpus": 0.0, "segment": [0.0]},
        "rouge-score.L.f": {
            "corpus": 0.05555555555555555,
            "segment": [0.05555555555555555],
        },
        "rouge-score.L.precision": {"corpus": 0.5, "segment": [0.5]},
        "rouge-score.L.recall": {
            "corpus": 0.029411764705882353,
            "segment": [0.029411764705882353],
        },
        "rouge-1.5.5.1.f": {
            "corpus": 0.05555555555555555,
            "segment": [0.05555555555555555],
        },
        "rouge-1.5.5.1.precision": {"corpus": 0.5, "segment": [0.5]},
        "rouge-1.5.5.1.recall": {
            "corpus": 0.029411764705882353,
            "segment": [0.029411764705882353],
        },
        "rouge-1.5.5.2.f": {"corpus": 0.0, "segment": [0.0]},
        "rouge-1.5.5.2.precision": {"corpus": 0.0, "segment": [0.0]},
        "rouge-1.5.5.2.recall": {"corpus": 0.0, "segment": [0.0]},
        "rouge-1.5.5.L.f": {
            "corpus": 0.05555555555555555,
            "segment": [0.05555555555555555],
        },
        "rouge-1.5.5.L.precision": {"corpus": 0.5, "segment": [0.5]},
        "rouge-1.5.5.L.recall": {
            "corpus": 0.029411764705882353,
            "segment": [0.029411764705882353],
        },
    },
    "M_sacrebleu_beam_2": {
        "tercom": {"corpus": 0.49, "segment": [0.49]},
        "sacrebleu.ter": {"corpus": 0.46, "segment": [0.46]},
        "sacrebleu.chrf++": {
            "corpus": 0.8641665602383238,
            "segment": [0.8641665602383238],
        },
        "sacrebleu.chrf++.eps": {
            "corpus": 0.864166477027288,
            "segment": [0.864166477027288],
        },
        "jiwer": {"corpus": 0.54, "segment": [0.54]},
        "sclite": {"corpus": 0.54, "segment": [0.54]},
        "chrf++.py": {
            "corpus": 0.86416647702729,
            "corpus_avg": 0.86416647702729,
            "segment": [0.86416647702729],
        },
        "rouge-score.1.f": {
            "corpus": 0.9547738693467336,
            "segment": [0.9547738693467336],
        },
        "rouge-score.1.precision": {
            "corpus": 0.9595959595959596,
            "segment": [0.9595959595959596],
        },
        "rouge-score.1.recall": {"corpus": 0.95, "segment": [0.95]},
        "rouge-score.2.f": {
            "corpus": 0.7918781725888324,
            "segment": [0.7918781725888324],
        },
        "rouge-score.2.precision": {
            "corpus": 0.7959183673469388,
            "segment": [0.7959183673469388],
        },
        "rouge-score.2.recall": {
            "corpus": 0.7878787878787878,
            "segment": [0.7878787878787878],
        },
        "rouge-score.L.f": {
            "corpus": 0.7035175879396985,
            "segment": [0.7035175879396985],
        },
        "rouge-score.L.precision": {
            "corpus": 0.7070707070707071,
            "segment": [0.7070707070707071],
        },
        "rouge-score.L.recall": {"corpus": 0.7, "segment": [0.7]},
        "rouge-1.5.5.1.f": {
            "corpus": 0.9547738693467336,
            "segment": [0.9547738693467336],
        },
        "rouge-1.5.5.1.precision": {
            "corpus": 0.9595959595959596,
            "segment": [0.9595959595959596],
        },
        "rouge-1.5.5.1.recall": {"corpus": 0.95, "segment": [0.95]},
        "rouge-1.5.5.2.f": {
            "corpus": 0.7918781725888324,
            "segment": [0.7918781725888324],
        },
        "rouge-1.5.5.2.precision": {
            "corpus": 0.7959183673469388,
            "segment": [0.7959183673469388],
        },
        "rouge-1.5.5.2.recall": {
            "corpus": 0.7878787878787878,
            "segment": [0.7878787878787878],
        },
        "rouge-1.5.5.L.f": {
            "corpus": 0.7035175879396985,
            "segment": [0.7035175879396985],
        },
        "rouge-1.5.5.L.precision": {
            "corpus": 0.7070707070707071,
            "segment": [0.7070707070707071],
        },
        "rouge-1.5.5.L.recall": {"corpus": 0.7, "segment": [0.7]},
    },
    "M_sacrebleu_beam_3": {
        "tercom": {"corpus": 0.36, "segment": [0.36]},
        "sacrebleu.ter": {"corpus": 0.26, "segment": [0.26]},
        "sacrebleu.chrf++": {
            "corpus": 0.9241579482560767,
            "segment": [0.9241579482560767],
        },
        "sacrebleu.chrf++.eps": {
            "corpus": 0.924157934558919,
            "segment": [0.924157934558919],
        },
        "jiwer": {"corpus": 0.54, "segment": [0.54]},
        "sclite": {"corpus": 0.57, "segment": [0.57]},
        "chrf++.py": {
            "corpus": 0.92415793455892,
            "corpus_avg": 0.92415793455892,
            "segment": [0.92415793455892],
        },
        "rouge-score.1.f": {
            "corpus": 0.9949748743718593,
            "segment": [0.9949748743718593],
        },
        "rouge-score.1.precision": {"corpus": 1.0, "segment": [1.0]},
        "rouge-score.1.recall": {"corpus": 0.99, "segment": [0.99]},
        "rouge-score.2.f": {
            "corpus": 0.8629441624365481,
            "segment": [0.8629441624365481],
        },
        "rouge-score.2.precision": {
            "corpus": 0.8673469387755102,
            "segment": [0.8673469387755102],
        },
        "rouge-score.2.recall": {
            "corpus": 0.8585858585858586,
            "segment": [0.8585858585858586],
        },
        "rouge-score.L.f": {
            "corpus": 0.6733668341708543,
            "segment": [0.6733668341708543],
        },
        "rouge-score.L.precision": {
            "corpus": 0.6767676767676768,
            "segment": [0.6767676767676768],
        },
        "rouge-score.L.recall": {"corpus": 0.67, "segment": [0.67]},
        "rouge-1.5.5.1.f": {
            "corpus": 0.9949748743718593,
            "segment": [0.9949748743718593],
        },
        "rouge-1.5.5.1.precision": {"corpus": 1.0, "segment": [1.0]},
        "rouge-1.5.5.1.recall": {"corpus": 0.99, "segment": [0.99]},
        "rouge-1.5.5.2.f": {
            "corpus": 0.8629441624365481,
            "segment": [0.8629441624365481],
        },
        "rouge-1.5.5.2.precision": {
            "corpus": 0.8673469387755102,
            "segment": [0.8673469387755102],
        },
        "rouge-1.5.5.2.recall": {
            "corpus": 0.8585858585858586,
            "segment": [0.8585858585858586],
        },
        "rouge-1.5.5.L.f": {
            "corpus": 0.6733668341708543,
            "segment": [0.6733668341708543],
        },
        "rouge-1.5.5.L.precision": {
            "corpus": 0.6767676767676768,
            "segment": [0.6767676767676768],
        },
        "rouge-1.5.5.L.recall": {"corpus": 0.67, "segment": [0.67]},
    },
    "M_sacrebleu_ranking_1": {
        "tercom": {"corpus": 0.4, "segment": [0.4]},
        "sacrebleu.ter": {"corpus": 0.4, "segment": [0.4]},
        "sacrebleu.chrf++": {
            "corpus": 0.618299062049062,
            "segment": [0.618299062049062],
        },
        "sacrebleu.chrf++.eps": {
            "corpus": 0.618299062049062,
            "segment": [0.618299062049062],
        },
        "jiwer": {"corpus": 0.8, "segment": [0.8]},
        "sclite": {"corpus": 0.8, "segment": [0.8]},
        "chrf++.py": {
            "corpus": 0.61829906204906,
            "corpus_avg": 0.61829906204906,
            "segment": [0.61829906204906],
        },
        "rouge-score.1.f": {"corpus": 1.0, "segment": [1.0]},
        "rouge-score.1.precision": {"corpus": 1.0, "segment": [1.0]},
        "rouge-score.1.recall": {"corpus": 1.0, "segment": [1.0]},
        "rouge-score.2.f": {"corpus": 0.5, "segment": [0.5]},
        "rouge-score.2.precision": {"corpus": 0.5, "segment": [0.5]},
        "rouge-score.2.recall": {"corpus": 0.5, "segment": [0.5]},
        "rouge-score.L.f": {
            "corpus": 0.4000000000000001,
            "segment": [0.4000000000000001],
        },
        "rouge-score.L.precision": {"corpus": 0.4, "segment": [0.4]},
        "rouge-score.L.recall": {"corpus": 0.4, "segment": [0.4]},
        "rouge-1.5.5.1.f": {"corpus": 1.0, "segment": [1.0]},
        "rouge-1.5.5.1.precision": {"corpus": 1.0, "segment": [1.0]},
        "rouge-1.5.5.1.recall": {"corpus": 1.0, "segment": [1.0]},
        "rouge-1.5.5.2.f": {"corpus": 0.5, "segment": [0.5]},
        "rouge-1.5.5.2.precision": {"corpus": 0.5, "segment": [0.5]},
        "rouge-1.5.5.2.recall": {"corpus": 0.5, "segment": [0.5]},
        "rouge-1.5.5.L.f": {
            "corpus": 0.4000000000000001,
            "segment": [0.4000000000000001],
        },
        "rouge-1.5.5.L.precision": {"corpus": 0.4, "segment": [0.4]},
        "rouge-1.5.5.L.recall": {"corpus": 0.4, "segment": [0.4]},
    },
    "M_sacrebleu_ranking_2": {
        "tercom": {"corpus": 0.5, "segment": [0.5]},
        "sacrebleu.ter": {"corpus": 0.5, "segment": [0.5]},
        "sacrebleu.chrf++": {
            "corpus": 0.5831984219126247,
            "segment": [0.5831984219126247],
        },
        "sacrebleu.chrf++.eps": {
            "corpus": 0.5831984219126247,
            "segment": [0.5831984219126247],
        },
        "jiwer": {"corpus": 0.7, "segment": [0.7]},
        "sclite": {"corpus": 0.7, "segment": [0.7]},
        "chrf++.py": {
            "corpus": 0.58319842191262,
            "corpus_avg": 0.58319842191262,
            "segment": [0.58319842191262],
        },
        "rouge-score.1.f": {"corpus": 1.0, "segment": [1.0]},
        "rouge-score.1.precision": {"corpus": 1.0, "segment": [1.0]},
        "rouge-score.1.recall": {"corpus": 1.0, "segment": [1.0]},
        "rouge-score.2.f": {
            "corpus": 0.4444444444444444,
            "segment": [0.4444444444444444],
        },
        "rouge-score.2.precision": {
            "corpus": 0.4444444444444444,
            "segment": [0.4444444444444444],
        },
        "rouge-score.2.recall": {
            "corpus": 0.4444444444444444,
            "segment": [0.4444444444444444],
        },
        "rouge-score.L.f": {"corpus": 0.5, "segment": [0.5]},
        "rouge-score.L.precision": {"corpus": 0.5, "segment": [0.5]},
        "rouge-score.L.recall": {"corpus": 0.5, "segment": [0.5]},
        "rouge-1.5.5.1.f": {"corpus": 1.0, "segment": [1.0]},
        "rouge-1.5.5.1.precision": {"corpus": 1.0, "segment": [1.0]},
        "rouge-1.5.5.1.recall": {"corpus": 1.0, "segment": [1.0]},
        "rouge-1.5.5.2.f": {
            "corpus": 0.4444444444444444,
            "segment": [0.4444444444444444],
        },
        "rouge-1.5.5.2.precision": {
            "corpus": 0.4444444444444444,
            "segment": [0.4444444444444444],
        },
        "rouge-1.5.5.2.recall": {
            "corpus": 0.4444444444444444,
            "segment": [0.4444444444444444],
        },
        "rouge-1.5.5.L.f": {"corpus": 0.5, "segment": [0.5]},
        "rouge-1.5.5.L.precision": {"corpus": 0.5, "segment": [0.5]},
        "rouge-1.5.5.L.recall": {"corpus": 0.5, "segment": [0.5]},
    },
    "M_sacrebleu_ranking_3": {
        "tercom": {"corpus": 0.25, "segment": [0.25]},
        "sacrebleu.ter": {"corpus": 0.25, "segment": [0.25]},
        "sacrebleu.chrf++": {
            "corpus": 0.8056511709114687,
            "segment": [0.8056511709114687],
        },
        "sacrebleu.chrf++.eps": {
            "corpus": 0.8056511709114687,
            "segment": [0.8056511709114687],
        },
        "jiwer": {"corpus": 0.3333333333333333, "segment": [0.3333333333333333]},
        "sclite": {"corpus": 0.3333333333333333, "segment": [0.3333333333333333]},
        "chrf++.py": {
            "corpus": 0.80565117091147,
            "corpus_avg": 0.80565117091147,
            "segment": [0.80565117091147],
        },
        "rouge-score.1.f": {"corpus": 1.0, "segment": [1.0]},
        "rouge-score.1.precision": {"corpus": 1.0, "segment": [1.0]},
        "rouge-score.1.recall": {"corpus": 1.0, "segment": [1.0]},
        "rouge-score.2.f": {
            "corpus": 0.7272727272727273,
            "segment": [0.7272727272727273],
        },
        "rouge-score.2.precision": {
            "corpus": 0.7272727272727273,
            "segment": [0.7272727272727273],
        },
        "rouge-score.2.recall": {
            "corpus": 0.7272727272727273,
            "segment": [0.7272727272727273],
        },
        "rouge-score.L.f": {
            "corpus": 0.8333333333333334,
            "segment": [0.8333333333333334],
        },
        "rouge-score.L.precision": {
            "corpus": 0.8333333333333334,
            "segment": [0.8333333333333334],
        },
        "rouge-score.L.recall": {
            "corpus": 0.8333333333333334,
            "segment": [0.8333333333333334],
        },
        "rouge-1.5.5.1.f": {"corpus": 1.0, "segment": [1.0]},
        "rouge-1.5.5.1.precision": {"corpus": 1.0, "segment": [1.0]},
        "rouge-1.5.5.1.recall": {"corpus": 1.0, "segment": [1.0]},
        "rouge-1.5.5.2.f": {
            "corpus": 0.7272727272727273,
            "segment": [0.7272727272727273],
        },
        "rouge-1.5.5.2.precision": {
            "corpus": 0.7272727272727273,
            "segment": [0.7272727272727273],
        },
        "rouge-1.5.5.2.recall": {
            "corpus": 0.7272727272727273,
            "segment": [0.7272727272727273],
        },
        "rouge-1.5.5.L.f": {
            "corpus": 0.8333333333333334,
            "segment": [0.8333333333333334],
        },
        "rouge-1.5.5.L.precision": {
            "corpus": 0.8333333333333334,
            "segment": [0.8333333333333334],
        },
        "rouge-1.5.5.L.recall": {
            "corpus": 0.8333333333333334,
            "segment": [0.8333333333333334],
        },
    },
}
