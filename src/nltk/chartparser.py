# Natural Language Toolkit: A Chart Parser
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
The chartparser module defines the C{ChartParser} class, and two supporting
classes, C{Edge} and C{Chart}.
"""

from parser import *
from token import *
from rule import *
from tree import *

def edgecmp(e1,e2):
    return cmp((e1.loc().length(), e1.loc(), e1.dr()),
               (e2.loc().length(), e2.loc(), e2.dr()))

class Edge:
    """
    An edge of a chart.    Edges are represented using C{Token}s, since
    an edge is just a piece of linguistic information at a
    C{Location}.    Edges also contain a C{DottedRule} and a
    possibly-empty tuple of children (C{Tree}s).    This class mainly
    provides a convenient wrapper around C{Token} with a suitable
    initializer and accessor functions.    Additionally, it provides
    functions to perform common chart-parser functions on edges.

    @type _edge: C{Token}
    @ivar _edge: The edge data structure, a C{Token} with a complex type
    """
    # [edloper 8/14/01] As far as I can tell, edges only ever have one
    # or zero children (either a Tree or nothing).    I would suggest that
    # an edge always has exactly one child.    When you would have zero
    # children (i.e., for the bottom up rule), you can have a Tree with
    # no children.    If/when we change to TreeTokens, it would also have
    # a zero-length location.
    
    def __init__(self, dr, children, loc):
        self._edge = Token((dr, children), loc)
    def dr(self):
        return self._edge.type()[0]
    def children(self):
        return self._edge.type()[1]
    def lhs(self):
        return self.dr().lhs()
    def next(self):
        return self.dr().next()
    def complete(self):
        return self.dr().complete()
    def loc(self):
        return self._edge.loc()
    def start(self):
        return self.loc().start()
    def end(self):
        return self.loc().end()
    def __repr__(self):
        return DottedRule.__repr__(self.dr()) + repr(self.children()) + Location.__repr__(self.loc())
    def __eq__(self, other):
        return (self._edge == other._edge)
    def __hash__(self):
        return hash((self.dr(), self.children(), self.loc()))

    def self_loop_start(self, rule):
        # change to use future methods Location.startLoc() ...
        loc = self.loc().start_loc()
        dr = rule.dotted()
        return Edge(dr, (), loc)

    def self_loop_end(self, rule):
        # change to use future methods Location.startLoc() ...
        loc = self.loc().end_loc()
        dr = rule.dotted()
        return Edge(dr, (), loc)

    def FR(self, edge):
        loc = self.loc().union(edge.loc())
        dr = self.dr().shift()
        children = self.children() + edge.children()
        if dr.complete():
            children = (Tree(dr.lhs(), *children),)
        return Edge(dr,children,loc)

class Chart:
    """
    A chart: a blackboard for hypotheses about syntactic constituents.

    @type _chart: C{Set} of C{Edge}s
    @ivar _chart: The set of C{Edge}s, keys of the hash array
    @type _loc: C{Location}
    @ivar _loc: The span of the chart, the C{Location} of a complete edge
    """
    def __init__(self, loc):
        self._chart = {}
        self._loc = loc
    def chart(self):
        return self._chart
    def loc(self):
        return self._loc
    def edges(self):
        return self._chart.keys()
    def size(self):
        return len(self.edges())
    def complete_edges(self):
        return [e for e in self.edges() if e.complete()]
    def incomplete_edges(self):
        return [e for e in self.edges() if not e.complete()]
    def copy(self):
        # make a copy of the chart
        chart = Chart(self.loc())
        for edge in self.edges():
            chart.add_edge(edge)
        return chart
    def add_edge(self,edge):
        if self._chart.has_key(edge):
            return []
        self._chart[edge] = 1
        return [edge]
    def parses(self, node):
        parses = []
        for edge in self.edges():
            if edge.loc() == self._loc and edge.lhs() == node:
                parses.append(edge.children()[0])
        return parses
            
    #draw (replace with tkinter version)
    def draw(self, width=7):
        print "="*75
        edges = self.edges()
        edges.sort(edgecmp)
        for edge in edges:
            start = edge.start()
            end = edge.end()
            indent = " " * width * start
            print indent, edge.dr()
            print indent + "|" + "-"*(width*(end-start)-1) + "|"

# get the location of a tokenized sentence (this is sick)
def _sentence_loc(tok_sent):
    return TreeToken('xyzzy', *tok_sent).loc()

#     - I think parsers should probably return TreeTokens, not Trees.
#       To get a Tree from a TreeToken, just use the .type() method
#       (TreeTokens are a subclass of Token).

# [edloper 8/14/01] Did you want to have methods for stepping through
# a parse?
class ChartParser(ParserI):
    """
    A generic chart parser.

    @type _grammar: C{Set} of C{Rule}s
    @ivar _grammar: The C{Rule}s of the grammar
    @type _basecat: C{string}
    @ivar _basecat: The top-level category of the grammar (e.g. 'S')
    @type _lexicon: C{Set} of C{Rule}s
    @ivar _lexicon: The C{Rule}s of the lexicon;
        lexical rules are assumed to have only one rhs element
    """
    def __init__(self, grammar, lexicon, basecat, **kwargs):
        self._grammar = grammar
        self._lexicon = lexicon
        self._basecat = basecat
        self._callback = self._trace = None
        if kwargs.has_key('callback'):
            self._callback = kwargs['callback']
        if kwargs.has_key('trace'):
            self._trace = kwargs['trace']
        self._functions = self._edgetrigger = ()
        self._chart = None

    def chart(self):
        return self._chart

    # set up the rule invocation strategy and the sentence to parse
    def load(self, strategy, tok_sent):
        (self._functions, self._edgetrigger) = strategy
        loc = _sentence_loc(tok_sent)
        self._chart = Chart(loc)

        added = []
        for word in tok_sent:
            for rule in self._lexicon:
                if word.type() == rule[0]:
                    dr = DottedRule(rule.lhs(), rule[:], 1)
                    tree = Tree(rule.lhs(), *rule[:])
                    edge = Edge(dr, (tree,), word.loc())
                    added += self.add_edge(edge)
        if self._trace:
            self._chart.draw()
        return added

    def load_test(self):
        if self._functions:
            return 1
        else:
            raise ValueError('Attempt to use chart parser before loading it')

    def add_edge(self, edge):
        added = self._chart.add_edge(edge)
        if added:
            if self._trace:
                print edge
            if self._callback:
                self._callback(self._chart, edge)
        for func in self._edgetrigger:
            added += func(edge)
        return added

    def TD_init(self):
        added = []
        loc = self._chart.loc().start_loc()
        for rule in self._grammar:
            if rule.lhs() == self._basecat:
                dr = rule.dotted()
                new_edge = Edge(dr, (), loc)
                added += self.add_edge(new_edge)
        if self._trace:
            self._chart.draw()
        return added

    def TD_edge(self, edge):
        added = []
        for rule in self._grammar:
            if not edge.complete() and rule.lhs() == edge.next():
                new_edge = edge.self_loop_end(rule)
                added += self.add_edge(new_edge)
        return added

    def BU_init_edge(self, edge):
        added = []
        for rule in self._grammar:
            if edge.lhs() == rule[0]:
                new_edge = edge.self_loop_start(rule)
                added += self.add_edge(new_edge)
        return added

    def BU_init(self):
        added = []
        found = 1 # gets us past the loop test
        while found:
            found = []
            for edge in self._chart.edges():
                found += self.BU_init_edge(edge)
            added += found
        if self._trace:
            self._chart.draw()
        return added

    def FR_edge(self, edge):
        added = []
        if not edge.complete():
            for edge2 in self._chart.complete_edges():
                if edge.next() == edge2.lhs() and edge.end() == edge2.start():
                    new_edge = edge.FR(edge2)
                    added += self.add_edge(new_edge)
        return added

    # fundamental rule
    def FR(self):
        added = []
        found = 1
        while found:
            found = []
            for edge in self._chart.edges():
                found += self.FR_edge(edge)
            added += found
        if self._trace:
            self._chart.draw()
        return added

    # rule-invocation strategies
    def td_strategy(self):
        return ((self.TD_init, self.FR), (self.TD_edge,))
    def bu_strategy(self):
        return ((self.BU_init, self.FR), ())

    def parses(self):
        return self._chart.parses(self._basecat)

    def parse(self, tok_sent):
        self.load_test()
        for func in self._functions:
            func()
        return self.parses()

class SteppingChartParser(ChartParser):
    def __init__(self, grammar, lexicon, basecat, **kwargs):
        ChartParser.__init__(self, grammar, lexicon, basecat, **kwargs)
        self._queue = []
        self._action = ()

    def clear(self):
        self._queue = []
    def empty(self):
        return self._queue == []
    def dequeue(self):
        if self._queue == []:
            return None
        front = self._queue[0]
        self._queue = self._queue[1:]
        return front
    def next(self):
        added = []
        while added == [] and not self.empty():
            next_edge = self.dequeue()
            added = self._chart.add_edge(next_edge)
        if added == []:
            return None
        else:
            return added[0]

    def FR_step(self, edge):
        if self._action != ("FR", edge) or self.empty():
            tmp_chart = self._chart.copy()
            self._queue = self.FR_edge(edge)
            self._chart = tmp_chart
        self._action = ("FR", edge)
        return self.next()

    def TD_step(self, edge):
        if self._action != ("TD", edge) or self.empty():
            tmp_chart = self._chart.copy()
            self._queue = self.TD_edge(edge)
            self._chart = tmp_chart
        self._action = ("TD", edge)
        return self.next()

    def TD_init_step(self):
        if self._action != "TDI" or self.empty():
            tmp_chart = self._chart.copy()
            self._queue = self.TD_init()
            self._chart = tmp_chart
        self._action = "TDI"
        return self.next()

    def BU_init_step(self, edge):
        if self._action != ("BUI", edge) or self.empty():
            tmp_chart = self._chart.copy()
            self._queue = self.BU_init_edge(edge)
            self._chart = tmp_chart
        self._action = ("BUI", edge)
        return self.next()

edgenum = 0
def xyzzy(chart, edge):
    global edgenum
    edgenum += 1
    print edgenum, edge
    return 0

# DEMONSTRATION CODE

grammar = (
    Rule('S',('NP','VP')),
    Rule('NP',('Det','N')),
    Rule('NP',('Det','N', 'PP')),
    Rule('VP',('V','NP')),
    Rule('VP',('V','PP')),
    Rule('VP',('V','NP', 'PP')),
    Rule('VP',('V','NP', 'PP', 'PP')),
    Rule('PP',('P','NP'))
)

lexicon = (
    Rule('NP',('I',)),
    Rule('Det',('the',)),
    Rule('Det',('a',)),
    Rule('N',('man',)),
    Rule('V',('saw',)),
    Rule('P',('in',)),
    Rule('P',('with',)),
    Rule('N',('park',)),
    Rule('N',('telescope',))
)

def demo2():
    global grammar, lexicon
    
    sent = 'I saw a man in the park with a telescope'
    print "Sentence:\n", sent

    # tokenize the sentence
    tok_sent = WSTokenizer().tokenize(sent)

    # initialize the chartparser
    cp = ChartParser(grammar, lexicon, 'S', callback=xyzzy, trace=0)
    cp.load(cp.bu_strategy(), tok_sent)

    # run the parser
    parses = cp.parse(tok_sent)

    print "Parse(s):"
    for parse in parses:
        print parse.pp()

def demo():
    global grammar, lexicon
    
    sent = 'I saw a man in the park with a telescope'
    print "Sentence:\n", sent

    # tokenize the sentence
    tok_sent = WSTokenizer().tokenize(sent)

    # initialize the chartparser
    cp = SteppingChartParser(grammar, lexicon, 'S')
    cp.load(cp.bu_strategy(), tok_sent)

    print "THE INITIAL CHART:"
    cp.chart().draw() # NB cp.chart() is ahead of us

    for x in range(2):
        next = cp.TD_init_step()
        print "TD_INIT:", next

    for e in range(3,8):
        edge = cp.chart().edges()[e]
        print "USER PICKED EDGE:", edge
        for x in range(1):
            next = cp.BU_init_step(edge)
            print "BU_INIT:", next

    edge = cp.chart().edges()[2]
    print "USER PICKED EDGE:", edge
    next = cp.FR_step(edge)
    print "FUNDAMENTAL:", next
    if next:
        next = cp.FR_step(next)
        print "FUNDAMENTAL:", next

    edge = cp.chart().edges()[11]
    print "USER PICKED EDGE:", edge
    next = cp.FR_step(edge)
    print "FUNDAMENTAL:", next
    if next:
        next = cp.FR_step(next)
        print "FUNDAMENTAL:", next

    edge = cp.chart().edges()[10]
    print "USER PICKED EDGE:", edge

    for x in range(4):
        next = cp.TD_step(edge)
        print "TD_STEP:", next

    edge = cp.chart().edges()[3]
    print "USER PICKED EDGE:", edge

    for x in range(4):
        next = cp.BU_init_step(edge)
        print "BU_INIT:", next

    cp.chart().draw()

    print "ALRIGHT, LET'S APPLY THE BU_INIT RULE MAXIMALLY"

    edges = cp.BU_init()

    print "ADDED:"
    print edges

    cp.chart().draw()

    edge = cp.chart().edges()[12]
    print "USER PICKED EDGE:", edge
    next = cp.FR_step(edge)
    print "FUNDAMENTAL:", next
    if next:
        next = cp.FR_step(next)
        print "FUNDAMENTAL:", next

    print "NOW LET'S APPLY THE FR MAXIMALLY"
    edges = cp.FR()

    print "ADDED:"
    print edges

    cp.chart().draw()

    print "Parse(s):"
    for parse in cp.parses():
        print parse.pp()
