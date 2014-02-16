# Natural Language Toolkit: Semantic Interpretation
#
# Author: Ewan Klein <ewan@inf.ed.ac.uk>
#
# Copyright (C) 2001-2014 NLTK Project
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

from nltk.sem.logic import (AllExpression, AndExpression, ApplicationExpression,
                            EqualityExpression, ExistsExpression, IffExpression,
                            ImpExpression, NegatedExpression, OrExpression,
                            VariableExpression, skolem_function, unique_variable)

def skolemize(expression, univ_scope=None, used_variables=None):
    """
    Skolemize the expression and convert to conjunctive normal form (CNF)
    """
    if univ_scope is None:
        univ_scope = set()
    if used_variables is None:
        used_variables = set()

    if isinstance(expression, AllExpression):
        term = skolemize(expression.term, univ_scope|set([expression.variable]), used_variables|set([expression.variable]))
        return term.replace(expression.variable, VariableExpression(unique_variable(ignore=used_variables)))
    elif isinstance(expression, AndExpression):
        return skolemize(expression.first, univ_scope, used_variables) &\
               skolemize(expression.second, univ_scope, used_variables)
    elif isinstance(expression, OrExpression):
        return to_cnf(skolemize(expression.first, univ_scope, used_variables),
                      skolemize(expression.second, univ_scope, used_variables))
    elif isinstance(expression, ImpExpression):
        return to_cnf(skolemize(-expression.first, univ_scope, used_variables),
                      skolemize(expression.second, univ_scope, used_variables))
    elif isinstance(expression, IffExpression):
        return to_cnf(skolemize(-expression.first, univ_scope, used_variables),
                      skolemize(expression.second, univ_scope, used_variables)) &\
               to_cnf(skolemize(expression.first, univ_scope, used_variables),
                      skolemize(-expression.second, univ_scope, used_variables))
    elif isinstance(expression, EqualityExpression):
        return expression
    elif isinstance(expression, NegatedExpression):
        negated = expression.term
        if isinstance(negated, AllExpression):
            term = skolemize(-negated.term, univ_scope, used_variables|set([negated.variable]))
            if univ_scope:
                return term.replace(negated.variable, skolem_function(univ_scope))
            else:
                skolem_constant = VariableExpression(unique_variable(ignore=used_variables))
                return term.replace(negated.variable, skolem_constant)
        elif isinstance(negated, AndExpression):
            return to_cnf(skolemize(-negated.first, univ_scope, used_variables),
                          skolemize(-negated.second, univ_scope, used_variables))
        elif isinstance(negated, OrExpression):
            return skolemize(-negated.first, univ_scope, used_variables) &\
                   skolemize(-negated.second, univ_scope, used_variables)
        elif isinstance(negated, ImpExpression):
            return skolemize(negated.first, univ_scope, used_variables) &\
                   skolemize(-negated.second, univ_scope, used_variables)
        elif isinstance(negated, IffExpression):
            return to_cnf(skolemize(-negated.first, univ_scope, used_variables),
                          skolemize(-negated.second, univ_scope, used_variables)) &\
                   to_cnf(skolemize(negated.first, univ_scope, used_variables),
                          skolemize(negated.second, univ_scope, used_variables))
        elif isinstance(negated, EqualityExpression):
            return expression
        elif isinstance(negated, NegatedExpression):
            return skolemize(negated.term, univ_scope, used_variables)
        elif isinstance(negated, ExistsExpression):
            term = skolemize(-negated.term, univ_scope|set([negated.variable]), used_variables|set([negated.variable]))
            return term.replace(negated.variable, VariableExpression(unique_variable(ignore=used_variables)))
        elif isinstance(negated, ApplicationExpression):
            return expression
        else:
            raise Exception('\'%s\' cannot be skolemized' % expression)
    elif isinstance(expression, ExistsExpression):
        term = skolemize(expression.term, univ_scope, used_variables|set([expression.variable]))
        if univ_scope:
            return term.replace(expression.variable, skolem_function(univ_scope))
        else:
            skolem_constant = VariableExpression(unique_variable(ignore=used_variables))
            return term.replace(expression.variable, skolem_constant)
    elif isinstance(expression, ApplicationExpression):
        return expression
    else:
        raise Exception('\'%s\' cannot be skolemized' % expression)

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
