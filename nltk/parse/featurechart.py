# -*- coding: utf-8 -*-
# Natural Language Toolkit: Chart Parser for Feature-Based Grammars
#
# Copyright (C) 2001-2010 NLTK Project
# Author: Rob Speer <rspeer@mit.edu>
#         Peter Ljunglöf <peter.ljunglof@heatherleaf.se>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT
#
# $Id$

"""
Extension of chart parsing implementation to handle grammars with
feature structures as nodes.
"""

import yaml, sys

from nltk.featstruct import FeatStruct, unify, FeatStructParser, TYPE, find_variables
from nltk.sem import logic
from nltk.grammar import Nonterminal, Production, ContextFreeGrammar
from nltk.compat import defaultdict
from nltk.grammar import FeatStructNonterminal
import nltk.data

from api import *
from chart import *

#////////////////////////////////////////////////////////////
# Tree Edge
#////////////////////////////////////////////////////////////

class FeatureTreeEdge(TreeEdge):
    """
    A specialized tree edge that allows shared variable bindings
    between nonterminals on the left-hand side and right-hand side.

    Each C{FeatureTreeEdge} contains a set of C{bindings}, i.e., a
    dictionary mapping from variables to values.  If the edge is not
    complete, then these bindings are simply stored.  However, if the
    edge is complete, then the constructor applies these bindings to
    every nonterminal in the edge whose symbol implements the
    interface L{SubstituteBindingsI}.
    """
    def __init__(self, span, lhs, rhs, dot=0, bindings=None):
        """
        Construct a new edge.  If the edge is incomplete (i.e., if
        C{dot<len(rhs)}), then store the bindings as-is.  If the edge
        is complete (i.e., if C{dot==len(rhs)}), then apply the
        bindings to all nonterminals in C{lhs} and C{rhs}, and then
        clear the bindings.  See L{TreeEdge} for a description of
        the other arguments.
        """
        if bindings is None: bindings = {}
        
        # If the edge is complete, then substitute in the bindings,
        # and then throw them away.  (If we didn't throw them away, we
        # might think that 2 complete edges are different just because
        # they have different bindings, even though all bindings have
        # already been applied.)
        if dot == len(rhs) and bindings:
            lhs = self._bind(lhs, bindings)
            rhs = [self._bind(elt, bindings) for elt in rhs]
            bindings = {}

        # Initialize the edge.
        TreeEdge.__init__(self, span, lhs, rhs, dot)
        self._bindings = bindings

    # [staticmethod]
    def from_production(production, index):
        """
        @return: A new C{TreeEdge} formed from the given production.
            The new edge's left-hand side and right-hand side will
            be taken from C{production}; its span will be 
            C{(index,index)}; and its dot position will be C{0}.
        @rtype: L{TreeEdge}
        """
        return FeatureTreeEdge(span=(index, index), lhs=production.lhs(),
                               rhs=production.rhs(), dot=0)
    from_production = staticmethod(from_production)

    def move_dot_forward(self, new_end, bindings=None):
        """
        @return: A new C{FeatureTreeEdge} formed from this edge.
            The new edge's dot position is increased by C{1}, 
            and its end index will be replaced by C{new_end}.
        @rtype: L{FeatureTreeEdge}
        @param new_end: The new end index.
        @type new_end: C{int}
        @param bindings: Bindings for the new edge.
        @type bindings: C{dict}
        """
        return FeatureTreeEdge(span=(self._span[0], new_end),
                               lhs=self._lhs, rhs=self._rhs,
                               dot=self._dot+1, bindings=bindings)

    def _bind(self, nt, bindings):
        if not isinstance(nt, FeatStructNonterminal): return nt
        return nt.substitute_bindings(bindings)

    def next_with_bindings(self):
        return self._bind(self.next(), self._bindings)

    def bindings(self):
        """
        Return a copy of this edge's bindings dictionary.
        """
        return self._bindings.copy()

    def variables(self):
        """
        @return: The set of variables used by this edge.
        @rtype: C{set} of L{Variable}
        """
        return find_variables([self._lhs] + list(self._rhs) +
                              self._bindings.keys() + self._bindings.values(),
                              fs_class=FeatStruct)

    def __str__(self):
        if self.is_complete():
            return TreeEdge.__str__(self)
        else:
            bindings = '{%s}' % ', '.join('%s: %r' % item for item in
                                           sorted(self._bindings.items()))
            return '%s %s' % (TreeEdge.__str__(self), bindings)

    # two edges with different bindings are not equal.
    def __cmp__(self, other):
        if self.__class__ != other.__class__: return -1
        return cmp((self._span, self._lhs, self._rhs,
                    self._dot, self._bindings),
                   (other._span, other._lhs, other._rhs,
                    other._dot, other._bindings))
    
    def __hash__(self):
        # cache this:?
        return hash((self._lhs, self._rhs, self._span, self._dot,
                     tuple(sorted(self._bindings))))


