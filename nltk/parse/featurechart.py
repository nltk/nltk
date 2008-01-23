# Natural Language Toolkit: Chart Parser for Feature-Based Grammars
#
# Copyright (C) 2001-2008 University of Pennsylvania
# Author: Rob Speer <rspeer@mit.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
Extension of chart parsing implementation to handle grammars with
feature structures as nodes.
"""

import yaml
from api import *
from chart import *
from nltk.featstruct import FeatStruct, unify, FeatStructParser
from nltk.sem.logic import SubstituteBindingsI, unique_variable
from nltk import cfg, defaultdict
from nltk.cfg import FeatStructNonterminal
from nltk.internals import Counter
import nltk.data

def load_earley(filename, trace=0, cache=False, verbose=False,
                chart_class=Chart):
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
    grammar = nltk.data.load(filename, cache=cache, verbose=verbose)
    return FeatureEarleyChartParser(grammar, trace=trace,
                                    chart_class=chart_class)

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

    def __str__(self):
        if self.is_complete():
            return TreeEdge.__str__(self)
        else:
            bindings = '{%s}' % ', '.join('%s: %r' % item for item in
                                           sorted(self._bindings.items()))
            return '%s %s' % (TreeEdge.__str__(self), bindings)

    # two edges w/ different bindings are not equal.
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
        - [AS{->}S{alpha}*B1S{beta}][i:j]
        - [B2S{->}S{gamma}*][j:k]
    licenses the edge:
        - [AS{->}S{alpha}B3*S{beta}][i:j]
    assuming that B1 and B2 can be unified to generate B3.
    """
    def apply_iter(self, chart, grammar, left_edge, right_edge):
        # Make sure the rule is applicable.
        if not (left_edge.end() == right_edge.start() and
                left_edge.is_incomplete() and
                right_edge.is_complete() and
                isinstance(left_edge, TreeEdge) and
                isinstance(right_edge, TreeEdge)):
            return

        # Unify B1 (left_edge.next) with B2 (right_edge.lhs) to
        # generate B3 (result).
        bindings = left_edge.bindings() # creates a copy.
        result = unify(left_edge.next(), right_edge.lhs(),
                       bindings, rename_vars=False)
        if result is None: return

        # Construct the new edge.
        new_edge = FeatureTreeEdge(span=(left_edge.start(), right_edge.end()),
                                   lhs=left_edge.lhs(), rhs=left_edge.rhs(),
                                   dot=left_edge.dot()+1, bindings=bindings)
        
        # Add it to the chart, with appropriate child pointers.
        changed_chart = False
        for cpl1 in chart.child_pointer_lists(left_edge):
            if chart.insert(new_edge, cpl1+(right_edge,)):
                changed_chart = True

        # If we changed the chart, then generate the edge.
        if changed_chart: yield new_edge

class FeatureTopDownExpandRule(TopDownExpandRule):
    """
    A specialized version of the top down expand rule that operates on
    nonterminals whose symbols are C{FeatStructNonterminal}s.  Rather
    tha simply comparing the nonterminals for equality, they are
    unified.

    The top down expand rule states that:
        - [AS{->}S{alpha}*B1S{beta}][i:j]
    licenses the edge:
        - [B2S{->}*S{gamma}][j:j]
    for each grammar production C{B2S{->}S{gamma}}, assuming that B1
    and B2 can be unified.
    """
    def apply_iter(self, chart, grammar, edge):
        if edge.is_complete(): return
        for prod in grammar.productions():
            # Note: we rename vars here, because we don't want variables
            # from the two different productions to match.
            if unify(prod.lhs(), edge.next_with_bindings(), rename_vars=True):
                new_edge = FeatureTreeEdge(span=(edge.end(), edge.end()),
                                           lhs=prod.lhs(),
                                           rhs=prod.rhs(), dot=0)
                if chart.insert(new_edge, ()):
                    yield new_edge

#////////////////////////////////////////////////////////////
# Earley Parsing Rules
#////////////////////////////////////////////////////////////

class FeatureCompleterRule(CompleterRule):
    """
    A specialized version of the completer rule that operates on
    nonterminals whose symbols are C{FeatStructNonterminal}s.  Rather
    tha simply comparing the nonterminals for equality, they are
    unified.  See L{CompleterRule} for more information.
    """
    _fundamental_rule = FeatureFundamentalRule()
    
    def apply_iter(self, chart, grammar, edge1):
        fr = self._fundamental_rule
        for edge2 in chart.select(end=edge1.start(), is_complete=False):
            for new_edge in fr.apply_iter(chart, grammar, edge2, edge1):
                yield new_edge

class FeatureScannerRule(ScannerRule):
    def apply_iter(self, chart, gramar, edge):
        if edge.is_complete() or edge.end()>=chart.num_leaves(): return
        index = edge.end()
        leaf = chart.leaf(index)
        for pos in self._word_to_pos.get(leaf, []):
            if unify(pos, edge.next_with_bindings(), rename_vars=True):
                new_leaf_edge = LeafEdge(leaf, index)
                if chart.insert(new_leaf_edge, ()):
                    yield new_leaf_edge
                new_pos_edge = FeatureTreeEdge((index, index+1), pos,
                                               [leaf], 1)
                if chart.insert(new_pos_edge, (new_leaf_edge,)):
                    yield new_pos_edge

# This is just another name for TopDownExpandRule:
class FeaturePredictorRule(FeatureTopDownExpandRule): pass
    
