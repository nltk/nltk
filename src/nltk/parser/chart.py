# Natural Language Toolkit: A Chart Parser
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""



"""

from nltk.parser import ParserI
from nltk.token import Token, Location
from nltk.tree import TreeToken
from nltk.set import Set
from nltk.cfg import CFG, CFGProduction, Nonterminal

def edgecmp(e1,e2):
    return cmp((e1.loc().length(), e1.loc(), e1.dprod()),
               (e2.loc().length(), e2.loc(), e2.dprod()))

# this code should be replaced with a more transparent version
def _seq_loc(tok_sent):
    """
    Return the location that spans a given sequence of tokens.
    """
    return TreeToken('', *tok_sent).loc()

##//////////////////////////////////////////////////////
##  Dotted Productions
##//////////////////////////////////////////////////////

class DottedCFGProduction(CFGProduction):
    """
    A dotted context-free grammar production.

    The "dot" is a distinguished position at the boundary of any
    element on the right-hand side of the production.

    @type _lhs: C{object}
    @ivar _lhs: The left-hand side of the production, a non-terminal
    @type _rhs: C{tuple} of C{object}s
    @ivar _rhs: The right-hand side of the production, a list of terminals
          and non-terminals.
    @type _pos: C{int}
    @ivar _pos: The position of the dot.
    """

    def __init__(self, lhs, rhs, pos=0):
        """
        Construct a new C{DottedCFGProduction}.

        @param lhs: The left-hand side of the new C{CFGProduction}.
        @type lhs: C{object}
        @param rhs: The right-hand side of the new C{CFGProduction}.
        @type rhs: C{tuple} of C{objects}s
        @param pos: The position of the dot (defaults to zero).
        @type pos: C{int}
        """
        self._lhs = lhs
        self._rhs = rhs
        self._pos = pos

    def pos(self):
        """
        @return: the position of the dot in the C{DottedCFGProduction}.
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
        DottedCFGProduction).
        
        @raise IndexError: If the dot position is beyond the end of
            the projection's right hand side.
        """
        if self._pos < len(self.rhs()):
            return DottedCFGProduction(self._lhs, self._rhs, self._pos + 1)
        else:
            raise IndexError('Attempt to move dot position past end of production')

    def complete(self):
        """
        @return: true if the dot is in the final position on the
            right-hand side.
        @rtype: C{boolean}
        """
        return self._pos == len(self.rhs())

    def copy(self):
        """
        @return: a copy of the dotted production
        @rtype: C{DottedCFGProduction}
        """
        return DottedCFGProduction(self._lhs, self._rhs, self._pos)

    def __repr__(self):
        """
        @return: A concise string representation of the C{DottedCFGProduction}.
        @rtype: C{string}
        """
        return '[Production: %s]' % self

    def __str__(self):
        """
        @return: A verbose string representation of the C{DottedCFGProduction}.
        @rtype: C{string}
        """
        if isinstance(self._lhs, Nonterminal): str = '%s ->' % self._lhs
        else: str = '%r ->' % self._lhs
            
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
        @return: true if this C{DottedCFGProduction} is equal to C{other}.
        @rtype: C{boolean}
        """
        return (CFGProduction.__eq__(self, other) and
                self._pos == other._pos)

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        """
        @return: A hash value for the C{DottedCFGProduction}.
        @rtype: C{int}
        """
        return hash((self._lhs, self._rhs, self._pos))

##//////////////////////////////////////////////////////
##  Edge
##//////////////////////////////////////////////////////

