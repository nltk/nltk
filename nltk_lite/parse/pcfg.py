# Natural Language Toolkit: Probabilistic Context Free Grammars
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Steven Bird <sb@csse.unimelb.edu.au>
#         Edward Loper <edloper@ldc.upenn.edu> (minor additions)
#         Nathan Bodenstab <bodenstab@cslu.ogi.edu> (induction)
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

import re
from nltk_lite.parse import *
from nltk_lite.probability import ImmutableProbabilisticMixIn

class WeightedProduction(Production, ImmutableProbabilisticMixIn):
    """
    A probabilistic context free grammar production.
    PCFG C{WeightedProduction}s are essentially just C{Production}s that
    have probabilities associated with them.  These probabilities are
    used to record how likely it is that a given production will
    be used.  In particular, the probability of a C{WeightedProduction}
    records the likelihood that its right-hand side is the correct
    instantiation for any given occurance of its left-hand side.

    @see: L{Production}
    """
    def __init__(self, lhs, rhs, **prob):
        """
        Construct a new C{WeightedProduction}.

        @param lhs: The left-hand side of the new C{WeightedProduction}.
        @type lhs: L{Nonterminal}
        @param rhs: The right-hand side of the new C{WeightedProduction}.
        @type rhs: sequence of (C{Nonterminal} and (terminal))
        @param **prob: Probability parameters of the new C{WeightedProduction}.
        """
        ImmutableProbabilisticMixIn.__init__(self, **prob)
        Production.__init__(self, lhs, rhs)

    def __str__(self):
        return Production.__str__(self) + ' [%s]' % self.prob()

    def __eq__(self, other):
        return (isinstance(other, self.__class__) and
                self._lhs == other._lhs and
                self._rhs == other._rhs and
                self.prob() == other.prob())

    def __hash__(self):
        return hash((self._lhs, self._rhs, self.prob()))

class WeightedGrammar(Grammar):
    """
    A probabilistic context-free grammar.  A Weighted Grammar consists of a start
    state and a set of weighted productions.  The set of terminals and
    nonterminals is implicitly specified by the productions.

    PCFG productions should be C{WeightedProduction}s.  C{WeightedGrammar}s impose
    the constraint that the set of productions with any given
    left-hand-side must have probabilities that sum to 1.

    If you need efficient key-based access to productions, you can use
    a subclass to implement it.

    @type EPSILON: C{float}
    @cvar EPSILON: The acceptable margin of error for checking that
        productions with a given left-hand side have probabilities
        that sum to 1.
    """
    EPSILON = 0.01

    def __init__(self, start, productions):
        """
        Create a new context-free grammar, from the given start state
        and set of C{WeightedProduction}s.

        @param start: The start symbol
        @type start: L{Nonterminal}
        @param productions: The list of productions that defines the grammar
        @type productions: C{list} of C{Production}
        @raise ValueError: if the set of productions with any left-hand-side
            do not have probabilities that sum to a value within
            EPSILON of 1.
        """
        Grammar.__init__(self, start, productions)

        # Make sure that the probabilities sum to one.
        probs = {}
        for production in productions:
            probs[production.lhs()] = (probs.get(production.lhs(), 0) +
                                       production.prob())
        for (lhs, p) in probs.items():
            if not ((1-WeightedGrammar.EPSILON) < p < (1+WeightedGrammar.EPSILON)):
                raise ValueError("Productions for %r do not sum to 1" % lhs)

def induce(start, productions):
    """
    Induce a PCFG grammar from a list of productions.

    The probability of a production A -> B C in a PCFG is:

    |                count(A -> B C)
    |  P(B, C | A) = ---------------       where * is any right hand side
    |                 count(A -> *)

    @param start: The start symbol
    @type start: L{Nonterminal}
    @param productions: The list of productions that defines the grammar
    @type productions: C{list} of L{Production}
    """

    pcount = {} # Production count: the number of times a given production occurs
    lcount = {} # LHS-count: counts the number of times a given lhs occurs

    for prod in productions:
        lcount[prod.lhs()] = lcount.get(prod.lhs(), 0) + 1
        pcount[prod]       = pcount.get(prod,       0) + 1

    prods = [WeightedProduction(p.lhs(), p.rhs(), prob=float(pcount[p]) / lcount[p.lhs()])\
             for p in pcount]
    return WeightedGrammar(start, prods)

#################################################################
# Parsing PCFGs
#################################################################

_PARSE_RE = re.compile(r'''^\s*                 # leading whitespace
                          (\w+(?:/\w+)?)\s*     # lhs
                          (?:[-=]+>)\s*         # arrow
                          (?:(                  # rhs:
                               "[^"]+"          # doubled-quoted terminal
                             | '[^']+'          # single-quoted terminal
                             | \w+(?:/\w+)?     # non-terminal
                             | \[[01]?\.\d+\]   # probability
                             | \|               # disjunction
                             )
                             \s*)               # trailing space
                             *$''',             # zero or more copies
                       re.VERBOSE)
