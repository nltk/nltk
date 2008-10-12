# -*- coding: utf-8 -*-
# Copyright © 2007-2008 Stockholm TreeAligner Project
# Author: Torsten Marek <shlomme@gmx.net>
# Licensed under the GNU GPLv2
"""This module contains the class for searching nodes that fit a given node description.

"""
import os
import operator
import re

from itertools import count
from functools import partial

from nltk_contrib.tiger.graph import NodeType
from nltk_contrib.tiger.index import IndexNodeId
from nltk_contrib.tiger.query.node_variable import NodeVariable
from nltk_contrib.tiger.query import ast
from nltk_contrib.tiger.query.predicates import NodeTypePredicate
from nltk_contrib.tiger.query.ast_visitor import AstVisitor, node_handler, post_child_handler
from nltk_contrib.tiger.query.ast_utils import split_children
from nltk_contrib.tiger.query.exceptions import ConflictError

__all__ = ["NodeSearcher"]


class EmptyResultException(Exception):
    """Escaping exception for queries that are trivially empty."""
    pass


class NullGraphFilter(object):
    """Graph filter that does not filter anything."""
    def get_initial_filters(self, corpus_size):
        """Returns the initial graph filter.
        
        In this implementation, there are no filters.
        """
        return []


class EqualPartitionsGraphFilter(object):
    """A graph filter to split a corpus into N equally large parts.
    
    *Parameters*:
     * `this_part`: the ID of the current part, 0-based
     * `part_count`: the number of total parts
    """
    def __init__(self, this_part, part_count):
        self._this_part = this_part
        self._part_count = part_count

    def get_initial_filters(self, corpus_size):
        """Returns the initial graph filter.
        
        In this implementation, returns a filter that will select all graphs
        from a given range of graph IDs.
        """
        f = []
        
        part_size = corpus_size // self._part_count
        
        if self._this_part > 0:
            f.append("node_data.id >= %i" % (
                (self._this_part * part_size) << IndexNodeId.NODE_BIT_WIDTH, ))
        if self._this_part + 1 < self._part_count:
            f.append("node_data.id < %i" % (
                ((self._this_part + 1) * part_size) << IndexNodeId.NODE_BIT_WIDTH, ))
        return f
        
        
