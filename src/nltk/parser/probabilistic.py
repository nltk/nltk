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
structures that represent the internal organization of a text.  The
probabilistic parser module defines two probablistic parsers,
C{ViterbiPCFGParser} and C{BottomUpPCFGChartParser}.

C{ViterbiPCFGParser} is a C{PCFG} parser based on a Viterbi-style
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

from nltk import TaskI, PropertyIndirectionMixIn
from nltk.parser import ParserI, AbstractParser
from nltk.cfg import PCFG, PCFGProduction, Nonterminal, nonterminals
from nltk.token import Token, CharSpanLocation #ProbabilisticToken, Token
from nltk.tree import ProbabilisticTree
from nltk.parser.chart import Chart, LeafEdge, TreeEdge, AbstractChartRule
from nltk.chktype import chktype as _chktype
from nltk.tree import Tree
import types

##//////////////////////////////////////////////////////
##  Viterbi PCFG Parser
##//////////////////////////////////////////////////////

class ViterbiPCFGParser(AbstractParser):
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
    def __init__(self, grammar, trace=0, **property_names):
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
        AbstractParser.__init__(self, **property_names)

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

    def get_parse_list(self, token):
        # Inherit docs from ParserI
        assert _chktype(1, token, Token)
        SUBTOKENS = self.property('SUBTOKENS')
        LEAF = self.property('LEAF')

        subtokens = token[SUBTOKENS]

        # The most likely consituant table.  This table specifies the
        # most likely constituent for a given span and type.
        # Constituents can be either Trees or Tokens.  For
        # Trees, the "type" is the Nonterminal for the tree's
        # root node value.  For Tokens, the "type" is the token's
        # type.  The table is stored as a dictionary, since it is
        # sparse.
        constituents = {}
        
        # Initialize the constituents dictionary with the words from
        # the text.
        if self._trace: print ('Inserting tokens into the most likely'+
                               ' constituents table...')
        for index in range(len(subtokens)):
            tok = subtokens[index]
            probtok = tok.copy()
            constituents[index,index+1,tok[LEAF]] = probtok
            if self._trace > 1:
                self._trace_lexical_insertion(tok, subtokens)

        # Consider each span of length 1, 2, ..., n; and add any trees
        # that might cover that span to the constituents dictionary.
        for length in range(1, len(subtokens)+1):
            if self._trace:
                if self._trace > 1: print
                print ('Finding the most likely constituents'+
                       ' spanning %d text elements...' % length)
            #print constituents
            for start in range(len(subtokens)-length+1):
                span = (start, start+length)
                self._add_constituents_spanning(span, constituents,
                                                subtokens)

        # Find all trees that span the entire text & have the right cat
        trees = [constituents.get((0, len(subtokens),
                                   self._grammar.start()), [])]

        # Sort the trees, and return the requested number of them.
        trees.sort(lambda t1,t2: cmp(t2.prob(), t1.prob()))
        return trees

    def _add_constituents_spanning(self, span, constituents, subtokens):
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
            C{ProbabilisticTree}).
        @param constituents: The most likely constituents table.  This
            table records the most probable tree representation for
            any given span and node value.  In particular,
            C{constituents(M{s},M{e},M{nv})} is the most likely
            C{ProbabilisticTree} that covers C{M{text}[M{s}:M{e}]}
            and has a node value C{M{nv}.symbol()}, where C{M{text}}
            is the text that we are parsing.  When
            C{_add_constituents_spanning} is called, C{constituents}
            should contain all possible constituents that are shorter
            than C{span}.
            
        @type subtokens: C{list} of C{Token}
        @param subtokens: The text we are parsing.  This is only used for
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
            # ProbabilisticTree whose probability is the product
            # of the childrens' probabilities and the production's
            # probability.
            for (production, children) in instantiations:
                subtrees = [c for c in children if isinstance(c, Tree)]
                p = reduce(lambda pr,t:pr*t.prob(),
                           subtrees, production.prob())
                node = production.lhs().symbol()
                tree = ProbabilisticTree(node, children, prob=p)

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
                        self._trace_production(production, tree, subtokens, p)
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
            (C{ProbabilisticTree} or C{Token})

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
            C{ProbabilisticTree}).
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
        @rtype: C{list} of (C{list} of C{ProbabilisticTree} or
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
            C{ProbabilisticTree}).
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

    def _span(self, tree):
        if isinstance(tree, Tree):
            leaves = tree.leaves()
            return [leaves[0]['LOC'].start(), leaves[-1]['LOC'].end()]
        else:
            return tree['LOC'].start(), tree['LOC'].end()

    def _trace_production(self, production, tree, subtokens, p):
        """
        Print trace output indicating that a given production has been
        applied at a given location.

        @param production: The production that has been applied
        @type production: C{PCFGProduction}
        @type subtokens: C{list} of C{Token}
        @param subtokens: The text we are parsing.  This is only used for
            trace output.  
        @param p: The probability of the tree produced by the
            production.  
        @type p: C{float}
        @rtype: C{None}
        """
        start = self._span(tree)[0]
        
        str = '|' + '.'*(start-self._span(subtokens[0])[0])
        
        pos = start
        for child in tree:
            if pos == start: str += '['
            else: str += '|'
            str += ('='*(self._span(child)[1]-pos-1))
            pos = self._span(child)[1]
        str = str + ']'

        str += '.'*(self._span(subtokens[-1])[1]-pos) + '| '
        str += '%s' % production
        if self._trace > 2: str = '%-40s %12.10f ' % (str, p)

        print str

    def _trace_lexical_insertion(self, tok, subtokens):
        LEAF = self.property('LEAF')
        start = self._span(tok)[0]
        str = '   Insert: |' + '.'*(start-self._span(subtokens[0])[0])
        s,e =self._span(tok)
        str += '[' + '='*(e-s-1) + ']'
        str += '.'*(self._span(subtokens[-1])[1]-start-1-(e-s-1))
        str += '| '
        str += '%s' % (tok[LEAF],)
        print str

    def __repr__(self):
        return '<ViterbiPCFGParser for %r>' % self._grammar

