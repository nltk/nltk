# Natural Language Toolkit: Test Code for CFGs
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
Unit testing for L{nltk.cfg}.
"""

from nltk.cfg import *

def test_Nonterminal():
    """
Unit testing for L{Nonterminal}.

Nonterminals are constructed from node values (or 'symbols'):

    >>> S = Nonterminal('S')
    >>> VP = Nonterminal('VP')
    >>> print S, VP
    S VP

The symbol can be accessed via the C{symbol} method:

    >>> S.symbol()
    'S'
    >>> VP.symbol()
    'VP'

Two Nonterminals are equal iff they have equal symbols:

    >>> S == VP
    False
    >>> S == S
    True
    >>> Nonterminal('X'*2) == Nonterminal('XX')
    True
    >>> S != VP
    True
    >>> S != S
    False
    >>> S<S or S>S
    False
    >>> S<VP or S>VP
    True

Nonterminals are hashable, and so can be used as dictionary keys:

    >>> {S: 1}
    {<S>: 1}

Currently, we use <symbol> as a repr for Nonterminals:

    >>> print repr(S), repr(VP)
    <S> <VP>

But that's in conflict with Token's repr, so we'll probably change it.

'Slashed nonterminals' can be constructed from two nonterminals that
have string symbols via division:

    >>> S/VP
    <S/VP>

The L{nonterminals} function can be used to quickly construct a set of
nonterminals.  Commas are the easiest delimiter, since they let you
copy/paste the same string for the assignment target and argument:

    >>> S,NP,VP,PP,P,N,V = nonterminals('S,NP,VP,PP,P,N,V')
    >>> print S, NP, VP, PP, P, N, V
    S NP VP PP P N V

But spaces can be used instead:

    >>> S,NP,VP,PP,P,N,V = nonterminals('S NP VP PP P N V')
    >>> print S, NP, VP, PP, P, N, V
    S NP VP PP P N V

If commas are used, then nonterminal symbols can contain internal
whitespace:

    >>> AB, CD, EF = nonterminals('A B, C D, E F')
    >>> print '%r %r %r' % (AB, CD, EF)
    <A B> <C D> <E F>
"""

def test_CFGProduction():
    """
Unit tests for L{CFGProduction}.
    
A CFG production is constructed from a left-hand side element and
zero or more right-hand side elements:

    >>> S,NP,VP,PP,P,N,V = nonterminals('S,NP,VP,PP,P,N,V')
    >>> CFGProduction(S)
    [Production: S ->]
    >>> CFGProduction(S, NP)
    [Production: S -> NP]
    >>> CFGProduction(S, NP, VP)
    [Production: S -> NP VP]
    >>> CFGProduction(S, NP, VP, PP)
    [Production: S -> NP VP PP]
    >>> CFGProduction(N, 'dog')
    [Production: N -> 'dog']
    >>> CFGProduction(PP, 'in', NP)
    [Production: PP -> 'in' NP]

The left-hand side and right-hand side are accessed with lhs() and
rhs(), repsectively:

    >>> prod = CFGProduction(S, NP, VP)
    >>> print '%r %r' % (prod.lhs(), prod.rhs())
    <S> (<NP>, <VP>)
    
str() representation is like repr() representation, but without the
surrounding [Production:].

    >>> str(CFGProduction(S))
    'S ->'
    >>> str(CFGProduction(S, NP))
    'S -> NP'
    >>> str(CFGProduction(PP, 'in', NP))
    \"PP -> 'in' NP\"

Two productions are equal if their LHS and RHS are equal:

    >>> CFGProduction(S, NP) == CFGProduction(S, NP)
    True
    >>> CFGProduction(S, NP) == CFGProduction(VP, NP)
    False
    >>> CFGProduction(S, NP) == CFGProduction(S, VP)
    False
    >>> CFGProduction(S, NP) != CFGProduction(S, NP)
    False
    >>> CFGProduction(S, NP) != CFGProduction(S, VP)
    True
    >>> CFGProduction(S) != CFGProduction(S, NP)
    True
    >>> prod1, prod2 = CFGProduction(S, NP), CFGProduction(S, VP)
    >>> prod1 < prod1 or prod1 > prod1
    False
    >>> prod1 < prod2 or prod1 > prod2
    True

Productions are hashable, and so can be used as dictionary keys:

    >>> {prod1:0}
    {[Production: S -> NP]: 0}
"""

#######################################################################
# Test Runner
#######################################################################

import sys, os, os.path
if __name__ == '__main__': sys.path[0] = None
import unittest, doctest, trace

def testsuite():
    import doctest, nltk.test.cfg
    reload(nltk.test.cfg)
    return doctest.DocTestSuite(nltk.test.cfg)

def test(verbosity=2):
    runner = unittest.TextTestRunner(verbosity=verbosity)
    runner.run(testsuite())

if __name__ == '__main__':
    test()
