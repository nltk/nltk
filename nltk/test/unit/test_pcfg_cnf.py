"""Probability and compatibility regressions for PCFG CNF conversion."""

from collections import defaultdict
from itertools import product
from math import fsum, isclose
from random import Random

import pytest

from nltk import CFG, PCFG, Nonterminal, ProbabilisticProduction
from nltk.grammar import is_nonterminal
from nltk.parse import InsideChartParser, ViterbiParser


def inside(grammar, tokens):
    """Independent CKY sum over every CNF parse of a token sequence."""
    chart = defaultdict(float)
    for width in range(1, len(tokens) + 1):
        for start in range(len(tokens) - width + 1):
            end = start + width
            for rule in grammar.productions():
                rhs = rule.rhs()
                if width == 1 and rhs == (tokens[start],):
                    chart[start, end, rule.lhs()] += rule.prob()
                elif len(rhs) == 2:
                    chart[start, end, rule.lhs()] += rule.prob() * fsum(
                        chart[start, split, rhs[0]] * chart[split, end, rhs[1]]
                        for split in range(start + 1, end)
                    )
    return chart[0, len(tokens), grammar.start()]


def enumerate_distribution(grammar):
    """Enumerate leftmost derivations of the small acyclic input fixtures."""
    pending = [((grammar.start(),), 1.0)]
    result = defaultdict(float)
    while pending:
        symbols, probability = pending.pop()
        for index, symbol in enumerate(symbols):
            if is_nonterminal(symbol):
                for rule in grammar.productions(lhs=symbol):
                    pending.append(
                        (
                            symbols[:index] + rule.rhs() + symbols[index + 1 :],
                            probability * rule.prob(),
                        )
                    )
                break
        else:
            result[symbols] += probability
    return dict(result)


def assert_cnf(grammar):
    assert isinstance(grammar, PCFG)
    assert grammar.is_chomsky_normal_form()
    totals = defaultdict(list)
    for rule in grammar.productions():
        assert isinstance(rule, ProbabilisticProduction)
        assert 0 < rule.prob() <= 1
        totals[rule.lhs()].append(rule.prob())
    assert all(
        isclose(fsum(values), 1, rel_tol=0, abs_tol=1e-12) for values in totals.values()
    )


ACYCLIC_GRAMMARS = [
    "S -> VP [1]\nVP -> V [1]\nV -> 'v' [0.3] | 'a' [0.7]",
    "S -> A B C [0.4] | A B [0.6]\nA -> 'a' [1]\nB -> 'b' [1]\nC -> 'c' [1]",
    "S -> A B C [0.4] | A B D [0.6]\nA -> 'a' [1]\nB -> 'b' [1]\nC -> 'c' [1]\nD -> 'd' [1]",
    "S -> A B C D [0.3] | A B C D E [0.7]\nA -> 'a' [1]\nB -> 'b' [1]\nC -> 'c' [1]\nD -> 'd' [1]\nE -> 'e' [1]",
    "S -> 'a' B 'a' [0.4] | 'A' B '!' [0.6]\nB -> 'b' [1]",
    "S -> A [0.4] | B [0.6]\nA -> 'a' [0.2] | C D [0.8]\nB -> 'a' [0.5] | C D [0.5]\nC -> 'c' [1]\nD -> 'd' [1]",
    "S -> A [0.2] | B C [0.3] | C B [0.5]\nA -> B C [1]\nB -> 'b' [1]\nC -> 'c' [1]",
    "S -> A [1]\nA -> 'a' [0.2] | 'a' [0.3] | 'b' [0.5]",
    "S -> 'a' 'b' 'a' [0.4] | 'a' 'b' [0.6]",
]


@pytest.mark.parametrize("source", ACYCLIC_GRAMMARS)
def test_acyclic_string_distribution(source):
    original = PCFG.fromstring(source)
    before = list(original.productions())
    expected = enumerate_distribution(original)
    converted = original.chomsky_normal_form()
    assert_cnf(converted)
    assert enumerate_distribution(converted) == pytest.approx(
        expected, rel=1e-12, abs=0
    )
    assert original.productions() == before
    assert converted.start() == original.start()


def test_issue_3384_unreachable_rules():
    converted = PCFG.fromstring(ACYCLIC_GRAMMARS[0]).chomsky_normal_form()
    assert {p.lhs() for p in converted.productions()} == {Nonterminal("S")}
    assert {p.rhs(): p.prob() for p in converted.productions()} == {
        ("v",): 0.3,
        ("a",): 0.7,
    }


