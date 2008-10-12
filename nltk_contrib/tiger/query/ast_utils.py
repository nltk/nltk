# -*- coding: utf-8 -*-
# Copyright © 2007-2008 Stockholm TreeAligner Project
# Author: Torsten Marek <shlomme@gmx.net>
# Licensed under the GNU GPLv2
"""Utility functions for the abstract syntax trees defined in `nltk_contrib.tiger.query.ast`.
"""
from functools import partial

from nltk_contrib.tiger.query import ast
from nltk_contrib.tiger.query.ast_visitor import AstVisitor, node_handler
from nltk_contrib.tiger.query.exceptions import UndefinedNameError

__all__ = ["create_varref", "create_vardef", "split_children", "to_dnf"]

def create_varref(name, var_type=ast.VariableTypes.NodeIdentifier, 
                  container_type=ast.ContainerTypes.Single):
    """Creates a new `VariableReference` to a variable `name`.
    
    *Parameters*:
     * `name`: the name of the variable.
     * `var_type`: the type of the variable, a member of `nltk_contrib.tiger.query.ast.VariableTypes`.
     * `container_type`: the container type of the variable, a member of 
         `nltk_contrib.tiger.query.ast.ContainerTypes`.
    """
    return ast.VariableReference(ast.Variable(name, var_type, container_type))



def create_vardef(name, expression, var_type=ast.VariableTypes.NodeIdentifier, 
                  container_type=ast.ContainerTypes.Single):
    """Creates a new `VariableDefinition` of a variable `name` and a RHS `expression`.
    
    *Parameters*:
     * `name`: the name of the variable
     * `expression`: the expression which is assigned to the variable
     * `var_type`: the type of the variable, a member of `nltk_contrib.tiger.query.ast.VariableTypes`
     * `container_type`: the container type, a member of `nltk_contrib.tiger.query.ast.ContainerTypes`
    """
    return ast.VariableDefinition(ast.Variable(name, var_type, container_type), expression)


def split_children(ast_node, ast_type):
    """Sorts the children of `ast_node` into two lists, based on their type.
    
    *Parameters*:
     * `ast_node`: the AST node whose children should be sorted
     * `ast_type`: the type all children in the first list should have.
     
    *Return Value*:
    A tuple `(a, b)` of lists, `a` contains all child nodes with type `ast_type`, `b` the rest.
    """
    match, nomatch = [], []
    for node in ast_node:
        if node.TYPE is ast_type:
            match.append(node)
        else:
            nomatch.append(node)
    return match, nomatch


class NegNormalizer(AstVisitor):
    """An AST visitor that normalizes all negations in a boolean expression.
    
    The visitor applies the following transformations:
     - elimination of double negation: ``!!a => a``
     - De Morgan's laws:
       * ``!(a | b) => !a & !b``
       * ``!(a & b) => !a | !b``
       
    After the transformation, `Negation` nodes will only contain atoms, not other terms.
    
    *Parameters*:
     * `feature_types`: a dictionary that maps feature names to `NodeType`s, needed for negation
       `FeatureRecords`.
    """
    def __init__(self, feature_types):
        super(self.__class__, self).__init__()
        self._feature_types = feature_types
    
    @node_handler(ast.Negation)
    def normalize_neg(self, child_node):
        """Normalizes a negation if is reigns over something other than a term."""
        if child_node.expression.TYPE is ast.FeatureConstraint:
            # cf. TIGERSearch Query Language, section 8.4 (http://tinyurl.com/2jm24u)
            # !(pos="ART") === !(T & pos="ART") === !(T) | (pos != "ART")
            try:
                orig_type = self._feature_types[child_node.expression.feature]
            except KeyError, e:
                raise UndefinedNameError, (UndefinedNameError.FEATURE, e.args[0])
            return self.REPLACE(
                ast.Disjunction([
                    ast.FeatureRecord(~orig_type),
                    ast.FeatureConstraint(
                        child_node.expression.feature,
                        ast.Negation(child_node.expression.expression))]))
        else:
            try:
                return self.REPLACE(~child_node.expression)
            except TypeError:
                return self.CONTINUE(child_node)


def outer_product(l):
    """Produces the outer product of a list of lists.
    
    Example:
    >>> l = [[1, 2], [3, 4]]
    >>> outer_product(l) == [[1, 3], [1, 4], [2, 3], [2, 4]]
    
    If the number of lists is fixed, it is better to use a list comprehension
    >>> [(e1, e2) for e1 in l1 for e2 in l2]
    """
    def _expand(l, pos, result):
        """Recurses on `l` and produces all combinations of elements from the lists."""
        for e in l[pos]:
            result.append(e)
            if pos == len(l) - 1:
                yield result[:]
            else:
                for r in _expand(l, pos + 1, result):
                    yield r
            result.pop()
    return _expand(l, 0, [])


def _distribute(top_conjunction):
    """Applies the law of distributivity to a conjunction that has disjunctions.
    
    Example:
    ``(d1 | d2) & d3 => (d1 & d3) | (d2 & d3)``
    
    The function also applies associatity laws, it will never produce
    nested expressions with the same operators.
    """
    disj, terms = split_children(top_conjunction, ast.Disjunction)
    
    terms = [
        ast.Conjunction(t + combination)
        for t in [terms]
        for combination in outer_product(disj)
    ]
    
    for t in terms:
        t.apply_associativity()
        
    return ast.Disjunction(terms)


def distribute_disjunctions(tree):
    """Distributes all disjunctions in `tree` and also applies the law of associativity.
    
    Example:
    ``A & (B & (C | D) | E) => (A & B & C) | (A & B & D) | (A & E)``
    """
    has_disj = False
    for child_name, child_node in tree.named_iter():
        if child_node.TYPE in (ast.Conjunction, ast.Disjunction):
            new = distribute_disjunctions(child_node)
            if new.TYPE is ast.Disjunction:
                has_disj = True
            
            new.apply_associativity()
            tree.set_child(child_name, new)

    if tree.TYPE is ast.Conjunction and has_disj:
        return _distribute(tree)
    else:
        return tree
    

def to_dnf(tree, feature_types):
    """Converts a boolean expression into Disjunctive Normal Form.

    After the transformation, the boolean expression will be a disjunction of terms, negation will
    be normalized as well, and associativity laws have been applied.
    
    Note that the `tree` node itself will not be considered to be a part of the boolean expression.
    
    *Parameters*:
     * `feature_types`: a dictionary that maps feature names to `NodeType`s, needed for negation of
       `FeatureRecords`.
    """
    n = NegNormalizer(feature_types)
    n.run(tree)
    return distribute_disjunctions(tree)


class NodeDescriptionNormalizer(AstVisitor):
    """Normalizes a node description.
    
    After normalization, a node description is in disjunctive normal form, 
    and no feature constraint expression contains any disjunctions.
    """
    
    def __init__(self, feature_types):
        super(self.__class__, self).__init__()
        self._feature_types = feature_types
        
    @node_handler(ast.FeatureConstraint)
    def distribute(self, child_node):
        """Normalizes feature constraint expressions.
        
        A feature constraint with disjunctions is turned into a disjunction of feature
        constraints.
        """
        to_dnf(child_node, self._feature_types)
        if child_node.expression.TYPE is ast.Disjunction:
            fc = partial(ast.FeatureConstraint, child_node.feature)
            return self.REPLACE(ast.Disjunction(
                [fc(term) for term in child_node.expression]))
        else:
            return self.CONTINUE(child_node)
    
    def result(self, query):
        """Normalizes the node description, after all feature constraints have been normalized."""
        to_dnf(query, self._feature_types)
