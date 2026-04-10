# Natural Language Toolkit: Combinatory Categorial Grammar
#
# Copyright (C) 2001-2026 NLTK Project
# Author: Tanin Na Nakorn (@tanin)
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""
Helper functions for CCG semantics computation
"""

import copy

from nltk.sem.logic import *


def _alpha_convert_all(expr):
    """Recursively alpha-convert every bound variable in *expr* to a
    fresh unique name.

    This enforces the Barendregt variable convention so that no two
    binders share a variable name, preventing accidental variable
    capture when expressions are combined.

    Uses the existing ``VariableBinderExpression.alpha_convert`` method
    from ``nltk.sem.logic``.

    :param expr: ``Expression``
    :return: ``Expression`` with all bound variables freshly renamed
    """
    if isinstance(expr, VariableBinderExpression):
        # First recurse into the body to rename inner binders
        recursed = expr.__class__(expr.variable, _alpha_convert_all(expr.term))
        # Then alpha-convert this binder to a fresh variable
        return recursed.alpha_convert(unique_variable(pattern=expr.variable))
    elif isinstance(expr, ApplicationExpression):
        return ApplicationExpression(
            _alpha_convert_all(expr.function),
            _alpha_convert_all(expr.argument),
        )
    elif isinstance(expr, NegatedExpression):
        return NegatedExpression(_alpha_convert_all(expr.term))
    elif isinstance(expr, BinaryExpression):
        return expr.__class__(
            _alpha_convert_all(expr.first),
            _alpha_convert_all(expr.second),
        )
    else:
        # Leaf nodes: variable expressions, constants, etc.
        return expr


def compute_type_raised_semantics(semantics):
    semantics_copy = copy.deepcopy(semantics)
    core = semantics_copy
    parent = None
    while isinstance(core, LambdaExpression):
        parent = core
        core = core.term

    var = Variable("F")
    while var in core.free():
        var = unique_variable(pattern=var)
    core = ApplicationExpression(FunctionVariableExpression(var), core)

    if parent is not None:
        parent.term = core
    else:
        semantics_copy = core

    return LambdaExpression(var, semantics_copy)


def compute_function_semantics(function, argument):
    function = _alpha_convert_all(function)
    argument = _alpha_convert_all(argument)
    return ApplicationExpression(function, argument).simplify()


def compute_composition_semantics(function, argument):
    assert isinstance(argument, LambdaExpression), (
        "`" + str(argument) + "` must be a lambda expression"
    )
    function = _alpha_convert_all(function)
    argument = _alpha_convert_all(argument)
    return LambdaExpression(
        argument.variable, ApplicationExpression(function, argument.term).simplify()
    )


def compute_substitution_semantics(function, argument):
    assert isinstance(function, LambdaExpression) and isinstance(
        function.term, LambdaExpression
    ), ("`" + str(function) + "` must be a lambda expression with 2 arguments")
    assert isinstance(argument, LambdaExpression), (
        "`" + str(argument) + "` must be a lambda expression"
    )

    function = _alpha_convert_all(function)
    argument = _alpha_convert_all(argument)

    new_argument = ApplicationExpression(
        argument, VariableExpression(function.variable)
    ).simplify()
    new_term = ApplicationExpression(function.term, new_argument).simplify()

    return LambdaExpression(function.variable, new_term)
