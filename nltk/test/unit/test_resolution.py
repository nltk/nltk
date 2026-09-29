"""Soundness regressions for resolution (issue #2699)."""

from itertools import combinations, product

import pytest

from nltk.inference.resolution import Clause, ResolutionProver
from nltk.sem.logic import Expression

read = Expression.fromstring


def test_biconditional_does_not_prove_unrelated_goal():
    assumption = read("all x.all y.(parentof(y,x) <-> childof(x,y))")
    assert not ResolutionProver().prove(read("foo(Bar)"), [assumption])


@pytest.mark.parametrize(
    "left,right",
    [
        (["P(Adam)", "Q(Adam)"], ["-P(Adam)", "-Q(Adam)"]),
        (["P(Adam)", "P(Bob)"], ["-P(Adam)", "-P(Bob)"]),
        (["P(x)", "Q(x)"], ["-P(Adam)", "-Q(Adam)"]),
        (["P(Adam)", "-Q(y)"], ["-P(x)", "Q(Bob)"]),
        (["P(Adam)", "-P(Bob)"], ["-P(Adam)", "P(Bob)"]),
    ],
)
def test_distinct_pivots_do_not_produce_empty_clause(left, right):
    resolvents = Clause(map(read, left)).unify(Clause(map(read, right)))
    assert resolvents
    assert all(resolvents)


@pytest.mark.parametrize(
    "left,right",
    [
        (["P(Adam)", "P(Adam)"], ["-P(Adam)", "-P(Adam)"]),
        (["P(x)", "P(y)"], ["-P(Adam)", "-P(Adam)"]),
        (["P(x)", "P(y)"], ["-P(u)", "-P(v)"]),
        (["-P(x)", "-P(y)"], ["P(u)", "P(v)"]),
    ],
)
def test_factoring_still_produces_empty_clause(left, right):
    assert Clause(map(read, left)).unify(Clause(map(read, right))) == [Clause([])]


def test_factoring_substitutes_remaining_literals():
    left = Clause(map(read, ["P(x)", "P(y)", "R(x,y)"]))
    right = Clause(map(read, ["-P(u)", "-P(v)"]))
    resolvents = left.unify(right)
    assert len(resolvents) == 1
    assert len(resolvents[0]) == 1
    predicate, arguments = resolvents[0][0].uncurry()
    assert predicate == read("R")
    assert len(arguments) == 2
    assert arguments[0] == arguments[1]


def test_ground_resolvents_follow_from_their_parents():
    """Check the resolution rule against truth assignments, independently of MGU."""
    atoms = list(map(read, ["P(Adam)", "P(Bob)", "Q(Adam)"]))
    literals = atoms + [-atom for atom in atoms]
    clauses = [Clause(pair) for pair in combinations(literals, 2)]
    for left, right in combinations(clauses, 2):
        resolvents = left.unify(right)
        for values in product([False, True], repeat=len(atoms)):
            assignment = dict(zip(atoms, values))
            assignment.update({-atom: not value for atom, value in zip(atoms, values)})
            if all(
                any(assignment[term] for term in clause) for clause in (left, right)
            ):
                assert all(
                    any(assignment[term] for term in clause) for clause in resolvents
                ), (left, right, resolvents, assignment)
