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
        return Production.__str__(self) + ' (p=%s)' % self.prob()

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
# Toy PCFGs
#################################################################

_S, _VP, _NP, _PP = nonterminals('S, VP, NP, PP')
_V, _N, _P, _Name, _Det = nonterminals('V, N, P, Name, Det')

toy1 = WeightedGrammar(_S, [
    WeightedProduction(_NP, [_Det, _N], prob=0.5),
    WeightedProduction(_NP, [_NP, _PP], prob=0.25),
    WeightedProduction(_NP, ['John'], prob=0.1),
    WeightedProduction(_NP, ['I'], prob=0.15),
    WeightedProduction(_Det, ['the'], prob=0.8),
    WeightedProduction(_Det, ['my'], prob=0.2),
    WeightedProduction(_N, ['dog'], prob=0.5),
    WeightedProduction(_N, ['cookie'], prob=0.5),
    WeightedProduction(_VP, [_VP, _PP], prob=0.1),
    WeightedProduction(_VP, [_V, _NP], prob=0.7),
    WeightedProduction(_VP, [_V], prob=0.2),
    WeightedProduction(_V, ['ate'], prob=0.35),
    WeightedProduction(_V, ['saw'], prob=0.65),
    WeightedProduction(_S, [_NP, _VP], prob=1.0),
    WeightedProduction(_PP, [_P, _NP], prob=1.0),
    WeightedProduction(_P, ['with'], prob=0.61),
    WeightedProduction(_P, ['under'], prob=0.39)])

toy2 = Grammar(_S, [
    WeightedProduction(_V, ['saw'], prob=0.21),
    WeightedProduction(_V, ['ate'], prob=0.51),
    WeightedProduction(_V, ['ran'], prob=0.28),
    WeightedProduction(_N, ['boy'], prob=0.11),
    WeightedProduction(_N, ['cookie'], prob=0.12),
    WeightedProduction(_N, ['table'], prob=0.13),
    WeightedProduction(_N, ['telescope'], prob=0.14),
    WeightedProduction(_N, ['hill'], prob=0.50),
    WeightedProduction(_Name, ['Jack'], prob=0.52),
    WeightedProduction(_Name, ['Bob'], prob=0.48),
    WeightedProduction(_P, ['with'], prob=0.61),
    WeightedProduction(_P, ['under'], prob=0.39),
    WeightedProduction(_Det, ['the'], prob=0.41),
    WeightedProduction(_Det, ['a'], prob=0.31),
    WeightedProduction(_Det, ['my'], prob=0.28),
    WeightedProduction(_S, [_NP, _VP], prob=1.00),
    WeightedProduction(_VP, [_V, _NP], prob=0.59),
    WeightedProduction(_VP, [_V], prob=0.40),
    WeightedProduction(_VP, [_VP, _PP], prob=0.01),
    WeightedProduction(_NP, [_Det, _N], prob=0.41),
    WeightedProduction(_NP, [_Name], prob=0.28),
    WeightedProduction(_NP, [_NP, _PP], prob=0.31),
    WeightedProduction(_PP, [_P, _NP], prob=1.00)])

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

    # Create some probabilistic CFG Productions
    S, A, B, C = cfg.nonterminals('S A B C')
    pcfg_prods = [pcfg.WeightedProduction(A, [B, B], prob=0.3),
                  pcfg.WeightedProduction(A, [C, B, C], prob=0.7),
                  pcfg.WeightedProduction(B, [B, 'b'], prob=0.5),
                  pcfg.WeightedProduction(B, [C], prob=0.5),
                  pcfg.WeightedProduction(C, ['a'], prob=0.1),
                  pcfg.WeightedProduction(C, ['b'], prob=0.9)]

    pcfg_prod = pcfg_prods[2]
    print 'A PCFG production:', `pcfg_prod`
    print '    pcfg_prod.lhs()  =>', `pcfg_prod.lhs()`
    print '    pcfg_prod.rhs()  =>', `pcfg_prod.rhs()`
    print '    pcfg_prod.prob() =>', `pcfg_prod.prob()`
    print

    # Create and print a PCFG
    grammar = pcfg.WeightedGrammar(S, pcfg_prods)
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