#////////////////////////////////////////////////////////////
# A specialized Chart for feature grammars
#////////////////////////////////////////////////////////////

# TODO: subsumes check when adding new edges

class FeatureChart(Chart):
    """
    A Chart for feature grammars.
    @see: L{Chart} for more information.
    """

    def select(self, **restrictions):
        """
        Returns an iterator over the edges in this chart. 
        See L{Chart.select} for more information about the
        C{restrictions} on the edges.
        """
        # If there are no restrictions, then return all edges.
        if restrictions=={}: return iter(self._edges)
            
        # Find the index corresponding to the given restrictions.
        restr_keys = restrictions.keys()
        restr_keys.sort()
        restr_keys = tuple(restr_keys)

        # If it doesn't exist, then create it.
        if restr_keys not in self._indexes:
            self._add_index(restr_keys)
                
        vals = tuple(self._get_type_if_possible(restrictions[key]) 
                     for key in restr_keys)
        return iter(self._indexes[restr_keys].get(vals, []))
    
    def _add_index(self, restr_keys):
        """
        A helper function for L{select}, which creates a new index for
        a given set of attributes (aka restriction keys).
        """
        # Make sure it's a valid index.
        for key in restr_keys:
            if not hasattr(EdgeI, key):
                raise ValueError, 'Bad restriction: %s' % key

        # Create the index.
        index = self._indexes[restr_keys] = {}

        # Add all existing edges to the index.
        for edge in self._edges:
            vals = tuple(self._get_type_if_possible(getattr(edge, key)()) 
                         for key in restr_keys)
            index.setdefault(vals, []).append(edge)
    
    def _register_with_indexes(self, edge):
        """
        A helper function for L{insert}, which registers the new
        edge with all existing indexes.
        """
        for (restr_keys, index) in self._indexes.items():
            vals = tuple(self._get_type_if_possible(getattr(edge, key)())
                         for key in restr_keys)
            index.setdefault(vals, []).append(edge)

    def _get_type_if_possible(self, item):
        """
        Helper function which returns the C{TYPE} feature of the C{item}, 
        if it exists, otherwise it returns the C{item} itself
        """
        if isinstance(item, dict) and TYPE in item:
            return item[TYPE]
        else:
            return item

    def parses(self, start, tree_class=Tree):
        trees = []
        for edge in self.select(start=0, end=self._num_leaves):
            if ( (isinstance(edge, FeatureTreeEdge)) and
                 (edge.lhs()[TYPE] == start[TYPE]) and
                 (unify(edge.lhs(), start, rename_vars=True)) ):
                trees += self.trees(edge, complete=True, tree_class=tree_class)
        return trees


#////////////////////////////////////////////////////////////
# Fundamental Rule
#////////////////////////////////////////////////////////////

class FeatureFundamentalRule(FundamentalRule):
    """
    A specialized version of the fundamental rule that operates on
    nonterminals whose symbols are C{FeatStructNonterminal}s.  Rather
    tha simply comparing the nonterminals for equality, they are
    unified.  Variable bindings from these unifications are collected
    and stored in the chart using a L{FeatureTreeEdge}.  When a
    complete edge is generated, these bindings are applied to all
    nonterminals in the edge.

    The fundamental rule states that:
        - [A S{->} S{alpha} * B1 S{beta}][i:j]
        - [B2 S{->} S{gamma} *][j:k]
    licenses the edge:
        - [A S{->} S{alpha} B3 * S{beta}][i:j]
    assuming that B1 and B2 can be unified to generate B3.
    """
    def apply_iter(self, chart, grammar, left_edge, right_edge):
        # Make sure the rule is applicable.
        if not (left_edge.end() == right_edge.start() and
                left_edge.is_incomplete() and
                right_edge.is_complete() and
                isinstance(left_edge, FeatureTreeEdge)):
            return
        found = right_edge.lhs()
        next = left_edge.next()
        if isinstance(right_edge, FeatureTreeEdge):
            if not is_nonterminal(next): return
            if left_edge.next()[TYPE] != right_edge.lhs()[TYPE]: return
            # Create a copy of the bindings.
            bindings = left_edge.bindings()
            # We rename vars here, because we don't want variables
            # from the two different productions to match.
            found = found.rename_variables(used_vars=left_edge.variables())
            # Unify B1 (left_edge.next) with B2 (right_edge.lhs) to
            # generate B3 (result).
            result = unify(next, found, bindings, rename_vars=False)
            if result is None: return
        else:
            if next != found: return
            # Create a copy of the bindings.
            bindings = left_edge.bindings()

        # Construct the new edge.
        new_edge = left_edge.move_dot_forward(right_edge.end(), bindings)
        
        # Add it to the chart, with appropriate child pointers.
        if chart.insert_with_backpointer(new_edge, left_edge, right_edge):
            yield new_edge