class NodeQueryCompiler(AstVisitor):
    """An AST visitor that takes a node query and compiles it into an SQL query."""
    class PaddingCursor(object):
        """A fake node cursor that returns a node for each graph in the corpus.
        
        Used to pad queries that only contain set variables.
        
        *Parameters*:
         * `length`: the size of the corpus
        """
        def __init__(self, length):
            self._length = length
            
        def __iter__(self):
            return ((0, graph_id) for graph_id in xrange(self._length))
        
        
    get_temp_table = ("_temp_regex_table_%i_%i" % (os.getpid(), c) for c in count()).next

    MATCH = True
    NO_MATCH = False
    SQL_OPERATORS = {MATCH: "=", NO_MATCH: "!="}

    def __init__(self, db, graph_filter):
        super(self.__class__, self).__init__()
        self._featureids = dict(
            db.execute("SELECT name, id FROM features"))

        self._feature_caches = dict(
            (name, {}) for name in self._featureids)
        
        self._db = db
        self.corpus_size = self._db.execute("SELECT COUNT(id) FROM graphs").fetchone()[0]
        self._temp_tables = {}
        self.current_query = []
        self._graph_filter = graph_filter
        
    @post_child_handler(ast.Disjunction)
    def after_disjunction_subexpr(self, node, child_name):
        """Creates a new query for a new part of a toplevel disjunction."""
        if child_name < len(node.children) - 1:
            self.current_query = []
            self.queries.append(self.current_query)
            self.types.append(None)
            
    @node_handler(ast.FeatureRecord)
    def handle_feature_record(self, child_node):
        if self._node_type is NodeType.UNKNOWN:
            self.types[-1] = child_node.type
        return self.STOP
    
    @node_handler(ast.FeatureConstraint)
    def handle_feature_constraint(self, child_node):
        """Handles a feature constraint and stores it for later conversion into SQL."""
        expr = child_node.expression
        if expr.TYPE is ast.Negation:
            self.current_query.append((child_node.feature, self.NO_MATCH, expr.expression))
        elif expr.TYPE is ast.Conjunction:
            self._add_conjunction_constraints(child_node.feature, expr)
        else:
            self.current_query.append((child_node.feature, self.MATCH, expr))
            
        return self.STOP

    def _add_conjunction_constraints(self, feature_name, expr):
        """Adds all literals from a conjunction to the list of feature constraints.
        
        Conflict checking is performed, expressions like "A"&"B" will lead to a 
        `ConflictError`.
        """
        negated, literals = split_children(expr, ast.Negation)
            
        has_explicit_match = False
        
        for literal in literals:
            if literal.TYPE is ast.StringLiteral:
                if has_explicit_match:
                    raise ConflictError, \
                          "Feature '%s' has two conflicting constraints." % (feature_name, )
                
                has_explicit_match = True

                self.current_query.append((feature_name, self.MATCH, literal))
            
        if not has_explicit_match:
            for literal in literals:
                self.current_query.append((feature_name, self.MATCH, literal))
                    
            for n in negated:
                self.current_query.append((feature_name, self.NO_MATCH, n.expression))
        
    def setup(self, query, node_type, predicates):
        """Setup ast visitor for a new run."""
        self._node_type = node_type
        self.current_query = []
        self.queries = [self.current_query]
        self.types = [None]
        
    def cleanup_temporary_tables(self):
        """Drops all temporary tables created for regex matches."""
        for table_name in self._temp_tables.itervalues():
            self._db.execute("DROP TABLE %s" % (table_name, ))
        self._temp_tables = {}
        
    def _get_feature_value_id(self, feature_name, feature_value):
        """Returns the value id of `feature_value` from the feature `feature_name`.
        
        Uses a cache internally."""
        try:
            return self._feature_caches[feature_name][feature_value]
        except KeyError:
            cur = self._db.cursor()
            cur.execute("""SELECT value_id FROM feature_values 
            WHERE feature_id = ? AND value = ?""", 
                        (self._featureids[feature_name], feature_value))
            try:
                value_id = cur.fetchone()[0]
            except TypeError:
                raise EmptyResultException
            self._feature_caches[feature_name][feature_value] = value_id
            return value_id

    def _create_new_regex_table(self, feature_name, match_policy, regex_string):
        """Creates a temporary table for evaluation of regular expression constraints.
        
        A new temporary table is created, containing all values of a given feature, matching
        a regular expression with a given match policy. The table contains a single column, 
        named `id`, which is also the primary key, and contains the feature value ids.
        
        *Parameters*:
         * `feature_name`: the feature for which to create the table
         * `match_policy`: NodeSearcher.MATCH or NodeSearch.NO_MATCH
         * `regex_string`: the regular expression string to use
        
        Returns the name of the temporary table that contains the values.
        """
        expected = bool if match_policy is self.MATCH else partial(operator.is_, None)
        
        if not regex_string.endswith("$"):
            regex_string += "$"
            
        match = re.compile(regex_string, re.UNICODE).match

        table_name = self.get_temp_table()
                
        cursor = self._db.cursor()
        cursor.execute("CREATE TEMPORARY TABLE %s (id INTEGER PRIMARY KEY)" % (table_name, ))
        self._db.create_function("CURR_REGEX", 1, lambda feature: expected(match(feature)))
        cursor.execute(
            """INSERT INTO %s (id) 
            SELECT value_id FROM feature_values 
            WHERE feature_id = ? AND CURR_REGEX(value)""" % (table_name, ),
                                                          (self._featureids[feature_name], ))
        cursor.close()
        if cursor.rowcount == 0:
            self._db.rollback()
            raise EmptyResultException
        else:
            self._db.commit()
            return table_name
        
    def _get_temp_regex_table(self, feature_name, match_policy, regex_string):
        """Returns the temporary table for reguluar expression constraints.
        
        Creates the table, if necessary.
        """
        temp_table_key = (feature_name, match_policy, regex_string)
        try:
            return self._temp_tables[temp_table_key]
        except KeyError:
            temp_table_name = self._create_new_regex_table(feature_name, match_policy, regex_string)
            return self._temp_tables.setdefault(temp_table_key, temp_table_name)
            
    def _create_single_select_stmt(self, feature_constraints, node_type, predicates):
        """Creates an SQL select statement from feature constraints and predicates.
        
        Handles only a single disjunct of a query."""
        joins = set()
        wheres = self._graph_filter.get_initial_filters(self.corpus_size)

        if len(feature_constraints) == 0 and node_type is not None:
            wheres.append("(%s)" % (NodeTypePredicate(node_type).get_query_fragment(), ))
        
        for name, match_policy, value in feature_constraints:
            joins.add("JOIN feature_iidx_%s ON feature_iidx_%s.node_id = node_data.id" % (
                name, name))
            
            if value.TYPE is ast.StringLiteral:
                wheres.append("(feature_iidx_%s.value_id %s %s)" % (
                    name, self.SQL_OPERATORS[match_policy], 
                    self._get_feature_value_id(name, value.string)))
            elif value.TYPE is ast.RegexLiteral:
                temp_table = self._get_temp_regex_table(name, match_policy, value.regex)
                
                joins.add(
                    "JOIN %s ON %s.id = feature_iidx_%s.value_id" % (temp_table, temp_table, name))
        
        wheres.extend("(%s)" % (f.get_query_fragment(), ) for f in predicates if f.FOR_NODE)
        if not wheres:
            wheres = ["1"]
        return "SELECT node_data.id, node_data.id >> 12 AS graphid FROM node_data %s WHERE %s" % (
            " ".join(joins), " AND ".join(wheres))

    def result(self, query_ast, inferred_node_type, predicates):
        """Assembles the parts of a query and returns the final query string."""
        order_clause = " ORDER BY graphid" if len(self.queries) > 1 else ""

        return " UNION ".join(self._create_single_select_stmt(query, node_type, predicates) 
                              for query, node_type in zip(self.queries, self.types)) + order_clause


    def compile_query(self, query_ast, inferred_node_type, predicates):
        """Creates the complete SQL query for a single node description.
        
        Several disjuncts will be connected by an SQL UNION statement. Nodes from the same graph 
        are guaranteed to be consecutive in the result set."""
        return self.run(query_ast, inferred_node_type, predicates)
    
    def get_cursor(self, expression):
        return self._db.cursor().execute(expression)
    
    def get_padding_cursor(self):
        return iter(self.PaddingCursor(self.corpus_size))
    

