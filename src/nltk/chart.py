# Natural Language Toolkit: Chart Parsing Datatypes
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
Chart parsing data types.
"""

from nltk.parser import *
from nltk.token import *
from nltk.cfg import *
from nltk.tree import *
from nltk.set import *

def edgecmp(e1,e2):
    return cmp((e1.loc().length(), e1.loc(), e1.drule()),
               (e2.loc().length(), e2.loc(), e2.drule()))

##//////////////////////////////////////////////////////
##  Dotted Rules
##//////////////////////////////////////////////////////

class DottedCFG_Rule(CFG_Rule):
    """
    A dotted context-free grammar rule.

    This version will superceed DottedRule, eventually.

    The "dot" is a distinguished position at the boundary of any
    element on the right-hand side of the rule.

    @type _lhs: C{object}
    @ivar _lhs: The left-hand side of the rule, a non-terminal
    @type _rhs: C{tuple} of C{object}s
    @ivar _rhs: The right-hand side of the rule, a list of terminals
          and non-terminals.
    @type _pos: C{int}
    @ivar _pos: The position of the dot.
    """

    def __init__(self, lhs, rhs, pos=0):
        """
        Construct a new C{DottedCFG_Rule}.

        @param lhs: The left-hand side of the new C{CFG_Rule}.
        @type lhs: C{object}
        @param rhs: The right-hand side of the new C{CFG_Rule}.
        @type rhs: C{tuple} of C{objects}s
        @param pos: The position of the dot (defaults to zero).
        @type pos: C{int}
        """
        self._lhs = lhs
        self._rhs = rhs
        self._pos = pos

    def pos(self):
        """
        @return: the position of the dot in the C{DottedCFG_Rule}.
        @rtype: C{int}
        """
        return self._pos

    def next(self):
        """
        @return: the next element on the right-hand side following the dot.
        @rtype: C{object}
        """
        return self.rhs()[self._pos]

    def shift(self):
        """
        Shift the dot one position to the right (returns a new
        DottedCFG_Rule).
        
        @raise IndexError: If the dot position is beyond the end of
            the rule.
        """
        if self._pos < len(self.rhs()):
            return DottedCFG_Rule(self._lhs, self._rhs, self._pos + 1)
        else:
            raise IndexError('Attempt to move dot position past end of rule')

    def complete(self):
        """
        @return: true if the dot is in the final position on the
            right-hand side.
        @rtype: C{boolean}
        """
        return self._pos == len(self.rhs())

    def copy(self):
        """
        @return: a copy of the dotted rule
        @rtype: C{DottedCFG_Rule}
        """
        return DottedCFG_Rule(self._lhs, self._rhs, self._pos)

    def __repr__(self):
        """
        @return: A concise string representation of the C{DottedCFG_Rule}.
        @rtype: C{string}
        """
        return '[Rule: %s]' % self

    def __str__(self):
        """
        @return: A verbose string representation of the C{DottedCFG_Rule}.
        @rtype: C{string}
        """
        str = '%s ->' % self._lhs
        for elt in self._rhs[:self._pos]:
            if isinstance(elt, Nonterminal): str += ' %s' % elt.symbol()
            else: str += ' %r' % elt
        str += ' *'
        for elt in self._rhs[self._pos:]:
            if isinstance(elt, Nonterminal): str += ' %s' % elt.symbol()
            else: str += ' %r' % elt
        return str

    def __eq__(self, other):
        """
        @return: true if this C{DottedCFG_Rule} is equal to C{other}.
        @rtype: C{boolean}
        """
        return (CFG_Rule.__eq__(self, other) and
                self._pos == other._pos)

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        """
        @return: A hash value for the C{DottedCFG_Rule}.
        @rtype: C{int}
        """
        return hash((self._lhs, self._rhs, self._pos))

# !! document this.
class DottedPCFG_Rule(DottedCFG_Rule, ProbablisticMixIn):
    def __init__(self, p, lhs, rhs, pos=0):
        ProbablisticMixIn.__init__(self, p)
        DottedCFG_Rule.__init__(self, lhs, rhs, pos)

    def shift(self):
        # Shifting a DottedPCFG_Rule should return a DottedPCFG_Rule.
        if self._pos < len(self.rhs()):
            return DottedPCFG_Rule(self._p, self._lhs,
                                   self._rhs, self._pos + 1)
        else:
            raise IndexError('Attempt to move dot position past end of rule')

    def __str__(self):
        return DottedCFG_Rule.__str__(self)+' (p=%s)' % self._p
    def __repr__(self):
        return DottedCFG_Rule.__repr__(self)+' (p=%s)' % self._p

##//////////////////////////////////////////////////////
##  Edge
##//////////////////////////////////////////////////////

class Edge:
    """
    An edge of a chart.  An edge is a span of tokens (i.e. a
    C{Location}) with an associated C{DottedCFG_Rule} and a C{Tree}.
    The Edge class provides basic functions plus a some common
    chart-parser functions on edges.

    @type _drule: C{DottedCFG_Rule}
    @ivar _drule: The dotted rule of the edge.
    @type _tree: C{TreeToken}
    @ivar _tree: The current parse tree of the edge.
    @type _loc: C{Location}
    @ivar _loc: The span of tokens covered by the edge.
    """
    
    def __init__(self, drule, tree, loc):
        """
        Construct a new C{Edge}.

        @param drule: The dotted rule associated with the edge.
        @type drule: C{DottedCFG_Rule}
        @param tree: The (partial) parse tree so far constructed for the edge.
        @type tree: C{TreeToken}
        @param loc: The location spanned by the edge.
        @type loc: C{Location}
        """
        self._drule = drule
        self._tree = tree
        self._loc = loc

    def drule(self):
        """
        @return: the dotted rule of the edge.
        @rtype: C{DottedCFG_Rule}
        """
        return self._drule

    def tree(self):
        """
        @return: the parse tree of the edge.
        @rtype: C{TreeToken}
        """
        return self._tree
    
    # a complete edge is one whose dotted rule is complete
    def complete(self):
        """
        @return: true if the C{DottedCFG_Rule} of this edge is complete
        @rtype: C{boolean}
        """
        return self._drule.complete()

    def loc(self):
        """
        @return: the location spanned by this edge
        @rtype: C{Location}
        """
        return self._loc

    # the start/end of an edge is the start/end of the edge's location
    def start(self):
        """
        @return: the start index of the edge's location
        @rtype: C{Location}
        """
        return self._loc.start()

    def end(self):
        """
        @return: the end index of the edge's location
        @rtype: C{Location}
        """
        return self._loc.end()

    def __repr__(self):
        """
        @return: A concise string representation of the C{Edge}
        @rtype: C{string}
        """
        return '[Edge: %s]%s' % (self._drule, self._loc)

    def __str__(self):
        return '[Edge: %s]%r' % (self._drule, self._loc)

    def __eq__(self, other):
        """
        @return: true if this C{Edge} is equal to C{other}.
        @rtype: C{boolean}
        """
        return (self._drule == other._drule and
                self._tree == other._tree and
                self._loc == other._loc)

    def __hash__(self):
        """
        @return: A hash value for the C{Edge}.
        @rtype: C{int}
        """
        return hash((self._drule, self._tree, self._loc))

    def self_loop_start(self, rule):
        """
        B{this will be removed}
        
        @param rule: A grammar rule
        @type rule: C{Rule}
        @return: a zero-width self-loop edge at the start of this edge,
            with a dotted rule initialized from this rule
        @rtype: C{Edge}
        """
        loc = self.loc().start_loc()
        dr = rule.drule()
        return Edge(dr, TreeToken(dr.lhs()), loc)

    def self_loop_end(self, rule):
        """
        B{this will be removed}
        
        @param rule: A grammar rule
        @type rule: C{Rule}
        @return: a zero-width self-loop edge at the end of this edge,
            with a dotted rule initialized from this rule
        @rtype: C{Edge}
        """
        loc = self._loc.end_loc()
        dr = rule.drule()
        return Edge(dr, TreeToken(dr.lhs()), loc)

    def FR(self, edge):
        """
        B{this will be removed}
        
        @param edge: a completed edge immediately to the right
        @type edge: C{Edge}
        @return: a new edge resulting from the application of the
            fundamental rule of chart parsing
        @rtype: C{Edge}
        """
        loc = self._loc.union(edge.loc())
        dr = self._drule.shift()
        tree = TreeToken(self._tree.node(),
                         *(self._tree.children() + (edge.tree(),)))
        return Edge(dr, tree, loc)

##//////////////////////////////////////////////////////
##  Chart
##//////////////////////////////////////////////////////

class Chart:
    """
    A blackboard for hypotheses about syntactic constituents.

    @type _chart: C{Set} of C{Edge}s
    @ivar _chart: The set of C{Edge}s, keys of the hash array
    @type _loc: C{Location}
    @ivar _loc: The span of the chart, the C{Location} of a complete edge
    """
    def __init__(self, loc):
        """
        Construct a new Chart.
        
        @param loc: The span of text that it covered by this chart.  All
            edge indices in the chart will fall within this location.
        @type loc: C{Location}
        """
        self._edgeset = Set()
        self._loc = loc
        
    def loc(self):
        """
        @return: A location specifying the span of text covered by
            this chart.
        @rtype: C{Location}
        """
        return self._loc
    
    def edgeset(self):
        """
        @return: The set of edges contained in this chart.
        @rtype: C{Set} of C{Edge}
        """
        return self._edgeset
    
    def edges(self):
        """
        @return: A list of the edges contained in this chart.
        @rtype: C{sequence} of C{Edge}
        """
        return self._edgeset.elements()
    
    def __len__(self):
        """
        @return: The number of edges contained in this chart.
        @rtype: C{int}
        """
        return len(self._edgeset)

    def complete_edges(self):
        """
        @return: A list of all complete edges contained in this chart.
            A complete edge is an edge whose dotted rule has its dot
            in the final position.
        @rtype: C{sequence} of C{Edge}
        """
        return [e for e in self.edges() if e.complete()]
    
    def incomplete_edges(self):
        """
        @return: A list of all incomplete edges contained in this chart.
            An incomplete edge is an edge whose dotted rule has its dot
            in a nonfinal position.
        @rtype: C{sequence} of C{Edge}
        """
        return [e for e in self.edges() if not e.complete()]

    # [edloper 9/27/01] There is a copy module, which provides both
    # shallow & deep copying..  But I'm not sure that we need this
    # copy method anyway.  It wreaks havoc with my ChartView class,
    # cuz it doesn't like having to switch to a new chart. :)
    def copy(self):
        """
        @return: A deep copy of this chart.
        @rtype: C{Chart}
        """
        chart = Chart(self.loc())
        chart._edgeset = self._edgeset.copy()
        return chart
    
    def insert(self, edge):
        """
        Attempt to insert a new edge into this chart.  If the edge is
        already present, return []; otherwise, return a list
        containing the inserted edge.
        """
        if self._edgeset.insert(edge):
            return [edge]
        else:
            return []
        
    def parses(self, node):
        """
        Return the set of complete parses encoded by this chart, whose
        root node value is C{node}.  Use self._loc to test if the edge
        spans the entire chart.
        """
        return [edge.tree() for edge in self.edges() if
                edge.loc() == self._loc and edge.drule().lhs() == node]

    def contains(self, edge):
        """
        @return: true iff this C{Chart} contains the specified edge.
        @rtype: C{boolean}
        """
        return edge in self._edgeset
        
    def __contains__(self, edge):
        """
        @return: true iff this C{Chart} contains the specified edge.
        @rtype: C{boolean}
        """
        return edge in self._edgeset
            
    #draw (NB, there is also a tkinter version nltk.draw.chart)
    def old_draw(self, width=7):
        print "="*75
        edges = self.edges()
        edges.sort(edgecmp)
        for edge in edges:
            start = edge.start()
            end = edge.end()
            indent = " " * width * start
            print indent, edge.drule()
            print indent + "|" + "-"*(width*(end-start)-1) + "|"

    def draw(self, text=None, **kwargs):
        import nltk.draw.chart
        nltk.draw.chart.ChartView(self, text, **kwargs)

    def pp_edge(self, edge, width=3):
        """
        Return a pretty-printed representation of a given edge on this
        chart.
        """
        (chart_start, chart_end) = (self._loc.start(), self._loc.end())
        (start, end) = (edge.start(), edge.end())

        str = '|' + ('.'+' '*(width-1))*(start-chart_start)

        # Zero-width edges are "#" if complete, ">" if incomplete
        if start == end:
            if edge.complete(): str += '#'
            else: str += '>'

        # Spanning complete edges are "[===]"; Other edges are
        # "[---]" if complete, "[--->" if incomplete
        elif edge.complete() and edge.loc() == self._loc:
            str += '['+('='*width)*(end-start-1) + '='*(width-1)+']'
        elif edge.complete():
            str += '['+('-'*width)*(end-start-1) + '-'*(width-1)+']'
        else:
            str += '['+('-'*width)*(end-start-1) + '-'*(width-1)+'>'
        
        str += (' '*(width-1)+'.')*(chart_end-end)
        return str + '| %s ' % edge.drule()
        
    def pp(self, text=None, width=3):
        (chart_start, chart_end) = (self._loc.start(), self._loc.end())
        str = ''

        # Draw a header.  Header line shows what words correspond to
        # each position.
        if text:
            str += '| '
            pos = chart_start
            for tok in text:
                str += (tok.loc().start() - pos) * '   '
                len = 3*(tok.loc().end() - tok.loc().start())
                type = ('%s' % tok.type())[:len-1]
                str += ('%-'+`len`+'s') % type
                pos = tok.loc().end()
            str += '   '*(chart_end - text[-1].loc().end()) + '|\n'

        # Draw each edge on a separate line.
        edges = self.edges()
        edges.sort(edgecmp)
        for edge in edges:
            str += self.pp_edge(edge, width) + '\n'
        return str

class FRChart(Chart):
    """
    A specialized chart that can efficiently find the set of edges
    that could combine with a given edge by the fundamental rule.  The
    fundamental rule can combine two edges C{M{e1}} and C{M{e2}} if
    C{M{e1}.end()==M{e2}.start()} and
    C{M{e1}.drule().next()==M{e2}.drule().lhs()}.

    C{FRChart} indexes the set of complete edges in the chart by their
    start location and their dotted rule's left hand side; and indexes
    the set of incomplete edges in the chart by their end location and
    the element of their dotted rule's right hand side following its
    dot.  To access edges using these indices, use the optional
    arguments for C{complete_edges} and C{incomplete_edges}.

    @ivar _complete: A dictionary containing all complete edges,
        indexed by their start position & lhs nonterminal
    @type _complete: C{list} of C{Edge}
    @ivar _incomplete: A dictionary containing all incomplete edges,
        indexed by their end position & 1st rhs elt after the dot.
    @type _incomplete: C{list} of C{Edge}
    """
    def __init__(self, loc):
        # Inherit docs.
        Chart.__init__(self, loc)
        self._complete = {}
        self._incomplete = {}

    def insert(self, edge):
        # Inherit docs.
        return_value = Chart.insert(self, edge)
        if return_value:
            if edge.complete():
                key = (edge.start(), edge.drule().lhs())
                self._complete.setdefault(key, []).append(edge)
            else:
                key = (edge.end(), edge.drule().next())
                self._incomplete.setdefault(key, []).append(edge)
        return return_value

    def complete_edges(self, start=None, lhs=None):
        """
        @return: A list of complete edges contained in this chart.
            A complete edge is an edge whose dotted rule has its dot
            in the final position.  If C{start} and C{lhs} are 
            specified, then return all edges that begin at C{start}
            and whose dotted rules have a left hand side C{lhs}.
            Otherwise, return all complete edges contained in this
            chart. 
        @rtype: C{sequence} of C{Edge}
        """
        if start is None or lhs is None:
            return Chart.complete_edges(self)
        return self._complete.get((start, lhs), [])

    def incomplete_edges(self, end=None, next=None):
        """
        @return: A list of all incomplete edges contained in this chart.
            An incomplete edge is an edge whose dotted rule has its dot
            in a nonfinal position.  If C{end} and C{next} are 
            specified, then return all edges that end at C{end}
            and that have dotted rules whose first element after the
            dot is C{next}.  Otherwise, return all complete edges
            contained in this chart.
        @rtype: C{sequence} of C{Edge}
        """
        if start is None or lhs is None:
            return Chart.complete_edges(self)
        return self._incomplete.get((end, next), [])

    def fr_with(self, edge):
        """
        @return: a list of the edges that can be combined with C{edge}
            by the fundamental rule.  If C{edge} is a complete edge,
            then this is a list of incomplete edges that could be
            expanded with C{edge}.  If C{edge} is an incomplete edge,
            then this is a list of complete edges that can be used to
            expand C{edge}.
        @rtype: C{list} of C{Edge}

        @param edge: An edge (not necessarily in this chart), for which
            to find the set of edges in this chart that could be
            combined with the fundamental rule.
        @type edge: C{Edge}
        """
        drule = edge.drule()
        if edge.complete():
            return self._incomplete.get((edge.start(), drule.lhs()),[])
        else:
            return self._complete.get((edge.end(), drule.next()),[])
