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
C{pcfgparser} currently defines two C{ProbablisticParser}s:

    - C{ViterbiPCFGParser} is a parser based on the Viterbi algorithm.
      It efficiently finds the single most likely parse for a given
      text.  
    - C{InsidePCFGParser} is a bottom-up chart-based parser for
      C{PCFG}s.  It maintains a sorted queue of edges, and expands
      them one at a time.  The ordering of this queue is based on the
      probabilities of the edges' dotted rules, allowing the parser to
      expand more likely edges before less likely ones.
      C{InsidePCFGParser} tries edges in best-first order; but
      subclasses can easily redefine the queue sorting algorithm, to
      implement other seach strategies (such as A*).
"""

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
    A simple bottom-up probablistic CFG parser.  This parser uses
    C{PFGRule}s to determine the probability of different tree
    structures for a given text.
    
    Currently, the following restrictions are imposed:
      - binary and unary branching only for the grammar

    @param _grammar: The grammar, stored as a dictionary from
        right-hand-sides to grammar rules.
    """
    def __init__(self, grammar, basecat):
        self._basecat = basecat
        if not isinstance(self._basecat, Nonterminal):
            self._basecat = Nonterminal(self._basecat)
        
        # Store the grammar as a dictionary from rhs's
        g = self._grammar = {}
        for rule in grammar:
            g.setdefault(rule.rhs(), []).append(rule)

    def parse(self, text):
        # Inherit docs from ProbablisticParserI; and delegate to parse_n
        final_trees = self.parse_n(text, 1)
        if len(final_trees) == 0: return None
        else: return final_trees[0]
        
    def parse_n(self, text, n=None):
        """
        Trees maps from spans to lists of possible (Tree)Tokens
        """
        # This is just for debugging purposes
        self._text = text
        
        # C{constituants} is a dictionary from spans to sets of
        # constituants that might cover those spans.  Constituants can
        # be either treetokens (corresponding to nonterminals) or
        # tokens (corresponding to terminals)
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
            #print constituants
            for start in range(len(text)-length+1):
                span = (start, start+length)
                self._add_constituants_spanning(span, constituants)

        # Find all trees that span the entire text & have the right cat
        trees = [constituants.get((0, len(text),
                                   self._basecat), [])]

        # Sort the trees, and return the requested number of them.
        trees.sort(lambda t1,t2: cmp(t2.p(), t1.p()))
        if n is None: return trees
        else: return trees[:n]

    def _add_constituants_spanning(self, span, constituants):
        """
        Find any constituants that might cover C{span}, and add them
        to C{constituants}.
        
        @type span: C{pair} of C{int}
        @param span: The section of the text for which we are
            trying to find possible constituants.  The span is
            specified as a pair of integers, where the first integer
            is the index of the first token that should be included in
            the constituant; and the second integer is the index of
            the first token that should not be included in the
            constituant.  I.e., the constituant should cover
            C{M{text}[span[0]:span[1]]}, where C{M{text}} is the text
            that we are parsing.
        @type constituants: C{dictionary} from (C{pair} of C{int}) to
            C{list} of (C{Token} or C{ProbablisticTreeToken}).
        @param constituants: The constituants that we have discovered
            to cover given C{span}s in the senence.  In particular,
            C{constituants[M{s}]} is a list of all constituants that
            cover the span C{M{s}}.  When
            C{_add_constituants_spanning} is called, C{constituants}
            should contain all possible constituants that are shorter
            than C{span}.  C{_add_constituants_spanning} will add any
            new constituants it finds to C{constituants[span]}.
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
                    #self._printrule(span, rule)
                    constituants[span[0], span[1], rule.lhs()] = tree
                    changed = 1

    def _find_instantiations(self, (start, end), constituants):
        """
        Find all possible rule instantiations that cover a given
        span of the text.

        @return: A list of all (rule, children) tuples...
        @rtype: C{list} of ({PCFG_Rule}, {list} of
            (C{ProbablisticTreeToken} or C{Token})
        """
        rv = []
        for rules in self._grammar.values():
            for rule in rules:
                childrens = self._match_rhs(rule.rhs(), (start, end),
                                            constituants)
                for children in childrens:
                    rv.append( (rule, children) )
        return rv

    def _match_rhs(self, rhs, (start, end), constituants):
        """
        Return all childlists that match the given RHS.
        """
        
        # Base case
        if start >= end and rhs == (): return [[]]
        if start >= end or rhs == (): return []

        # Find everything that matches the 1st symbol of the RHS
        childlists = []
        for split in range(start, end+1):
            l=constituants.get((start,split,rhs[0]))
            if l is not None:
                #print '     ', l
                rights = self._match_rhs(rhs[1:], (split,end), constituants)
                childlists += [[l]+r for r in rights]

        return childlists

    def _printrule(self, span, rule):
        """
        Print 
        """
        print '[' + ' '*span[0] + '.'*(span[1]-span[0]) + \
              ' '*(len(self._text)-span[1]) + ']', rule

##//////////////////////////////////////////////////////
##  Bottom-Up PCFG Chart Parser
##//////////////////////////////////////////////////////

class InsidePCFGParser(ProbablisticParserI):
    def __init__(self, grammar, basecat):
        self._grammar = grammar
        self._basecat = basecat

    def parse(self, text):
        # Inherit docs from ProbablisticParserI; and delegate to parse_n
        final_trees = self.parse_n(text, 1)
        if len(final_trees) == 0: return None
        else: return final_trees[0]
        
    def parse_n(self, text, n=None):
        import time
        t = time.time()
        loc = Location(text[0].loc().start(), text[-1].loc().end(),
                       unit=text[0].loc().unit(),
                       source=text[0].loc().source())
        chart = FRChart(loc)

        self._add_lexical_edges(text, chart)
        self._bottom_up_init(chart)
        
        edge_queue = self._init_edge_queue(chart)

        parses = []
        t = time.time()
        while edge_queue:
            # Handle the most likely edge
            self._sort_queue(edge_queue)
            parses += self._add_edge(edge_queue, chart)
            if len(parses) == n: return parses

        return parses

    def _sort_queue(self, queue): 
        queue.sort(lambda e1,e2:cmp(e1.tree().p(), e2.tree().p()))

    def _add_lexical_edges(self, text, chart):
        # Create lexical edges.
        for tok in text:
            drule = DottedPCFG_Rule(1, tok.type(), ())
            treetok = tok
            edge = Edge(drule, treetok, tok.loc())
            chart.insert(edge)

    def _bottom_up_init(self, chart):
        # Do bottom-up initialization.
        edges = chart.edges()
        i = 0
        while i < len(edges):
            edge = edges[i]
            i += 1
            for rule in self._grammar:
                #for edge in chart.edges():
                if rule.rhs()[0] == edge.drule().lhs():
                    loc = edge.loc().start_loc()
                    node = rule.lhs().symbol()
                    tree = ProbablisticTreeToken(rule.p(), node)
                    drule = DottedPCFG_Rule(rule.p(), rule.lhs(),
                                            rule.rhs(), 0)
                    new_edge = Edge(drule, tree, loc)
                    if chart.insert(new_edge):
                        edges.append(new_edge)

    def _init_edge_queue(self, chart):
        # Initialize the queue
        edge_queue = []
        for e1 in chart.edges():
            for e2 in chart.edges():
                if (e1.end() == e2.start() and
                    e2.complete() and not e1.complete() and
                    e1.drule().next() == e2.drule().lhs()):
                    edge_queue.append(self._fr(e1,e2))
        return edge_queue

    def _add_edge(self, edge_queue, chart):
        # Get the most likely edge, and add it to the chart.
        edge = edge_queue.pop()
        chart.insert(edge)

        # Find any new places where we can apply the FR
        drule = edge.drule()
        if edge.complete():
            edge_queue += [self._fr(e2,edge) for e2 in chart.fr_with(edge)]
        else:
            edge_queue += [self._fr(edge,e2) for e2 in chart.fr_with(edge)]

        # Check if the edge is a complete parse.
        if (edge.loc() == chart.loc() and drule.lhs() == self._basecat):
            return [edge.tree()]
        else:
            return []

    def _fr(self, e1, e2):
        """
        Combine e1 and e2 with the fundamental rule.
        """
        loc = e1.loc().union(e2.loc())
        drule = e1.drule().shift()

        #DottedPCFG_Rule(p, self._lhs, self._rhs, self._pos + 1)
        children = e1.tree().children() + (e2.tree(),)
        p = 1
        if isinstance(e1.tree(), ProbablisticTreeToken): p *= e1.tree().p()
        if isinstance(e2.tree(), ProbablisticTreeToken): p *= e2.tree().p()
        tree = ProbablisticTreeToken(p, e1.tree().node(), *children)
        return Edge(drule, tree, loc)


if __name__ == '__main__':
    nonterminals = 'S VP NP PP P N Name V Det'
    (S, VP, NP, PP, P, N, Name, V, Det) = [Nonterminal(s)
                                           for s in nonterminals.split()]
    lexicon = [PCFG_Rule(0.2, V, 'saw'),
               PCFG_Rule(0.5, V, 'ate'),
               PCFG_Rule(0.3, V, 'ran'),
               PCFG_Rule(0.2, N, 'boy'),
               PCFG_Rule(0.2, N, 'man'),
               PCFG_Rule(0.2, N, 'table'),
               PCFG_Rule(0.2, N, 'telescope'),
               PCFG_Rule(0.2, N, 'hill'),
               PCFG_Rule(0.5, Name, 'Jack'),
               PCFG_Rule(0.5, Name, 'Bob'),
               PCFG_Rule(0.5, P, 'with'),
               PCFG_Rule(0.5, P, 'under'),
               PCFG_Rule(0.5, Det, 'the'),
               PCFG_Rule(0.5, Det, 'a')
               ]

    grammar = [
        PCFG_Rule(1, S, NP, VP),
        PCFG_Rule(0.4, VP, V, NP),
        PCFG_Rule(0.4, VP, V),
        PCFG_Rule(0.2, VP, VP, PP),
        PCFG_Rule(0.4, NP, Det, N),
        PCFG_Rule(0.3, NP, Name),
        PCFG_Rule(0.1, NP, NP, PP),
        PCFG_Rule(1.0, PP, P, NP),
               ]
    g = grammar+lexicon
    
    from nltk.token import WSTokenizer
    s = 'the boy with Bob saw Jack under the table with a telescope'
    #s = 'the boy saw Jack'
    text = WSTokenizer().tokenize(s)
    
    parser1 = InsidePCFGParser(g, S)
    parser2 = ViterbiPCFGParser(g, S)

    for p in parser1.parse_n(text, 3): print p
    print '================='
    print parser2.parse(text)

    #for tree in parser.parse_n(text, 3):
    #    print tree

    #import time
    #t = time.time()
    #parser.parse_n(text, 1)
    #print 'Parse 1:', time.time()-t
    #t = time.time()
    #parser.parse_n(text, 4)
    #print 'Parse 4:', time.time()-t
    #t = time.time()
    #ps=parser.parse_n(text)
    #print 'Parse %d:' % len(ps), time.time()-t
    
    

