# Natural Language Toolkit: A Chart Parser
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
Data classes and C{ParserI} implementations for "chart parsers," which
use dynamic programming to efficiently parse a text.  A X{chart
parser} derives parse trees for a text by iteratively adding "edges"
to a "chart."  Each X{edge} represents a hypothesis about the tree
structure for a subsequence of the text.  The X{chart} is a
"blackboard" for composing and combining these hypotheses.

When a chart parser begins parsing a text, it creates a new (empty)
chart, spanning the text.  It then incrementally adds new edges to the
chart.  A set of X{chart rules} specifies the conditions under which
new edges should be added to the chart.

Once the chart reaches a stage where none of the chart rules adds any
new edges, parsing is complete.
          
The set of chart rules used by a chart parser is known as its
X{strategy}.  Several standard strategies, such as X{top-down parsing}
and X{bottom-up parsing}, are already defined by the
C{nltk.chartparser} module; however, you can easily create your own
rules and strategies, as well.

Edges are encoded with the C{Edge} class, and charts are encoded with
the C{Chart} class or one of its specailized subclasses.  The chart
parser module includes definitions for three chart parsers:

  - C{ChartParser} is a simple and flexible chart parser.  Its chart rules
    must implement the C{ChartRuleI} interface.
  - C{SteppingChartParser} is a subclass of C{ChartParser} that can be
    used to step through the parsing process.
  - C{IncrementalChartParser} is a more efficient chart parser
    implementation.  Its chart rules implement the
    C{IncrementalChartRule} interface, which returns only the edges
    that can be produced from a given edge.

@group Data Types: Chart, EdgeI, ProductionEdge, TokenEdge, FRChart
@group Chart Parsers: ChartParser, SteppingChartParser,
    IncrementalChartParser
@group Chart Rules: ChartRuleI, BottomUpRule, FundamentalRule,
    TopDownRule, TopDownInitRule, IncrementalChartRuleI,
    IncrementalBottomUpRule, IncrementalFundamentalRule,
    IncrementalTopDownRule, IncrementalTopDownInitRule
@sort: ChartParser, SteppingChartParser, IncrementalChartParser,
    Chart, EdgeI, ProductionEdge, TokenEdge, FRChart,
    ChartRuleI, BottomUpRule, FundamentalRule,
    TopDownRule, TopDownInitRule, IncrementalChartRuleI,
    IncrementalBottomUpRule, IncrementalFundamentalRule,
    IncrementalTopDownRule, IncrementalTopDownInitRule, demo