_SPLIT_RE = re.compile(r'''(\w+(?:/\w+)?|\[[01]?\.\d+\]|[-=]+>|"[^"]+"|'[^']+'|\|)''')

def parse_production(s):
    """
    Returns a list of productions
    """
    # Use _PARSE_RE to check that it's valid.
    if not _PARSE_RE.match(s):
        raise ValueError, 'Bad production string'
    # Use _SPLIT_RE to process it.
    pieces = _SPLIT_RE.split(s)
    pieces = [p for i,p in enumerate(pieces) if i%2==1]
    lhside = Nonterminal(pieces[0])
    rhsides = [[]]
    probabilities = [0.0]
    for piece in pieces[2:]:
        if piece == '|':
            rhsides.append([])                     # Vertical bar
            probabilities.append(0.0)
        elif piece[0] in ('"', "'"):
            rhsides[-1].append(piece[1:-1])        # Terminal
        elif piece[0] in "[":
            probabilities[-1] = float(piece[1:-1]) # Probability
        else:
            rhsides[-1].append(Nonterminal(piece)) # Nonterminal
    return [WeightedProduction(lhside, rhside, prob=probability)
            for (rhside, probability) in zip(rhsides, probabilities)]

def parse_grammar(s):
    productions = []
    for linenum, line in enumerate(s.split('\n')):
        line = line.strip()
        if line.startswith('#') or line=='': continue
        try: productions += parse_production(line)
        except ValueError:
            raise ValueError, 'Unable to parse line %s: %s' % (linenum, line)
    if len(productions) == 0:
        raise ValueError, 'No productions found!'
    start = productions[0].lhs()
    return WeightedGrammar(start, productions)


toy1 = parse_grammar("""
    S -> NP VP [1.0]
    NP -> Det N [0.5] | NP PP [0.25] | 'John' [0.1] | 'I' [0.15]
    Det -> 'the' [0.8] | 'my' [0.2]
    N -> 'man' [0.5] | 'telescope' [0.5]
    VP -> VP PP [0.1] | V NP [0.7] | V [0.2]
    V -> 'ate' [0.35] | 'saw' [0.65]
    PP -> P NP [1.0]
    P -> 'with' [0.61] | 'under' [0.39]
    """)

toy2 = parse_grammar("""
    S    -> NP VP         [1.0]
    VP   -> V NP          [.59]
    VP   -> V             [.40]
    VP   -> VP PP         [.01]
    NP   -> Det N         [.41]
    NP   -> Name          [.28]
    NP   -> NP PP         [.31]
    PP   -> P NP          [1.0]
    V    -> 'saw'         [.21]
    V    -> 'ate'         [.51]
    V    -> 'ran'         [.28]
    N    -> 'boy'         [.11]
    N    -> 'cookie'      [.12]
    N    -> 'table'       [.13]
    N    -> 'telescope'   [.14]
    N    -> 'hill'        [.5]
    Name -> 'Jack'        [.52]
    Name -> 'Bob'         [.48]
    P    -> 'with'        [.61]
    P    -> 'under'       [.39]
    Det  -> 'the'         [.41]
    Det  -> 'a'           [.31]
    Det  -> 'my'          [.28]
    """)

#################################################################
# Demonstration
#################################################################

def demo():
    """
    A demonstration showing how PCFG C{Grammar}s can be created and used.
    """

    from nltk_lite.corpora import treebank, extract
    from nltk_lite.parse import cfg, pcfg, pchart, treetransforms
    from itertools import islice

    pcfg_prods = pcfg.toy1.productions()

    pcfg_prod = pcfg_prods[2]
    print 'A PCFG production:', `pcfg_prod`
    print '    pcfg_prod.lhs()  =>', `pcfg_prod.lhs()`
    print '    pcfg_prod.rhs()  =>', `pcfg_prod.rhs()`
    print '    pcfg_prod.prob() =>', `pcfg_prod.prob()`
    print

    grammar = pcfg.toy2
    print 'A PCFG grammar:', `grammar`
    print '    grammar.start()       =>', `grammar.start()`
    print '    grammar.productions() =>',
    # Use string.replace(...) is to line-wrap the output.
    print `grammar.productions()`.replace(',', ',\n'+' '*26)
    print

    # extract productions from three trees and induce the PCFG
    print "Induce PCFG grammar from treebank data:"

    productions = []
    for tree in islice(treebank.parsed(),3):
        # perform optional in-place tree transformations, e.g.:
        # treetransforms.collapseUnary(tree, collapsePOS = False)
        # treetransforms.chomskyNormalForm(tree, horzMarkov = 2)

        productions += tree.productions()

    S = Nonterminal('S')
    grammar = pcfg.induce(S, productions)
    print grammar
    print

    print "Parse sentence using induced grammar:"

    parser = pchart.InsideParse(grammar)
    parser.trace(3)

    sent = extract(0, treebank.raw())
    print sent
    for parse in parser.get_parse_list(sent):
        print parse

if __name__ == '__main__': demo()
