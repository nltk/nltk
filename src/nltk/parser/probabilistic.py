# Natural Language Toolkit: Probabilistic Parsers
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
Classes and interfaces for associating probabilities with tree
structures that represent the internal organziation of a text.  The
probabilistic parser module defines C{ProbabilisticParserI}, a
standard interface for associating probabilities with parses for a
text.  It also defines two implementations of the
C{ProbablisticParserI} interface, C{ViterbiPCFGParser} and
C{BottomUpPCFGChartParser}.

C{ViterbiPCFGParser} is a C{PCFG} parser based on a Viterbi-sytle
algorithm.  It uses dynamic programming to efficiently find the single
most likely parse for a given text.

C{BottomUpPCFGChartParser} is an abstract class that implements a
bottom-up chart parser for C{PCFG}s.  It maintains a queue of edges,
and adds them to the chart one at a time.  The ordering of this queue
is based on the probabilities associated with the edges, allowing the
parser to expand more likely edges before less likely ones.  Each
subclass implements a different queue ordering, producing different
search strategies.  Currently the following subclasses are defined:

  - C{InsidePCFGParser} searches edges in decreasing order of
    their trees' inside probabilities.
  - C{RandomPCFGParser} searches edges in random order.
  - C{LongestPCFGParser} searches edges in decreasing order of their
    location's length.
  - C{BeamPCFGParser} limits the number of edges in the queue, and
    searches edges in decreasing order of their trees' inside
    probabilities.

@group Interfaces: ProbabilisticParserI
@group Viterbi Parsers: ViterbiPCFGParser
@group Chart Parsers: BottomUpPCFGChartParser, InsidePCFGParser,
    RandomPCFGParser, LongestPCFGParser, BeamPCFGParser,
    UnsortedPCFGParser
@sort: BottomUpPCFGChartParser, InsidePCFGParser,
       RandomPCFGParser, UnsortedPCFGParser, LongestPCFGParser,
       BeamPCFGParser

@todo: Define C{OutsidePCFGParser}, which searches edges using
       best-first search.
@todo: Define C{InsideOutsidePCFGParser}, which searches edges using
       A* search.

@bug: The C{BottomUpPCFGParser} subclasses don't appear to generate
      all parses.
