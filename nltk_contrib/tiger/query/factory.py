# -*- coding: utf-8 -*-
# Copyright © 2007-2008 Stockholm TreeAligner Project
# Author: Torsten Marek <shlomme@gmx.net>
# Licensed under the GNU GPLv2

"""This module contains classes to create a result builder from a query AST.
"""
from collections import defaultdict
from itertools import count

from nltk_contrib.tiger.graph import NodeType
from nltk_contrib.tiger.query import ast_visitor
from nltk_contrib.tiger.query.ast_utils import create_varref, NodeDescriptionNormalizer
from nltk_contrib.tiger.query.node_variable import NodeVariable
from nltk_contrib.tiger.query import ast
from nltk_contrib.tiger.query.predicates import PredicateFactory, NodeTypePredicate
from nltk_contrib.tiger.query.constraints import ConstraintFactory
from nltk_contrib.tiger.query.exceptions import TigerTypeError, UndefinedNameError

__all__ = ["QueryFactory"]


class NodeTypeInferencer(ast_visitor.AstVisitor):
    """An AST visitor that processes a node description and infers the type 
    of the node variable using the feature constraints.
    
    *Parameters*:
     * `terminal_features`: the set of features on T nodes
     * `nonterminal_features`: the set of features on NT nodes
    """
    def __init__(self, feature_types):
        super(self.__class__, self).__init__()
        self._type_assoc = feature_types
        
    def setup(self, *args):
        """Prepares the typer for a new variable."""
        self._types = set()
        self._disjoints = [self._types]
        self._has_frec = False

    @ast_visitor.post_child_handler(ast.Disjunction)
    def after_disjunction_subexpr(self, node, child_idx):
        """Handles disjunctions."""
        if child_idx < len(node.children) - 1:
            self._types = set()
            self._disjoints.append(self._types)
        
    @ast_visitor.node_handler(ast.FeatureConstraint)
    def feature_constraints(self, node):
        """Adds type information based on the feature name."""
        try:
            self._types.add(self._type_assoc[node.feature])
        except KeyError:
            raise UndefinedNameError, (UndefinedNameError.FEATURE, node.feature)
        return self.STOP
    
    @ast_visitor.node_handler(ast.FeatureRecord)
    def feature_record(self, node):
        """Adds the type specified in a feature record."""
        self._types.add(node.type)
        self._has_frec = True
        return self.STOP
    
    def result(self, query_ast, node_variable):
        """Returns the type inferred type of the node variable.
        
        The return value is a member of the enum `nltk_contrib.tiger.graph.NodeType`.
        
        If the feature refer to conflicting node types, a `TigerTypeError` is raised.
        """
        node_var_type = set()

        for disj in self._disjoints:
            if len(disj) == 2:
                raise TigerTypeError, node_variable.name
            else:
                node_var_type.update(disj)

        if len(node_var_type) == 1:
            return (list(node_var_type)[0], self._has_frec)
        else:
            return (NodeType.UNKNOWN, False)