"""

from nltk.parser import ParserI
from nltk.token import Token, Location
from nltk.tree import TreeToken
from nltk.set import MutableSet
from nltk.cfg import CFG, CFGProduction, Nonterminal, nonterminals

from nltk.chktype import chktype as _chktype 
from nltk.chktype import classeq as _classeq
import types

##//////////////////////////////////////////////////////
##  Edge
##//////////////////////////////////////////////////////

class EdgeI:
    """
    A hypothesis about the tree structure for a subsequence of a text.
    Each edge records the fact that a structure is (partially)
    consistent with the text.  Every edge contains:

        - A C{Location}, indicating what subsequence of the text is
          consistent with the structure.

        - A X{left-hand side}, specifying what kind of structure is
          consistent with the subsequence.  The left-hand side can be
          either a nonterminal or a text type:
              - A nonterminal specifies a C{TreeToken} whose node type
                is the nonterminal's symbol.
              - A text type specifies a C{Token} with that type.

        - A C{Token}, recording the actual structure that is
          consistent with the text.  This value is not used during
          chart parsing; but it provides convenient access to complete
          parses once the chart parsing algorithm terminates.

    In addition, every edge is either "complete" or "incomplete."  An
    edge is X{complete} if its structure has been found to be fully
    consistent with the text.  An edge is X{incomplete} if its
    structure is partially consistent with the text.  In particular,
    if an edge is incomplete, then the subsequence of the text
    specified by its location is a possible prefix for its structure.

    There are two kinds of edge:

        - C{TokenEdge}s record which tokens occur in the text.
          C{TokenEdge}s are always complete.

        - C{ProductionEdge}s record which trees have been found to be
          (partially) consistent with the text.  In addition to the
          fields discussed above, each C{ProductionEdge} contains a
          X{right-hand side}, specifying what kind of children the
          tree structure has.

    The C{EdgeI} interface provides a common interface to both types
    of edge, allowing chart parsers to treat them in a uniform manner.
    """
    def __init__(self):
        """
        Construct a new edge.
        """
        raise AssertionError("EdgeI is an abstract interface")

    def lhs(self):
        """
        @return: this edge's left-hand side.  The left-hand side is a
            nonterminal or text type specifying what kind of
            structure this edge contains:
                - A nonterminal specifies a C{TreeToken} whose node
                  type is the nonterminal's symbol.
                - A text type specifies a C{Token} with that type.
        @rtype: C{Nonterminal} or text type
        """
        raise AssertionError('EdgeI is an abstract interface')

    def complete(self):
        """
        @return: true if this edge's structure is fully consistent
            with the text.
        @rtype: C{boolean}
        """
        raise AssertionError('EdgeI is an abstract interface')

    def structure(self):
        """
        @return: this edge's structure.
        @rtype: C{TreeToken} or C{Token}
        """
        raise AssertionError('EdgeI is an abstract interface')

    def loc(self):
        """
        @return: the location spanned by this edge.  This location
            indicates which span of the text is (partially) consistent
            with this edge's structure.
        @rtype: C{Location}
        """
        raise AssertionError('EdgeI is an abstract interface')

    def start(self):
        """
        @return: the start index of this edge's location.
        @rtype: C{int}
        """
        raise AssertionError('EdgeI is an abstract interface')

    def end(self):
        """
        @return: the end index of this edge's location.
        @rtype: C{int}
        """
        raise AssertionError('EdgeI is an abstract interface')

class ProductionEdge(EdgeI):
    """
    A X{production edge} specifies that a tree licensed by a
    C{CFGProduction} is partially consistent with the text.  In
    particular, it indicates that a prefix of the production's right
    hand side is consistent with a subsequence of the text.  Each
    C{ProductionEdge} contains:

        - The CFG production licensing the tree that is partially
          consistent with the text.

        - The X{dot position}, which specifies what prefix of the
          production's right hand side is consistent with the text.
          In particular, if C{M{prod}} is the production, then the dot
          position C{M{d}} specifies that C{M{prod}.rhs()[:M{d}]} is
          the prefix of the production's right hand that is consistent
          with the text.
          
        - A C{Location} specifying the span of the text that is
          consistent with the prefix of the production's right hand
          side.

    For example, the production edge based on the production
    C{[Production: VP -> V NP PP]}, with dot position C{2} and
    location C{@[3w:7w]} indicates that the tree structure::

        [VP: [V: ...] [NP: ...] [PP: ...]]

    is partially consistent with the text.  In particular, it
    specifies that the first two children of the tree are consistent
    with the text spanning from the third word to the seventh word.

    A C{ProductionEdge} with production C{[Production: A -> B C D]},
    location C{@[3w:8w]}, and dot position 2 is written::

        [Edge: A -> B C * D]@[3w:8w]

    @type _prod: C{CFGProduction}
    @ivar _prod: The production of the edge.
    @type _dotpos: C{int}
    @ivar _dotpos: The position of the dot.
    @type _structure: C{TreeToken}
    @ivar _structure: The current parse tree of the edge.
    @type _loc: C{Location}
    @ivar _loc: The span of tokens covered by the edge.
    """
    def __init__(self, prod, structure, loc, dotpos=0):
        """
        Construct a new C{ProductionEdge}.

        @param prod: The CFG production that the edge is based on.
        @type prod: C{CFGProduction}
        @param structure: The (partial) parse tree that is consistent
            with a subsequence of the text.  This tree's node value
            should be based on the production's left-hand side.  It
            should have C{dotpos} children, corresponding to the first
            C{dotpos} elements of the production's right-hand side.
            Each nonterminal in the production's right hand side
            should correspond to a subtree whose node value is the
            nonterminal's symbol.  Each terminal in the production's
            right-hand side should correspond to a token whose type is
            equal to the terminal.
        @type structure: C{TreeToken}
        @param loc: The location spanned by the edge.  This location
            specifies the span of the text that is consistent with
            a prefix of the production's right hand side.
        @type loc: C{Location}
        @param dotpos: The position of the edge's dot.  This position
            specifies what prefix of the production's right hand side
            is consistent with the text.  In particular, if C{M{prod}}
            is the production, then the dot position C{M{d}} specifies
            that C{M{prod}.rhs()[:M{d}]} is the prefix of the
            production's right hand that is consistent with the text.
        @type dotpos: C{int}
        """
        assert _chktype(1, prod, CFGProduction)
        assert _chktype(2, structure, TreeToken)
        assert _chktype(3, loc, Location)
        assert _chktype(4, dotpos, types.IntType)
        self._prod = prod
        self._structure = structure
        self._loc = loc
        self._dotpos = dotpos

    # Accessors -- inherit docs from EdgeI
    def lhs(self): return self._prod.lhs()
    def structure(self): return self._structure
    def loc(self): return self._loc
    def start(self): return self._loc.start()
    def end(self): return self._loc.end()
    
    def prod(self):
        """
        @return: the production that this edge is based on.
        @rtype: C{CFGProduction}
        """
        return self._prod

    def dotpos(self):
        """
        @return: the position of the dot in the edge's production.
        @rtype: C{int}
        """
        return self._dotpos

    def next(self):
        """
        @return: the element of the edge's production's right hand
            side that immediately follows the dot.
        @rtype: C{Nonterminal} or terminal
        """
        return self._prod.rhs()[self._dotpos]

    def rhs(self):
        """
        @return: the right hand side of the production that this edge
            is based on.
        @rtype: C{list} of (C{Nonterminal} and terminal)
        """
        return self._prod.rhs()
        
    def complete(self):
        # Docs inherited from EdgeI
        return self._dotpos == len(self._prod.rhs())

    def __repr__(self):
        """
        @return: A concise string representation of the C{Edge}
        @rtype: C{string}
        """
        return '[Edge: %s]%s' % (self, self._loc)

    def __str__(self):
        """
        @return: A verbose string representation of the C{Edge}
        @rtype: C{string}
        """
        str = '%s ->' % (self._prod._lhs.symbol(),)
        for i in range(len(self._prod.rhs())):
            if i == self._dotpos: str += ' *'
            if isinstance(self._prod.rhs()[i], Nonterminal):
                str += ' %s' % (self._prod.rhs()[i].symbol(),)
            else:
                str += ' %r' % (self._prod.rhs()[i],)
        return str

    def __eq__(self, other):
        """
        @return: true if this C{Edge} is equal to C{other}.
        @rtype: C{boolean}
        """
        return (_classeq(self, other) and 
                self._prod == other._prod and
                self._structure == other._structure and
                self._loc == other._loc and
                self._dotpos == other._dotpos)

    def __cmp__(self, other):
        if self == other: return 0
        if isinstance(other, TokenEdge): return 1
        val = cmp([self._loc.start(), self._loc.length()],
                  [other._loc.start(), other._loc.length()])
        if val == 0: return 1
        else: return val

    def __hash__(self):
        """
        @return: A hash value for the C{Edge}.
        @rtype: C{int}
        """
        return hash((self._prod, self._structure, self._loc, self._dotpos))

class TokenEdge(EdgeI):
    """
    A C{token edge} specifies that a single token occurs in the text.
    Encoding the text tokens as edges allows chart parsers to treat
    tokens and subtrees in a uniform manner.

    A C{TokenEdge} with left-hand side C{'cat'} and location C{@[2w]}
    is written::

        [Edge: 'cat' -> *]

    """
    def __init__(self, token):
        """
        Construct a new C{TokenEdge}.
        @type token: C{Token}
        """
        assert _chktype(1, token, Token)
        self._token = token

    # Accessors -- inherit docs from EdgeI
    def lhs(self): return self._token.type()
    def structure(self): return self._token
    def loc(self): return self._token.loc()
    def start(self): return self._token.loc().start()
    def end(self): return self._token.loc().end()
    
    def complete(self):
        # Inherit docs from EdgeI
        return 1

    def __repr__(self):
        """
        @return: A concise string representation of the C{Edge}
        @rtype: C{string}
        """
        return '[Edge: %s]%s' % (self, self._token.loc())

    def __str__(self):
        """
        @return: A verbose string representation of the C{Edge}
        @rtype: C{string}
        """
        return '%r.' % self._token.type()

    def __eq__(self, other):
        """
        @return: true if this C{Edge} is equal to C{other}.
        @rtype: C{boolean}
        """
        return _classeq(self, other) and self._token == other._token

    def __cmp__(self, other):
        if self == other: return 0
        if isinstance(other, ProductionEdge): return -1
        val = cmp(self._token.loc().start(),
                  other._token.loc().start())
        if val == 0: return 1
        else: return val

    def __hash__(self):
        """
        @return: A hash value for the C{Edge}.
        @rtype: C{int}
        """
        return hash(self._token)
    
##//////////////////////////////////////////////////////
##  Chart
##//////////////////////////////////////////////////////

class Chart:
    """
    A blackboard for hypotheses about syntactic constituents.

    @type _chart: C{MutableSet} of C{Edge}s
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
        assert _chktype(1, loc, Location)
        self._edgeset = MutableSet()
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
            A complete edge is an edge whose dot is in the final
            position.
        @rtype: C{sequence} of C{Edge}
        """
        return [e for e in self.edges() if e.complete()]
    
    def incomplete_edges(self):
        """
        @return: A list of all incomplete edges contained in this chart.
            An incomplete edge is an edge whose dot is in a nonfinal
            position.
        @rtype: C{sequence} of C{Edge}
        """
        return [e for e in self.edges() if not e.complete()]

    def insert(self, edge):
        """
        Attempt to insert a new edge into this chart.  If the edge is
        already present, return []; otherwise, return a list
        containing the inserted edge.
        """
        assert _chktype(1, edge, EdgeI)
        if self._edgeset.insert(edge):
            return [edge]
        else:
            return []
        
    def parses(self, node):
        """
        Return the set of complete parses encoded by this chart, whose
        root node value is C{node}.  Use self._loc to test if the edge
        spans the entire chart.

        @type node: C{Nonterminal}
        """
        assert _chktype(1, node, Nonterminal)
        return [edge.structure() for edge in self.edges() if
                edge.loc() == self._loc and edge.lhs() == node and
                edge.complete()]

    def contains(self, edge):
        """
        @return: true iff this C{Chart} contains the specified edge.
        @rtype: C{boolean}
        """
        assert _chktype(1, edge, EdgeI)
        return edge in self._edgeset
        
    def __contains__(self, edge):
        """
        @return: true iff this C{Chart} contains the specified edge.
        @rtype: C{boolean}
        """
        assert _chktype(1, edge, EdgeI)
        return edge in self._edgeset
            
    def draw(self, text=None, **kwargs):
        assert _chktype(1, text, [Token], (Token), types.NoneType)
        import nltk.draw.chart
        nltk.draw.chart.ChartView(self, text, **kwargs)

    def pp_edge(self, edge, width=3):
        """
        Return a pretty-printed representation of a given edge on this
        chart.
        """
        assert _chktype(1, edge, EdgeI)
        assert _chktype(2, width, types.IntType)
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
        return str + '| %s ' % edge #FIXME
        
    def pp(self, text=None, width=3):
        assert _chktype(1, text, [Token], (Token), types.NoneType)
        assert _chktype(2, width, types.IntType)
        (chart_start, chart_end) = (self._loc.start(), self._loc.end())
        str = ''

        # Draw a header.  Header line shows what words correspond to
        # each position.
        if text:
            str += '| '
            pos = chart_start
            for tok in text:
                str += (tok.loc().start() - pos) * '   '
                len = width*(tok.loc().end() - tok.loc().start())
                type = ('%s' % tok.type())[:len-1]
                str += ('%-'+`len`+'s') % type
                pos = tok.loc().end()
            str += '   '*(chart_end - text[-1].loc().end()) + '|\n'

        # Draw each edge on a separate line.
        edges = self.edges()
        edges.sort()
        for edge in edges:
            str += self.pp_edge(edge, width) + '\n'
        return str

class FRChart(Chart):
    """
    A specialized chart that can efficiently find the set of edges
    that could combine with a given edge by the fundamental rule.  The
    fundamental rule can combine two edges C{M{e1}} and C{M{e2}} if
    C{M{e1}.end()==M{e2}.start()} and
    C{M{e1}.next()==M{e2}.lhs()}.

    C{FRChart} indexes the set of complete edges in the chart by their
    start location and their production's left hand side; and indexes
    the set of incomplete edges in the chart by their end location and
    the element of their production's right hand side following its
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
        assert _chktype(1, loc, Location)
        Chart.__init__(self, loc)
        self._complete = {}
        self._incomplete = {}

    def insert(self, edge):
        # Inherit docs.
        assert _chktype(1, edge, EdgeI)
        return_value = Chart.insert(self, edge)
        if return_value:
            if edge.complete():
                key = (edge.start(), edge.lhs())
                self._complete.setdefault(key, []).append(edge)
            else:
                key = (edge.end(), edge.next())
                self._incomplete.setdefault(key, []).append(edge)
        return return_value

    def complete_edges(self, start=None, lhs=None):
        """
        @return: A list of complete edges contained in this chart.
            A complete edge is an edge whose dot
            in the final position.  If C{start} and C{lhs} are 
            specified, then return all edges that begin at C{start}
            and whose productions have a left hand side C{lhs}.
            Otherwise, return all complete edges contained in this
            chart. 
        @rtype: C{sequence} of C{Edge}
        """
        assert _chktype(1, start, types.NoneType, types.IntType)
        if start is None or lhs is None:
            return Chart.complete_edges(self)
        return self._complete.get((start, lhs), [])

    def incomplete_edges(self, end=None, next=None):
        """
        @return: A list of all incomplete edges contained in this chart.
            An incomplete edge is an edge whose dot
            in a nonfinal position.  If C{end} and C{next} are 
            specified, then return all edges that end at C{end}
            and that have productions whose first element after the
            dot is C{next}.  Otherwise, return all complete edges
            contained in this chart.
        @rtype: C{sequence} of C{Edge}
        """
        assert _chktype(1, end, types.NoneType, types.intType)
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
        assert _chktype(1, edge, EdgeI)
        if edge.complete():
            return self._incomplete.get((edge.start(), edge.lhs()),[])
        else:
            return self._complete.get((edge.end(), edge.next()),[])