"""

from nltk.parser import ParserI
from nltk.cfg import PCFG, PCFGProduction, Nonterminal
from nltk.token import ProbabilisticToken, Location, Token
from nltk.tree import ProbabilisticTreeToken
from nltk.parser.chart import Chart, FRChart, TokenEdge, ProductionEdge
from nltk.chktype import chktype as _chktype
import types

##//////////////////////////////////////////////////////
##  Probabilistic Parser Interface
##//////////////////////////////////////////////////////
class ProbabilisticParserI(ParserI):
    """
    A processing interface for associating proabilities with trees
    that represent possible structures for a sequence of tokens.  A
    C{ProbabilisticParser} is a C{Parser} whose quality ratings are
    probabilities.  In particular, the quality of a parse for a given
    text is the probability that the parse is the correct
    representation for the structure of the text.

    In order to allow access to the probabilities associated with each
    parse, the parses are returned as C{ProbabilisticTreeToken}s.
    C{ProbabilisticTreeToken}s are C{TreeToken}s that have
    probabilities associated with them.

    In addition to the methods defined by the C{Parser} interface,
    C{ProbabilisticParser} defines the C{parse_dist} method, which
    returns a C{ProbDist} whose samples are C{parses}.

    @see: C{ProbabilisticTreeToken}
    """
    def __init__(self):
        """
        Construct a new C{ProbabilisticParser}.
        """
        assert 0, "ProbabilisticParserI is an abstract interface"

    def parse(self, text):
        """
        Return the best parse for the given text, or C{None} if no
        parses are available.
        
        @return: The highest-quality parse for the given text.  If
            multiple parses are tied for the highest quality, then
            choose one arbitrarily.  If no parse is available for the
            given text, return C{None}.
        @rtype: C{ProbabilisticTreeToken} or C{None}
        @param text: The text to be parsed.  This text consists
            of a list of C{Tokens}, ordered by their C{Location}.
        @type text: C{list} of C{Token}
        """
        assert 0, "ParserI is an abstract interface"

    def parse_n(self, text, n=None):
        """
        @return: a list of the C{n} best parses for the given text,
            sorted in descending order of quality (or all parses, if
            the text has less than C{n} parses).  The order among
            parses with the same quality is undefined.  I.e., the
            first parse in the list will have the highest quality; and
            each subsequent parse will have equal or lower quality.
            Note that the empty list will be returned if no parses
            were found.
        @rtype: C{list} of C{ProbabilisticTreeToken}
        @param n: The number of parses to generate.  At most C{n}
            parses will be returned.  If C{n} is C{None}, return all
            parses. 
        @type n: C{int}
        @param text: The text to be parsed.  This text consists
            of a list of C{Tokens}, ordered by their C{Location}.
        @type text: C{list} of C{Token}
        """
        assert 0, "ParserI is an abstract interface"

    def parse_dist(self, text):
        """
        @return: a C{ProbDist} that specifies probabilities of parses
            for the given text.  The samples of this C{ProbDist}
            are the possible parses for the given text; and their
            probabilities indicate the likelihood that they are the
            correct representation for the structure of the given
            text.
        @rtype: C{ProbDist} with C{TreeToken} samples
        @param text: The text to be parsed.  This text consists
            of a list of C{Tokens}, ordered by their C{Location}.
        @type text: C{list} of C{Token}
        """
        assert 0, "ProbabilisticParserI is an abstract interface"

##//////////////////////////////////////////////////////
##  Viterbi PCFG Parser
##//////////////////////////////////////////////////////

class ViterbiPCFGParser(ProbabilisticParserI):
    """
    A bottom-up C{PCFG} parser that uses dynamic programming to find
    the single most likely parse for a text.  C{ViterbiPCFGParser}
    parses texts by filling in a X{most likely constituent table}.
    This table records the most probable tree representation for any
    given span and node value.  In particular, it has an entry for
    every start index, end index, and node value, recording the most
    likely subtree that spans from the start index to the end index,
    and has the given node value.

    C{ViterbiPCFGParser} fills in this table incrementally.  It starts
    by filling in all entries for constituents that span one element
    of text (i.e., entries where the end index is one greater than the
    start index).  After it has filled in all table entries for
    constituents that span one element of text, it fills in the
    entries for constitutants that span two elements of text.  It
    continues filling in the entries for constituents spanning larger
    and larger portions of the text, until the entire table has been
    filled.  Finally, it returns the table entry for a constituent
    spanning the entire text, whose node value is the grammar's start
    symbol.

    In order to find the most likely constituent with a given span and
    node value, C{ViterbiPCFGParser} considers all productions that
    could produce that node value.  For each production, it finds all
    children that collectively cover the span and have the node values
    specified by the production's right hand side.  If the probability
    of the tree formed by applying the production to the children is
    greater than the probability of the current entry in the table,
    then the table is updated with this new tree.

    A pseudo-code description of the algorithm used by
    C{ViterbiPCFGParser} is:

      - Create an empty most likely constituent table, M{MLC}.
      - For M{width} in 1...len(M{text}):
        - For M{start} in 1...len(M{text})-M{width}:
          - For M{prod} in grammar.productions:
            - For each sequence of subtrees [M{t[1]}, M{t[2]}, ..., 
              M{t[n]}] in M{MLC}, where M{t[i]}.node==M{prod}.rhs[i],
              and the sequence covers [M{start}:M{start}+M{width}]:
                - M{old_p} = M{MLC}[M{start}, M{start+width}, M{prod}.lhs]
                - M{new_p} = P(M{t[1]})*P(M{t[1]})*...*P(M{t[n]})*P(M{prod})
                - if M{new_p} > M{old_p}:
                  - M{new_tree} = Tree(M{prod}.lhs, M{t[1]}, M{t[2]},
                    ..., M{t[n]})
                  - M{MLC}[M{start}, M{start+width}, M{prod}.lhs]
                    = M{new_tree}
      - Return M{MLC}[0, len(M{text}), M{start_symbol}]
                
    @type _grammar: C{PCFG}
    @ivar _grammar: The grammar used to parse sentences.
    @type _trace: C{int}
    @ivar _trace: The level of tracing output that should be generated
        when parsing a text.
    """
    def __init__(self, grammar, trace=0):
        """
        Create a new C{ViterbiPCFGParser}, that uses {grammar} to
        parse texts.

        @type grammar: C{PCFG}
        @param grammar: The grammar used to parse texts.
        @type trace: C{int}
        @param trace: The level of tracing that should be used when
            parsing a text.  C{0} will generate no tracing output;
            and higher numbers will produce more verbose tracing
            output.
        """
        assert _chktype(1, grammar, PCFG)
        assert _chktype(2, trace, types.IntType)
        self._grammar = grammar
        self._trace = trace

    def trace(self, trace=2):
        """
        Set the level of tracing output that should be generated when
        parsing a text.

        @type trace: C{int}
        @param trace: The trace level.  A trace level of C{0} will
            generate no tracing output; and higher trace levels will
            produce more verbose tracing output.
        @rtype: C{None}
        """
        assert _chktype(1, trace, types.IntType)
        self._trace = trace

    def parse(self, text):
        # Inherit docs from ProbabilisticParserI; and delegate to parse_n
        assert _chktype(1, text, [Token], (Token))
        final_trees = self.parse_n(text, 1)
        if len(final_trees) == 0: return None
        else: return final_trees[0]
        
    def parse_dist(self, text):
        # Inherit docs from ProbabilisticParserI; and delegate to parse_n
        prob_dict = {}
        for parse in self.parse_n(text):
            prob_dict[parse] = parse.p()
        return DictionaryProbDist(prob_dict)

    def parse_n(self, text, n=None):
        # Inherit docs from ProbabilisticParserI
        assert _chktype(1, text, [Token], (Token))
        assert _chktype(2, n, types.IntType, types.NoneType)

        # The most likely consituant table.  This table specifies the
        # most likely constituent for a given span and type.
        # Constituents can be either TreeTokens or Tokens.  For
        # TreeTokens, the "type" is the Nonterminal for the tree's
        # root node value.  For Tokens, the "type" is the token's
        # type.  The table is stored as a dictionary, since it is
        # sparse.
        constituents = {}
        
        # Initialize the constituents dictionary with the words from
        # the text.
        if self._trace: print ('Inserting tokens into the most likely'+
                               ' constituents table...')
        for index in range(len(text)):
            tok = text[index]
            probtok = ProbabilisticToken(1, tok.type(), tok.loc())
            constituents[index,index+1,tok.type()] = probtok
            if self._trace > 1: self._trace_lexical_insertion(tok, text)

        # Consider each span of length 1, 2, ..., n; and add any trees
        # that might cover that span to the constituents dictionary.
        for length in range(1, len(text)+1):
            if self._trace:
                if self._trace > 1: print
                print ('Finding the most likely constituents'+
                       ' spanning %d text elements...' % length)
            #print constituents
            for start in range(len(text)-length+1):
                span = (start, start+length)
                self._add_constituents_spanning(span, constituents, text)

        # Find all trees that span the entire text & have the right cat
        trees = [constituents.get((0, len(text),
                                   self._grammar.start()), [])]

        # Sort the trees, and return the requested number of them.
        trees.sort(lambda t1,t2: cmp(t2.prob(), t1.prob()))
        if n is None: return trees
        else: return trees[:n]

    def _add_constituents_spanning(self, span, constituents, text):
        """
        Find any constituents that might cover C{span}, and add them
        to the most likely constituents table.

        @rtype: C{None}
        @type span: C{(int, int)}
        @param span: The section of the text for which we are
            trying to find possible constituents.  The span is
            specified as a pair of integers, where the first integer
            is the index of the first token that should be included in
            the constituent; and the second integer is the index of
            the first token that should not be included in the
            constituent.  I.e., the constituent should cover
            C{M{text}[span[0]:span[1]]}, where C{M{text}} is the text
            that we are parsing.

        @type constituents: C{dictionary} from
            C{(int,int,Nonterminal)} to (C{ProbabilisticToken} or
            C{ProbabilisticTreeToken}).
        @param constituents: The most likely constituents table.  This
            table records the most probable tree representation for
            any given span and node value.  In particular,
            C{constituents(M{s},M{e},M{nv})} is the most likely
            C{ProbabilisticTreeToken} that covers C{M{text}[M{s}:M{e}]}
            and has a node value C{M{nv}.symbol()}, where C{M{text}}
            is the text that we are parsing.  When
            C{_add_constituents_spanning} is called, C{constituents}
            should contain all possible constituents that are shorter
            than C{span}.
            
        @type text: C{list} of C{Token}
        @param text: The text we are parsing.  This is only used for
            trace output.  
        """
        # Since some of the grammar productions may be unary, we need to
        # repeatedly try all of the productions until none of them add any
        # new constituents.
        changed = 1
        while changed:
            changed = 0
            
            # Find all ways instantiations of the grammar productions that
            # cover the span.
            instantiations = self._find_instantiations(span, constituents)

            # For each production instantiation, add a new
            # ProbabilisticTreeToken whose probability is the product
            # of the childrens' probabilities and the production's
            # probability.
            for (production, children) in instantiations:
                p = reduce(lambda pr,t:pr*t.prob(),
                           children, production.prob())
                node = production.lhs().symbol()
                tree = ProbabilisticTreeToken(p, node, *children)

                # If it's new a constituent, then add it to the
                # constituents dictionary.
                c = constituents.get((span[0], span[1], production.lhs()),
                                     None)
                if self._trace > 1:
                    if c is None or c != tree:
                        if c is None or c.prob() < tree.prob():
                            print '   Insert:',
                        else:
                            print '  Discard:',
                        self._trace_production(production, tree, text, p)
                if c is None or c.prob() < tree.prob():
                    constituents[span[0], span[1], production.lhs()] = tree
                    changed = 1

    def _find_instantiations(self, span, constituents):
        """
        @return: a list of the production instantiations that cover a
            given span of the text.  A X{production instantiation} is
            a tuple containing a production and a list of children,
            where the production's right hand side matches the list of
            children; and the children cover C{span}.  @rtype: C{list}
            of C{pair} of C{PCFGProduction}, (C{list} of
            (C{ProbabilisticTreeToken} or C{Token})

        @type span: C{(int, int)}
        @param span: The section of the text for which we are
            trying to find production instantiations.  The span is
            specified as a pair of integers, where the first integer
            is the index of the first token that should be covered by
            the production instantiation; and the second integer is
            the index of the first token that should not be covered by
            the production instantiation.
        @type constituents: C{dictionary} from
            C{(int,int,Nonterminal)} to (C{ProbabilisticToken} or
            C{ProbabilisticTreeToken}).
        @param constituents: The most likely constituents table.  This
            table records the most probable tree representation for
            any given span and node value.  See the module
            documentation for more information.
        """
        rv = []
        for production in self._grammar.productions():
            childlists = self._match_rhs(production.rhs(), span, constituents)
                                        
            for childlist in childlists:
                rv.append( (production, childlist) )
        return rv

    def _match_rhs(self, rhs, span, constituents):
        """
        @return: a set of all the lists of children that cover C{span}
            and that match C{rhs}.
        @rtype: C{list} of (C{list} of C{ProbabilisticTreeToken} or
            C{Token}) 

        @type rhs: C{list} of C{Nonterminal} or (any)
        @param rhs: The list specifying what kinds of children need to
            cover C{span}.  Each nonterminal in C{rhs} specifies
            that the corresponding child should be a tree whose node
            value is that nonterminal's symbol.  Each terminal in C{rhs}
            specifies that the corresponding child should be a token
            whose type is that terminal.
        @type span: C{(int, int)}
        @param span: The section of the text for which we are
            trying to find child lists.  The span is specified as a
            pair of integers, where the first integer is the index of
            the first token that should be covered by the child list;
            and the second integer is the index of the first token
            that should not be covered by the child list.
        @type constituents: C{dictionary} from
            C{(int,int,Nonterminal)} to (C{ProbabilisticToken} or
            C{ProbabilisticTreeToken}).
        @param constituents: The most likely constituents table.  This
            table records the most probable tree representation for
            any given span and node value.  See the module
            documentation for more information.
        """
        (start, end) = span
        
        # Base case
        if start >= end and rhs == (): return [[]]
        if start >= end or rhs == (): return []

        # Find everything that matches the 1st symbol of the RHS
        childlists = []
        for split in range(start, end+1):
            l=constituents.get((start,split,rhs[0]))
            if l is not None:
                rights = self._match_rhs(rhs[1:], (split,end), constituents)
                childlists += [[l]+r for r in rights]

        return childlists

    def _trace_production(self, production, tree, text, p):
        """
        Print trace output indicating that a given production has been
        applied at a given location.

        @param production: The production that has been applied
        @type production: C{PCFGProduction}
        @type text: C{list} of C{Token}
        @param text: The text we are parsing.  This is only used for
            trace output.  
        @param p: The probability of the tree produced by the
            production.  
        @type p: C{float}
        @rtype: C{None}
        """
        start = tree.loc().start()
        
        str = '|' + '. '*(start-text[0].loc().start())
        
        pos = start
        for child in tree.children():
            if pos == start: str += '[='
            else: str += '|='
            str += ('=='*(child.loc().end()-pos-1))
            pos = child.loc().end()
        str = str + ']'

        str += ' .'*(text[-1].loc().end()-pos) + '| '
        str += '%s' % production
        if self._trace > 2: str = '%-40s %12.10f ' % (str, p)

        print str

    def _trace_lexical_insertion(self, tok, text):
        start = tok.loc().start()
        str = '   Insert: |' + '. '*(start-text[0].loc().start())
        str += '[=]' + ' .'*(text[-1].loc().end()-start-1) + '| '
        str += '%s' % (tok.type(),)
        print str

    def __repr__(self):
        return '<ViterbiPCFGParser for %r>' % self._grammar

##//////////////////////////////////////////////////////
##  Bottom-Up PCFG Chart Parser
##//////////////////////////////////////////////////////

class BottomUpPCFGChartParser(ProbabilisticParserI):
    """
    An abstract bottom-up parser for C{PCFG}s that uses a C{Chart} to
    record partial results.  C{BottomUpPCFGChartParser} maintains a
    queue of edges that can be added to the chart.  This queue is
    initialized with edges for each token in the text that is being
    parsed.  C{BottomUpPCFGChartParser} inserts these edges into to the
    chart one at a time, starting with the most likely edges, and
    proceeding to less likely edges.  For each edge that is added to
    the chart, it may become possible to insert additional edges into
    the chart; these are added to the queue.  This process continues
    until enough complete parses have been generated, or until the
    queue is empty.

    The sorting order for the queue is not specified by
    C{BottomUpPCFGChartParser}.  Different sorting orders will result
    in different search strategies.  The sorting order for the queue
    is defined by the method C{sort_queue}; subclasses are required
    to provide a definition for this method.

    @type _grammar: C{PCFG}
    @ivar _grammar: The grammar used to parse sentences.
    @type _trace: C{int}
    @ivar _trace: The level of tracing output that should be generated
        when parsing a text.
    """
    def __init__(self, grammar, trace=0):
        """
        Create a new C{BottomUpPCFGChartParser}, that uses C{grammar}
        to parse texts.

        @type grammar: C{PCFG}
        @param grammar: The grammar used to parse texts.
        @type trace: C{int}
        @param trace: The level of tracing that should be used when
            parsing a text.  C{0} will generate no tracing output;
            and higher numbers will produce more verbose tracing
            output.
        """
        assert _chktype(1, grammar, PCFG)
        assert _chktype(2, trace, types.IntType)
        self._grammar = grammar
        self._trace = trace

        # Create a hash to efficiently look up the productions that
        # start with a given nonterminal.
        self._production_by_rhs0 = {}
        for prod in grammar.productions():
            rhs0 = prod.rhs()[0]
            if not self._production_by_rhs0.has_key(rhs0):
                self._production_by_rhs0[rhs0] = []
            self._production_by_rhs0[rhs0].append(prod)

    def trace(self, trace=2):
        """
        Set the level of tracing output that should be generated when
        parsing a text.

        @type trace: C{int}
        @param trace: The trace level.  A trace level of C{0} will
            generate no tracing output; and higher trace levels will
            produce more verbose tracing output.
        @rtype: C{None}
        """
        assert _chktype(1, trace, types.IntType)
        self._trace = trace

    def parse(self, text):
        # Inherit docs from ProbabilisticParserI; and delegate to parse_n
        assert _chktype(1, text, [Token], (Token))
        final_trees = self.parse_n(text, 1)
        if len(final_trees) == 0: return None
        else: return final_trees[0]
        
    def parse_dist(self, text):
        # Inherit docs from ProbabilisticParserI; and delegate to parse_n
        prob_dict = {}
        for parse in self.parse_n(text):
            prob_dict[parse] = parse.p()
        return DictionaryProbDist(prob_dict)

    def parse_n(self, text, n=None):
        # Inherit docs from ProbabilisticParserI
        assert _chktype(1, text, [Token], (Token))
        assert _chktype(2, n, types.IntType, types.NoneType)
        
        loc = Location(text[0].loc().start(), text[-1].loc().end(),
                       unit=text[0].loc().unit(),
                       source=text[0].loc().source())
        chart = FRChart(loc)

        if self._trace: print 'Initializing the queue with token edges...'
        edge_queue = self._init_edge_queue(text, chart)

        # Note that we're adding edges to the end of the queue as we
        # process it.  But we'll eventually get to the end of the
        # queue, since we ignore any edges that are already in the
        # chart (so we can add each edge at most once).
        if self._trace: print 'Processing the edge queue...'
        parses = []
        while edge_queue:
            # Handle the most likely edge
            self.sort_queue(edge_queue, chart)
            edge = edge_queue.pop()
            self._add_edge(edge, chart, edge_queue)
            if self._trace > 1:
                print '  %-60s %10.12f' % (chart.pp_edge(edge,2),
                                           edge.structure().prob())

            # Check if the edge is a complete parse.
            if (edge.loc() == chart.loc() and
                edge.lhs() == self._grammar.start()):
                parses.append(edge.structure())
                if len(parses) == n: break

        if self._trace:
            print 'Found %d parses with %d edges' % (len(parses), len(chart))
            if edge_queue: print '  (Edge queue not empty)'

        # Sort the parses by decreasing likelihood, and return them
        parses.sort(lambda p1,p2: -cmp(p1.prob(),p2.prob()))
        return parses

    def sort_queue(self, queue, chart):
        """
        Sort the given queue of C{Edge}s, placing the edge that should
        be tried first at the beginning of the queue.  This method
        will be called after each C{Edge} is added to the queue.

        @param queue: The queue of C{Edge}s to sort.  Each edge in
            this queue is an edge that could be added to the chart by
            the fundamental rule; but that has not yet been added.
        @type queue: C{list} of C{Edge}
        @param chart: The chart being used to parse the text.  This
            chart can be used to provide extra information for sorting
            the queue.
        @type chart: C{Chart}
        @rtype: C{None}
        """
        raise AssertionError, "BottomUpPCFGChartParser is an abstract class"

    def _init_edge_queue(self, text, chart):
        """
        Initialize the edge queue with an edge for each token in the
        text.  For each token M{tok} with type M{typ} and location
        M{loc}, return a new edge with production
        C{[Production: M{typ} -> ]}, location M{loc}, tree
        C{tok}, and dot position 0.

        @param text: The text to be parsed.  This text consists
            of a list of C{Tokens}, ordered by their C{Location}.
        @type text: C{list} of C{Token}
        @type chart: C{Chart}
        @param chart: The chart being used to parse C{text}.
        @return: The initial edge queue, containing an edge for each
            token in C{text}.
        @rtype: C{list} of C{Edge}
        """
        edge_queue = []
        for tok in text:
            probtok = ProbabilisticToken(1, tok.type(), tok.loc())
            edge_queue.append(TokenEdge(probtok))

        # This is purely aesthetic: put the first word at the
        # beginning of the queue, not the last word.
        edge_queue.reverse()
        
        return edge_queue

    def _add_edge(self, edge, chart, edge_queue):
        """
        Insert C{edge} into C{chart}, and add any new edges that can
        be generated with C{edge} in the chart to C{edge_queue}.

        @type edge: C{Edge}
        @param edge: The edge that should be inserted into C{chart}.
        @type chart: C{Chart}
        @param chart: The chart being used to parse C{text}.
        @type edge_queue: C{list} of C{Edge}
        @param edge_queue: A queue of edges that can be added to the
            chart.  C{_add_edge} will add any new edges that can be
            generated with C{edge} in the chart to the end of
            C{edge_queue}. 
        @rtype: C{None}
        """
        # If the edge is already in the chart, then do nothing.
        if not chart.insert(edge): return
        
        # If this is a token edge, or if it's a production edge with a
        # dot in the zero position, then apply the bottom-up
        # initialization rule.
        if ((isinstance(edge, TokenEdge) or edge.dotpos() == 0) and not
            (isinstance(edge, ProductionEdge) and len(edge.rhs()) > 0 and
             edge.lhs() == edge.rhs()[0])):
            edge_queue += [self._self_loop_edge(production, edge.loc())
                           for production in
                           self._production_by_rhs0.get(edge.lhs(), [])]

        # Find any new places where we can apply the fundamental
        # rule. 
        if edge.complete():
            edge_queue += [self._fr(e2,edge) for e2 in chart.fr_with(edge)]
        else:
            edge_queue += [self._fr(edge,e2) for e2 in chart.fr_with(edge)]

    def _self_loop_edge(self, production, loc):
        """
        @return: a zero-width edge formed from C{production}, starting
            at the beginning of C{loc}.  The new edge's production is
            C{production}, and its dot position is C{0}.  The new
            edge's tree has a node value equal to C{production}'s left
            hand side, and no children.  Its probability is equal to
            C{production}'s probability.
        @rtype: C{Edge}

        @type production: C{PCFGProduction}
        @param production: The production to base the self-loop edge
            on.  The new edge's production and tree are based
            on this production.
        @type loc: C{Location}
        @param loc: A location whose start will be the beginning of
            the edge's (zero-width) location.
        """
        node = production.lhs().symbol()
        tree = ProbabilisticTreeToken(production.prob(), node)
        return ProductionEdge(production, tree, loc.start_loc())

    def _fr(self, e1, e2):
        """
        @return: the edge formed by combine edges C{e1} and C{e2}
            using the fundamental rule.  C{e1} should be an incomplete
            edge, and the next element following its dot should be
            C{e2}'s left-hand side.  C{e2} should be a complete edge
            that immediately follows C{e1}.

            The new edge's left hand side is equal to C{e1}'s.  It's
            right hand side is equal to C{e1}'s, with the dot shifted
            right one element.  Its tree is formed by adding C{e2}'s
            tree as a child to C{e1}'s tree, and combining their
            probabilities.
            
        @rtype: C{Edge}
        @type e1: C{Edge}
        @param e1: The incomplete edge that should be combined with
            C{e2} by the fundamental rule.
        @type e2: C{Edge}
        @param e2: The complete edge that should be combined with 
            C{e1} by the fundamental rule.
        """
        p = e1.structure().prob() * e2.structure().prob()
        children = e1.structure().children() + (e2.structure(),)
        tree = ProbabilisticTreeToken(p, e1.structure().node(), *children)
        loc = e1.loc().union(e2.loc())
        return ProductionEdge(e1.prod(), tree, loc, e1.dotpos()+1)

    def __repr__(self):
        # Use __class__.__name__ to get the name of the class, since
        # this method will be used by subclasses.
        return '<%s for %r>' % (self.__class__.__name__, self._grammar)


class InsidePCFGParser(BottomUpPCFGChartParser):
    """
    A bottom-up parser for C{PCFG}s that tries edges in descending
    order of the inside probabilities of their trees.  The X{inside
    probability} of a tree is simply the
    probability of the entire tree, ignoring its context.  In
    particular, the inside probability of a tree generated by
    production M{p} with children M{c[1]}, M{c[2]}, ..., M{c[n]} is
    P(M{p})*P(M{c[1]})*P(M{c[2]})*M{...}*P(M{c[n]}); and the inside
    probability of a token is 1 if it is present in the text, and 0 if
    it is absent.

    This sorting order results in a type of lowest-cost-first search
    strategy.
    """
    # Inherit constructor.
    def sort_queue(self, queue, chart):
        """
        Sort the given queue of edges, in descending order of the
        inside probabilities of the edges' trees.

        @param queue: The queue of C{Edge}s to sort.  Each edge in
            this queue is an edge that could be added to the chart by
            the fundamental rule; but that has not yet been added.
        @type queue: C{list} of C{Edge}
        @param chart: The chart being used to parse the text.  This
            chart can be used to provide extra information for sorting
            the queue.
        @type chart: C{Chart}
        @rtype: C{None}
        """
        queue.sort(lambda e1,e2:cmp(e1.structure().prob(),
                                    e2.structure().prob()))

# Eventually, this will become some sort of inside-outside parser:
# class InsideOutsideParser(BottomUpPCFGChartParser):
#     def __init__(self, grammar, trace=0):
#         # Inherit docs.
#         BottomUpPCFGChartParser.__init__(self, grammar, trace)
#
#         # Find the best path from S to each nonterminal
#         bestp = {}
#         for production in grammar.productions(): bestp[production.lhs()]=0
#         bestp[grammar.start()] = 1.0
#
#         for i in range(len(grammar.productions())):
#             for production in grammar.productions():
#                 lhs = production.lhs()
#                 for elt in production.rhs():
#                     bestp[elt] = max(bestp[lhs]*production.prob(),
#                                      bestp.get(elt,0))
#
#         self._bestp = bestp
#         for (k,v) in self._bestp.items(): print k,v
#
#     def _cmp(self, e1, e2):
#         return cmp(e1.structure().prob()*self._bestp[e1.lhs()],
#                    e2.structure().prob()*self._bestp[e2.lhs()])
#        
#     def sort_queue(self, queue, chart):
#         queue.sort(self._cmp)

import random
class RandomPCFGParser(BottomUpPCFGChartParser):
    """
    A bottom-up parser for C{PCFG}s that tries edges in random order.
    This sorting order results in a random search strategy.
    """
    # Inherit constructor
    def sort_queue(self, queue, chart):
        i = random.randint(0, len(queue)-1)
        (queue[-1], queue[i]) = (queue[i], queue[-1])

class UnsortedPCFGParser(BottomUpPCFGChartParser):
    """
    A bottom-up parser for C{PCFG}s that tries edges in whatever order..
    """
    # Inherit constructor
    def sort_queue(self, queue, chart): return

class LongestPCFGParser(BottomUpPCFGChartParser):
    """
    A bottom-up parser for C{PCFG}s that tries longer edges before
    shorter ones.  This sorting order results in a type of best-first
    search strategy.
    """
    # Inherit constructor
    def sort_queue(self, queue, chart):
        queue.sort(lambda e1,e2: cmp(len(e1.loc()), len(e2.loc())))

class BeamPCFGParser(BottomUpPCFGChartParser):
    """
    A bottom-up parser for C{PCFG}s that limits the number of edges in
    its edge queue.
    """
    def __init__(self, beam_size, grammar, trace=0):
        """
        Create a new C{BottomUpPCFGChartParser}, that uses C{grammar}
        to parse texts.

        @type beam_size: C{int}
        @param beam_size: The maximum length for the parser's edge queue.
        @type grammar: C{PCFG}
        @param grammar: The grammar used to parse texts.
        @type trace: C{int}
        @param trace: The level of tracing that should be used when
            parsing a text.  C{0} will generate no tracing output;
            and higher numbers will produce more verbose tracing
            output.
        """
        assert _chktype(1, beam_size, types.IntType)
        assert _chktype(2, grammar, PCFG)
        assert _chktype(3, trace, types.IntType)
        BottomUpPCFGChartParser.__init__(self, grammar, trace)
        self._beam_size = beam_size
        
    def sort_queue(self, queue, chart):
        queue.sort(lambda e1,e2:cmp(e1.structure().prob(),
                                    e2.structure().prob()))
        if len(queue) > self._beam_size:
            split = len(queue)-self._beam_size
            if self._trace > 2:
                for edge in queue[:split]:
                    print '  %-60s [DISCARDED]' % chart.pp_edge(edge,2)
            queue[:] = queue[split:]

##//////////////////////////////////////////////////////
##  Test Code
##//////////////////////////////////////////////////////

def demo():
    """
    A demonstration of the probabilistic parsers.  The user is
    prompted to select which demo to run, and how many parses should
    be found; and then each parser is run on the same demo, and a
    summary of the results are displayed.
    """
    import sys, time
    from nltk.tokenizer import WSTokenizer
    
    nonterminals = 'S VP NP PP P N Name V Det'
    (S, VP, NP, PP, P, N, Name, V, Det) = [Nonterminal(s)
                                           for s in nonterminals.split()]
    lexicon = [PCFGProduction(0.21, V, 'saw'),
               PCFGProduction(0.51, V, 'ate'),
               PCFGProduction(0.28, V, 'ran'),
               PCFGProduction(0.11, N, 'boy'),
               PCFGProduction(0.12, N, 'cookie'),
               PCFGProduction(0.13, N, 'table'),
               PCFGProduction(0.14, N, 'telescope'),
               PCFGProduction(0.50, N, 'hill'),
               PCFGProduction(0.52, Name, 'Jack'),
               PCFGProduction(0.48, Name, 'Bob'),
               PCFGProduction(0.61, P, 'with'),
               PCFGProduction(0.39, P, 'under'),
               PCFGProduction(0.41, Det, 'the'),
               PCFGProduction(0.31, Det, 'a'),
               PCFGProduction(0.28, Det, 'my'),
               ]

    grammar_productions2 = lexicon + [
        PCFGProduction(1.00, S, NP, VP),
        PCFGProduction(0.59, VP, V, NP),
        PCFGProduction(0.40, VP, V),
        PCFGProduction(0.01, VP, VP, PP),
        PCFGProduction(0.41, NP, Det, N),
        PCFGProduction(0.28, NP, Name),
        PCFGProduction(0.31, NP, NP, PP),
        PCFGProduction(1.00, PP, P, NP),
               ]

    grammar_productions1 = [
        PCFGProduction(0.5, NP, Det, N), PCFGProduction(0.25, NP, NP, PP),
        PCFGProduction(0.1, NP, 'John'), PCFGProduction(0.15, NP, 'I'), 
        PCFGProduction(0.8, Det, 'the'), PCFGProduction(0.2, Det, 'my'),
        PCFGProduction(0.5, N, 'dog'),   PCFGProduction(0.5, N, 'cookie'),

        PCFGProduction(0.1, VP, VP, PP), PCFGProduction(0.7, VP, V, NP),
        PCFGProduction(0.2, VP, V),
        
        PCFGProduction(0.35, V, 'ate'),  PCFGProduction(0.65, V, 'saw'),

        PCFGProduction(1.0, S, NP, VP),  PCFGProduction(1.0, PP, P, NP),
        PCFGProduction(0.61, P, 'with'), PCFGProduction(0.39, P, 'under')]

    # Default to (2)
    demos = [('I saw John with my cookie', PCFG(S, grammar_productions1)),
             ('the boy saw Jack with Bob under the table with a telescope',
              PCFG(S, grammar_productions2))]

    print
    for i in range(len(demos)):
        print '%3s: %s' % (i+1, demos[i][0])
        print '     %r' % demos[i][1]
        print
    
    print 'Which demo (%d-%d)? ' % (1, len(demos)),
    try:
        snum = int(sys.stdin.readline().strip())-1
        s, pcfg = demos[snum]
    except:
        print 'Bad sentence number'
        return
    
    text = WSTokenizer().tokenize(s)
    
    parsers = [ViterbiPCFGParser(pcfg), InsidePCFGParser(pcfg), 
               RandomPCFGParser(pcfg), UnsortedPCFGParser(pcfg),
               LongestPCFGParser(pcfg),
               BeamPCFGParser(len(text)+1, pcfg)]

    print '\nNumber of parses to find (1+): ',
    try:
        max_parses = max(1, int(sys.stdin.readline().strip()))
    except:
        print 'Bad number of parses; finding all parses'
        max_parses = None
        
#     # Default to (all parsers)
#     print '\nChoose a parser:'
#     for i in range(len(parsers)):
#         print '%3d: %s' % (i+1, parsers[i].__class__.__name__)
#     try:
#         print '%3d: %s' % (len(parsers)+1, '(all parsers)')
#         print '=> ',
#         pnum = int(sys.stdin.readline().strip())-1
#         if pnum != len(parsers):
#             parsers = [parsers[pnum]]
#     except:
#         print 'Bad parser number'
#         return

    # Run the parser(s)
    times = []
    average_p = []
    num_parses = []
    all_parses = {}
    for parser in parsers:
        print '\ns: %s\nparser: %s\ngrammar: %s' % (s,parser,pcfg)
        parser.trace(3)
        t = time.time()
        parses = parser.parse_n(text, max_parses)
        times.append(time.time()-t)
        if parses: p = reduce(lambda a,b:a+b.prob(), parses, 0)/len(parses)
        else: p = 0
        average_p.append(p)
        num_parses.append(len(parses))
        for p in parses: all_parses[p] = 1

    # Print some summary statistics
    print
    print '       Parser      | Time (secs)   # Parses   Average P(parse)'
    print '-------------------+------------------------------------------'

    for i in range(len(parsers)):
        print '%18s |%11.4f%11d%19.14f' % (parsers[i].__class__.__name__,
                                         times[i],num_parses[i],average_p[i])

    parses = all_parses.keys()
    if parses: p = reduce(lambda a,b:a+b.prob(), parses, 0)/len(parses)
    else: p = 0
    print '-------------------+------------------------------------------'
    print '%18s |%11s%11d%19.14f' % ('(All Parses)', 'n/a', len(parses), p)

    print
    print 'Draw parses (y/n)? ',
    if sys.stdin.readline().strip().lower().startswith('y'):
        import nltk.draw.tree
        nltk.draw.tree.draw_trees(*parses)
    print
    print 'Print parses (y/n)? ',
    if sys.stdin.readline().strip().lower().startswith('y'):
        for parse in parses:
            print parse

if __name__ == '__main__':
    demo()