#////////////////////////////////////////////////////////////
# Earley Parser
#////////////////////////////////////////////////////////////

class FeatureEarleyChartParser(EarleyChartParser):
    """
    A chart parser implementing the Earley parsing algorithm, allowing
    nonterminals that have features (known as L{FeatStructNonterminal}s).
    See L{EarleyChartParser} for more details.
    """
    _predictor_class = FeaturePredictorRule
    _completer_class = FeatureCompleterRule
    _scanner_class = FeatureScannerRule
    _trace_chart_width = 10 # Edges are big, so compress the chart.

    def _starter_edge(self, start):
        root = FeatStructNonterminal('[*type*="[INIT]"]')
        return FeatureTreeEdge((0,0), root, (start,), 0)
        
    def _parses(self, chart, start, tree_class):
        # Output a list of complete parses.
        trees = []
        for edge in chart.select(span=(0, chart.num_leaves())):
            if unify(edge.lhs(), start, rename_vars=True):
                trees += chart.trees(edge, complete=True,
                                     tree_class=tree_class)
        return trees

#////////////////////////////////////////////////////////////
# Instantiate Variable Chart
#////////////////////////////////////////////////////////////

class InstantiateVarsChart(Chart):
    """
    A specialized chart that 'instantiates' variables whose names
    start with '@', by replacing them with unique new variables.
    In particular, whenever a complete edge is added to the chart, any
    variables in the edge's C{lhs} whose names start with '@' will be
    replaced by unique new L{IndVariable}s.
    """
    def __init__(self, tokens):
        Chart.__init__(self, tokens)
        self._instantiated = set()
        
    def insert(self, edge, child_pointer_list):
        if edge in self._instantiated: return False
        edge = self.instantiate_edge(edge)
        return Chart.insert(self, edge, child_pointer_list)
    
    def instantiate_edge(self, edge):
        # If the edge is a leaf, or is not complete, or is
        # already in the chart, then just return it as-is.
        if not isinstance(edge, FeatureTreeEdge): return edge
        if not edge.is_complete(): return edge
        if edge in self._edge_to_cpls: return edge
        
        # Get a list of variables that need to be instantiated.
        # If there are none, then return the edge as-is.
        inst_vars = self.inst_vars(edge)
        if not inst_vars: return edge
        
        # Instantiate the edge!
        self._instantiated.add(edge)
        lhs = edge.lhs().substitute_bindings(inst_vars)
        return FeatureTreeEdge(edge.span(), lhs, edge.rhs(),
                               edge.dot(), edge.bindings())
    
    counter = Counter(100)
    def inst_vars(self, edge):
        return dict((var, unique_variable(self.counter).variable)
                    for var in edge.lhs().variables()
                    if var.name.startswith('@'))

#////////////////////////////////////////////////////////////
# Demo
#////////////////////////////////////////////////////////////

# TODO: update to use grammar parser
def demo():
    import sys, time

    S = FeatStructNonterminal('S')
    VP = FeatStructNonterminal('VP')
    NP = FeatStructNonterminal('NP')
    PP = FeatStructNonterminal('PP')
    V = FeatStructNonterminal('V')
    N = FeatStructNonterminal('N')
    P = FeatStructNonterminal('P')
    Name = FeatStructNonterminal('Name')
    Det = FeatStructNonterminal('Det')
    DetSg = FeatStructNonterminal('Det[-pl]')
    DetPl = FeatStructNonterminal('Det[+pl]')
    NSg = FeatStructNonterminal('N[-pl]')
    NPl = FeatStructNonterminal('N[+pl]')

    # Define some grammatical productions.
    grammatical_productions = [
        cfg.Production(S, (NP, VP)),  cfg.Production(PP, (P, NP)),
        cfg.Production(NP, (NP, PP)),
        cfg.Production(VP, (VP, PP)), cfg.Production(VP, (V, NP)),
        cfg.Production(VP, (V,)), cfg.Production(NP, (DetPl, NPl)),
        cfg.Production(NP, (DetSg, NSg))]

    # Define some lexical productions.
    lexical_productions = [
        cfg.Production(NP, ('John',)), cfg.Production(NP, ('I',)),
        cfg.Production(Det, ('the',)), cfg.Production(Det, ('my',)),
        cfg.Production(Det, ('a',)),
        cfg.Production(NSg, ('dog',)),   cfg.Production(NSg, ('cookie',)),
        cfg.Production(V, ('ate',)),  cfg.Production(V, ('saw',)),
        cfg.Production(P, ('with',)), cfg.Production(P, ('under',)),
    ]


    earley_lexicon = defaultdict(list)
    for prod in lexical_productions:
        earley_lexicon[prod.rhs()[0]].append(prod.lhs())
    #print "Lexicon:"
    #print earley_lexicon
    earley_grammar = cfg.Grammar(S, grammatical_productions, earley_lexicon)
    print earley_grammar
    
    sent = 'I saw John with a dog with my cookie'
    print "Sentence:\n", sent
    tokens = sent.split()
    t = time.time()
    cp = FeatureEarleyChartParser(earley_grammar, trace=1)
    trees = cp.nbest_parse(tokens)
    print "Time: %s" % (time.time() - t)
    for tree in trees: print tree

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
    cp = load_earley('grammars/feat0.fcfg', trace=2)
    sent = 'Kim likes children'
    tokens = sent.split()
    trees = cp.nbest_parse(tokens)
    print trees

