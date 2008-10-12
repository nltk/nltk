# -*- coding: utf-8 -*-
# Copyright © 2007-2008 Stockholm TreeAligner Project
# Author: Torsten Marek <shlomme@gmx.net>
# Licensed under the GNU GPLv2
"""This module contains classes for building result sets for TIGERSearch queries .

The result builder classes evaluate a TigerSearch query based on the internal
representation of the query.

The algorithm and the interfaces in this module are still subject to heavy change. For more
information, see the inline comments.
"""
import operator
from functools import partial
from itertools import count, izip
from collections import defaultdict

from nltk_contrib.tiger.index import IndexNodeId
from nltk_contrib.tiger.query.exceptions import MissingFeatureError
from nltk_contrib.tiger.utils.parallel import multiprocessing
from nltk_contrib.tiger.query.constraints import Direction
from nltk_contrib.tiger.query.nodesearcher import NodeSearcher, EqualPartitionsGraphFilter

__all__ = ["ResultBuilder", "ParallelResultBuilder"]

product = partial(reduce, operator.mul)

def named_cross_product(items):
    def _outer_product(depth, combination):
        varname, nodes = items[-depth]
        for node in nodes:
            combination[varname] = node
            if depth == 1:
                yield combination.copy()
            else:
                for res in _outer_product(depth - 1, combination):
                    yield res
    
    if items:
        return _outer_product(len(items), {})
    else:
        return iter([{}])


def partition_variables(variables, constraints):
    var_connections = dict(izip(variables, count()))
    
    for l, r in constraints:
        new_id = var_connections[l]
        old_id = var_connections[r]
        for name, value in var_connections.iteritems():
            if value == old_id:
                var_connections[name] = new_id
        
    sets = defaultdict(set)
    for name, value in var_connections.iteritems():
        sets[value].add(name)
    return sets.values()


class ConstraintChecker(object):
    @classmethod
    def _nodevar_idx_combinations(cls, ordered_node_vars):
        return [(upper_key, lower_key) 
                for lower_key in xrange(1, len(ordered_node_vars))
                for upper_key in xrange(lower_key)]
    
    @classmethod
    def _get_node_variables(cls, constraints):
        return set(var for var_pair in constraints for var in var_pair)
    
    @classmethod
    def prepare(cls, constraints, sizes = {}):
        constraints = dict(constraints)
        
        set_weight = sum(sizes.values()) + 1
        
        ordered_node_vars = sorted(
            cls._get_node_variables(constraints),
            key = lambda k: set_weight if k.is_set else sizes.get(k, 0))
        
        ordered_constraints = []
        for (upper_idx, lower_idx) in cls._nodevar_idx_combinations(ordered_node_vars):
            var_pair = (ordered_node_vars[upper_idx], ordered_node_vars[lower_idx])
            
            fail_after_success = False
            
            if var_pair in constraints:
                constraint = constraints[var_pair].check
                direction = constraints[var_pair].get_singlematch_direction()

                if direction is Direction.BOTH or direction is Direction.LEFT_TO_RIGHT:
                    fail_after_success = True
                ordered_constraints.append((var_pair[0], var_pair[1], constraint, False, fail_after_success))

            elif var_pair[::-1] in constraints:
                constraint = constraints[var_pair[::-1]].check
                direction = constraints[var_pair[::-1]].get_singlematch_direction()

                if direction is Direction.BOTH or direction is Direction.RIGHT_TO_LEFT:
                    fail_after_success = True
                ordered_constraints.append((var_pair[0], var_pair[1], constraint, True, fail_after_success))


        return partial(ConstraintChecker, ordered_constraints)
        
    def __init__(self, constraints, nodes, query_context):
        self.ordered_constraints = constraints
        self.nodes = nodes
        self.ok = set()
        self.has_results = self.prefilter(query_context)

    def prefilter(self, query_context):
        for (left_var, right_var, constraint, exchange, fail_after_success) in self.ordered_constraints:
            l_success = set()
            r_success = set()
            for left in self.nodes[left_var]:
                ldata = query_context.get_node(left)
                
                for right in self.nodes[right_var]:
                    rdata = query_context.get_node(right)
                    
                    if exchange:
                        larg, rarg = rdata, ldata
                    else:
                        larg, rarg = ldata, rdata
                    
                    query_context.constraint_checks += 1
                    if constraint(larg, rarg, query_context):
                        self.ok.add((left, right))
                        if not right_var.is_set:
                            l_success.add(left)
                            r_success.add(right)
                            if fail_after_success:
                                break
                    elif right_var.is_set:
                        break
                else:
                    if right_var.is_set:
                        l_success.add(left)
                        r_success.update(self.nodes[right_var])
                       
            if not l_success:
                return False
            if not r_success and not right_var.is_set:
                return False
            self.nodes[left_var] = list(l_success)
            self.nodes[right_var] = list(r_success)
        return True
            
    def _nodeids(self, query_result):
        for node_var in query_result:
            query_result[node_var] = IndexNodeId.from_int(query_result[node_var])
        return query_result
    
    def extract(self):
        """Creates the result set.
        
        The function currently uses a brute-force attempt. Please see the TODOs at the top
        of the module.
        """
        if self.has_results:
            g = [item for item in self.nodes.items() if not item[0].is_set]
            
            return [self._nodeids(query_result)
                    for query_result in named_cross_product(g)
                    if self._check(query_result)]
        else:
            return []

    def _check(self, result):
        for (left_variable, right_variable, __, __, __) in self.ordered_constraints:
            if right_variable.is_set:
                for right_node in self.nodes[right_variable]:
                    if (result[left_variable], right_node) not in self.ok:
                        return False
            else:
                if (result[left_variable], result[right_variable]) not in self.ok:
                    return False
        return True
        
