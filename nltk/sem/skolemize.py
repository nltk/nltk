# Natural Language Toolkit: Semantic Interpretation
#
# Author: Ewan Klein <ewan@inf.ed.ac.uk>
#
# Copyright (C) 2001-2022 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

from nltk.sem.logic import (
    AllExpression,
    AndExpression,
    ApplicationExpression,
    EqualityExpression,
    ExistsExpression,
    IffExpression,
    ImpExpression,
    NegatedExpression,
    OrExpression,
    VariableExpression,
    skolem_function,
    unique_variable,
)


def skolemize(expression, univ_scope=None, used_variables=None):
    """
    Skolemize the expression and convert to conjunctive normal form (CNF)
    """
    if univ_scope is None:
        univ_scope = set()
    if used_variables is None:
        used_variables = set()

    if isinstance(expression, AllExpression):
        term = skolemize(
            expression.term,
            univ_scope | {expression.variable},
            used_variables | {expression.variable},
        )
        return term.replace(
            expression.variable,
            VariableExpression(unique_variable(ignore=used_variables)),
        )
    elif isinstance(expression, AndExpression):
        return skolemize(expression.first, univ_scope, used_variables) & skolemize(
            expression.second, univ_scope, used_variables
        )
    elif isinstance(expression, OrExpression):
        return to_cnf(
            skolemize(expression.first, univ_scope, used_variables),
            skolemize(expression.second, univ_scope, used_variables),
        )
    elif isinstance(expression, ImpExpression):
        return to_cnf(
            skolemize(-expression.first, univ_scope, used_variables),
            skolemize(expression.second, univ_scope, used_variables),
        )
    elif isinstance(expression, IffExpression):
        return to_cnf(
            skolemize(-expression.first, univ_scope, used_variables),
            skolemize(expression.second, univ_scope, used_variables),
        ) & to_cnf(
            skolemize(expression.first, univ_scope, used_variables),
            skolemize(-expression.second, univ_scope, used_variables),
        )
    elif isinstance(expression, EqualityExpression):
        return expression
    elif isinstance(expression, NegatedExpression):
        negated = expression.term
        if isinstance(negated, AllExpression):
            term = skolemize(
                -negated.term, univ_scope, used_variables | {negated.variable}
            )
            if univ_scope:
                return term.replace(negated.variable, skolem_function(univ_scope))
            else:
                skolem_constant = VariableExpression(
                    unique_variable(ignore=used_variables)
                )
                return term.replace(negated.variable, skolem_constant)
        elif isinstance(negated, AndExpression):
            return to_cnf(
                skolemize(-negated.first, univ_scope, used_variables),
                skolemize(-negated.second, univ_scope, used_variables),
            )
        elif isinstance(negated, OrExpression):
            return skolemize(-negated.first, univ_scope, used_variables) & skolemize(
                -negated.second, univ_scope, used_variables
            )
        elif isinstance(negated, ImpExpression):
            return skolemize(negated.first, univ_scope, used_variables) & skolemize(
                -negated.second, univ_scope, used_variables
            )
        elif isinstance(negated, IffExpression):
            return to_cnf(
                skolemize(-negated.first, univ_scope, used_variables),
                skolemize(-negated.second, univ_scope, used_variables),
            ) & to_cnf(
                skolemize(negated.first, univ_scope, used_variables),
                skolemize(negated.second, univ_scope, used_variables),
            )
        elif isinstance(negated, EqualityExpression):
            return expression
        elif isinstance(negated, NegatedExpression):
            return skolemize(negated.term, univ_scope, used_variables)
        elif isinstance(negated, ExistsExpression):
            term = skolemize(
                -negated.term,
                univ_scope | {negated.variable},
                used_variables | {negated.variable},
            )
            return term.replace(
                negated.variable,
                VariableExpression(unique_variable(ignore=used_variables)),
            )
        elif isinstance(negated, ApplicationExpression):
            return expression
        else:
            raise Exception("'%s' cannot be skolemized" % expression)
    elif isinstance(expression, ExistsExpression):
        term = skolemize(
            expression.term, univ_scope, used_variables | {expression.variable}
        )
        if univ_scope:
            return term.replace(expression.variable, skolem_function(univ_scope))
        else:
            skolem_constant = VariableExpression(unique_variable(ignore=used_variables))
            return term.replace(expression.variable, skolem_constant)
    elif isinstance(expression, ApplicationExpression):
        return expression
    else:
        raise Exception("'%s' cannot be skolemized" % expression)


