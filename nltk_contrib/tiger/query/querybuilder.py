# -*- coding: utf-8 -*-
# Copyright © 2007-2008 Stockholm TreeAligner Project
# Author: Torsten Marek <shlomme@gmx.net>
# Licensed under the GNU GPLv2
from functools import partial
from nltk_contrib.tiger.query import ast, predicates
from nltk_contrib.tiger.query.ast_utils import create_varref, create_vardef
from nltk_contrib.tiger.query.tsqlparser import NODE_VAR_PREFIXES

# This interface is currently unused.
__all__ = ["QueryBuilder"]


class _BuilderBase(object):
    def _get_container_type(self, node_var):
        return NODE_VAR_PREFIXES.get(node_var[0], ast.ContainerTypes.Single)
    
    def _create_varref(self, node_var):
        return create_varref(node_var, container_type = self._get_container_type(node_var))


class _PredicateFactory(_BuilderBase):
    AST_NODES = {
        int: ast.IntegerLiteral,
    }
    def _get_ast_args(self, args):
        predicate_args = [self._create_varref(args[0])]
        predicate_args.extend(
            [self.AST_NODES[type(a)](a) 
             for a in args[1:]])
        return predicate_args
            
    def build(self, name, *args):
        return ast.Predicate(name, self._get_ast_args(args))
    
    def __getattr__(self, attr):
        return partial(self.build, attr)


class _ConstraintFactory(_BuilderBase):
    OPS = {
        "secedge": ast.SecEdgeOperator,
        "dominance": ast.DominanceOperator,
        "corner": ast.CornerOperator,
        "sibling": ast.SiblingOperator,
        "precedence": ast.PrecedenceOperator,
    }
    def build(self, name, left_op, right_op, **kwargs):
        op_cls = self.OPS[name]
        return op_cls(self._create_varref(left_op), self._create_varref(right_op),
                      **kwargs)
    
    def __getattr__(self, attr):
        return partial(self.build, attr)


class _Composite(object):
    def __and__(self, other):
        if other.__class__ == self.__class__:
            return And(self.children + other.children)
        else:
            self.children.append(other)
            return self
        
    def __or__(self, other):
        if other.__class__ == self.__class__:
            return Or(self.children + other.children)
        else:
            self.children.append(other)
            return self
    
    
class _ExprBase(object):
    def __and__(self, other):
        if isinstance(other, And):
            return other.__and__(self)
        else:
            return And([self, other])
        
    def __or__(self, other):
        if isinstance(other, Or):
            return other.__or__(self)
        else:
            return Or([self, other])


class And(_Composite, ast.Conjunction):
    TYPE = ast.Conjunction


class Or(_Composite, ast.Disjunction):
    TYPE = ast.Disjunction


class FeatureConstraint(_ExprBase, ast.FeatureConstraint):
    TYPE = ast.FeatureConstraint
    

class Feature(object):
    def __init__(self, feature_name):
        self._feature_name = feature_name

    def not_matches(self, regex):
        return FeatureConstraint(self._feature_name, ast.Negation(ast.RegexLiteral(regex.expr)))
                                  
    def matches(self, regex):
        return FeatureConstraint(self._feature_name, ast.RegexLiteral(regex.expr))
    
    def equals(self, literal):
        return FeatureConstraint(self._feature_name, ast.StringLiteral(literal))
        
    def not_equals(self, literal):
        return FeatureConstraint(self._feature_name, ast.Negation(ast.StringLiteral(literal)))


class _FeatureFactory(object):
    def __getattr__(self, attr):
        return Feature(attr)


class QueryBuilder(_BuilderBase):
    feature = _FeatureFactory()
    predicate = _PredicateFactory()
    constraint = _ConstraintFactory()

    def __init__(self, query_factory):
        super(self.__class__, self).__init__()
        self._factory = query_factory
        self._nodes = []
        self._predicates = []
        self._constraints = []
    
    def add_constraint(self, name, *args, **kwargs):
        self._constraints.append(self.constraint.build(name, *args, **kwargs))
        return self
    
    def add_predicate(self, name, *args):
        self._predicates.append(self.predicate.build(name, *args))
        return self
    
    def add_node(self, name, expression):
        a = create_vardef(name, ast.NodeDescription(expression),
                          container_type=self._get_container_type(name))
        self._nodes.append(a)
        return self
    
    def finish(self):
        return self._factory.from_ast(
            ast.TsqlExpression(ast.Conjunction(self._nodes + self._predicates + self._constraints)))
