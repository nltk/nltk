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

# Edward: please add members of Location to do this
def start_loc(l):
    return Location(l.start(), l.start(), unit=l.unit(), source=l.source())
def end_loc(l):
    return Location(l.end(), l.end(), unit=l.unit(), source=l.source())


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
        loc = start_loc(self.loc())
        dr = rule.dotted()
        return Edge(dr, (), loc)

    def self_loop_end(self, rule):
        # change to use future methods Location.startLoc() ...
        loc = end_loc(self.loc())
        dr = rule.dotted()
        return Edge(dr, (), loc)

    def fundamental(self, edge):
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
    def final_edges(self):
        return [e for e in self.edges() if e.complete()]
    def nonfinal_edges(self):
        return [e for e in self.edges() if not e.complete()]
    def add_edge(self,edge):
        if self._chart.has_key(edge):
            return 0
        self._chart[edge] = 1
        return 1
    def parses(self, node):
        parses = []
        for edge in self.edges():
            if edge.loc() == self._loc and edge.lhs() == node:
                parses.append(edge.children()[0])
        return parses
            
    #draw (replace with tkinter version)
    def draw(self, width=8):
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
    def __init__(self, **kwargs):
        self._grammar = kwargs['grammar']
        self._lexicon = kwargs['lexicon']
        self._basecat = kwargs['basecat']
        self._trace = None
        if kwargs.has_key('trace'):
            self._trace = kwargs['trace']

    def load_sentence(self, tok_sent):
        loc = _sentence_loc(tok_sent)
        chart = Chart(loc)

        for word in tok_sent:
            for rule in self._lexicon:
                if word.type() == rule[0]:
                    dr = DottedRule(rule.lhs(), rule[:], 1)
                    tree = Tree(rule.lhs(), *rule[:])
                    edge = Edge(dr, (tree,), word.loc())
                    chart.add_edge(edge)
        if self._trace:
            chart.draw()
        return chart

    def top_down_init(self, chart):
        loc = start_loc(chart.loc())
        for rule in self._grammar:
            if rule.lhs() == self._basecat:
                dr = rule.dotted()
                new_edge = Edge(dr, (), loc)
                chart.add_edge(new_edge)
        if self._trace:
            chart.draw()
        return chart

    def top_down_step(self, chart, edge):
        for rule in self._grammar:
            if not edge.complete() and rule.lhs() == edge.next():
                new_edge = edge.self_loop_end(rule)
                chart.add_edge(new_edge)
        return chart

    def bottom_up(self, chart):
        added = 1
        while added > 0:
            added = 0
            for edge in chart.edges():
                for rule in self._grammar:
                    if edge.lhs() == rule[0]:
                        new_edge = edge.self_loop_start(rule)
                        added += chart.add_edge(new_edge)
        if self._trace:
            chart.draw()
        return chart

    # fundamental rule
    def fundamental(self, chart):
        added = 1
        while added > 0:
            added = 0
            for edge1 in chart.nonfinal_edges():
                for edge2 in chart.final_edges():
                    if edge1.next() == edge2.lhs() and edge1.end() == edge2.start():
                        new_edge = edge1.fundamental(edge2)
                        added += chart.add_edge(new_edge)
                        chart = self.top_down_step(chart, new_edge)
        if self._trace:
            chart.draw()
        return chart

    def parse(self, tok_sent):
        chart = self.load_sentence(tok_sent)
#        chart = self.bottom_up(chart)
        chart = self.top_down_init(chart)
        chart = self.fundamental(chart)
        return chart.parses(self._basecat)

def demo():
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

    sent = 'I saw a man in the park with a telescope'
    print "Sentence:\n", sent

    cp = ChartParser(grammar=grammar, lexicon=lexicon, basecat='S', trace=1)
    tok_sent = WSTokenizer().tokenize(sent)
    parses = cp.parse(tok_sent)

    print "Parse(s):"
    for parse in parses:
        print parse.pp()
