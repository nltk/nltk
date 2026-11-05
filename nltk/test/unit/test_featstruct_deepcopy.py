"""
Variables and feature names are not changed once made, so a deep copy shares
them, as it shares strings. The feature structures around them are still
copied: a copy can be unified or renamed without touching the original.
"""

import copy

from nltk.featstruct import SLASH, TYPE, FeatStruct, Feature, RangeFeature, unify
from nltk.sem.logic import Expression, Variable


def test_a_variable_deep_copies_to_itself():
    var = Variable("?x")
    assert copy.deepcopy(var) is var
    # A shallow copy is still a new, equal variable.
    assert copy.copy(var) == var and copy.copy(var) is not var


def test_a_feature_deep_copies_to_itself():
    for feature in (TYPE, SLASH, Feature("num"), RangeFeature("span")):
        assert copy.deepcopy(feature) is feature


def test_a_copied_feature_structure_is_still_its_own():
    fstruct = FeatStruct("[a=?x, b=(1)[c=?x, d=sg], e->(1), f=[g=?y]]")
    copied = copy.deepcopy(fstruct)
    assert copied == fstruct and repr(copied) == repr(fstruct)
    assert copied is not fstruct and copied["b"] is not fstruct["b"]
    # The reentrance is kept within the copy, not shared with the original.
    assert copied["b"] is copied["e"]
    assert copied["a"] is fstruct["a"]
    copied["b"]["d"] = "pl"
    copied["f"]["g"] = "sg"
    assert fstruct["b"]["d"] == "sg" and fstruct["f"]["g"] == Variable("?y")


def test_unification_and_renaming_still_leave_their_inputs():
    fstruct1, fstruct2 = FeatStruct("[a=?x]"), FeatStruct("[b=?x]")
    assert repr(fstruct1.unify(fstruct2)) == "[a=?x, b=?x2]"
    assert repr(fstruct1) == "[a=?x]" and repr(fstruct2) == "[b=?x]"
    fstruct = FeatStruct("[a=?x, b=[c=?x]]")
    assert repr(fstruct.rename_variables()) == "[a=?x2, b=[c=?x2]]"
    assert repr(fstruct) == "[a=?x, b=[c=?x]]"
    bindings = {Variable("?x"): FeatStruct("[n=sg]")}
    unified = unify(FeatStruct("[a=?x]"), FeatStruct("[a=[m=1]]"), bindings)
    # Expected values as develop gives them, before variables were shared.
    assert repr(unified) == "[a=[m=1, n='sg']]"
    assert repr(bindings) == "{Variable('?x'): [m=1, n='sg']}"


def test_a_logic_expression_still_deep_copies_equal():
    expression = Expression.fromstring(r"\x.exists y.(P(x) & Q(y))")
    copied = copy.deepcopy(expression)
    assert copied == expression and str(copied) == str(expression)
