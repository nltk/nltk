# -*- coding: utf-8 -*-
# Natural Language Toolkit: Chart Parser for Feature-Based Grammars
#
# Copyright (C) 2001-2009 NLTK Project
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

from nltk.featstruct import FeatStruct, unify, FeatStructParser, TYPE
from nltk.sem import logic
from nltk.grammar import Nonterminal, Production, ContextFreeGrammar
from nltk.compat import defaultdict
from nltk.grammar import FeatStructNonterminal
import nltk.data

from api import *
from chart import *

def load_earley(filename, trace=0, cache=False, verbose=False,
                chart_class=Chart, logic_parser=None, fstruct_parser=None):
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
                isinstance(right_edge, TreeEdge) and
                left_edge.next()[TYPE] == right_edge.lhs()[TYPE]):
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
            # Be sure not to predict lexical edges. 
            # (The ScannerRule takes care of those.)
            if len(prod.rhs()) == 1 and isinstance(prod.rhs()[0], str): continue
            # Note: we rename vars here, because we don't want variables
            # from the two different productions to match.
            if ((prod.lhs()[TYPE] == edge.next()[TYPE]) and 
                unify(prod.lhs(), edge.next_with_bindings(), rename_vars=True)):
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
        for pos in [prod.lhs() for prod in gramar.productions(rhs=leaf)]:
            if (pos[TYPE] == edge.next()[TYPE] and 
                unify(pos, edge.next_with_bindings(), rename_vars=True)):
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

## Simple Earley Chart Parser, without features
## (defined here because the feature version needs to build on it, but
## chart.py has a simpler way to use the Earley algorithm)