PREPARE_NEW_AFTER = 100

def cct_search(graph_results, query_context):
    query_context._ncache.clear()
    query_context.checked_graphs += 1
    if query_context.checked_graphs == PREPARE_NEW_AFTER:
        query_context.checker_factory = ConstraintChecker.prepare(query_context.constraints, query_context.node_counts)
    elif query_context.checked_graphs < PREPARE_NEW_AFTER:
        for node_var, node_ids in graph_results.iteritems():
            query_context.node_counts[node_var] += len(node_ids)
        
    c = query_context.checker_factory(graph_results, query_context)
    return c.extract()


class LazyResultSet(object):
    def __init__(self, nodes, query_context):
        query_context.checked_graphs += 1
        self._nodes = [(node_var.name, [IndexNodeId.from_int(nid) for nid in node_ids])
                       for node_var, node_ids in nodes.iteritems()
                       if not node_var.is_set]

        self._size = product((len(ids) for var, ids in self._nodes), 1)
        self._items = None
        
    def __len__(self):
        return self._size

    def __getitem__(self, idx):
        if self._items is None:
            self._items = list(iter(self))
        return self._items[idx]
    
    def __iter__(self):
        return named_cross_product(self._nodes)
        

class QueryContext(object):
    def __init__(self, db, constraints, nodevars):
        self.cursor = db.cursor()
        self._ncache = {}
        self.constraints = constraints
        self.node_counts = defaultdict(int)
        
        variable_partitions = partition_variables(nodevars, (c[0] for c in constraints))
        if len(variable_partitions) == len(nodevars):
            self.constraint_checker = LazyResultSet
        elif len(variable_partitions) == 1:
            self.checker_factory = ConstraintChecker.prepare(constraints)
            self.constraint_checker = cct_search
        else:
            raise MissingFeatureError, "Missing feature: disjoint constraint sets. Please file a bug report."
        self._reset_stats()
        
    def _reset_stats(self):
        self.node_cache_hits = 0
        self.node_cache_misses = 0
        self.checked_graphs = 0
        self.constraint_checks = 0
        
    def get_node(self, node_id):
        try:
            self.node_cache_hits += 1
            return self._ncache[node_id]
        except KeyError:
            self.node_cache_misses += 1
            self.cursor.execute("""SELECT id, edge_label,  
            continuity, left_corner, right_corner, token_order, gorn_address
            FROM node_data WHERE id = ?""", (node_id, ))
            rs = self._ncache[node_id] = self.cursor.fetchone()
            return rs    
    

class ResultBuilderBase(object):
    def __init__(self, node_descriptions, predicates):
        self._nodes = node_descriptions
        self._predicates = predicates
        
    def node_variable_names(self):
        """Returns the set of node variables defined in the query."""
        return frozenset(nv.name for nv in self._nodes)


class ResultBuilder(QueryContext, ResultBuilderBase):
    def __init__(self, ev_context, node_descriptions, predicates, constraints):
        QueryContext.__init__(self, ev_context.db, constraints, node_descriptions.keys())
        ResultBuilderBase.__init__(self, node_descriptions, predicates)
        self._nodesearcher = ev_context.nodesearcher
        
    def evaluate(self):
        """Evaluates the query.
        
        Returns a list of `(graph_number, results)` tuples, where `results` is a list of 
        dictionaries that contains `variable: node_id` pairs for all defined variable names.
        """
        self._reset_stats()
        matching_graphs = self._nodesearcher.search_nodes(self._nodes, self._predicates)

        return filter(operator.itemgetter(1),
                      ((graph_id, self.constraint_checker(nodes, self))
                       for graph_id, nodes in matching_graphs))


class ParallelEvaluatorContext(object):
    def __init__(self, db_provider, graph_filter):
        self.db = db_provider.connect()
        self.nodesearcher = NodeSearcher(self.db, graph_filter)
        self.db_provider = db_provider


def evaluate_parallel(db_provider, nodes, predicates, constraints, result_queue, graph_filter):
    ev_ctx = ParallelEvaluatorContext(db_provider, graph_filter)
    query = ResultBuilder(ev_ctx, nodes, predicates, constraints)

    result_set = query.evaluate()
    result_queue.put((result_set, (query.checked_graphs, query.constraint_checks, 
                      query.node_cache_hits, query.node_cache_misses)))
    result_queue.close()
    

class ParallelResultBuilder(ResultBuilderBase):
    def __init__(self, ev_context, node_descriptions, predicates, constraints):
        super(self.__class__, self).__init__(node_descriptions, predicates)
        self._constraints = constraints
        self._db_provider = ev_context.db_provider
        self._reset_stats()
        
    def _reset_stats(self):
        self.node_cache_hits = 0
        self.node_cache_misses = 0
        self.checked_graphs = 0
        self.constraint_checks = 0
        
    def evaluate(self):
        self._reset_stats()
        result_queue = multiprocessing.Queue()
        num_workers = multiprocessing.cpuCount()
        workers = []
        for i in range(num_workers):
            worker = multiprocessing.Process(
                target = evaluate_parallel,
                args = (self._db_provider, self._nodes, self._predicates,
                        self._constraints, result_queue, 
                        EqualPartitionsGraphFilter(i, num_workers)))
            worker.start()
            workers.append(worker)
        
        results = []
        running_workers = num_workers
        while running_workers > 0:
            partial_result, stats = result_queue.get()
            results.extend(partial_result)
            self.checked_graphs += stats[0]
            self.constraint_checks += stats[1]
            self.node_cache_hits += stats[2]
            self.node_cache_misses += stats[3]
            
            running_workers -= 1
        for worker in workers:
            worker.join()
        return results
