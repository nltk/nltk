# Natural Language Toolkit: A Chart Parser
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""

This is a version of chartparser that uses a single ChartRule interface,
which can be C{apply}ed to a chart...

The chartparser module defines the C{ChartParser} class, and two supporting
classes, C{Edge} and C{Chart}.

'chart rule' is really not a very good name..  What might be a better
name?  We could use 'strategy.'  Hmm..  Of course, right now, a
strategy is a collection of chart rules..  Which is nice, for talking
about, e.g., BU strategy.  Hrm..  


"""

from nltk.parser import *
from nltk.token import *
from nltk.tree import *
from nltk.set import *
from nltk.chart import *
from nltk.cfg import *

def edgecmp(e1,e2):
    return cmp((e1.loc().length(), e1.loc(), e1.drule()),
               (e2.loc().length(), e2.loc(), e2.drule()))

# this code should be replaced with a more transparent version
def _seq_loc(tok_sent):
    """
    Return the location that spans a given sequence of tokens.
    """
    return TreeToken('', *tok_sent).loc()

##//////////////////////////////////////////////////////
##  ChartRule
##//////////////////////////////////////////////////////

class ChartRuleI:
    def apply(self, chart, grammar):
        """
        Apply this rule to the given chart, with the given CFG grammar.
        """
        raise AssertionError, "abstract class"
    def __repr__(self):
        return '<%s>' % self.__class__.__name__
    def __str__(self):
        return '%s' % self.__class__.__name__

##//////////////////////////////////////////////////////
##  ChartParser
##//////////////////////////////////////////////////////

class ChartParser(ParserI):
    ##############################################
    # Initialization
    ##############################################
    def __init__(self, grammar, strategy, **kwargs):
        self._grammar = grammar
        self._strategy = strategy
        self._trace = kwargs.get('trace', 0)

    ##############################################
    # Accessor functions.
    ##############################################
    def grammar(self):
        """
        @return: The list of production rules in the
            C{ChartParser}'s grammar.
        @rtype: C{list} of C{Rule}
        """
        return self._grammar

    ##############################################
    # Parsing
    ##############################################

    def _create_chart(self, text):
        """
        @param text: The text to be parsed
        @rtype: C{Chart}
        """
        # Construct a new (empty) chart that spans the given
        # sentence.
        loc = Location(text[0].loc().start(), text[-1].loc().end(),
                       unit=text[0].loc().unit(),
                       source=text[0].loc().source())
        chart = Chart(loc)

        # Add an edge for each lexical item.
        if self._trace: print 'Adding lexical edges...'
        for tok in text:
            drule = DottedCFGProduction(tok.type(), ())
            probtok = ProbabilisticToken(1, tok.type(), tok.loc())
            new_edge = Edge(drule, probtok, tok.loc())
            if chart.insert(new_edge):
                if self._trace > 1:
                    print '%-20s %s' % ('Lexical', chart.pp_edge(edge))

        # Return the new chart
        return chart

    def parse_n(self, text, n=None):
        # Inherit documentation from ParserI

        # Create a new chart.
        chart = self._create_chart(text)

        # Run the rules until they generate no new edges.
        while 1:
            added = []
            for rule in self._strategy:
                for edge in rule.apply(chart, self._grammar):
                    if chart.insert(edge):
                        if self._trace > 1:
                            print '%-20s %s' % (rule, chart.pp_edge(edge))
                        added.append(edge)
            if not added:
                if self._trace:
                    parses = chart.parses(self._grammar.start())
                    print 'Found %d parses with %d edges' % (len(parses), 
                                                             len(chart))
                return chart.parses(self._grammar.start())

    def parse(self, text, n=None):
        # (broken for now)
        return self.parse_n(text, n)

##//////////////////////////////////////////////////////
##  Chart Rules
##//////////////////////////////////////////////////////
#
# See the docstring for ChartParser for a discussion of the
# different types of chart rules.

def self_loop_edge(grammar_rule, loc):
    """
    Return an edge formed from rule and loc.  Its dot is at the
    leftmost position, and it has no children.
    """
    drule = DottedCFGProduction(grammar_rule.lhs(), grammar_rule.rhs(), 0)
    treetok = TreeToken(drule.lhs().symbol())
    return Edge(drule, treetok, loc)

def fr_edge(edge1, edge2):
    """
    Return a fundamental-rule edge.
    """
    loc = edge1._loc.union(edge2.loc())
    dr = edge1._drule.shift()
    children = edge1._tree.children() + (edge2.tree(),)
    treetok = TreeToken(edge1._tree.node(), *children)
    return Edge(dr, treetok, loc)
    
class TopDownInitRule(ChartRuleI):
    def apply(self, chart, grammar):
        edges = []
        for grammar_rule in grammar.rules():
            if grammar_rule.lhs() == grammar.start():
                loc = chart.loc().start_loc()
                edges.append(self_loop_edge(grammar_rule, loc))

        return edges

    def old_apply(self, chart, grammar):
        "This is shorter, but maybe a little harder to read... "
        return [self_loop_edge(grammar_rule, chart.loc().start_loc())
                for grammar_rule in grammar.rules()
                if grammar_rule.lhs() == grammar.start()]

class TopDownRule(ChartRuleI):
    def apply(self, chart, grammar):
        edges = []
        for grammar_rule in grammar.rules():
            for edge in chart.incomplete_edges():
                if grammar_rule.lhs() == edge.drule().next():
                    loc = edge.loc().end_loc()
                    edges.append(self_loop_edge(grammar_rule, loc))
                                                
        return edges

    def _apply(self, chart, grammar):
        "This is shorter, but maybe a little harder to read... "
        return [self_loop_edge(grammar_rule, edge.loc().end_loc())
                for grammar_rule in grammar.rules()
                for edge in chart.incomplete_edges()
                if grammar_rule.lhs() == edge.drule().next()]

class BottomUpRule(ChartRuleI):
    def apply(self, chart, grammar):
        edges = []
        for grammar_rule in grammar.rules():
            for edge in chart.edges():
                if edge.drule().lhs() == grammar_rule.rhs()[0]:
                    loc = edge.loc().start_loc()
                    edges.append(self_loop_edge(grammar_rule, loc))
                                                
        return edges

class FundamentalRule(ChartRuleI):
    def apply(self, chart, grammar):
        edges = []
        for edge in chart.incomplete_edges():
            for edge2 in chart.complete_edges():
                if (edge.drule().next() == edge2.drule().lhs() and
                    edge.end() == edge2.start()):
                    edges.append(fr_edge(edge, edge2))
        return edges

##//////////////////////////////////////////////////////
##  Strategies
##//////////////////////////////////////////////////////

# Define some useful rule invocation strategies.
TD_STRATEGY = [TopDownInitRule(), TopDownRule(), FundamentalRule()]
BU_STRATEGY = [BottomUpRule(), FundamentalRule()]

##//////////////////////////////////////////////////////
##  SteppingChartParser
##//////////////////////////////////////////////////////

class SteppingChartParser(ChartParser):
    def __init__(self, grammar, strategy=None, **kwargs):
        if strategy is None: strategy = []
        ChartParser.__init__(self, grammar, strategy, **kwargs)

        self._chart = None
        self._edge_queue = []
        self._current_rule = None

    def initialize(self, text):
        """
        For now, just take a text.. eventually we want to be able to
        take a chart!
        """
        self._chart = self._create_chart(text)
        self._edge_queue = []
        self._current_rule = None

    def set_strategy(self, strategy):
        if strategy != self._strategy:
            self._strategy = strategy
            self._edge_queue = []

    def parses(self):
        return self._chart.parses(self._grammar.start())

    def chart(self):
        return self._chart

    def current_rule(self):
        return self._current_rule

    def step(self, **kwarg):
        if kwarg.has_key('strategy'): self.set_strategy(kwarg['strategy'])
        
        # Try moving an edge from the queue to the chart (note that
        # the edges on the queue might already be on the chart)
        while self._edge_queue:
            edge = self._edge_queue.pop()
            if self._chart.insert(edge):
                if self._trace:
                    print '%-20s %s' % (self._current_rule, chart.pp_edge(edge))
                return edge

        # If there are no new edges, try generating some.
        for rule in self._strategy:
            self._edge_queue += rule.apply(self._chart, self._grammar)
            self._current_rule = rule
            while self._edge_queue:
                edge = self._edge_queue.pop()
                if self._chart.insert(edge): 
                    if self._trace:
                        print '%-20s %s' % (self._current_rule,
                                            chart.pp_edge(edge))
                    return edge

        # We couldn't find anything to do.
        self._current_rule = None
        return None

    def parse_n(self, text, n=None):
        # Inherit documentation from ParserI

        self.initialize(text)
        while self.step(): pass
        parses = self.parses()
        if self._trace:
            print 'Found %d parses with %d edges' % (len(parses), 
                                                     len(self._chart))
        if n is None:
            return parses
        else:
            return parses[:n]

##//////////////////////////////////////////////////////
##  IncrementalChartParser
##//////////////////////////////////////////////////////

class IncrementalChartRuleI:
    def apply(self, chart, grammar, edge):
        """
        Apply this rule to the given chart, with the given CFG grammar.
        """
        raise AssertionError, "abstract class"
    def __repr__(self):
        return '<%s>' % self.__class__.__name__
    
class IncrementalChartParser:
    """
    Add one edge at a time..
    """
    def __init__(self, grammar, strategy, **kwargs):
        self._grammar = grammar
        self._strategy = strategy
        self._trace = kwargs.get('trace', 0)

    def grammar(self):
        """
        @return: The list of production rules in the
            C{ChartParser}'s grammar.
        @rtype: C{list} of C{Rule}
        """
        return self._grammar

    def _create_chart(self, text):
        """
        @param text: The text to be parsed
        @rtype: C{Chart}
        """
        # Construct a new (empty) chart that spans the given
        # sentence.
        loc = Location(text[0].loc().start(), text[-1].loc().end(),
                       unit=text[0].loc().unit(),
                       source=text[0].loc().source())
        return Chart(loc)

    def _create_edge_queue(self, text):
        edge_queue = []
        for tok in text:
            drule = DottedCFGProduction(tok.type(), ())
            edge_queue.append(Edge(drule, tok, tok.loc()))
        return edge_queue

    def parse_n(self, text, n=None):
        # Inherit documentation from ParserI

        # Create a new chart.
        chart = self._create_chart(text)
        edge_queue = self._create_edge_queue(text)
        parses = []

        # Note that we're adding edges to the end of the queue as we
        # process it.  But we'll eventually get to the end of the
        # queue, since we ignore any edges that are already in the
        # chart (so we can add each edge at most once).
        if self._trace: print 'Processing the edge queue...'
        parses = []
        while edge_queue:
            edge = edge_queue.pop()
            self._add_edge(edge, chart, edge_queue)
            
            # Check if the edge is a complete parse.
            if (edge.loc() == chart.loc() and
                edge.drule().lhs() == self._grammar.start()):
                parses.append(edge.tree())
                if len(parses) == n: break

        if self._trace:
            print 'Found %d parses with %d edges' % (len(parses), len(chart))

        # Sort the parses by decreasing likelihood, and return them
        return parses

    def _add_edge(self, edge, chart, edge_queue):
        # If the edge is already in the chart, then do nothing.
        if not chart.insert(edge): return
        if self._trace > 1: chart.pp_edge(edge)
        
        # Apply all rules.
        for rule in self._strategy:
            edge_queue += rule.apply(chart, self._grammar, edge)

    def parse(self, text, n=None):
        # (broken for now)
        return self.parse_n(text, n)

class IncrementalTopDownInitRule(ChartRuleI):
    def apply(self, chart, grammar, edge):
        if isinstance(edge.tree(), TreeToken): return []
        return [self_loop_edge(grammar_rule, chart.loc().start_loc())
                for grammar_rule in grammar.rules()
                if grammar_rule.lhs() == grammar.start()]

class IncrementalTopDownRule(ChartRuleI):
    def apply(self, chart, grammar, edge):
        if edge.complete(): return []
        return [self_loop_edge(grammar_rule, edge.loc().end_loc())
                for grammar_rule in grammar.rules()
                if grammar_rule.lhs() == edge.drule().next()]

class IncrementalBottomUpRule(IncrementalChartRuleI):
    def apply(self, chart, grammar, edge):
        return [self_loop_edge(grammar_rule, edge.loc().start_loc())
                for grammar_rule in grammar.rules()
                if edge.drule().lhs() == grammar_rule.rhs()[0]]

class IncrementalFundamentalRule(IncrementalChartRuleI):
    def apply(self, chart, grammar, edge):
        if edge.complete():
            return [fr_edge(edge2, edge)
                    for edge2 in chart.incomplete_edges()
                    if (edge2.drule().next() == edge.drule().lhs() and
                        edge2.end() == edge.start())]
        else:
            return [fr_edge(edge, edge2)
                    for edge2 in chart.complete_edges()
                    if (edge.drule().next() == edge2.drule().lhs() and
                        edge.end() == edge2.start())]

INCREMENTAL_BU_STRATEGY = [IncrementalBottomUpRule(),
                           IncrementalFundamentalRule()]
INCREMENTAL_TD_STRATEGY = [IncrementalTopDownRule(),
                           IncrementalTopDownInitRule(),
                           IncrementalFundamentalRule()]

##//////////////////////////////////////////////////////
##  Demonstration Code
##//////////////////////////////////////////////////////

def demo():
    nonterminals = 'S VP NP PP P N Name V Det'
    (S, VP, NP, PP, P, N, Name, V, Det) = [Nonterminal(s)
                                           for s in nonterminals.split()]
    
    grammar_rules1 = [
        CFGProduction(NP, 'John'), CFGProduction(NP, 'I'), 
        CFGProduction(Det, 'the'), CFGProduction(Det, 'my'),
        CFGProduction(Det, 'a'),
        CFGProduction(N, 'dog'),   CFGProduction(N, 'cookie'),
        CFGProduction(V, 'ate'),  CFGProduction(V, 'saw'),
        CFGProduction(P, 'with'), CFGProduction(P, 'under'),

        CFGProduction(S, NP, VP),  CFGProduction(PP, P, NP),
        CFGProduction(NP, Det, N), CFGProduction(NP, NP, PP),
        CFGProduction(VP, VP, PP), CFGProduction(VP, V, NP),
        CFGProduction(VP, V),
        ]

    grammar = CFG(S, grammar_rules1)

    sent = 'I saw John with a dog with my cookie'
    print "Sentence:\n", sent

    # tokenize the sentence
    tok_sent = WSTokenizer().tokenize(sent)

    # Which tests?
    BU = TD = STEP = INCR = 0
    INCR = TD = BU = 1

    tr = 1
    import time
    if INCR:
        t = time.time()
        cp = IncrementalChartParser(grammar, INCREMENTAL_BU_STRATEGY, trace=tr)
        for parse in cp.parse(tok_sent): pass #print parse
        print 'incremental bottom up', (time.time()-t), '\n'
        t = time.time()
        cp = IncrementalChartParser(grammar, INCREMENTAL_TD_STRATEGY, trace=tr)
        for parse in cp.parse(tok_sent): pass #print parse
        print 'incremental top down ', (time.time()-t), '\n'
    if BU:
        t = time.time()
        cp = ChartParser(grammar, BU_STRATEGY, trace=tr)
        for parse in cp.parse(tok_sent): pass #print parse
        print 'global bottom up     ', (time.time()-t), '\n'
    if TD:
        t = time.time()
        cp = ChartParser(grammar, TD_STRATEGY, trace=tr)
        for parse in cp.parse(tok_sent): pass #print parse
        print 'global top down      ', (time.time()-t), '\n'
    if STEP:
        cp = SteppingChartParser(grammar, trace=2)
        cp.initialize(tok_sent)
        for j in range(5):
            print 'TOP DOWN'
            cp.set_strategy(TD_STRATEGY)
            for i in range(20):
                if not cp.step(): break
            print 'BOTTOM UP'
            cp.set_strategy(BU_STRATEGY)
            for i in range(20):
                if not cp.step(): break
            print 'CHART SIZE:', len(cp.chart())
        for parse in cp.parses(): print parse
            


if __name__ == '__main__': demo()