@pytest.mark.parametrize("grammar_class", [CFG, PCFG])
def test_generated_symbols_round_trip(grammar_class):
    source = "S -> N V P [1]\nN -> 'n' [1]\nV -> 'v' [1]\nP -> 'p' [1]"
    if grammar_class is CFG:
        source = source.replace(" [1]", "")
    converted = grammar_class.fromstring(source).chomsky_normal_form()
    text = "% start " + str(converted.start()) + "\n"
    text += "\n".join(map(str, converted.productions()))
    loaded = grammar_class.fromstring(text)
    assert loaded.start() == converted.start()
    assert loaded.productions() == converted.productions()


@pytest.mark.parametrize("padding", ["@$@", "_", ""])
def test_fresh_symbols_and_repeated_terminals(padding):
    grammar = PCFG.fromstring(
        f"S -> 'a' CNF{padding}LEX0 A B [0.4] | A B CNF{padding}BIN1 [0.6]\n"
        f"CNF{padding}LEX0 -> 'z' [1]\nCNF{padding}BIN1 -> 'c' [1]\n"
        "A -> 'a' [1]\nB -> 'b' [1]"
    )
    converted = grammar.chomsky_normal_form(new_token_padding=padding)
    assert_cnf(converted)
    assert enumerate_distribution(converted) == pytest.approx(
        enumerate_distribution(grammar)
    )


def test_flexible_keeps_unit_rules_and_probabilities():
    grammar = PCFG.fromstring(
        "S -> A [0.4] | 'a' B C [0.6]\nA -> 'x' [1]\nB -> 'b' [1]\nC -> 'c' [1]"
    )
    converted = grammar.chomsky_normal_form(flexible=True)
    assert isinstance(converted, PCFG)
    assert converted.is_flexible_chomsky_normal_form()
    assert not converted.is_chomsky_normal_form()
    assert enumerate_distribution(converted) == pytest.approx(
        enumerate_distribution(grammar)
    )


@pytest.mark.parametrize(
    ("start", "expected"),
    [("S", (4 / 7, 3 / 7)), ("A", (4 / 7, 3 / 7)), ("B", (1 / 7, 6 / 7))],
)
def test_unit_cycle_geometric_series(start, expected):
    # Lemma B.13 preserves string probabilities from every nonterminal.
    # From A: x_a = 1/2 + (1/2)(1/4)x_a, x_b = (1/2)(3/4) + x_b/8.
    grammar = PCFG.fromstring(
        "S -> A [1]\nA -> B [0.5] | 'a' [0.5]\nB -> A [0.25] | 'b' [0.75]"
    )
    converted = PCFG(Nonterminal(start), grammar.productions()).chomsky_normal_form()
    assert_cnf(converted)
    for token, probability in zip("ab", expected):
        assert inside(converted, (token,)) == pytest.approx(
            probability, rel=1e-12, abs=0
        )


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("S -> A [0.5] | 'x' [0.5]\nA -> A [1]", 0.5),
        ("S -> A [0.5] | 'x' [0.5]\nA -> B [1]\nB -> A [1]", 0.5),
        ("S -> A [0.5] | 'x' [0.5]", 0.5),
        # x = 3/8 + x/2 gives finite mass 3/4; the closed B-C class gets 1/4.
        ("S -> S [0.5] | B [0.125] | 'x' [0.375]\nB -> C [1]\nC -> B [1]", 0.75),
    ],
)
def test_nontermination_mass_is_not_renormalized(source, expected):
    converted = PCFG.fromstring(source).chomsky_normal_form()
    assert_cnf(converted)
    assert inside(converted, ("x",)) == expected
    assert inside(converted, ("x", "x")) == 0


def test_only_closed_unit_cycle():
    converted = PCFG.fromstring("S -> A [1]\nA -> S [1]").chomsky_normal_form()
    assert_cnf(converted)
    assert inside(converted, ("a",)) == 0


def test_unreachable_closed_cycle():
    grammar = PCFG.fromstring("S -> A [1]\nA -> 'a' [1]\nU -> U [1]")
    converted = grammar.chomsky_normal_form()
    assert_cnf(converted)
    assert len(converted.productions()) == 1


