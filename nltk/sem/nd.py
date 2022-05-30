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
)


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
        firsts, firsts_ = itertools.tee(firsts)
        for first in firsts_:
            seconds, seconds_ = itertools.tee(seconds)
            for second in seconds_:
                tree["first"] = first
                tree["second"] = second
                yield form[0](**tree)
        if isinstance(expression, AndExpression):
            yield from firsts
            yield from seconds
    else:
        yield expression


def atomics(expression):
    if hasattr(expression, "term"):
        yield from atomics(expression.term)
    elif hasattr(expression, "first"):
        yield from atomics(expression.first)
        yield from atomics(expression.second)
    else:
        if isinstance(expression, ApplicationExpression):
            yield expression


def get_basic_assumptions(expression):
    basic_assumptions = set()
    atoms = set(atomics(expression))

    for expr in atoms:
        vars = expr.variables()
        for var in vars:
            expr_ = expr
            for var_ in vars:
                if var_ == var:
                    var_all = var
                else:
                    expr_ = ExistsExpression(var_, expr_)
            basic_assumptions.add(-AllExpression(var_all, expr_))
        basic_assumptions.add(ExistsExpression(var_all, expr_))

    cond = conjunctive_form(basic_assumptions)
    for x in basic_assumptions:
        assert not prove(ImpExpression(cond, -x))

    return cond