class FeatureSingleEdgeFundamentalRule(SingleEdgeFundamentalRule):
    """
    A specialized version of the completer / single edge fundamental rule 
    that operates on nonterminals whose symbols are C{FeatStructNonterminal}s.  
    Rather than simply comparing the nonterminals for equality, they are
    unified. 
    """
    _fundamental_rule = FeatureFundamentalRule()

    def _apply_complete(self, chart, grammar, right_edge):
        fr = self._fundamental_rule
        for left_edge in chart.select(end=right_edge.start(), 
                                      is_complete=False,
                                      next=right_edge.lhs()):
            for new_edge in fr.apply_iter(chart, grammar, left_edge, right_edge):
                yield new_edge

    def _apply_incomplete(self, chart, grammar, left_edge):
        fr = self._fundamental_rule
        for right_edge in chart.select(start=left_edge.end(), 
                                       is_complete=True,
                                       lhs=left_edge.next()):
            for new_edge in fr.apply_iter(chart, grammar, left_edge, right_edge):
                yield new_edge


#////////////////////////////////////////////////////////////
# Top-Down Prediction
#////////////////////////////////////////////////////////////

class FeatureTopDownInitRule(TopDownInitRule):
    def apply_iter(self, chart, grammar):
        for prod in grammar.productions(lhs=grammar.start()):
            new_edge = FeatureTreeEdge.from_production(prod, 0)
            if chart.insert(new_edge, ()):
                yield new_edge

class FeatureTopDownPredictRule(CachedTopDownPredictRule):
    """
    A specialized version of the (cached) top down predict rule that operates
    on nonterminals whose symbols are C{FeatStructNonterminal}s.  Rather
    than simply comparing the nonterminals for equality, they are
    unified.

    The top down expand rule states that:
        - [A S{->} S{alpha} * B1 S{beta}][i:j]
    licenses the edge:
        - [B2 S{->} * S{gamma}][j:j]
    for each grammar production C{B2 S{->} S{gamma}}, assuming that B1
    and B2 can be unified.
    """
    def apply_iter(self, chart, grammar, edge):
        if edge.is_complete(): return
        next, index = edge.next(), edge.end()
        if not is_nonterminal(next): return

        # If we've already applied this rule to an edge with the same
        # next & end, and the chart & grammar have not changed, then
        # just return (no new edges to add).
        done = self._done.get((next, index), (None,None))
        if done[0] is chart and done[1] is grammar: return
        
        for prod in grammar.productions(lhs=edge.next()):
            # If the left corner in the predicted production is 
            # leaf, it must match with the input.
            if prod.rhs():
                first = prod.rhs()[0]
                if is_terminal(first):
                    if index >= chart.num_leaves(): continue
                    if first != chart.leaf(index): continue
            
            # We rename vars here, because we don't want variables
            # from the two different productions to match.
            if unify(prod.lhs(), edge.next_with_bindings(), rename_vars=True):
                new_edge = FeatureTreeEdge.from_production(prod, edge.end())
                if chart.insert(new_edge, ()):
                    yield new_edge
        
        # Record the fact that we've applied this rule.
        self._done[next, index] = (chart, grammar)


#////////////////////////////////////////////////////////////
# Bottom-Up Prediction
#////////////////////////////////////////////////////////////