def richardize(expression, univ_scope=None, used_variables=None):
    """
    richardize? the expression and convert to a simplest equivalent form FOL
    """
    if univ_scope is None:
        univ_scope = set()
    if used_variables is None:
        used_variables = set()

    if isinstance(expression, AllExpression):
        term = richardize(
            expression.term,
            univ_scope | {expression.variable},
            used_variables | {expression.variable},
        )
        if expression.variable in term.variables():
            return AllExpression(expression.variable, term)
        else:
            return term
    elif isinstance(expression, AndExpression):
        return richardize(expression.first, univ_scope, used_variables) & richardize(
            expression.second, univ_scope, used_variables
        )
    elif isinstance(expression, OrExpression):
        return to_cnf(
            richardize(expression.first, univ_scope, used_variables),
            richardize(expression.second, univ_scope, used_variables),
        )
    elif isinstance(expression, ImpExpression):
        return to_cnf(
            richardize(-expression.first, univ_scope, used_variables),
            richardize(expression.second, univ_scope, used_variables),
        )
    elif isinstance(expression, IffExpression):
        return to_cnf(
            richardize(-expression.first, univ_scope, used_variables),
            richardize(expression.second, univ_scope, used_variables),
        ) & to_cnf(
            richardize(expression.first, univ_scope, used_variables),
            richardize(-expression.second, univ_scope, used_variables),
        )
    elif isinstance(expression, EqualityExpression):
        return expression
    elif isinstance(expression, NegatedExpression):
        negated = expression.term
        if isinstance(negated, AllExpression):
            term = richardize(
                -negated.term, univ_scope, used_variables | {negated.variable}
            )
            if negated.variable in term.variables():
                return ExistsExpression(negated.variable, term)
            else:
                return term
        elif isinstance(negated, AndExpression):
            return to_cnf(
                richardize(-negated.first, univ_scope, used_variables),
                richardize(-negated.second, univ_scope, used_variables),
            )
        elif isinstance(negated, OrExpression):
            return richardize(-negated.first, univ_scope, used_variables) & richardize(
                -negated.second, univ_scope, used_variables
            )
        elif isinstance(negated, ImpExpression):
            return richardize(negated.first, univ_scope, used_variables) & richardize(
                -negated.second, univ_scope, used_variables
            )
        elif isinstance(negated, IffExpression):
            return to_cnf(
                richardize(-negated.first, univ_scope, used_variables),
                richardize(-negated.second, univ_scope, used_variables),
            ) & to_cnf(
                richardize(negated.first, univ_scope, used_variables),
                richardize(negated.second, univ_scope, used_variables),
            )
        elif isinstance(negated, EqualityExpression):
            return expression
        elif isinstance(negated, NegatedExpression):
            return richardize(negated.term, univ_scope, used_variables)
        elif isinstance(negated, ExistsExpression):
            term = richardize(
                -negated.term,
                univ_scope | {negated.variable},
                used_variables | {negated.variable},
            )
            if negated.variable in term.variables():
                return AllExpression(negated.variable, term)
            else:
                return term
        elif isinstance(negated, ApplicationExpression):
            return expression
        else:
            raise Exception("'%s' cannot be richardized" % expression)
    elif isinstance(expression, ExistsExpression):
        term = richardize(
            expression.term, univ_scope, used_variables | {expression.variable}
        )
        if expression.variable in term.variables():
            return ExistsExpression(expression.variable, term)
        else:
            return term
    elif isinstance(expression, ApplicationExpression):
        return expression
    else:
        raise Exception("'%s' cannot be richardized" % expression)


def to_cnf(first, second):
    """
    Convert this split disjunction to conjunctive normal form (CNF)
    """
    if isinstance(first, AndExpression):
        r_first = to_cnf(first.first, second)
        r_second = to_cnf(first.second, second)
        return r_first & r_second
    elif isinstance(second, AndExpression):
        r_first = to_cnf(first, second.first)
        r_second = to_cnf(first, second.second)
        return r_first & r_second
    else:
        return first | second


def conjunctive_form(expressions):
    if len(expressions) == 1:
        return expressions.pop()
    else:
        return expressions.pop() & conjunctive_form(expressions)


def disjunctive_form(expressions):
    if len(expressions) == 1:
        return expressions.pop()
    else:
        return expressions.pop() | disjunctive_form(expressions)


def commuted_items(expression):
    if isinstance(expression, AndExpression) or isinstance(expression, OrExpression):
        expression.second = to_sorted(expression.second)
        if isinstance(expression.first, expression.__class__):
            items = commuted_items(expression.first)
            items.append(expression.second)
        else:
            items = [to_sorted(expression.first), expression.second]

    return sorted(set(items), key=lambda x: x.__str__())


def to_sorted(expression):
    if isinstance(expression, AndExpression):
        return conjunctive_form(commuted_items(expression))
    elif isinstance(expression, OrExpression):
        return disjunctive_form(commuted_items(expression))
    elif isinstance(expression, ApplicationExpression) or isinstance(
        expression, EqualityExpression
    ):
        return expression
    else:
        expression.term = to_sorted(expression.term)
        return expression


import itertools


def conj_elim(expression):
    _, form, tree = expression.__reduce__()
    tree = tree.copy()
    if "term" in tree:
        for term in conj_elim(tree["term"]):
            tree["term"] = term
            yield form[0](**tree)
    elif "first" in tree:
        firsts = conj_elim(tree["first"])
        seconds = conj_elim(tree["second"])
        for first in firsts:
            seconds, seconds_ = itertools.tee(seconds)
            for second in seconds_:
                tree["first"] = first
                tree["second"] = second
                yield form[0](**tree)
        if isinstance(expression, AndExpression):
            firsts, firsts_ = itertools.tee(firsts)
            yield from firsts_
            seconds, seconds_ = itertools.tee(seconds)
            yield from seconds_
    else:
        yield expression
