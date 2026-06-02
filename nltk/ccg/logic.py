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
import re

from nltk.sem.logic import *


def barendregt_normalize(expr, counters=None):
    """
    Canonicalizes variables while preserving NLTK's prefix-based typing.
    Ensures alpha-equivalent formulas produce identical strings without capture.
    Draws from standard pools (x,y,z for individuals; F,G for functors).
    """
    if expr is None:
        return None

    if counters is None:
        expr = expr.simplify()
        counters = {}

    if isinstance(expr, VariableBinderExpression):
        # Extract the alphabetic prefix
        match = re.match(r"^([A-Za-z_]+)", expr.variable.name)
        base = match.group(1) if match else "v"

        # Group into pedagogical type pools to satisfy NLTK's type constraints
        # while maintaining standard x, y, z readability.
        if base in ("x", "y", "z", "w"):
            category, pool = "ind", ["x", "y", "z"]
        elif base in ("P", "Q", "R"):
            category, pool = "pred", ["P", "Q", "R"]
        elif base in ("F", "G", "H"):
            category, pool = "func", ["F", "G"]
        elif base == "e":
            category, pool = "event", ["e"]
        else:
            category, pool = base, [base]

        if category not in counters:
            counters[category] = 0

        free_in_body = expr.term.free() - {expr.variable}

        while True:
            idx = counters[category]
            pool_var = pool[idx % len(pool)]
            suffix = idx // len(pool)
            new_name = f"{pool_var}{suffix if suffix > 0 else ''}"
            new_var = Variable(new_name)
            counters[category] += 1

            # Prevent capture with strictly external free variables
            if new_var not in free_in_body:
                break

        safe_expr = expr.alpha_convert(new_var)
        return safe_expr.__class__(
            safe_expr.variable, barendregt_normalize(safe_expr.term, counters)
        )

    elif isinstance(expr, ApplicationExpression):
        return ApplicationExpression(
            barendregt_normalize(expr.function, counters),
            barendregt_normalize(expr.argument, counters),
        )

    elif isinstance(expr, BooleanExpression):
        return expr.__class__(
            barendregt_normalize(expr.first, counters),
            barendregt_normalize(expr.second, counters),
        )

    elif isinstance(expr, NegatedExpression):
        return NegatedExpression(barendregt_normalize(expr.term, counters))

    elif isinstance(expr, EqualityExpression):
        return expr.__class__(
            barendregt_normalize(expr.first, counters),
            barendregt_normalize(expr.second, counters),
        )

    return expr


def compute_function_semantics(function, argument):
    if function is None or argument is None:
        return None
    return barendregt_normalize(ApplicationExpression(function, argument))


def compute_type_raised_semantics(semantics):
    if semantics is None:
        return None
    core = unique_variable(pattern=Variable("F"))
    # Strictly pure type-raising: \F.F(semantics)
    return barendregt_normalize(
        LambdaExpression(
            core,
            ApplicationExpression(VariableExpression(core), copy.deepcopy(semantics)),
        )
    )


def compute_composition_semantics(function, argument):
    if function is None or argument is None:
        return None
    assert isinstance(
        argument, LambdaExpression
    ), f"`{argument}` must be a lambda expression"

    # Extract the type pattern directly from the argument
    v = unique_variable(pattern=argument.variable)
    return barendregt_normalize(
        LambdaExpression(
            v,
            ApplicationExpression(
                function, ApplicationExpression(argument, VariableExpression(v))
            ),
        )
    )


def compute_substitution_semantics(function, argument):
    if function is None or argument is None:
        return None
    assert isinstance(function, LambdaExpression) and isinstance(
        function.term, LambdaExpression
    ), f"`{function}` must be a lambda expression with 2 arguments"
    assert isinstance(
        argument, LambdaExpression
    ), f"`{argument}` must be a lambda expression"

    # Copilot Fix: Extract the type pattern directly from the function
    x_var = unique_variable(pattern=function.variable)
    return barendregt_normalize(
        LambdaExpression(
            x_var,
            ApplicationExpression(
                ApplicationExpression(function, VariableExpression(x_var)),
                ApplicationExpression(argument, VariableExpression(x_var)),
            ),
        )
    )