class FeatureBottomUpPredictRule(BottomUpPredictRule):
    def apply_iter(self, chart, grammar, edge):
        if edge.is_incomplete(): return
        for prod in grammar.productions(rhs=edge.lhs()):
            if isinstance(edge, FeatureTreeEdge): 
                next = prod.rhs()[0]
                if not is_nonterminal(next): continue
            
            new_edge = FeatureTreeEdge.from_production(prod, edge.start())
            if chart.insert(new_edge, ()):
                yield new_edge

class FeatureBottomUpPredictCombineRule(BottomUpPredictCombineRule):
    def apply_iter(self, chart, grammar, edge):
        if edge.is_incomplete(): return
        found = edge.lhs()
        for prod in grammar.productions(rhs=found):
            bindings = {}
            if isinstance(edge, FeatureTreeEdge): 
                next = prod.rhs()[0]
                if not is_nonterminal(next): continue
                
                # We rename vars here, because we don't want variables
                # from the two different productions to match.
                used_vars = find_variables((prod.lhs(),) + prod.rhs(),
                                           fs_class=FeatStruct)
                found = found.rename_variables(used_vars=used_vars)
                
                result = unify(next, found, bindings, rename_vars=False)
                if result is None: continue
            
            new_edge = (FeatureTreeEdge.from_production(prod, edge.start())
                        .move_dot_forward(edge.end(), bindings))
            if chart.insert(new_edge, (edge,)):
                yield new_edge

class FeatureEmptyPredictRule(EmptyPredictRule):
    def apply_iter(self, chart, grammar):
        for prod in grammar.productions(empty=True):
            for index in xrange(chart.num_leaves() + 1):
                new_edge = FeatureTreeEdge.from_production(prod, index)
                if chart.insert(new_edge, ()):
                    yield new_edge


#////////////////////////////////////////////////////////////
# Feature Chart Parser
#////////////////////////////////////////////////////////////

TD_FEATURE_STRATEGY = [LeafInitRule(),
                       FeatureTopDownInitRule(), 
                       FeatureTopDownPredictRule(), 
                       FeatureSingleEdgeFundamentalRule()]
BU_FEATURE_STRATEGY = [LeafInitRule(),
                       FeatureEmptyPredictRule(),
                       FeatureBottomUpPredictRule(),
                       FeatureSingleEdgeFundamentalRule()]
BU_LC_FEATURE_STRATEGY = [LeafInitRule(),
                          FeatureEmptyPredictRule(),
                          FeatureBottomUpPredictCombineRule(),
                          FeatureSingleEdgeFundamentalRule()]

class FeatureChartParser(ChartParser):
    def __init__(self, grammar, 
                 strategy=BU_LC_FEATURE_STRATEGY, 
                 trace_chart_width=20, 
                 chart_class=FeatureChart, 
                 **parser_args):
        ChartParser.__init__(self, grammar, 
                             strategy=strategy, 
                             trace_chart_width=trace_chart_width, 
                             chart_class=chart_class, 
                             **parser_args)

class FeatureTopDownChartParser(FeatureChartParser):
    def __init__(self, grammar, **parser_args):
        FeatureChartParser.__init__(self, grammar, TD_FEATURE_STRATEGY, **parser_args)

class FeatureBottomUpChartParser(FeatureChartParser):
    def __init__(self, grammar, **parser_args):
        FeatureChartParser.__init__(self, grammar, BU_FEATURE_STRATEGY, **parser_args)

class FeatureBottomUpLeftCornerChartParser(FeatureChartParser):
    def __init__(self, grammar, **parser_args):
        FeatureChartParser.__init__(self, grammar, BU_LC_FEATURE_STRATEGY, **parser_args)


#////////////////////////////////////////////////////////////
# Instantiate Variable Chart
#////////////////////////////////////////////////////////////