##//////////////////////////////////////////////////////
##  ChartRule
##//////////////////////////////////////////////////////

class ChartRuleI:
    def apply(self, chart, grammar):
        """
        @return: a new edge that can be added to C{chart} by this
            rule, assuming the given grammar; or C{None} if no new
            edges can be added.
        @rtype: L{EdgeI} or C{None}
        @param chart: The chart in which the rule should be applied.
        @type chart: L{Chart}
        @param grammar: The grammar that is being used to parse
            C{chart}.
        @type grammar: L{CFG}
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
    """
    A flexible chart parser that uses C{ChartRule}s to decide which
    edges to add to a chart.
    """
    
    ##############################################
    # Initialization
    ##############################################
    def __init__(self, grammar, strategy, **kwargs):
        assert _chktype(1, grammar, CFG)
        assert _chktype(2, strategy, (ChartRuleI), [ChartRuleI])
        self._grammar = grammar
        self._strategy = strategy
        self._trace = kwargs.get('trace', 0)

    ##############################################
    # Accessor functions.
    ##############################################
    def grammar(self):
        """
        @return: The grammar used to parse texts.
        @rtype: C{CFG}
        """
        return self._grammar

    def set_grammar(self, grammar):
        """
        Change the grammar used to parse texts.
        
        @param grammar: The new grammar.
        @type grammar: C{CFG}
        """
        assert _chktype(1, grammar, CFG)
        self._grammar = grammar
    
    ##############################################
    # Parsing
    ##############################################

    def _create_chart(self, text):
        """
        @param text: The text to be parsed
        @rtype: C{Chart}
        """
        assert _chktype(1, text, [Token], (Token), types.NoneType)
        
        # Construct a new (empty) chart that spans the given
        # sentence.
        loc = Location(text[0].loc().start(), text[-1].loc().end(),
                       unit=text[0].loc().unit(),
                       source=text[0].loc().source())
        chart = Chart(loc)

        # Add an edge for each lexical item.
        #if self._trace: print 'Adding lexical edges...'
        for tok in text:
            new_edge = TokenEdge(tok)
            if chart.insert(new_edge):
                if self._trace > 1:
                    print '%-20s %s' % ('Lexical Insertion',
                                        chart.pp_edge(new_edge))

        # Return the new chart
        return chart

    def parse_n(self, text, n=None):
        # Inherit documentation from ParserI
        assert _chktype(1, text, [Token], (Token), types.NoneType)
        assert _chktype(2, n, types.IntType, types.NoneType)

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

    def parse(self, text):
        assert _chktype(1, text, [Token], (Token), types.NoneType)
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
    assert _chktype(1, production, CFGProduction)
    assert _chktype(2, loc, Location)
    treetok = TreeToken(production.lhs().symbol())
    return ProductionEdge(production, treetok, loc)

def fr_edge(edge1, edge2):
    """
    Return a fundamental-rule edge.
    """
    assert _chktype(1, edge1, EdgeI)
    assert _chktype(2, edge2, EdgeI)
    loc = edge1.loc().union(edge2.loc())
    children = edge1.structure().children() + (edge2.structure(),)
    treetok = TreeToken(edge1.structure().node(), *children)
    return ProductionEdge(edge1.prod(), treetok, loc, edge1.dotpos()+1)
    
class TopDownInitRule(ChartRuleI):
    def apply(self, chart, grammar):
        assert _chktype(1, chart, Chart)
        assert _chktype(2, grammar, CFG)
        edges = []
        for production in grammar.productions():
            if production.lhs() == grammar.start():
                loc = chart.loc().start_loc()
                edges.append(self_loop_edge(production, loc))
        return edges
    def __str__(self): return 'Top Down Init Rule'
    
class TopDownRule(ChartRuleI):
    def apply(self, chart, grammar):
        assert _chktype(1, chart, Chart)
        assert _chktype(2, grammar, CFG)
        # Sort to give the same behavior as Earley
        incomplete = chart.incomplete_edges()
        incomplete.sort()
        edges = []
        for production in grammar.productions():
            for edge in incomplete:
                if production.lhs() == edge.next():
                    loc = edge.loc().end_loc()
                    edges.append(self_loop_edge(production, loc))
        return edges
    def __str__(self): return 'Top Down Rule'

class BottomUpRule(ChartRuleI):
    def apply(self, chart, grammar):
        assert _chktype(1, chart, Chart)
        assert _chktype(2, grammar, CFG)
        edges = []
        complete = chart.complete_edges()
        complete.sort()
        for edge in complete:
            for production in grammar.productions():
                if edge.lhs() == production.rhs()[0]:
                    loc = edge.loc().start_loc()
                    edges.append(self_loop_edge(production, loc))
        edges.reverse()
        return edges
    def __str__(self): return 'Bottom Up Rule'

class FundamentalRule(ChartRuleI):
    def apply(self, chart, grammar):
        assert _chktype(1, chart, Chart)
        assert _chktype(2, grammar, CFG)
        # Sort to give the same behavior as Earley
        incomplete = chart.incomplete_edges()
        incomplete.sort()
        edges = []
        for edge in incomplete:
            for edge2 in chart.complete_edges():
                if (edge.next() == edge2.lhs() and
                    edge.end() == edge2.start()):
                    edges.append(fr_edge(edge, edge2))
        edges.reverse()
        return edges
    def __str__(self): return 'Fundamental Rule'

##//////////////////////////////////////////////////////
##  Strategies
##//////////////////////////////////////////////////////

# Define some useful rule invocation strategies.
TD_STRATEGY = [TopDownRule(), FundamentalRule(), TopDownInitRule()]
BU_STRATEGY = [BottomUpRule(), FundamentalRule()]

##//////////////////////////////////////////////////////
##  SteppingChartParser
##//////////////////////////////////////////////////////

class SteppingChartParser(ChartParser):
    """
    A C{ChartParser} that allows you to step through the parsing
    process, adding a single edge at a time.  It also allows you to
    change the parser's strategy or grammar midway through parsing a
    text.

    The C{initialize} method is used to start parsing a text.  C{step}
    adds a single edge to the chart.  C{set_strategy} changes the
    strategy used by the chart parser.  C{parses} returns the set of
    parses that has been found by the chart parser.
    """
    def __init__(self, grammar, strategy=None, **kwargs):
        assert _chktype(1, grammar, CFG)
        assert _chktype(2, strategy, (ChartRuleI), [ChartRuleI],
                        types.NoneType)
        if strategy is None: strategy = []
        ChartParser.__init__(self, grammar, strategy, **kwargs)

        self._chart = None
        self._edge_queue = []
        self._current_chartrule = None

    def initialize(self, text):
        """
        Start parsing a given text.
        
        For now, just take a text.. eventually we want to be able to
        take a chart, if the user wants to supply one.
        """
        assert _chktype(1, text, [Token], (Token), types.NoneType)
        self._chart = self._create_chart(text)
        self._edge_queue = []
        self._current_chartrule = None

    def set_strategy(self, strategy):
        """
        Change the startegy that the parser uses to decide which edges
        to add to the chart.
        """
        assert _chktype(1, strategy, (ChartRuleI), [ChartRuleI])
        if strategy != self._strategy:
            self._strategy = strategy
            self._edge_queue = []
            self._current_chartrule = None

    def parses(self):
        """
        Return the parses that are currently contained in the parser's
        chart.
        """
        if self._chart is None:
            raise ValueError('You must initialize the parser first.')
        return self._chart.parses(self._grammar.start())

    def chart(self):
        """
        Return the chart that is used by the parser.
        """
        return self._chart

    def set_chart(self, chart):
        """
        Load a given chart into the stepping chart parser.

        @param chart: The chart to use for parsing.
        @type chart: C{Chart}
        @rtype: C{none}
        """
        assert _chktype(1, chart, Chart)
        self._chart = chart
        self._edge_queue = []
        self._current_chartrule = None

    def current_chartrule(self):
        """
        @return: the chart rule that was used to generate the most
            recent edge.
        @rtype: C{ChartRuleI} or C{None}
        """
        return self._current_chartrule

    def step(self, **kwarg):
        """
        Add a single edge to the chart.
        
        @rtype: C{Edge} or C{None}
        @return: if an edge was added to the chart, then return the
            new edge; otherwise, return C{None}.
        """
        if self._chart is None:
            raise ValueError('You must initialize the parser before stepping.')
        
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

        strategy = self._strategy
        if self.current_chartrule() is not None:
            strategy.insert(0, self.current_chartrule())
            
        # If there are no new edges, try generating some.
        for chartrule in strategy:
            new_edges = chartrule.apply(self._chart, self._grammar)
            new_edges.reverse()
            self._edge_queue += new_edges
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
        assert _chktype(1, text, [Token], (Token), types.NoneType)
        assert _chktype(2, n, types.IntType, types.NoneType)

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
    A more efficient chart parser implementation.
    """
    def __init__(self, grammar, strategy, **kwargs):
        assert _chktype(1, grammar, CFG)
        assert _chktype(1, strategy, (IncrementalChartRuleI),
                        [IncrementalChartRuleI])
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
        assert _chktype(1, text, [Token], (Token), types.NoneType)
        # Construct a new (empty) chart that spans the given
        # sentence.
        loc = Location(text[0].loc().start(), text[-1].loc().end(),
                       unit=text[0].loc().unit(),
                       source=text[0].loc().source())
        return Chart(loc)

    def _create_edge_queue(self, text):
        edge_queue = []
        for tok in text:
            edge_queue.append(TokenEdge(tok))

        # Start with the first word (top of stack = last elt)
        edge_queue.reverse()
        
        return edge_queue

    def parse_n(self, text, n=None):
        # Inherit documentation from ParserI
        assert _chktype(1, text, [Token], (Token), types.NoneType)
        assert _chktype(2, n, types.IntType, types.NoneType)

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
            if (edge.loc() == chart.loc() and edge.complete() and 
                edge.lhs() == self._grammar.start()):
                parses.append(edge.structure())
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

    def parse(self, text):
        # Inherit docs from ProbabilisticParserI; and delegate to parse_n
        assert _chktype(1, text, [Token], (Token), types.NoneType)

        final_trees = self.parse_n(text, 1)
        if len(final_trees) == 0: return None
        else: return final_trees[0]

