import pytest

from nltk.ccg import lexicon
from nltk.ccg.combinator import BackwardT, ForwardT

LEX = lexicon.fromstring(
    r"""
    :- S, NP
    I => NP
    see => (S\NP)/NP
    saw => (S/NP)\NP
    """
)


def categ(word):
    return LEX.categories(word)[0].categ()


@pytest.mark.parametrize(
    "combinator, left, right",
    [
        (ForwardT, "I", "see"),
        (BackwardT, "saw", "I"),
        (ForwardT, "see", "I"),
        (BackwardT, "I", "see"),
    ],
)
def test_type_raise_can_combine_matches_combine(combinator, left, right):
    # can_combine used to raise NameError; it should agree with combine
    left, right = categ(left), categ(right)
    expected = bool(list(combinator.combine(left, right)))
    assert combinator.can_combine(left, right) is expected


def test_type_raise_can_combine():
    assert ForwardT.can_combine(categ("I"), categ("see"))
    assert BackwardT.can_combine(categ("saw"), categ("I"))
