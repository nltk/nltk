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
from tree2 import *

def edgesort(e1,e2):
  return cmp((e1.loc().length(), e1.loc(), e1.dr()),
             (e2.loc().length(), e2.loc(), e2.dr()))

class Edge:
  """
  An edge of a chart.  Edges are represented using C{Token}s, since
  an edge is just a piece of linguistic information at a
  C{Location}.  Edges also contain a C{DottedRule} and a
  possibly-empty tuple of children (C{Tree}s).  This class mainly
  provides a convenient wrapper around C{Token} with a suitable
  initializer and accessor functions.  Additionally, it provides
  functions to perform common chart-parser functions on edges.

  @type _edge: C{Token}
  @ivar _edge: The edge data structure, a C{Token} with a complex type
  """

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
  def final(self):
    return self.dr().final()
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

  def bottom_up(self, rule):
    loc = self.loc()
    loc = Location(loc.start(), loc.start(), unit=loc.unit(), source=loc.source())
    dr = rule.dotted()
    return Edge(dr, (), loc)

  def fundamental(self, edge):
    loc = self.loc().union(edge.loc())
    dr = self.dr().copy()
    dr.incr()
    children = self.children() + edge.children()
    if dr.final():
      children = (Tree(dr.lhs(), *children),)
    return Edge(dr,children,loc)

class Chart:
  """
  A chart: a blackboard for hypotheses about syntactic constituents.

  @type _chart: C{dict}
  @ivar _chart: The set of C{Edge}s, keys of the hash array
  @type _loc: C{Location}
  @ivar _loc: The span of the chart, the C{Location} of a complete edge
  """

  def __init__(self, loc):
    self._chart = {}
    self._loc = loc
  def chart(self):
    return self._chart
  def edges(self):
    return self._chart.keys()
  def final_edges(self):
    edges = []
    for edge in self.edges():
      if edge.final():
        edges.append(edge)
    return edges
  def nonfinal_edges(self):
    edges = []
    for edge in self.edges():
      if not edge.final():
        edges.append(edge)
    return edges
  def add_edge(self,edge):
    if self._chart.has_key(edge):
      return 0
    self._chart[edge] = 1
    return 1
  def parses(self, node):
    parses = []
    for edge in self.edges():
      if edge.loc() == self._loc and edge.lhs() == node:
        parses.append(edge.children())
    return parses
      
  #draw
  def draw(self, width=10):
    print "="*75
    edges = self.edges()
    edges.sort(edgesort)
    for edge in edges:
      start = edge.start()
      end = edge.end()
      indent = " " * width * start
      print indent, edge.dr()
      print indent + "|" + "-"*(width*(end-start)-1) + "|"

# get the location of a tokenized sentence (this is sick)
def _sentence_loc(tok_sent):
  start = tok_sent[0].loc().start()
  end = tok_sent[-1].loc().end()
  unit = tok_sent[0].loc().unit()
  source = tok_sent[0].loc().source()
  loc = Location(start, end, unit=unit, source=source)
  return loc

class ChartParser(ParserI):
  """
  A generic chart parser.

  @type _grammar: C{tuple}
  @ivar _grammar: A tuple of C{Rule}s containing the grammar
  @type _basecat: C{string}
  @ivar _basecat: The top-level category of the grammar (e.g. 'S')
  @type _lexicon: C{tuple}
  @ivar _lexicon: A tuple of C{Rule}s containing the lexicon;
    lexical rules are assumed to have only one rhs element
  """

  def __init__(self, grammar, basecat, lexicon):
    self._grammar = grammar
    self._basecat = basecat
    self._lexicon = lexicon

  def load_sentence(self, tok_sent):
    loc = _sentence_loc(tok_sent)
    chart = Chart(loc)

    for word in tok_sent:
      for rule in self._lexicon:
        if word.type() == rule[0]:
          dr = DottedRule(rule.lhs(), rule[:], 1)
          tree = Tree(rule.lhs(), *rule[:])
          chart.add_edge(Edge(dr, (tree,), word.loc()))
    return chart

  def bottom_up(self, chart):
    added = 1
    while added > 0:
      added = 0
      for edge in chart.edges():
        for rule in self._grammar:
          if edge.lhs() == rule[0]:
            new_edge = edge.bottom_up(rule)
            added += chart.add_edge(new_edge)
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
    return chart

  def parse(self, tok_sent):
    chart = self.load_sentence(tok_sent)
    chart = self.bottom_up(chart)
    chart = self.fundamental(chart)
    return chart.parses(self._basecat)

def demo():
  grammar = (
    Rule('S',('NP','VP')),
    Rule('NP',('Det','N')),
    Rule('VP',('V','PP')),
    Rule('PP',('P','NP'))
  )

  lexicon = (
    Rule('Det',('the',)),
    Rule('N',('cat',)),
    Rule('V',('sat',)),
    Rule('P',('on',)),
    Rule('N',('mat',))
  )

  sent = 'the cat sat on the mat'
  print "Sentence:\n", sent

  cp = ChartParser(grammar, 'S', lexicon)
  tok_sent = WSTokenizer().tokenize(sent)
  parses = cp.parse(tok_sent)

  print "Parse(s):"
  for parse in parses:
    print parse