class IncrementalTopDownInitRule(IncrementalChartRuleI):
    def apply(self, chart, grammar, edge):
        assert _chktype(1, chart, Chart)
        assert _chktype(2, grammar, CFG)
        assert _chktype(3, edge, EdgeI)
        if isinstance(edge.structure(), TreeToken): return []
        return [self_loop_edge(production, chart.loc().start_loc())
                for production in grammar.productions()
                if production.lhs() == grammar.start()]

class IncrementalTopDownRule(IncrementalChartRuleI):
    def apply(self, chart, grammar, edge):
        assert _chktype(1, chart, Chart)
        assert _chktype(2, grammar, CFG)
        assert _chktype(3, edge, EdgeI)
        if edge.complete(): return []
        return [self_loop_edge(production, edge.loc().end_loc())
                for production in grammar.productions()
                if production.lhs() == edge.next()]

class IncrementalBottomUpRule(IncrementalChartRuleI):
    def apply(self, chart, grammar, edge):
        assert _chktype(1, chart, Chart)
        assert _chktype(2, grammar, CFG)
        assert _chktype(3, edge, EdgeI)
        return [self_loop_edge(production, edge.loc().start_loc())
                for production in grammar.productions()
                if edge.lhs() == production.rhs()[0] and edge.complete()]