##//////////////////////////////////////////////////////
##  Bottom-Up PCFG Chart Parser
##//////////////////////////////////////////////////////

# [XX] This might not be implemented quite right -- it would be better
# to associate probabilities with child pointer lists.

# Probabilistic edges
class ProbabilisticLeafEdge(LeafEdge):
    def prob(self): return 1.0

class ProbabilisticTreeEdge(TreeEdge):
    def __init__(self, prob, *args, **kwargs):
        self._prob = prob
        TreeEdge.__init__(self, *args, **kwargs)
    def prob(self): return self._prob
    def __cmp__(self, other):
        if self._prob != other.prob(): return -1
        return TreeEdge.__cmp__(self, other)
    def from_production(production, index, p):
        return ProbabilisticTreeEdge(p, (index, index), production.lhs(),
                                     production.rhs(), 0)
    from_production = staticmethod(from_production)

# Rules using probabilistic edges
class BottomUpInitRule(AbstractChartRule):
    NUM_EDGES=0
    def apply_iter(self, chart, grammar):
        for index in range(chart.num_leaves()):
            new_edge = ProbabilisticLeafEdge(chart.leaf(index), index)
            if chart.insert(new_edge, ()):
                yield new_edge

class BottomUpPredictRule(AbstractChartRule):
    NUM_EDGES=1
    def apply_iter(self, chart, grammar, edge):
        if edge.is_incomplete(): return
        for prod in grammar.productions():
            if edge.lhs() == prod.rhs()[0]:
                new_edge = ProbabilisticTreeEdge.from_production(prod, edge.start(), prod.prob())
                if chart.insert(new_edge, ()):
                    yield new_edge
                    
class FundamentalRule(AbstractChartRule):
    NUM_EDGES=2
    def apply_iter(self, chart, grammar, left_edge, right_edge):
        # Make sure the rule is applicable.
        if not (left_edge.end() == right_edge.start() and
                left_edge.next() == right_edge.lhs() and
                left_edge.is_incomplete() and right_edge.is_complete()):
            return

        # Construct the new edge.
        p = left_edge.prob() * right_edge.prob()
        new_edge = ProbabilisticTreeEdge(p,
                            span=(left_edge.start(), right_edge.end()),
                            lhs=left_edge.lhs(), rhs=left_edge.rhs(),
                            dot=left_edge.dot()+1)

        # Add it to the chart, with appropraite child pointers.
        changed_chart = False
        for cpl1 in chart.child_pointer_lists(left_edge):
            if chart.insert(new_edge, cpl1+(right_edge,)):
                changed_chart = True

        # If we changed the chart, then generate the edge.
        if changed_chart: yield new_edge

class SingleEdgeFundamentalRule(AbstractChartRule):
    NUM_EDGES=1

    _fundamental_rule = FundamentalRule()
    
    def apply_iter(self, chart, grammar, edge1):
        fr = self._fundamental_rule
        if edge1.is_incomplete():
            # edge1 = left_edge; edge2 = right_edge
            for edge2 in chart.select(start=edge1.end(), is_complete=True,
                                     lhs=edge1.next()):
                for new_edge in fr.apply_iter(chart, grammar, edge1, edge2):
                    yield new_edge
        else:
            # edge2 = left_edge; edge1 = right_edge
            for edge2 in chart.select(end=edge1.start(), is_complete=False,
                                     next=edge1.lhs()):
                for new_edge in fr.apply_iter(chart, grammar, edge2, edge1):
                    yield new_edge

    def __str__(self): return 'Fundamental Rule'
    