class EarleyChartParser(ParserI):
    """
    A chart parser implementing the Earley parsing algorithm:

        - For each index I{end} in [0, 1, ..., N]:
          - For each I{edge} s.t. I{edge}.end = I{end}:
            - If I{edge} is incomplete, and I{edge}.next is not a part
              of speech:
                - Apply PredictorRule to I{edge}
            - If I{edge} is incomplete, and I{edge}.next is a part of
              speech:
                - Apply ScannerRule to I{edge}
            - If I{edge} is complete:
                - Apply CompleterRule to I{edge}
        - Return any complete parses in the chart

    @ivar _predictor_class, _completer_class, _scanner_class: The
    classes that are used to implement the three rules used by the
    Earley algorithm,  Replacement rules can be specified by
    subclasses (such as L{FeatureEarleyChartParser
    <nltk.parse.featurechar.FeatureEarleyChartParser>}).
    """
    _predictor_class = PredictorRule
    _completer_class = CompleterRule
    _scanner_class = ScannerRule

    def __init__(self, grammar, trace=0, chart_class=Chart):
        """
        Create a new Earley chart parser, that uses C{grammar} to
        parse texts.
        
        @type grammar: C{ContextFreeGrammar}
        @param grammar: The grammar used to parse texts.
        @type trace: C{int}
        @param trace: The level of tracing that should be used when
            parsing a text.  C{0} will generate no tracing output;
            and higher numbers will produce more verbose tracing
            output.
        @param chart_class: The class that should be used to create
            the charts used by this parser.
        """
        if isinstance(trace, dict):
            raise ValueError("Earley parser no longer takes a lexicon "
                             "as a separate parameter; the lexicon "
                             "is calculated from the grammar instead.")
        self._grammar = grammar
        self._trace = trace
        self._chart_class = chart_class

    def grammar(self):
        return self._grammar

    #: The default total width reserved for the chart in trace output.
    #: The remainder of each line will be used to display edges.
    _trace_chart_width = 40

    def nbest_parse(self, tokens, n=None, tree_class=Tree, trace=None):
        if trace is not None: self._trace = trace
        tokens = list(tokens)
        self._grammar.check_coverage(tokens)
        
        chart = self._chart_class(tokens)
        grammar = self._grammar

        # Width, for printing trace edges.
        w = max(2, self._trace_chart_width/(chart.num_leaves()+1))
        if self._trace > 1: print ' '*9, chart.pp_leaves(w)

        # Initialize the chart with a special "starter" edge.
        chart.insert(self._starter_edge(grammar.start()), ())

        # Create the 3 rules:
        predictor = self._predictor_class()
        completer = self._completer_class()
        scanner = self._scanner_class()

        for end in range(chart.num_leaves()+1):
            if self._trace > 2: print 'Processing queue %d' % end
            if self._trace == 1:
                sys.stdout.write('.'); sys.stdout.flush()
            for edge in chart.select(end=end):
                if edge.is_complete():
                    for e in completer.apply_iter(chart, grammar, edge):
                        if self._trace > 1:
                            print 'Completer', chart.pp_edge(e,w)
                if edge.is_incomplete():
                    for e in predictor.apply_iter(chart, grammar, edge):
                        if self._trace > 2:
                            print 'Predictor', chart.pp_edge(e,w)
                if edge.is_incomplete():
                    for e in scanner.apply_iter(chart, grammar, edge):
                        if self._trace > 1:
                            print 'Scanner  ', chart.pp_edge(e,w)

        # Output a list of complete parses.
        if self._trace == 1: print
        return self._parses(chart, grammar.start(), tree_class)[:n]

    # This is a separate method because FeatureEarleyChartParser needs
    # to replace it:
    def _starter_edge(self, start_sym):
        """Return a 'starter edge' that expands to the start symbol."""
        root = Nonterminal('[INIT]')
        return TreeEdge((0,0), root, (start_sym,))

    # This is a separate method because FeatureEarleyChartParser needs
    # to replace it:
    def _parses(self, chart, start_sym, tree_class):
        """Return a list of parses in the given chart."""
        return chart.parses(start_sym, tree_class=tree_class)

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
            if ( (not isinstance(edge, LeafEdge)) and
                 (edge.lhs()[TYPE] == start[TYPE]) and
                 (unify(edge.lhs(), start, rename_vars=True)) ):
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
    replaced by unique new L{Variable}s.
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
    
    def inst_vars(self, edge):
        return dict((var, logic.unique_variable())
                    for var in edge.lhs().variables()
                    if var.name.startswith('@'))

#////////////////////////////////////////////////////////////
# Demo
#////////////////////////////////////////////////////////////

# TODO: update to use grammar parser
def demo(should_print_times=True, trace=1):
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

    productions = [
        # Define some grammatical productions.
        Production(S, (NP, VP)),  Production(PP, (P, NP)),
        Production(NP, (NP, PP)),
        Production(VP, (VP, PP)), Production(VP, (V, NP)),
        Production(VP, (V,)),     Production(NP, (DetPl, NPl)),
        Production(NP, (DetSg, NSg)),
        # Define some lexical productions.
        Production(NP, ('John',)), Production(NP, ('I',)),
        Production(Det, ('the',)), Production(Det, ('my',)),
        Production(Det, ('a',)),
        Production(NSg, ('dog',)), Production(NSg, ('cookie',)),
        Production(V, ('ate',)),   Production(V, ('saw',)),
        Production(P, ('with',)),  Production(P, ('under',)),
    ]

    earley_grammar = ContextFreeGrammar(S, productions)
    print earley_grammar
    print

    sent = 'I saw John with a dog with my cookie'
    print "Sentence:", 
    print sent
    print
    tokens = sent.split()
    t = time.time()
    cp = FeatureEarleyChartParser(earley_grammar, trace=trace)
    trees = cp.nbest_parse(tokens)
    print
    if should_print_times:
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
    cp = load_earley('grammars/book_grammars/feat0.fcfg', trace=2)
    sent = 'Kim likes children'
    tokens = sent.split()
    trees = cp.nbest_parse(tokens)
    for tree in trees:
        print tree
