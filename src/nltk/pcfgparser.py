# Natural Language Toolkit: Probablistic CFG Parsers
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""

Parsers for probablistic context free grammars (C{PCFGs}).
C{nltk.pcfgparser} currently defines two basic types of
C{ProbablisticParser}: C{ViterbiPCFGParser} and
C{BottomUpPCFGChartParser}.

C{ViterbiPCFGParser} is a C{PCFG} parser based on a Viterbi-sytle
algorithm.  It uses dynamic programming to efficiently find the single
most likely parse for a given text.

C{BottomUpPCFGChartParser} is an abstract class that implements a
bottom-up chart parser for C{PCFG}s.  It maintains a queue of edges,
and adds them to the chart one at a time.  The ordering of this queue
is based on the probabilities of the edges' dotted rules, allowing the
parser to expand more likely edges before less likely ones.  Each
subclass implements a different queue ordering, producing different
search strategies.  Currently the following subclasses are defined:

  - C{InsidePCFGParser} searches edges using uniform-cost search.
  - C{RandomPCFGParser} searches edges using random search.
  
The following subclasses will be added in the near future:

  - C{OutsidePCFGParser} searches edges using best-first search.
  - C{InsideOutsidePCFGParser} searches edges using A* search.
"""

import nltk.chart; reload(nltk.chart)
from nltk.parser import *
from nltk.token import *
from nltk.cfg import *
from nltk.tree import *
from nltk.set import *
from nltk.chart import *

##//////////////////////////////////////////////////////
##  Viterbi PCFG Parser
##//////////////////////////////////////////////////////

class ViterbiPCFGParser(ProbablisticParserI):
    """
    A bottom-up C{PCFG} parser that uses dynamic programming to find
    the single most likely parse for a text.  C{ViterbiPCFGParser}
    parses texts by filling in a X{most likely constituant table}.
    This table records the most probable tree representation for any
    given span and node value.  In particular, it has an entry for
    every start index, end index, and node value, recording the most
    likely subtree that spans from the start index to the end index,
    and has the given node value.

    C{ViterbiPCFParser} fills in this table incrementally.  It starts
    by filling in all entries for constituants that span one element
    of text (i.e., entries where the end index is one greater than the
    start index).  After it has filled in all table entries for
    constituants that span one element of text, it fills in the
    entries for constitutants that span two elements of text.  It
    continues filling in the entries for constituants spanning larger
    and larger portions of the text, until the entire table has been
    filled.  Finally, it returns the table entry for a constituant
    spanning the entire text, whose node value is the grammar's start
    symbol.

    In order to find the most likely constituant with a given span and
    node value, C{ViterbiPCFGParser} considers all rules that could
    produce that node value.  For each rule, it finds all children
    that collectively cover the span and have the node values
    specified by the rule's right hand side.  If the probability of
    the tree formed by applying the rule to the children is greater
    than the probability of the current entry in the table, then the
    table is updated with this new tree.

    A pseudo-code description of the algorithm used by
    C{ViterbiPCFGParser} is:

      - Create an empty most likely constituant table, M{MLC}.
      - For M{width} in 1...len(M{text}):
        - For M{start} in 1...len(M{text})-M{width}:
          - For M{rule} in grammar:
            - For each sequence of subtrees [M{t[1]}, M{t[2]}, ..., 
              M{t[n]}] in M{MLC}, where M{t[i]}.node==M{rule}.rhs[i],
              and the sequence covers [M{start}:M{start}+M{width}]:
                - M{old_p} = M{MLC}[M{start}, M{start+width}, M{rule}.lhs]
                - M{new_p} = P(M{t[1]})*P(M{t[1]})*...*P(M{t[n]})*P(M{rule})
                - if M{new_p} > M{old_p}:
                  - M{new_tree} = Tree(M{rule}.lhs, M{t[1]}, M{t[2]},
                    ..., M{t[n]})
                  - M{MLC}[M{start}, M{start+width}, M{rule}.lhs]
                    = M{new_tree}
      - Return M{MLC}[0, len(M{text}), M{start_symbol}]
                
    @ivar _grammar: The grammar used to parse sentences.
    @type _grammar: C{PCFG}
    @ivar _trace: Whether to produce trace output; and if so, what
        verbosity of trace output to produce.
    @type _trace: C{int}
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
        self._grammar = grammar
        self._trace = trace

    def parse(self, text):
        # Inherit docs from ProbablisticParserI; and delegate to parse_n
        final_trees = self.parse_n(text, 1)
        if len(final_trees) == 0: return None
        else: return final_trees[0]
        
    def parse_n(self, text, n=None):
        # Inherit docs from ProbablisticParserI

        # The width of the text (used for trace output)
        w = len(text)
        
        # The most likely consituant table.  This table specifies the
        # most likely constituant for a given span and type.
        # Constituants can be either TreeTokens or Tokens.  For
        # TreeTokens, the "type" is the Nonterminal for the tree's
        # root node value.  For Tokens, the "type" is the token's
        # type.  The table is stored as a dictionary, since it is
        # sparse.
        constituants = {}
        
        # Initialize the constituants dictionary with the words from
        # the text.
        for index in range(len(text)):
            tok = text[index]
            probtok = ProbablisticToken(1, tok.type(), tok.loc())
            constituants[index,index+1,tok.type()] = probtok

        # Consider each span of length 1, 2, ..., n; and add any trees
        # that might cover that span to the constituants dictionary.
        for length in range(1, len(text)+1):
            if self._trace:
                if self._trace > 1: print
                print ('Finding most likely constituants'+
                       ' spanning %d text elements...' % length)
            #print constituants
            for start in range(len(text)-length+1):
                span = (start, start+length)
                self._add_constituants_spanning(span, constituants, w)

        # Find all trees that span the entire text & have the right cat
        trees = [constituants.get((0, len(text),
                                   self._grammar.start()), [])]

        # Sort the trees, and return the requested number of them.
        trees.sort(lambda t1,t2: cmp(t2.p(), t1.p()))
        if n is None: return trees
        else: return trees[:n]

    def _add_constituants_spanning(self, span, constituants, w):
        """
        Find any constituants that might cover C{span}, and add them
        to the most likely constituants table.

        @rtype: C{None}
        @type span: C{(int, int)}
        @param span: The section of the text for which we are
            trying to find possible constituants.  The span is
            specified as a pair of integers, where the first integer
            is the index of the first token that should be included in
            the constituant; and the second integer is the index of
            the first token that should not be included in the
            constituant.  I.e., the constituant should cover
            C{M{text}[span[0]:span[1]]}, where C{M{text}} is the text
            that we are parsing.

        @type constituants: C{dictionary} from
            C{(int,int,Nonterminal)} to (C{ProbablisticToken} or
            C{ProbablisticTreeToken}).
        @param constituants: The most likely constituants table.  This
            table records the most probable tree representation for
            any given span and node value.  In particular,
            C{constituants(M{s},M{e},M{nv})} is the most likely
            C{ProbablisticTreeToken} that covers C{M{text}[M{s}:M{e}]}
            and has a node value C{M{nv}.symbol()}, where C{M{text}}
            is the text that we are parsing.  When
            C{_add_constituants_spanning} is called, C{constituants}
            should contain all possible constituants that are shorter
            than C{span}.
            
        @type w: C{int}
        @param w: The width of the text.  This is used for trace output. 
        """
        # Since some of the grammar rules may be unary, we need to
        # repeatedly try all of the rules until none of them add any
        # new constituants.
        changed = 1
        while changed:
            changed = 0

            # Find all ways instantiations of the grammar rules that
            # cover the span.
            instantiations = self._find_instantiations(span, constituants)

            # For each rule instantiation, add a new
            # ProbablisticTreeToken whose probability is the product
            # of the childrens' probabilities and the rule's
            # probability.
            for (rule, children) in instantiations:
                p = reduce(lambda pr,t:pr*t.p(), children, rule.p())
                node = rule.lhs().symbol()
                tree = ProbablisticTreeToken(p, node, *children)

                # If it's new constituant, then add it to the
                # constituants dictionary.
                c = constituants.get((span[0], span[1], rule.lhs()), None)
                if c is None or c.p() < tree.p():
                    if self._trace > 1: self._trace_rule(span, rule, w, p)
                    constituants[span[0], span[1], rule.lhs()] = tree
                    changed = 1

    def _find_instantiations(self, span, constituants):
        """
        @return: a list of the rule instantiations that cover a given
            span of the text.  A X{rule instantiation} is a tuple
            containing a rule and a list of children, where the rule's
            right hand side matches the list of children; and the
            children cover C{span}.
        @rtype: C{list} of C{pair} of C{PCFG_Rule}, (C{list} of
            (C{ProbablisticTreeToken} or C{Token})

        @type span: C{(int, int)}
        @param span: The section of the text for which we are
            trying to find rule instantiations.  The span is
            specified as a pair of integers, where the first integer
            is the index of the first token that should be covered by
            the rule instantiation; and the second integer is the
            index of the first token that should not be covered by the
            rule instantiation.
        @type constituants: C{dictionary} from
            C{(int,int,Nonterminal)} to (C{ProbablisticToken} or
            C{ProbablisticTreeToken}).
        @param constituants: The most likely constituants table.  This
            table records the most probable tree representation for
            any given span and node value.  See the module
            documentation for more information.
        """
        rv = []
        for rule in self._grammar.rules():
            childrens = self._match_rhs(rule.rhs(), span, constituants)
                                        
            for children in childrens:
                rv.append( (rule, children) )
        return rv

    def _match_rhs(self, rhs, span, constituants):
        """
        @return: a set of all the lists of children that cover C{span}
            and that match C{rhs}.
        @rtype: C{list} of (C{list} of C{ProbablisticTreeToken} or
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
        @type constituants: C{dictionary} from
            C{(int,int,Nonterminal)} to (C{ProbablisticToken} or
            C{ProbablisticTreeToken}).
        @param constituants: The most likely constituants table.  This
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
            l=constituants.get((start,split,rhs[0]))
            if l is not None:
                rights = self._match_rhs(rhs[1:], (split,end), constituants)
                childlists += [[l]+r for r in rights]

        return childlists

    def _trace_rule(self, span, rule, w, p):
        """
        Print trace output indicating that a given rule has been
        applied at a given location.

        @param span: The span covered by the rule.
        @type span: C{(int, int)}
        @param rule: The rule that has been applied
        @type rule: C{PCFG_Rule}
        @param w: The number of tokens in the text being parsed.
        @type w: C{int}
        @param p: The probability of the tree produced by the rule.
        @type p: C{float}
        @rtype: C{None}
        """
        str = '  [' + ' '*span[0] + '.'*(span[1]-span[0])
        str += ' '*(w-span[1]) + '] '
        str += '%-30s' % rule
        if self._trace > 2: str += '%e ' % p
        print str

##//////////////////////////////////////////////////////
##  Bottom-Up PCFG Chart Parser
##//////////////////////////////////////////////////////

class BottomUpPCFGChartParser(ProbablisticParserI):
    """
    An abstract bottom-up parser for C{PCFG}s that uses a C{Chart} to
    record partial results.  C{BottomUpPCFGChartParser} maintains a
    queue of edges that can be added to the chart.  This queue is
    initialized with edges for each token in the text that is being
    parsed.  C{BottomUpPCFGParser} inserts these edges into to the
    chart one at a time, starting with the most likely edges, and
    proceeding to less likely edges.  For each edge that is added to
    the chart, it may become possible to insert additional edges into
    the chart; these are added to the queue.  This process continues
    until enough complete parses have been generated, or until the
    queue is empty.

    The sorting order for the queue is not specified by
    C{BottomUpPCFGChartParser}.  Different sorting orders will result
    in different search strategies.  The sorting order for the queue
    is defined by the method C{_sort_queue}; subclasses are required
    to provide a definition for this method.
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
        self._grammar = grammar
        self._trace = trace

    def parse(self, text):
        # Inherit docs from ProbablisticParserI; and delegate to parse_n
        final_trees = self.parse_n(text, 1)
        if len(final_trees) == 0: return None
        else: return final_trees[0]
        
    def parse_n(self, text, n=None):
        # Inherit docs from ProbablisticParserI
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
            self._sort_queue(edge_queue, chart)
            edge = edge_queue.pop()
            if self._add_edge(edge, chart, edge_queue):
                if self._trace > 1:
                    print '  %-60s %10.12f' % (chart.pp_edge(edge,2),
                                               edge.tree().p())
                

                # Check if the edge is a complete parse.
                if (edge.loc() == chart.loc() and
                    edge.drule().lhs() == self._grammar.start()):
                    parses.append(edge.tree())
                    if len(parses) == n: break

        if self._trace:
            print 'Found %d parses with %d edges' % (len(parses), len(chart))
                                                     
        return parses

    def _sort_queue(self, queue, chart):
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
        M{loc}, return a new edge with dotted rule C{[Rule: M{typ} ->
        *]}, location M{loc}, and tree C{tok}.

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
            drule = DottedPCFG_Rule(1, tok.type(), ())
            probtok = ProbablisticToken(1, tok.type(), tok.loc())
            edge_queue.append(Edge(drule, probtok, tok.loc()))
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
        @return: true iff C{edge} is not already in the chart.  If
            C{edge} is already in the chart, C{_add_edge} will not
            change C{chart} or C{edge_queue}.
        @rtype: C{boolean}
        """
        # If the edge is already in the chart, then return 0.
        if not chart.insert(edge): return 0
        
        # If the dot is in the zero-position, then apply the bottom-up
        # initialization rule.
        drule = edge.drule()
        if drule.pos() == 0:
            edge_queue += [self._self_loop_edge(rule, edge.loc())
                           for rule in self._grammar.rules()
                           if rule.rhs()[0] == drule.lhs()]

        # Find any new places where we can apply the fundamental
        # rule. 
        drule = edge.drule()
        if edge.complete():
            edge_queue += [self._fr(e2,edge) for e2 in chart.fr_with(edge)]
        else:
            edge_queue += [self._fr(edge,e2) for e2 in chart.fr_with(edge)]

        # The edge was not already in the chart, so return 1.
        return 1

    def _self_loop_edge(self, rule, loc):
        """
        @return: a zero-width edge formed from C{rule}, starting at
            the beginning of C{loc}.  The new edge's dotted rule has
            the same left hand side and right hand side as C{rule},
            and has its dot at position 0.  The new edge's tree has a
            node value equal to C{rule}'s left hand side, and no
            children.  Its probability is equal to C{rule}'s
            probability.
        @rtype: C{Edge}

        @type rule: C{PCFG_Rule}
        @param rule: The rule to base the self-loop edge on.  The new
            edge's dotted rule and tree are based on this rule.
        @type loc: C{Location}
        @param loc: A location whose start will be the beginning of
            the edge's (zero-width) location.
        """
        node = rule.lhs().symbol()
        tree = ProbablisticTreeToken(rule.p(), node)
        drule = DottedPCFG_Rule(rule.p(), rule.lhs(),
                                rule.rhs(), 0)
        return Edge(drule, tree, loc.start_loc())

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
        loc = e1.loc().union(e2.loc())
        drule = DottedPCFG_Rule(e1.drule().p(), e1.drule().lhs(),
                                e1.drule().rhs(), e1.drule().pos()+1)
        
        children = e1.tree().children() + (e2.tree(),)
        p = e1.tree().p() * e2.tree().p()
        tree = ProbablisticTreeToken(p, e1.tree().node(), *children)
        return Edge(drule, tree, loc)

class InsidePCFGParser(BottomUpPCFGChartParser):
    """
    A bottom-up parser for C{PCFG}s that tries edges in descending
    order of the inside probabilities of their trees.  The X{inside
    probability} of a tree is the probability that it is simply the
    probability of the entire tree, ignoring its context.  In
    particular, the inside probability of a tree generated by rule
    M{r} with children M{c[1]}, M{c[2]}, ..., M{c[n]} is
    M{r}*M{c[1]}*M{c[2]}*M{...}*M{c[n]}.

    This sorting order implements a uniform-cost search strategy.
    """
    # Inherit constructor.
    def _sort_queue(self, queue, chart):
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
        queue.sort(lambda e1,e2:cmp(e1.tree().p(), e2.tree().p()))

# Eventually, this will become some sort of inside-outside parser:
# class InsideOutsideParser(BottomUpPCFGChartParser):
#     def __init__(self, grammar, trace=0):
#         # Inherit docs.
#         BottomUpPCFGChartParser.__init__(self, grammar, trace)
#
#         # Find the best path from S to each nonterminal
#         bestp = {}
#         for rule in grammar.rules(): bestp[rule.lhs()]=0
#         bestp[grammar.start()] = 1.0
#
#         for i in range(len(grammar.rules())):
#             for rule in grammar.rules():
#                 lhs = rule.lhs()
#                 for elt in rule.rhs():
#                     bestp[elt] = max(bestp[lhs]*rule.p(),
#                                      bestp.get(elt,0))
#
#         self._bestp = bestp
#         for (k,v) in self._bestp.items(): print k,v
#
#     def _cmp(self, e1, e2):
#         return cmp(e1.tree().p()*self._bestp[e1.drule().lhs()],
#                    e2.tree().p()*self._bestp[e2.drule().lhs()])
#        
#     def _sort_queue(self, queue, chart):
#         queue.sort(self._cmp)

import random
class RandomPCFGParser(BottomUpPCFGChartParser):
    """
    A bottom-up parser for C{PCFG}s that tries edges in random order.
    This sorting order implements a random search strategy.
    """
    # Inherit constructor
    def _sort_queue(self, queue, chart):
        i = random.randint(0, len(queue)-1)
        (queue[0], queue[i]) = (queue[i], queue[0])

##//////////////////////////////////////////////////////
##  Test Code
##//////////////////////////////////////////////////////

if __name__ == '__main__':
    nonterminals = 'S VP NP PP P N Name V Det'
    (S, VP, NP, PP, P, N, Name, V, Det) = [Nonterminal(s)
                                           for s in nonterminals.split()]
    lexicon = [PCFG_Rule(0.21, V, 'saw'),
               PCFG_Rule(0.51, V, 'ate'),
               PCFG_Rule(0.29, V, 'ran'),
               PCFG_Rule(0.11, N, 'boy'),
               PCFG_Rule(0.12, N, 'man'),
               PCFG_Rule(0.13, N, 'table'),
               PCFG_Rule(0.14, N, 'telescope'),
               PCFG_Rule(0.50, N, 'hill'),
               PCFG_Rule(0.52, Name, 'Jack'),
               PCFG_Rule(0.48, Name, 'Bob'),
               PCFG_Rule(0.61, P, 'with'),
               PCFG_Rule(0.39, P, 'under'),
               PCFG_Rule(0.71, Det, 'the'),
               PCFG_Rule(0.29, Det, 'a'),
               ]

    grammar = [
        PCFG_Rule(1.00, S, NP, VP),
        PCFG_Rule(0.59, VP, V, NP),
        PCFG_Rule(0.40, VP, V),
        PCFG_Rule(0.01, VP, VP, PP),
        PCFG_Rule(0.41, NP, Det, N),
        PCFG_Rule(0.28, NP, Name),
        PCFG_Rule(0.31, NP, NP, PP),
        PCFG_Rule(1.00, PP, P, NP),
               ]

    lexicalized_grammar = (
        # S
        [PCFG_Rule(1, Nonterminal('S'), Nonterminal(('S',v)))
         for v in 'saw ate ran'.split()] +
        [PCFG_Rule(1, Nonterminal(('S', v)),
                   Nonterminal('NP'), Nonterminal(('VP', v)))
         for v in 'saw ate ran'.split()] +

        # VP
        [PCFG_Rule(0.59, Nonterminal(('VP', v)),
                   Nonterminal(('V', v)), Nonterminal('NP'))
         for v in 'saw ate ran'.split()] +
        [PCFG_Rule(0.4, Nonterminal(('VP', v)),
                   Nonterminal(('V', v)))
         for v in 'saw ate ran'.split()] +
        [PCFG_Rule(0.01, Nonterminal(('VP', v)),
                   Nonterminal(('V', v)), Nonterminal('PP'))
         for v in 'saw ate ran'.split()] +

        # NP
        [PCFG_Rule(1, Nonterminal('NP'), Nonterminal(('NP',n)))
         for n in 'man table boy telescope hill Jack Bob'.split()] +
        [PCFG_Rule(0.4, Nonterminal(('NP', n)),
                   Nonterminal('Det'), Nonterminal(('N',n)))
         for n in 'boy man table telescope hill'.split()] +
        [PCFG_Rule(0.3, Nonterminal(('NP', n)),
                   Nonterminal(('Name',n)))
         for n in 'Jack Bob'.split()] +
        [PCFG_Rule(0.3, Nonterminal(('NP', n)),
                   Nonterminal(('NP',n)), Nonterminal('PP'))
         for n in 'man table boy telescope hill Jack Bob'.split()] +
        
        # PP
        [PCFG_Rule(1, Nonterminal('PP'), Nonterminal(('PP',p)))
         for p in 'with under'.split()] +
        [PCFG_Rule(1.0, Nonterminal(('PP', p)),
                   Nonterminal(('P',p)), Nonterminal('NP'))
         for p in 'with under'.split()] +

        # Det
        [PCFG_Rule(1, Nonterminal('Det'), Nonterminal(('Det',d)))
         for d in 'the a'.split()] + 

        # Lexicon
        [PCFG_Rule(r.p(),
                   Nonterminal((r.lhs().symbol(), r.rhs()[0])),
                   r.rhs()[0])
         for r in lexicon]
        )

    pcfg = PCFG(S, grammar+lexicon)
    #pcfg = PCFG(S, lexicalized_grammar)
    
    from nltk.token import WSTokenizer
    s = 'the boy saw Jack with Bob under the table with a telescope'
    #s = 'the boy saw Jack'
    text = WSTokenizer().tokenize(s)
    
    parser1 = InsidePCFGParser(pcfg,1)
    parser2 = ViterbiPCFGParser(pcfg,0)
    parser3 = RandomPCFGParser(pcfg,1)

    if 0:
        print '\nInside PCFG Parser'
        parser1.parse_n(text)

    if 1:
        print '\nRandom PCFG Parser'
        parser3.parse_n(text, 3)

    if 1:
        print '\nInside PCFG Parser'
        parser1.parse_n(text, 3)

    if 0:
        print '\nViterbi PCFG Parser'
        print parser2.parse(text)

    if 0:
        import time
        N = 10
        t = time.time()
        for i in range(N): parser1.parse_n(text, 1)
        print 'Parse  1:', (time.time()-t)/N
        t = time.time()
        for i in range(N): parser1.parse_n(text, 4)
        print 'Parse  4:', (time.time()-t)/N
        t = time.time()
        for i in range(N): ps=parser1.parse_n(text)
        print 'Parse %2d:' % len(ps), (time.time()-t)/N
    
    

