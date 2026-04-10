# Natural Language Toolkit: Combinatory Categorial Grammar
#
# Copyright (C) 2001-2026 NLTK Project
# Author: Tanin Na Nakorn (@tanin)
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""
Helper functions for CCG semantics computation
"""

from nltk.sem.logic import *


def compute_type_raised_semantics(semantics):
    var = Variable("F")
    while var in semantics.free():
        var = unique_variable(pattern=var)
    variables = []
    body = semantics
    while isinstance(body, LambdaExpression):
        variables.append(body.variable)
        body = body.term
    result = ApplicationExpression(FunctionVariableExpression(var), body)
    for v in reversed(variables):
        result = LambdaExpression(v, result)
    return LambdaExpression(var, result)


def compute_function_semantics(function, argument):
    return ApplicationExpression(function, argument).simplify()


def compute_composition_semantics(function, argument):
    assert isinstance(argument, LambdaExpression), (
        "`" + str(argument) + "` must be a lambda expression"
    )
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

    new_argument = ApplicationExpression(
        argument, VariableExpression(function.variable)
    ).simplify()
    new_term = ApplicationExpression(function.term, new_argument).simplify()

    return LambdaExpression(function.variable, new_term)