class QueryFactory(ast_visitor.AstVisitor):
    """Creates the internal representation from a query AST.
    
    A query AST is split into three parts:
     * node descriptions: a dictionary of `varname: AST`
     * predicates: a dictionary with `varname: nltk_contrib.tiger.query.predicates.Predicate` entries
     * constraints: a list of ((left, right), nltk_contrib.tiger.query.constraints.Constraint)` tuples
    
    These collections will be used to instantiate a `Query` object.
    Anonymous node descriptions will be wrapped into a variable definition with an 
    automatically generated, globally unique variable name.
    """
    get_anon_nodevar = (":anon:%i" % (c, ) for c in count()).next
    constraint_factory = ConstraintFactory()
    predicate_factory = PredicateFactory()
    
    def __init__(self, ev_context):
        super(self.__class__, self).__init__()
        self.nodedesc_normalizer = NodeDescriptionNormalizer(ev_context.corpus_info.feature_types)
        self._ev_context = ev_context
        for cls in self.constraint_factory:
            cls.setup_context(self._ev_context)
        self._ntyper = NodeTypeInferencer(ev_context.corpus_info.feature_types)
        
    @ast_visitor.node_handler(ast.NodeDescription)
    def handle_node_description(self, child_node):
        """Replaces an anonymous node description with a reference to a fresh node variable.
        
        The node description is stored for later reference.
        """
        variable = NodeVariable(self.get_anon_nodevar(), False)
        self.node_defs[variable] = child_node
        self.node_vars[variable.name] = variable
        return self.REPLACE(create_varref(variable.name))
    
    @ast_visitor.node_handler(ast.VariableDefinition)
    def handle_node_variable_def(self, child_node):
        """Replaces a node variable definition with a reference, and stores it.
        
        If the variable has already been defined, the node descriptions are merged.
        """
        assert child_node.variable.type == ast.VariableTypes.NodeIdentifier
        node_variable = NodeVariable.from_node(child_node.variable)
        self.node_vars[child_node.variable.name] = node_variable
        
        if node_variable in self.node_defs:
            self.node_defs[node_variable] = ast.NodeDescription(
                ast.Conjunction([self.node_defs[node_variable].expression, 
                                 child_node.expression.expression]))
        else:
            self.node_defs[node_variable] = child_node.expression
        
        return self.REPLACE(create_varref(child_node.variable.name, 
                                          container_type = child_node.variable.container))
    
    @ast_visitor.node_handler(ast.Predicate)
    def handle_predicate(self, child_node):
        """Stores the predicate in the list of predicates."""
        self.predicates.append(child_node)
        return self.CONTINUE(child_node)
    
    @ast_visitor.node_handler(ast.SiblingOperator, 
               ast.CornerOperator,
               ast.DominanceOperator,
               ast.PrecedenceOperator,
               ast.SecEdgeOperator)
    def constraint_op(self, child_node):
        """Stores the constraint in the list of constraints."""
        self.constraints.append(child_node)
        return self.CONTINUE(child_node)
    
    def setup(self, query_ast):
        """Creates the collections for the internal representation of the query."""
        self.predicates = []
        self.node_defs = {}
        self.node_vars = {}
        self.constraints = []

    def _get_variable(self, variable):
        """Returns a node variable object associated with the AST fragment `variable`.
        
        If `variable` is seen the first time, a new node variable is created using
        `NodeVariable.from_node`.
        """
        try:
            return self.node_vars[variable.name]
        except KeyError:
            node_variable = self.node_vars[variable.name] = NodeVariable.from_node(variable)
            self.node_defs[node_variable] = ast.NodeDescription(ast.Nop())
            return node_variable
        
    def _process_predicates(self, predicates):
        """Creates the predicate objects.
        
        The predicate objects are created from the AST nodes using the `predicate_factory`.
        """
        for pred_ast_node in self.predicates:
            ast_var, predicate = self.predicate_factory.create(pred_ast_node)
            predicates[self._get_variable(ast_var)].append(predicate)
    
    def _process_constraints(self, predicates):
        """Creates the constraint objects.
        
        The constraints are created from the AST representations using the `constraint_factory`.
        """
        result = []
        for constraint_ast_node in self.constraints:
            left_var = self._get_variable(constraint_ast_node.left_operand.variable)
            right_var = self._get_variable(constraint_ast_node.right_operand.variable)
            
            constraint = self.constraint_factory.create(
                constraint_ast_node, (left_var.var_type, right_var.var_type), self._ev_context)
            
            result.append(((left_var, right_var), constraint))
            
            for node_var, var_type in zip((left_var, right_var), 
                                          constraint.get_node_variable_types()):
                node_var.refine_type(var_type)
        
        for (left_var, right_var), constraint in result:
            left_p, right_p = constraint.get_predicates(left_var, right_var)
            predicates[left_var].extend(left_p)
            predicates[right_var].extend(right_p)
            
        return result

    def _add_type_predicates(self, predicates):
        """Adds type predicates to the predicate lists if necessary.
        
        A type predicate is only added for a node variable if all of the following conditions
        are true:
         * the node description is empty
         * no predicates are defined for the variable
         * the variable type is not `NodeType.UNKNOWN`
        
        This mechanism is different from handling of feature records. The type predicate
        is added to each disjunct, while the feature record can differ between each disjunct.
        """
        for node_variable, description in self.node_defs.iteritems():
            if description.expression.TYPE is ast.Nop and len(predicates[node_variable]) == 0 \
                and node_variable.var_type is not NodeType.UNKNOWN:
                predicates[node_variable].append(NodeTypePredicate(node_variable.var_type))

    def from_ast(self, query_ast):
        """Convert a query AST into a result builder object.
        
        Query ASTs are in the same state as returned by the parser.
        
        The result builder class is injected using the `get_result_builder_class`
        on the evaluator context.
        """
        return self.run(query_ast)
    
    def result(self, query_ast):
        """Processes the collected items and returns the query object."""        
        predicates = defaultdict(list)
        
        for node_variable, node_desc in self.node_defs.iteritems():
            self.nodedesc_normalizer.run(node_desc)
            node_var_type, has_frec = self._ntyper.run(node_desc, node_variable)
            node_variable.refine_type(node_var_type)

            if has_frec:
                predicates[node_variable].append(NodeTypePredicate(node_var_type))
                
        
        self._process_predicates(predicates)
        constraints = self._process_constraints(predicates)
        self._add_type_predicates(predicates)

        return self._ev_context.get_result_builder_class(len(constraints) > 0)(
            self._ev_context, self.node_defs, predicates, constraints)