class Edge:
    """
    An edge of a chart.  An edge is a span of tokens (i.e. a
    C{Location}) with an associated C{DottedCFGProduction} and a C{Tree}.
    The Edge class provides basic functions plus a some common
    chart-parser functions on edges.

    @type _dprod: C{DottedCFGProduction}
    @ivar _dprod: The dotted production of the edge.
    @type _tree: C{TreeToken}
    @ivar _tree: The current parse tree of the edge.
    @type _loc: C{Location}
    @ivar _loc: The span of tokens covered by the edge.
    """
    
    def __init__(self, dprod, tree, loc):
        """
        Construct a new C{Edge}.

        @param dprod: The dotted production associated with the edge.
        @type dprod: C{DottedCFGProduction}
        @param tree: The (partial) parse tree so far constructed for the edge.
        @type tree: C{TreeToken}
        @param loc: The location spanned by the edge.
        @type loc: C{Location}
        """
        self._dprod = dprod
        self._tree = tree
        self._loc = loc

    def dprod(self):
        """
        @return: the dotted production of the edge.
        @rtype: C{DottedCFGProduction}
        """
        return self._dprod

    def tree(self):
        """
        @return: the parse tree of the edge.
        @rtype: C{TreeToken}
        """
        return self._tree
    
    # a complete edge is one whose dotted production is complete
    def complete(self):
        """
        @return: true if the C{DottedCFGProduction} of this edge is complete
        @rtype: C{boolean}
        """
        return self._dprod.complete()

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
        return '[Edge: %s]%s' % (self._dprod, self._loc)

    def __str__(self):
        return '[Edge: %s]%r' % (self._dprod, self._loc)

    def __eq__(self, other):
        """
        @return: true if this C{Edge} is equal to C{other}.
        @rtype: C{boolean}
        """
        return (self._dprod == other._dprod and
                self._tree == other._tree and
                self._loc == other._loc)

    def __hash__(self):
        """
        @return: A hash value for the C{Edge}.
        @rtype: C{int}
        """
        return hash((self._dprod, self._tree, self._loc))

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
            A complete edge is an edge whose dotted production has its dot
            in the final position.
        @rtype: C{sequence} of C{Edge}
        """
        return [e for e in self.edges() if e.complete()]
    
    def incomplete_edges(self):
        """
        @return: A list of all incomplete edges contained in this chart.
            An incomplete edge is an edge whose dotted production has its dot
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
                edge.loc() == self._loc and edge.dprod().lhs() == node]

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
            print indent, edge.dprod()
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
        return str + '| %s ' % edge.dprod()
        
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
    C{M{e1}.dprod().next()==M{e2}.dprod().lhs()}.

    C{FRChart} indexes the set of complete edges in the chart by their
    start location and their dotted production's left hand side; and indexes
    the set of incomplete edges in the chart by their end location and
    the element of their dotted production's right hand side following its
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
                key = (edge.start(), edge.dprod().lhs())
                self._complete.setdefault(key, []).append(edge)
            else:
                key = (edge.end(), edge.dprod().next())
                self._incomplete.setdefault(key, []).append(edge)
        return return_value

    def complete_edges(self, start=None, lhs=None):
        """
        @return: A list of complete edges contained in this chart.
            A complete edge is an edge whose dotted production has its dot
            in the final position.  If C{start} and C{lhs} are 
            specified, then return all edges that begin at C{start}
            and whose dotted productions have a left hand side C{lhs}.
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
            An incomplete edge is an edge whose dotted production has its dot
            in a nonfinal position.  If C{end} and C{next} are 
            specified, then return all edges that end at C{end}
            and that have dotted productions whose first element after the
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
        dprod = edge.dprod()
        if edge.complete():
            return self._incomplete.get((edge.start(), dprod.lhs()),[])
        else:
            return self._complete.get((edge.end(), dprod.next()),[])

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
        return '<%s>' % str(self)
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
        @return: The grammar used by the parser.
        @rtype: C{CFG}
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
        #if self._trace: print 'Adding lexical edges...'
        for tok in text:
            dprod = DottedCFGProduction(tok.type(), ())
            new_edge = Edge(dprod, tok, tok.loc())
            if chart.insert(new_edge):
                if self._trace > 1:
                    print '%-20s %s' % ('Lexical Insertion',
                                        chart.pp_edge(new_edge))

        # Return the new chart
        return chart

    def parse_n(self, text, n=None):
        # Inherit documentation from ParserI

        # Create a new chart.
        chart = self._create_chart(text)

        # Run the chart rules until they generate no new edges.
        while 1:
            added = []
            for chartrule in self._strategy:
                for edge in chartrule.apply(chart, self._grammar):
                    if chart.insert(edge):
                        if self._trace > 1:
                            print '%-20s %s' % (chartrule, chart.pp_edge(edge))
                        added.append(edge)
            if not added:
                if self._trace:
                    parses = chart.parses(self._grammar.start())
                    print 'Found %d parses with %d edges' % (len(parses), 
                                                             len(chart))
                return chart.parses(self._grammar.start())

    def parse(self, text, n=None):
        # Inherit docs from ProbabilisticParserI; and delegate to parse_n
        final_trees = self.parse_n(text, 1)
        if len(final_trees) == 0: return None
        else: return final_trees[0]

##//////////////////////////////////////////////////////
##  Chart Rules
##//////////////////////////////////////////////////////
#
# See the docstring for ChartParser for a discussion of the
# different types of chart rules.

def self_loop_edge(production, loc):
    """
    Return an edge formed from production and loc.  Its dot is at the
    leftmost position, and it has no children.
    """
    dprod = DottedCFGProduction(production.lhs(), production.rhs(), 0)
    treetok = TreeToken(dprod.lhs().symbol())
    return Edge(dprod, treetok, loc)

def fr_edge(edge1, edge2):
    """
    Return a fundamental-rule edge.
    """
    loc = edge1._loc.union(edge2.loc())
    dr = edge1._dprod.shift()
    children = edge1._tree.children() + (edge2.tree(),)
    treetok = TreeToken(edge1._tree.node(), *children)
    return Edge(dr, treetok, loc)
    
class TopDownInitRule(ChartRuleI):
    def apply(self, chart, grammar):
        edges = []
        for production in grammar.productions():
            if production.lhs() == grammar.start():
                loc = chart.loc().start_loc()
                edges.append(self_loop_edge(production, loc))
        return edges
    def __str__(self): return 'Top Down Init Rule'
    
class TopDownRule(ChartRuleI):
    def apply(self, chart, grammar):
        edges = []
        for production in grammar.productions():
            for edge in chart.incomplete_edges():
                if production.lhs() == edge.dprod().next():
                    loc = edge.loc().end_loc()
                    edges.append(self_loop_edge(production, loc))
        return edges
    def __str__(self): return 'Top Down Rule'

class BottomUpRule(ChartRuleI):
    def apply(self, chart, grammar):
        edges = []
        for production in grammar.productions():
            for edge in chart.edges():
                if edge.dprod().lhs() == production.rhs()[0]:
                    loc = edge.loc().start_loc()
                    edges.append(self_loop_edge(production, loc))
        return edges
    def __str__(self): return 'Bottom Up Rule'

class FundamentalRule(ChartRuleI):
    def apply(self, chart, grammar):
        edges = []
        for edge in chart.incomplete_edges():
            for edge2 in chart.complete_edges():
                if (edge.dprod().next() == edge2.dprod().lhs() and
                    edge.end() == edge2.start()):
                    edges.append(fr_edge(edge, edge2))
        return edges
    def __str__(self): return 'Fundamental Rule'

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
        self._current_chartrule = None

    def initialize(self, text):
        """
        For now, just take a text.. eventually we want to be able to
        take a chart!
        """
        self._chart = self._create_chart(text)
        self._edge_queue = []
        self._current_chartrule = None

    def set_strategy(self, strategy):
        if strategy != self._strategy:
            self._strategy = strategy
            self._edge_queue = []

    def parses(self):
        return self._chart.parses(self._grammar.start())

    def chart(self):
        return self._chart

    def current_chartrule(self):
        return self._current_chartrule

    def step(self, **kwarg):
        if kwarg.has_key('strategy'): self.set_strategy(kwarg['strategy'])
        
        # Try moving an edge from the queue to the chart (note that
        # the edges on the queue might already be on the chart)
        while self._edge_queue:
            edge = self._edge_queue.pop()
            if self._chart.insert(edge):
                if self._trace:
                    print '%-20s %s' % (self._current_chartrule,
                                        self._chart.pp_edge(edge))
                return edge

        # If there are no new edges, try generating some.
        for chartrule in self._strategy:
            self._edge_queue += chartrule.apply(self._chart, self._grammar)
            self._current_chartrule = chartrule
            while self._edge_queue:
                edge = self._edge_queue.pop()
                if self._chart.insert(edge): 
                    if self._trace:
                        print '%-20s %s' % (self._current_chartrule,
                                            self._chart.pp_edge(edge))
                    return edge

        # We couldn't find anything to do.
        self._current_chartrule = None
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
        @return: The grammar used by the parser.
        @rtype: C{CFG}
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
            dprod = DottedCFGProduction(tok.type(), ())
            edge_queue.append(Edge(dprod, tok, tok.loc()))

        # Start with the first word (top of stack = last elt)
        edge_queue.reverse()
        
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
                edge.dprod().lhs() == self._grammar.start()):
                parses.append(edge.tree())
                if len(parses) == n: break

        if self._trace:
            print 'Found %d parses with %d edges' % (len(parses), len(chart))

        # Sort the parses by decreasing likelihood, and return them
        return parses

    def _add_edge(self, edge, chart, edge_queue):
        # If the edge is already in the chart, then do nothing.
        if not chart.insert(edge): return
        if self._trace > 1: print chart.pp_edge(edge)
        
        # Apply all chart rules.
        for chartrule in self._strategy:
            edge_queue += chartrule.apply(chart, self._grammar, edge)

    def parse(self, text, n=None):
        # Inherit docs from ProbabilisticParserI; and delegate to parse_n
        final_trees = self.parse_n(text, 1)
        if len(final_trees) == 0: return None
        else: return final_trees[0]

class IncrementalTopDownInitRule(ChartRuleI):
    def apply(self, chart, grammar, edge):
        if isinstance(edge.tree(), TreeToken): return []
        return [self_loop_edge(production, chart.loc().start_loc())
                for production in grammar.productions()
                if production.lhs() == grammar.start()]

class IncrementalTopDownRule(ChartRuleI):
    def apply(self, chart, grammar, edge):
        if edge.complete(): return []
        return [self_loop_edge(production, edge.loc().end_loc())
                for production in grammar.productions()
                if production.lhs() == edge.dprod().next()]

class IncrementalBottomUpRule(IncrementalChartRuleI):
    def apply(self, chart, grammar, edge):
        return [self_loop_edge(production, edge.loc().start_loc())
                for production in grammar.productions()
                if edge.dprod().lhs() == production.rhs()[0]]

class IncrementalFundamentalRule(IncrementalChartRuleI):
    def apply(self, chart, grammar, edge):
        if edge.complete():
            return [fr_edge(edge2, edge)
                    for edge2 in chart.incomplete_edges()
                    if (edge2.dprod().next() == edge.dprod().lhs() and
                        edge2.end() == edge.start())]
        else:
            return [fr_edge(edge, edge2)
                    for edge2 in chart.complete_edges()
                    if (edge.dprod().next() == edge2.dprod().lhs() and
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
    
    productions = [
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

    grammar = CFG(S, productions)

    sent = 'I saw John with a dog with my cookie'
    print "Sentence:\n", sent

    # tokenize the sentence
    from nltk.token import WSTokenizer
    tok_sent = WSTokenizer().tokenize(sent)

    # Which tests?
    BU = TD = STEP = INCR = 1

    tr = 2
    import time
    if INCR:
        t = time.time()
        cp = IncrementalChartParser(grammar, INCREMENTAL_BU_STRATEGY, trace=tr)
        for parse in cp.parse(tok_sent): print parse
        print 'incremental bottom up', (time.time()-t), '\n'
        t = time.time()
        cp = IncrementalChartParser(grammar, INCREMENTAL_TD_STRATEGY, trace=tr)
        for parse in cp.parse(tok_sent): print parse
        print 'incremental top down ', (time.time()-t), '\n'
    if BU:
        t = time.time()
        cp = ChartParser(grammar, BU_STRATEGY, trace=tr)
        for parse in cp.parse(tok_sent): print parse
        print 'global bottom up     ', (time.time()-t), '\n'
    if TD:
        t = time.time()
        cp = ChartParser(grammar, TD_STRATEGY, trace=tr)
        for parse in cp.parse(tok_sent): print parse
        print 'global top down      ', (time.time()-t), '\n'
    if STEP:
        cp = SteppingChartParser(grammar, trace=tr)
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