class InstantiateVarsChart(FeatureChart):
    """
    A specialized chart that 'instantiates' variables whose names
    start with '@', by replacing them with unique new variables.
    In particular, whenever a complete edge is added to the chart, any
    variables in the edge's C{lhs} whose names start with '@' will be
    replaced by unique new L{Variable}s.
    """
    def __init__(self, tokens):
        FeatureChart.__init__(self, tokens)
        
    def initialize(self):
        self._instantiated = set()
        FeatureChart.initialize(self)

    def insert(self, edge, child_pointer_list):
        if edge in self._instantiated: return False
        self.instantiate_edge(edge)
        return FeatureChart.insert(self, edge, child_pointer_list)
    
    def instantiate_edge(self, edge):
        """
        If the edge is a L{FeatureTreeEdge}, and it is complete, 
        then instantiate all variables whose names start with '@',
        by replacing them with unique new variables.
        
        Note that instantiation is done in-place, since the
        parsing algorithms might already hold a reference to 
        the edge for future use.
        """
        # If the edge is a leaf, or is not complete, or is
        # already in the chart, then just return it as-is.
        if not isinstance(edge, FeatureTreeEdge): return 
        if not edge.is_complete(): return 
        if edge in self._edge_to_cpls: return 
        
        # Get a list of variables that need to be instantiated.
        # If there are none, then return as-is.
        inst_vars = self.inst_vars(edge)
        if not inst_vars: return 
        
        # Instantiate the edge!
        self._instantiated.add(edge)
        edge._lhs = edge.lhs().substitute_bindings(inst_vars)
    
    def inst_vars(self, edge):
        return dict((var, logic.unique_variable())
                    for var in edge.lhs().variables()
                    if var.name.startswith('@'))

#////////////////////////////////////////////////////////////
# Deprecated parser loading
#////////////////////////////////////////////////////////////

@deprecated("Use nltk.load_parser() instead.")
def load_earley(filename, trace=0, cache=False, verbose=False,
                chart_class=FeatureChart, logic_parser=None, fstruct_parser=None):
    """
    Load a grammar from a file, and build an Earley feature parser based on
    that grammar.

    You can optionally specify a tracing level, for how much output you
    want to see:

    0: No output.
    1: Show edges from scanner and completer rules (not predictor).
    2 (default): Show all edges as they are added to the chart.
    3: Show all edges, plus the results of successful unifications.
    4: Show all edges, plus the results of all attempted unifications.
    5: Show all edges, plus the results of all attempted unifications,
    including those with cached results.

    If C{verbose} is set to C{True}, then more diagnostic information about
    grammar-loading is displayed.
    """
    grammar = nltk.data.load(filename, cache=cache, verbose=verbose, 
                             logic_parser=logic_parser, 
                             fstruct_parser=fstruct_parser)
    return FeatureChartParser(grammar, trace=trace, chart_class=chart_class)

#////////////////////////////////////////////////////////////
# Demo
#////////////////////////////////////////////////////////////

def demo_grammar():
    return nltk.grammar.parse_fcfg("""
S  -> NP VP
PP -> Prep NP
NP -> NP PP
VP -> VP PP
VP -> Verb NP
VP -> Verb
NP -> Det[pl=?x] Noun[pl=?x]
NP -> "John"
NP -> "I"
Det -> "the"
Det -> "my"
Det[-pl] -> "a"
Noun[-pl] -> "dog"
Noun[-pl] -> "cookie"
Verb -> "ate"
Verb -> "saw"
Prep -> "with"
Prep -> "under"
""")

def demo(should_print_times=True, should_print_grammar=True,
         should_print_trees=True, should_print_sentence=True,
         trace=1,
         parser=FeatureChartParser,
         sent='I saw John with a dog with my cookie'):
    import sys, time
    print
    grammar = demo_grammar()
    if should_print_grammar:
        print grammar
        print
    print "*", parser.__name__
    if should_print_sentence:
        print "Sentence:", sent
    tokens = sent.split()
    t = time.clock()
    cp = parser(grammar, trace=trace)
    chart = cp.chart_parse(tokens)
    trees = chart.parses(grammar.start())
    if should_print_times:
        print "Time: %s" % (time.clock() - t)
    if should_print_trees:
        for tree in trees: print tree
    else:
        print "Nr trees:", len(trees)

def run_profile():
    import profile
    profile.run('for i in range(1): demo()', '/tmp/profile.out')
    import pstats
    p = pstats.Stats('/tmp/profile.out')
    p.strip_dirs().sort_stats('time', 'cum').print_stats(60)
    p.strip_dirs().sort_stats('cum', 'time').print_stats(60)

if __name__ == '__main__':
    demo()
    print
    grammar = nltk.data.load('grammars/book_grammars/feat0.fcfg')
    cp = FeatureChartParser(grammar, trace=2)
    sent = 'Kim likes children'
    tokens = sent.split()
    trees = cp.nbest_parse(tokens)
    for tree in trees:
        print tree
