from token import *
from rule import *
from tree2 import *

def edgesort(e1,e2):
  return cmp((e1.loc().length(), e1.loc(), e1.dr()),
             (e2.loc().length(), e2.loc(), e2.dr()))

class Edge:
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

class Chart:
  def __init__(self, loc):
    self._chart = {}
    self._loc = loc
  def chart(self):
    return self._chart
  def edgelist(self):
    return self._chart.keys()
  def add_edge(self,edge):
    if self._chart.has_key(edge):
      return 0
    self._chart[edge] = 1
    return 1
  def lex_edges(self,sentence,lexicon):
    for word in sentence:
      for rule in lexicon:
        if word.type() == rule[0]:
          dr = DottedRule(rule.lhs(), rule[:], 1)
          tree = Tree(rule.lhs(), *rule[:])
          self.add_edge(Edge(dr, (tree,), word.loc()))
  def bottom_up(self, grammar):
    added = 1
    while added > 0:
      added = 0
      for edge in self.edgelist():
        for rule in grammar:
          if edge.lhs() == rule[0]:
            loc = edge.loc()
            loc = Location(loc.start(), loc.start(), unit=loc.unit(), source=loc.source()) # cycle
            dr = DottedRule(rule.lhs(), rule[:]) # new rule with dot at left
            added += self.add_edge(Edge(dr, (), loc))

  # fundamental rule
  def fundamental(self):
    added = 1
    while added > 0:
      added = 0
      for edge1 in self.edgelist():
        if not edge1.final():
          for edge2 in self.edgelist():
            if edge2.final() and edge1.next() == edge2.lhs() and\
               edge1.end() == edge2.start():
              loc = edge1.loc().union(edge2.loc())
              dr = edge1.dr().copy()
              dr.incr()
              children = edge1.children() + edge2.children()
              if dr.final():
                children = (Tree(dr.lhs(), *children),)
              added += self.add_edge(Edge(dr,children,loc))
  def parses(self, node):
    parses = []
    for edge in self.edgelist():
      if edge.loc() == self._loc and edge.lhs() == node:
        parses.append(edge.children())
    return parses
      
  #draw
  def draw(self, width=10):
    print "="*75
    edgelist = self.edgelist()
    edgelist.sort(edgesort)
    for edge in edgelist:
      start = edge.start()
      end = edge.end()
      indent = " " * width * start
      print indent, edge.dr()
      print indent + "|" + "-"*(width*(end-start)-1) + "|"