@pytest.mark.parametrize("start", ["S", "CNF@$@DEAD"])
@pytest.mark.parametrize("flexible", [False, True])
def test_undefined_start_preserves_zero_finite_mass(start, flexible):
    grammar = PCFG.fromstring(f"% start {start}\nA -> B [1]\nB -> 'b' [1]")
    before = list(grammar.productions())
    assert enumerate_distribution(grammar) == {}
    converted = grammar.chomsky_normal_form(flexible=flexible)
    assert_cnf(converted)
    assert converted.start() == grammar.start()
    assert all(len(rule.rhs()) == 2 for rule in converted.productions())
    assert converted.start() not in {
        symbol for rule in converted.productions() for symbol in rule.rhs()
    }
    for length in range(4):
        assert inside(converted, ("b",) * length) == 0
    loaded = PCFG.fromstring(
        f"% start {converted.start()}\n" + "\n".join(map(str, converted.productions()))
    )
    assert loaded.productions() == converted.productions()
    assert grammar.productions() == before


def test_sparse_unary_elimination_scales_linearly(monkeypatch):
    # Count symbol lookups rather than relying on machine-dependent timings.
    original_hash = Nonterminal.__hash__
    lookups = 0

    def count_hash(symbol):
        nonlocal lookups
        lookups += 1
        return original_hash(symbol)

    counts = []
    for size in (128, 256):
        grammar = PCFG.fromstring(
            "S -> A [1]\nA -> " + " ".join(["N"] * size) + " [1]\nN -> 'n' [1]"
        )
        binary = PCFG.binarize(grammar)
        lookups = 0
        with monkeypatch.context() as patch:
            patch.setattr(Nonterminal, "__hash__", count_hash)
            converted = PCFG.remove_unitary_rules(binary)
        counts.append(lookups)
        assert_cnf(converted)
        assert enumerate_distribution(converted) == {("n",) * size: 1.0}
    # Doubling a sparsely unary grammar should not quadruple the work.
    assert counts[1] < 3 * counts[0]


@pytest.mark.parametrize("probability", [1e-8, 1e-13, 1e-20])
def test_small_positive_probabilities_survive(probability):
    grammar = PCFG.fromstring(
        f"S -> A [1]\nA -> 'rare' [{probability:.20f}] | 'common' [{1 - probability:.20f}]"
    )
    converted = grammar.chomsky_normal_form()
    assert inside(converted, ("rare",)) == pytest.approx(probability, rel=1e-12, abs=0)


def test_near_absorbing_self_loop():
    grammar = PCFG.fromstring(
        "S -> A [1]\nA -> A [0.999999999999] | 'a' [0.00000000000025] | 'b' [0.00000000000075]"
    )
    converted = grammar.chomsky_normal_form()
    assert_cnf(converted)
    assert inside(converted, ("a",)) == pytest.approx(0.25)
    assert inside(converted, ("b",)) == pytest.approx(0.75)


def test_recursive_binary_exits_and_start_collision():
    grammar = PCFG.fromstring(
        "S -> A [0.5] | S S0_SIGMA [0.25] | 'b' [0.25]\nA -> 'a' [1]\nS0_SIGMA -> 'c' [1]"
    )
    converted = grammar.chomsky_normal_form()
    assert_cnf(converted)
    assert converted.start() not in {
        symbol for p in converted.productions() for symbol in p.rhs()
    }
    for length in range(1, 5):
        for first, probability in [("a", 0.5), ("b", 0.25)]:
            assert inside(converted, (first,) + ("c",) * (length - 1)) == pytest.approx(
                probability * 0.25 ** (length - 1)
            )


@pytest.mark.parametrize("branch_probability", [0.5, 0.75])
def test_binary_ambiguity_with_unit_cycle(branch_probability):
    # With branch probability 3/4, finite termination has probability 1/3.
    # Lemma B.13 preserves each string's raw mass even in this case.
    grammar = PCFG.fromstring(
        "S -> A [1]\nA -> A [0.2] | "
        f"A A [{0.8 * branch_probability}] | 'a' [{0.8 * (1 - branch_probability)}]"
    )
    converted = grammar.chomsky_normal_form()
    assert_cnf(converted)
    for length, catalan in enumerate([1, 1, 2, 5, 14], start=1):
        assert inside(converted, ("a",) * length) == pytest.approx(
            catalan
            * branch_probability ** (length - 1)
            * (1 - branch_probability) ** length,
            rel=1e-12,
            abs=0,
        )


