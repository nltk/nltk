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
from set import *

def edgecmp(e1,e2):
    return cmp((e1.loc().length(), e1.loc(), e1.dotted_rule()),
               (e2.loc().length(), e2.loc(), e2.dotted_rule()))

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
    
    def __init__(self, dotted_rule, children, loc):
        self._edge = Token((dotted_rule, children), loc)
    def dotted_rule(self):
        return self._edge.type()[0]
    def children(self):
        return self._edge.type()[1]
    def lhs(self):
        return self.dotted_rule().lhs()
    def next(self):
        return self.dotted_rule().next()
    def complete(self):
        return self.dotted_rule().complete()
    def loc(self):
        return self._edge.loc()
    def start(self):
        return self.loc().start()
    def end(self):
        return self.loc().end()
    def __repr__(self):
        return DottedRule.__repr__(self.dotted_rule())\
               + repr(self.children()) + Location.__repr__(self.loc())
    def __eq__(self, other):
        return (self._edge == other._edge)
    def __hash__(self):
        return hash((self.dotted_rule(), self.children(), self.loc()))

    def self_loop_start(self, rule):
        loc = self.loc().start_loc()
        dotted_rule = rule.dotted()
        return Edge(dotted_rule, (), loc)

    def self_loop_end(self, rule):
        loc = self.loc().end_loc()
        dotted_rule = rule.dotted()
        return Edge(dotted_rule, (), loc)

    def FR(self, edge):
        loc = self.loc().union(edge.loc())
        dotted_rule = self.dotted_rule().shift()
        children = self.children() + edge.children()
        if dotted_rule.complete():
            children = (TreeToken(dotted_rule.lhs(), *children),)
        return Edge(dotted_rule,children,loc)

class Chart:
    """
    A chart: a blackboard for hypotheses about syntactic constituents.

    @type _chart: C{Set} of C{Edge}s
    @ivar _chart: The set of C{Edge}s, keys of the hash array
    @type _loc: C{Location}
    @ivar _loc: The span of the chart, the C{Location} of a complete edge
    """
    def __init__(self, loc):
        self._edgeset = Set()
        self._loc = loc
    def loc(self):
        return self._loc
    def edgeset(self):
        return self._edgeset
    def edges(self):
        return self._edgeset.elements()
    def size(self):
        return len(self._edgeset)
    def complete_edges(self):
        return [e for e in self.edges() if e.complete()]
    def incomplete_edges(self):
        return [e for e in self.edges() if not e.complete()]
    def copy(self):
        chart = Chart(self.loc())
        chart._edgeset = self._edgeset.copy()
        return chart
    def insert(self,edge):
        if self._edgeset.insert(edge):
            return [edge]
        else:
            return []
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
            print indent, edge.dotted_rule()
            print indent + "|" + "-"*(width*(end-start)-1) + "|"

# get the location of a tokenized sequence
def _seq_loc(tok_sent):
    return TreeToken('xyzzy', *tok_sent).loc()

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

    def grammar(self):
        return self._grammar
    def lexicon(self):
        return self._lexicon
    def basecat(self):
        return self._basecat
    def callback(self):
        return self._callback
    def trace(self):
        return self._trace
    def functions(self):
        return self._functions
    def edgetrigger(self):
        return self._edgetrigger
    def chart(self):
        return self._chart

    # set up the rule invocation strategy and the sentence to parse
    def load(self, strategy, tok_sent):
        (self._functions, self._edgetrigger) = strategy
        loc = _seq_loc(tok_sent)
        self._chart = Chart(loc)

        added = []
        for word in tok_sent:
            for rule in self._lexicon:
                if word.type() == rule[0]:
                    dotted_rule = DottedRule(rule.lhs(), rule[:], 1)
                    tree = TreeToken(rule.lhs(), word)
                    edge = Edge(dotted_rule, (tree,), word.loc())
                    added += self.insert(edge)
        if self._trace:
            self._chart.draw()
        return added

    def load_test(self):
        if self._functions:
            return 1
        else:
            raise ValueError('Attempt to use chart parser before loading it')

    def insert(self, edge):
        added = self._chart.insert(edge)
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
                dotted_rule = rule.dotted()
                new_edge = Edge(dotted_rule, (), loc)
                added += self.insert(new_edge)
        if self._trace:
            self._chart.draw()
        return added

    def TD_edge(self, edge):
        added = []
        for rule in self._grammar:
            if not edge.complete() and rule.lhs() == edge.next():
                new_edge = edge.self_loop_end(rule)
                added += self.insert(new_edge)
        return added

    def BU_init_edge(self, edge):
        added = []
        for rule in self._grammar:
            if edge.lhs() == rule[0]:
                new_edge = edge.self_loop_start(rule)
                added += self.insert(new_edge)
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
                    added += self.insert(new_edge)
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
            added = self._chart.insert(next_edge)
        if added == []:
            return None
        else:
            return added[0]

    def _step(self, edge, function, action):
        if self._action != action or self.empty():
            tmp_chart = self._chart.copy()
            if edge:
                self._queue = function(edge)
            else:
                self._queue = function()
            self._chart = tmp_chart
        self._action = action
        return self.next()

    def FR_step(self, edge):
        return self._step(edge, self.FR_edge, (edge, self.FR_edge))

    def TD_step(self, edge):
        return self._step(edge, self.TD_edge, (edge, self.TD_edge))

    def BU_init_step(self, edge):
        return self._step(edge, self.BU_init_edge, (edge, self.BU_init_edge))

    def TD_init_step(self):
        return self._step(None, self.TD_init, self.TD_init)

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