class GraphIterator(object):
    def __init__(self, query_compiler, node_descriptions, predicates):
        self._node_descriptions = node_descriptions
        self._predicates = predicates

        self._shared_variables = self._get_shared_variables()
        self._node_vars = [v for v in node_descriptions if v not in self._shared_variables]
        self._query_compiler = query_compiler
        
        self._node_cursors = []
        self._node_tips = {}
        self._set_tips = {}
       
    def _compile_query(self, node_variable):
        return self._query_compiler.compile_query(
            self._node_descriptions[node_variable], 
            node_variable.var_type, 
            self._predicates.get(node_variable, []))    
    
    def _get_shared_variables(self):
        def can_share(var_a, var_b):
            return (var_b not in shared \
                    and self._node_descriptions[var_a] == self._node_descriptions[var_b]\
                    and not (var_a in self._predicates or var_b in self._predicates))
        def variable_combinations():
            variables = list(self._node_descriptions)
            return [(variables[idx1], variables[idx2])
                    for idx1 in range(len(variables) - 1)
                    for idx2 in range(idx1 + 1, len(variables))]
        
        shared = {}
        for var1, var2 in variable_combinations():
            if can_share(var1, var2):
                shared[var2] = var1
        return shared

    def _get_set_predicates(self):
        """Returns a list `(var_name, predicate)` containing all constraints on node sets."""
        return [(name, pred)
                for name, node_predicates in self._predicates.iteritems()
                if name.is_set
                for pred in node_predicates
                if not pred.FOR_NODE]
    
    def _create_node_iters(self):
        self._node_cursors = []
        self._node_tips = {}
        self._set_tips = {}
        
        # a query compilation might trigger the creation of a temporary table,
        # so we have to compile all queries first before we get the cursors
        exprs = [(node_variable, self._compile_query(node_variable))
                 for node_variable in self._node_vars]
        
        self._node_cursors = [
            (node_variable, self._query_compiler.get_cursor(expression), 
             self._set_tips if node_variable.is_set else self._node_tips)
            for node_variable, expression in exprs]
        self._pad_nodesets()
        
    def _pad_nodesets(self):
        if all(var.is_set for var in self._node_vars):
            self._node_cursors.append(
                (NodeVariable("", False), self._query_compiler.get_padding_cursor(), 
                 self._node_tips))

    def _remove_iter(self, node_var, node_cursor):
        if node_var.is_set:
            node_cursor.close()
            self._node_cursors = [x for x in self._node_cursors if x[0] != node_var]
            return False
        else:
            return True
        
    def _read_tips(self):
        for node_variable, node_iter, tips in self._node_cursors:
            try:
                tips[node_variable] = node_iter.next()
            except StopIteration:
                if self._remove_iter(node_variable, node_iter):
                    raise EmptyResultException

    def _new_empty_result(self):
        current_graph = {}
        for node_var in self._node_vars:
            current_graph[node_var] = []
            
        for target, source in self._shared_variables.iteritems():
            current_graph[target] = current_graph[source]
        return current_graph    

    @staticmethod
    def _dump_nodes(from_iter, current_tip, next_graph):
        while current_tip[1] < next_graph:
            current_tip = from_iter.next()
        return current_tip
    
    def _find_graphs(self):
        depleted = False
        max_graphid = max(self._node_tips.values())[1]
        
        while not depleted:
            min_graphid = min(self._node_tips.values())[1]
            if min_graphid == max_graphid:
                new_result = self._new_empty_result()
                    
                for varname, node_iter, tips in self._node_cursors:
                    try:
                        node_list = new_result[varname]
                    except KeyError:
                        node_list = []
                        
                    try:
                        current_tip = self._dump_nodes(node_iter, tips[varname], min_graphid)
                            
                        while current_tip[1] == min_graphid:
                            node_list.append(current_tip[0])
                            current_tip = node_iter.next()
                        tips[varname] = current_tip
                        if not varname.is_set and current_tip[1] > max_graphid:
                            max_graphid = current_tip[1]
                    except StopIteration:
                        depleted = self._remove_iter(varname, node_iter)
                
                yield min_graphid, new_result
                
            else:
                for varname, node_iter, tips in self._node_cursors:
                    try:
                        current_tip = tips[varname] = \
                                    self._dump_nodes(node_iter, tips[varname], max_graphid)
                        if not varname.is_set and current_tip[1] > max_graphid:
                            max_graphid = current_tip[1]
                    except StopIteration:
                        depleted = self._remove_iter(varname, node_iter)
        
        self._cleanup()

    def _check_set_constraints(self, set_constraints, graph_result):
        for node_variable, constraint in set_constraints:
            if not constraint.check_node_set(graph_result[node_variable]):
                return False
        else:
            return True
    
    def _cleanup(self):
        for node_variable, cursor, tips in self._node_cursors:
            cursor.close()
        self._node_cursors = []
        self._query_compiler.cleanup_temporary_tables()
        
    def __iter__(self):
        try:
            self._create_node_iters()
            self._read_tips()
        except EmptyResultException:
            self._cleanup()
            return iter([])
        
        set_constraints = self._get_set_predicates()
        
        if set_constraints:
            return ((graphid, node_cands) for graphid, node_cands in self._find_graphs()
                    if self._check_set_constraints(set_constraints, node_cands))
        else:
            return self._find_graphs()


class NodeSearcher(object):
    """Class for node searching based on node descriptions and predicates.

    :Parameters:
      `db`: the database connection to be used.
      `graph_filter`: graph filter for partial results in parallel processing, 
       `NullGraphFilter` by default.
     
    Parallel Processing
    ===================
    For parallel procesing, the parameter `graph_filter` can be used so that a single node 
    searcher only returns a fraction of the graphs from the corpus, and several node searchers
    can be used in parallel to return all results.
    """            
    def __init__(self, db, graph_filter = NullGraphFilter()):
        self._query_compiler = NodeQueryCompiler(db, graph_filter)
    
    def search_nodes(self, node_descriptions, predicates):
        return GraphIterator(self._query_compiler, node_descriptions, predicates)