def test_parser_compatibility_and_inside_sum():
    grammar = PCFG.fromstring("S -> A [0.4] | B [0.6]\nA -> 'a' [1]\nB -> 'a' [1]")
    original = list(InsideChartParser(grammar).parse(["a"]))
    converted = grammar.chomsky_normal_form()
    parses = list(InsideChartParser(converted).parse(["a"]))
    assert fsum(t.prob() for t in original) == fsum(t.prob() for t in parses) == 1
    assert next(ViterbiParser(converted).parse(["a"])).prob() == 1


def test_empty_rules_still_rejected():
    with pytest.raises(ValueError, match="Empty rules"):
        PCFG.fromstring("S -> 'a' [0.5] | [0.5]").chomsky_normal_form()


def unary_matrices():
    for a, b, c, d in product(range(3), repeat=4):
        yield [[a / 8, b / 8], [c / 8, d / 8]]
    for seed in range(12):
        random = Random(seed)
        rows = [[random.randint(1, 8) for _ in range(4)] for _ in range(4)]
        yield [[weight / (2 * sum(row)) for weight in row] for row in rows]


@pytest.mark.parametrize("matrix", list(unary_matrices()))
def test_unit_paths_against_bounded_markov_walk(matrix):
    # Lemma B.13's hitting probabilities, checked by an independent path sum.
    # Unary mass per row <= 1/2 bounds the uncounted tail by 2**-80.
    states = [Nonterminal(index) for index in range(len(matrix))]
    left, right = Nonterminal("L"), Nonterminal("R")
    rules = [
        ProbabilisticProduction(left, ["l"], prob=1),
        ProbabilisticProduction(right, ["r"], prob=1),
    ]
    exits = [(1 - sum(row)) / 2 for row in matrix]
    for index, (state, row) in enumerate(zip(states, matrix)):
        rules.extend(
            ProbabilisticProduction(state, [target], prob=p)
            for target, p in zip(states, row)
        )
        rules.append(ProbabilisticProduction(state, [str(index)], prob=exits[index]))
        rules.append(
            ProbabilisticProduction(
                state, [left, right] if index % 2 else [right, left], prob=exits[index]
            )
        )
    grammar = PCFG(states[0], rules)
    expected = defaultdict(float)
    pending = [1.0] + [0.0] * (len(states) - 1)
    for _ in range(80):
        for index, probability in enumerate(pending):
            expected[(str(index),)] += probability * exits[index]
            expected[("l", "r") if index % 2 else ("r", "l")] += (
                probability * exits[index]
            )
        pending = [
            fsum(pending[row] * matrix[row][column] for row in range(len(states)))
            for column in range(len(states))
        ]
    converted = grammar.chomsky_normal_form()
    assert_cnf(converted)
    for sentence, probability in expected.items():
        assert inside(converted, sentence) == pytest.approx(
            probability, rel=1e-12, abs=0
        )


@pytest.mark.parametrize(
    "source", ["S -> 'a' [1]", "S -> 'a' [0.5] | 'b' [0.501]\nU -> 'u' [1]"]
)
def test_cnf_identity(source):
    # Preserve the inherited fast path, including the constructor's tolerance.
    grammar = PCFG.fromstring(source)
    assert grammar.chomsky_normal_form() is grammar


@pytest.mark.parametrize("probabilities", [(1.1, -0.1), (0.5, 0.501)])
def test_invalid_weights_are_not_silently_normalized(probabilities):
    start, child = Nonterminal("S"), Nonterminal("A")
    grammar = PCFG(
        start,
        [ProbabilisticProduction(start, [child], prob=1)]
        + [
            ProbabilisticProduction(child, [token], prob=p)
            for token, p in zip("ab", probabilities)
        ],
    )
    with pytest.raises(ValueError, match="CNF conversion requires"):
        grammar.chomsky_normal_form()


def test_probability_one_exit_roundoff():
    random = Random(23)
    states = [Nonterminal(str(index)) for index in range(6)]
    for _ in range(10):
        rules = []
        for state in states:
            weights = [random.random() for _ in range(7)]
            total = sum(weights)
            rules.extend(
                ProbabilisticProduction(state, [target], prob=weight / total)
                for weight, target in zip(weights, states + ["a"])
            )
        converted = PCFG(states[0], rules).chomsky_normal_form()
        assert_cnf(converted)
        assert inside(converted, ("a",)) == pytest.approx(1)