class BottomUpPCFGChartParser(AbstractParser):
    """
    An abstract bottom-up parser for C{PCFG}s that uses a C{Chart} to
    record partial results.  C{BottomUpPCFGChartParser} maintains a
    queue of edges that can be added to the chart.  This queue is
    initialized with edges for each token in the text that is being
    parsed.  C{BottomUpPCFGChartParser} inserts these edges into the
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
    def __init__(self, grammar, trace=0, **property_names):
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
        AbstractParser.__init__(self, **property_names)

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
        self._trace = trace
        
    def get_parse_list(self, token):
        chart = Chart(token, **self.property_names())
        grammar = self._grammar

        # Chart parser rules.
        bu_init = BottomUpInitRule()
        bu = BottomUpPredictRule()
        fr = SingleEdgeFundamentalRule()

        # Our queue!
        queue = []
        
        # Initialize the chart.
        for e in bu_init.apply_iter(chart, grammar):
            if self._trace>1: chart.pp_edge(e,width=2)
            queue.append(e)

        while len(queue) > 0:
            # Re-sort the queue.
            self.sort_queue(queue, chart)

            # Get the best edge.
            edge = queue.pop()
            if self._trace>0:
                print '  %-50s prob=%s' % (chart.pp_edge(edge,width=2),
                                           edge.prob())
            
            # Apply BU & FR to it.
            queue.extend(bu.apply(chart, grammar, edge))
            queue.extend(fr.apply(chart, grammar, edge))

        # Get a list of complete parses.
        parses = chart.parses(grammar.start(), ProbabilisticTree)

        # Assign probabilities to the trees.
        prod_probs = {}
        for prod in grammar.productions():
            prod_probs[prod.lhs(), prod.rhs()] = prod.prob()
        for parse in parses:
            self._setprob(parse, prod_probs)

        # Sort by probability
        parses.sort(lambda a,b: cmp(b.prob(), a.prob()))
        
        return parses

    def _setprob(self, tree, prod_probs):
        LEAF = self.property('LEAF')
        if tree.prob() is not None: return
        
        # Get the prob of the CFG production.
        lhs = Nonterminal(tree.node)
        rhs = []
        for child in tree:
            if isinstance(child, Tree):
                rhs.append(Nonterminal(child.node))
            else:
                rhs.append(child[LEAF])
        prob = prod_probs[lhs, tuple(rhs)]
        
        # Get the probs of children.
        for child in tree:
            if isinstance(child, Tree):
                self._setprob(child, prod_probs)
                prob *= child.prob()

        tree.set_prob(prob)
        
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
        queue.sort(lambda e1,e2:cmp(e1.prob(), e2.prob()))

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
#         return cmp(e1.structure()[PROB]*self._bestp[e1.lhs()],
#                    e2.structure()[PROB]*self._bestp[e2.lhs()])
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
        queue.sort(lambda e1,e2: cmp(e1.length(), e2.length()))

class BeamPCFGParser(BottomUpPCFGChartParser):
    """
    A bottom-up parser for C{PCFG}s that limits the number of edges in
    its edge queue.
    """
    def __init__(self, beam_size, grammar, trace=0, **property_names):
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
        BottomUpPCFGChartParser.__init__(self, grammar, trace,
                                         **property_names)
        self._beam_size = beam_size
        
    def sort_queue(self, queue, chart):
        queue.sort(lambda e1,e2:cmp(e1.prob(), e2.prob()))
        if len(queue) > self._beam_size:
            split = len(queue)-self._beam_size
            if self._trace > 2:
                for edge in queue[:split]:
                    print '  %-50s [DISCARDED]' % chart.pp_edge(edge,2)
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
    from nltk.tokenizer import WhitespaceTokenizer

    # Define some nonterminals
    S, VP, NP, PP = nonterminals('S, VP, NP, PP')
    V, N, P, Name, Det = nonterminals('V, N, P, Name, Det')

    # Define a PCFG
    grammar_productions1 = [
        PCFGProduction(NP, [Det, N], prob=0.5),
        PCFGProduction(NP, [NP, PP], prob=0.25),
        PCFGProduction(NP, ['John'], prob=0.1),
        PCFGProduction(NP, ['I'], prob=0.15), 
        PCFGProduction(Det, ['the'], prob=0.8),
        PCFGProduction(Det, ['my'], prob=0.2),
        PCFGProduction(N, ['dog'], prob=0.5),
        PCFGProduction(N, ['cookie'], prob=0.5),
        PCFGProduction(VP, [VP, PP], prob=0.1),
        PCFGProduction(VP, [V, NP], prob=0.7),
        PCFGProduction(VP, [V], prob=0.2),
        PCFGProduction(V, ['ate'], prob=0.35),
        PCFGProduction(V, ['saw'], prob=0.65),
        PCFGProduction(S, [NP, VP], prob=1.0),
        PCFGProduction(PP, [P, NP], prob=1.0),
        PCFGProduction(P, ['with'], prob=0.61),
        PCFGProduction(P, ['under'], prob=0.39)]
    pcfg1 = PCFG(S, grammar_productions1)

    # Define a second, more extensive, grammar.
    lexicon = [PCFGProduction(V, ['saw'], prob=0.21),
               PCFGProduction(V, ['ate'], prob=0.51),
               PCFGProduction(V, ['ran'], prob=0.28),
               PCFGProduction(N, ['boy'], prob=0.11),
               PCFGProduction(N, ['cookie'], prob=0.12),
               PCFGProduction(N, ['table'], prob=0.13),
               PCFGProduction(N, ['telescope'], prob=0.14),
               PCFGProduction(N, ['hill'], prob=0.50),
               PCFGProduction(Name, ['Jack'], prob=0.52),
               PCFGProduction(Name, ['Bob'], prob=0.48),
               PCFGProduction(P, ['with'], prob=0.61),
               PCFGProduction(P, ['under'], prob=0.39),
               PCFGProduction(Det, ['the'], prob=0.41),
               PCFGProduction(Det, ['a'], prob=0.31),
               PCFGProduction(Det, ['my'], prob=0.28),
               ]
    grammar_productions2 = lexicon + [
        PCFGProduction(S, [NP, VP], prob=1.00),
        PCFGProduction(VP, [V, NP], prob=0.59),
        PCFGProduction(VP, [V], prob=0.40),
        PCFGProduction(VP, [VP, PP], prob=0.01),
        PCFGProduction(NP, [Det, N], prob=0.41),
        PCFGProduction(NP, [Name], prob=0.28),
        PCFGProduction(NP, [NP, PP], prob=0.31),
        PCFGProduction(PP, [P, NP], prob=1.00),
        ]
    pcfg2 = PCFG(S, grammar_productions2)

    # Define two demos.  Each demo has a sentence and a grammar.
    demos = [('I saw John with my cookie', pcfg1),
             ('the boy saw Jack with Bob under the table with a telescope',
              pcfg2)]

    # Ask the user which demo they want to use.
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

    # Tokenize the sentence.
    token = Token(TEXT=s)
    WhitespaceTokenizer(SUBTOKENS='WORDS').tokenize(token, add_locs=True)

    # Define a list of parsers.  We'll use all parsers.
    parsers = [
        ViterbiPCFGParser(pcfg, LEAF='TEXT', SUBTOKENS='WORDS'),
        InsidePCFGParser(pcfg, LEAF='TEXT', SUBTOKENS='WORDS'), 
        RandomPCFGParser(pcfg, LEAF='TEXT', SUBTOKENS='WORDS'),
        UnsortedPCFGParser(pcfg, LEAF='TEXT', SUBTOKENS='WORDS'),
        LongestPCFGParser(pcfg, LEAF='TEXT', SUBTOKENS='WORDS'),
        BeamPCFGParser(len(token['WORDS'])+1, pcfg, LEAF='TEXT', SUBTOKENS='WORDS')
        ]

    # Run the parsers on the tokenized sentence.
    times = []
    average_p = []
    num_parses = []
    all_parses = {}
    for parser in parsers:
        print '\ns: %s\nparser: %s\ngrammar: %s' % (S,parser,pcfg)
        parser.trace(3)
        t = time.time()
        parses = parser.get_parse_list(token)
        times.append(time.time()-t)
        if parses: p = reduce(lambda a,b:a+b.prob(), parses, 0)/len(parses)
        else: p = 0
        average_p.append(p)
        num_parses.append(len(parses))
        for p in parses: all_parses[p.freeze(lambda t: t.freeze())] = 1

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

    # Ask the user if we should draw the parses.
    print
    print 'Draw parses (y/n)? ',
    if sys.stdin.readline().strip().lower().startswith('y'):
        import nltk.draw.tree
        print '  please wait...'
        nltk.draw.tree.draw_trees(*parses)

    # Ask the user if we should print the parses.
    print
    print 'Print parses (y/n)? ',
    if sys.stdin.readline().strip().lower().startswith('y'):
        for parse in parses:
            print parse

if __name__ == '__main__':
    demo()
