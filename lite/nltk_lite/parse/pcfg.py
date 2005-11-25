# Natural Language Toolkit: Probabilistic Context Free Grammars
#
# Copyright (C) 2001-2005 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@ldc.upenn.edu> (minor additions)
#         Nathan Bodenstab <bodenstab@cslu.ogi.edu> (induction)
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

import re
from nltk_lite.parse import cfg
from nltk_lite.probability import ImmutableProbabilisticMixIn

class Production(cfg.Production, ImmutableProbabilisticMixIn):
    """
    A probabilistic context free grammar production.
    PCFG C{Production}s are essentially just C{cfg.Production}s that
    have probabilities associated with them.  These probabilities are
    used to record how likely it is that a given production will
    be used.  In particular, the probability of a C{Production}
    records the likelihood that its right-hand side is the correct
    instantiation for any given occurance of its left-hand side.

    @see: L{cfg.Production}
    """
    def __init__(self, lhs, rhs, **prob_kwarg):
        """
        Construct a new C{Production}.

        @param prob: The probability of the new C{Production}.
        @param lhs: The left-hand side of the new C{Production}.
        @type lhs: L{Nonterminal}
        @param rhs: The right-hand side of the new C{Production}.
        @type rhs: sequence of (C{Nonterminal} and (terminal))
        """
        ImmutableProbabilisticMixIn.__init__(self, **prob_kwarg)
        cfg.Production.__init__(self, lhs, rhs)

    def __str__(self):
        return cfg.Production.__str__(self) + ' (p=%s)' % self.prob()

    def __eq__(self, other):
        return (_classeq(self, other) and
                self._lhs == other._lhs and
                self._rhs == other._rhs and
                self.prob() == other.prob())

    def __hash__(self):
        return hash((self._lhs, self._rhs, self.prob()))

class Grammar(cfg.Grammar):
    """
    A probabilistic context-free grammar.  A PCFG Grammar consists of a start
    state and a set of productions.  The set of terminals and
    nonterminals is implicitly specified by the productions.

    PCFG productions should be C{Production}s.  C{PCFG} Grammars impose
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
        and set of C{cfg.Production}s.

        @param start: The start symbol
        @type start: L{Nonterminal}
        @param productions: The list of productions that defines the grammar
        @type productions: C{list} of C{Production}
        @raise ValueError: if the set of productions with any left-hand-side
            do not have probabilities that sum to a value within
            EPSILON of 1.
        """
        cfg.Grammar.__init__(self, start, productions)

        # Make sure that the probabilities sum to one.
        probs = {}
        for production in productions:
            probs[production.lhs()] = (probs.get(production.lhs(), 0) +
                                       production.prob())
        for (lhs, p) in probs.items():
            if not ((1-Grammar.EPSILON) < p < (1+Grammar.EPSILON)):
                raise ValueError("cfg.Productions for %r do not sum to 1" % lhs)

def induce(start, productions):
    """
    Induce a PCFG grammar from a list of productions.

    The probability of a production A -> B C in a PCFG is:

                    count(A -> B C)
      P(B, C | A) = ---------------       where * is any right hand side
                     count(A -> *)

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

    prods = [Production(p.lhs(), p.rhs(), prob=float(pcount[p]) / lcount[p.lhs()])\
             for p in pcount]
    return Grammar(start, prods)


#################################################################
# Toy PCFGs
#################################################################

_S, _VP, _NP, _PP = cfg.nonterminals('S, VP, NP, PP')
_V, _N, _P, _Name, _Det = cfg.nonterminals('V, N, P, Name, Det')

toy1 = Grammar(_S, [
    Production(_NP, [_Det, _N], prob=0.5),
    Production(_NP, [_NP, _PP], prob=0.25),
    Production(_NP, ['John'], prob=0.1),
    Production(_NP, ['I'], prob=0.15),
    Production(_Det, ['the'], prob=0.8),
    Production(_Det, ['my'], prob=0.2),
    Production(_N, ['dog'], prob=0.5),
    Production(_N, ['cookie'], prob=0.5),
    Production(_VP, [_VP, _PP], prob=0.1),
    Production(_VP, [_V, _NP], prob=0.7),
    Production(_VP, [_V], prob=0.2),
    Production(_V, ['ate'], prob=0.35),
    Production(_V, ['saw'], prob=0.65),
    Production(_S, [_NP, _VP], prob=1.0),
    Production(_PP, [_P, _NP], prob=1.0),
    Production(_P, ['with'], prob=0.61),
    Production(_P, ['under'], prob=0.39)])

toy2 = Grammar(_S, [
    Production(_V, ['saw'], prob=0.21),
    Production(_V, ['ate'], prob=0.51),
    Production(_V, ['ran'], prob=0.28),
    Production(_N, ['boy'], prob=0.11),
    Production(_N, ['cookie'], prob=0.12),
    Production(_N, ['table'], prob=0.13),
    Production(_N, ['telescope'], prob=0.14),
    Production(_N, ['hill'], prob=0.50),
    Production(_Name, ['Jack'], prob=0.52),
    Production(_Name, ['Bob'], prob=0.48),
    Production(_P, ['with'], prob=0.61),
    Production(_P, ['under'], prob=0.39),
    Production(_Det, ['the'], prob=0.41),
    Production(_Det, ['a'], prob=0.31),
    Production(_Det, ['my'], prob=0.28),
    Production(_S, [_NP, _VP], prob=1.00),
    Production(_VP, [_V, _NP], prob=0.59),
    Production(_VP, [_V], prob=0.40),
    Production(_VP, [_VP, _PP], prob=0.01),
    Production(_NP, [_Det, _N], prob=0.41),
    Production(_NP, [_Name], prob=0.28),
    Production(_NP, [_NP, _PP], prob=0.31),
    Production(_PP, [_P, _NP], prob=1.00)])

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
    pcfg_prods = [pcfg.Production(A, [B, B], prob=0.3),
                  pcfg.Production(A, [C, B, C], prob=0.7),
                  pcfg.Production(B, [B, 'b'], prob=0.5),
                  pcfg.Production(B, [C], prob=0.5),
                  pcfg.Production(C, ['a'], prob=0.1),
                  pcfg.Production(C, ['b'], prob=0.9)]

    pcfg_prod = pcfg_prods[2]
    print 'A PCFG production:', `pcfg_prod`
    print '    pcfg_prod.lhs()  =>', `pcfg_prod.lhs()`
    print '    pcfg_prod.rhs()  =>', `pcfg_prod.rhs()`
    print '    pcfg_prod.prob() =>', `pcfg_prod.prob()`
    print

    # Create and print a PCFG
    grammar = pcfg.Grammar(S, pcfg_prods)
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
