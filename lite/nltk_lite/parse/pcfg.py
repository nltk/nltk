# Natural Language Toolkit: Probabilistic Context Free Grammars
#
# Copyright (C) 2001-2005 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@ldc.upenn.edu> (minor additions)
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

#################################################################
# Demonstration
#################################################################

def demo():
    """
    A demonstration showing how C{PCFG}s can be
    created and used.
    """

    from nltk_lite.parse import cfg, pcfg

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

if __name__ == '__main__': demo()