class IncrementalFundamentalRule(IncrementalChartRuleI):
    def apply(self, chart, grammar, edge):
        assert _chktype(1, chart, Chart)
        assert _chktype(2, grammar, CFG)
        assert _chktype(3, edge, EdgeI)
        if edge.complete():
            return [fr_edge(edge2, edge)
                    for edge2 in chart.incomplete_edges()
                    if (edge2.next() == edge.lhs() and
                        edge2.end() == edge.start())]
        else:
            return [fr_edge(edge, edge2)
                    for edge2 in chart.complete_edges()
                    if (edge.next() == edge2.lhs() and
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
    """
    A demonstration of the chart parsers.
    """
    import sys, time
    
    # Define some nonterminals
    S, VP, NP, PP = nonterminals('S, VP, NP, PP')
    V, N, P, Name, Det = nonterminals('V, N, P, Name, Det')

    # Define a gramar.
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

    # Tokenize a sample sentence.
    sent = 'I saw John with a dog with my cookie'
    print "Sentence:\n", sent
    from nltk.tokenizer import WSTokenizer
    tok_sent = WSTokenizer().tokenize(sent)

    # Ask the user which parser to test
    print '  1: Top-down chart parser'
    print '  2: Bottom-up chart parser'
    print '  3: Incremental chart parsers'
    print '  4: Stepping chart parser (alternating top-down & bottom-up)'
    print '  5: All parsers'
    print '\nWhich parser (1-5)? ',
    choice = sys.stdin.readline().strip()
    if choice not in '12345':
        print 'Bad parser number'
        return

    # Keep track of how long each parser takes.
    times = {}

    # Run the top-down parser, if requested.
    if choice in ('1', '5'):
        cp = ChartParser(grammar, TD_STRATEGY, trace=2)
        t = time.time()
        parses = cp.parse_n(tok_sent)
        times['top down'] = time.time()-t
        for parse in parses: print parse

    # Run the bottom-up parser, if requested.
    if choice in ('2', '5'):
        cp = ChartParser(grammar, BU_STRATEGY, trace=2)
        t = time.time()
        parses = cp.parse_n(tok_sent)
        times['bottom up'] = time.time()-t
        for parse in parses: print parse

    # Run the incremental parsers, if requested.
    if choice in ('3', '5'):
        cp = IncrementalChartParser(grammar, INCREMENTAL_TD_STRATEGY, trace=2)
        t = time.time()
        parses = cp.parse_n(tok_sent)
        times['incremental top down'] = time.time()-t
        for parse in parses: print parse
        t = time.time()
        cp = IncrementalChartParser(grammar, INCREMENTAL_BU_STRATEGY, trace=2)
        parses = cp.parse_n(tok_sent)
        times['incremental bottom up'] = time.time()-t
        for parse in parses: print parse

    # Run the stepping parser, if requested.
    if choice in ('4', '5'):
        t = time.time()
        cp = SteppingChartParser(grammar, trace=2)
        cp.initialize(tok_sent)
        for i in range(4):
            print '*** SWITCH TO TOP DOWN'
            cp.set_strategy(TD_STRATEGY)
            for j in range(20):
                if not cp.step(): break
            print '*** SWITCH TO BOTTOM UP'
            cp.set_strategy(BU_STRATEGY)
            for k in range(20):
                if not cp.step(): break
        times['stepping'] = time.time()-t
        for parse in cp.parses(): print parse

    # Print the times of all parsers:
    maxlen = max([len(key) for key in times.keys()])
    format = '%' + `maxlen` + 's parser: %6.3fsec'
    times_items = times.items()
    times_items.sort(lambda a,b:cmp(a[1], b[1]))
    for (parser, t) in times_items:
        print format % (parser, t)
            
if __name__ == '__main__': demo()
