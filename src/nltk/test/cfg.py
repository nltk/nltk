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
from nltk.util import mark_stdout_newlines

def test_Nonterminal(): """
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

def test_CFGProduction(): """
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

def test_CFG(): """
Unit tests for L{CFG}.
    
A context free grammar is constructed from a start symbol and a list
of productions:

    >>> S,NP,VP,PP,P,N,V = nonterminals('S,NP,VP,PP,P,N,V')
    >>> prods = [CFGProduction(S), CFGProduction(S, NP),
    ...          CFGProduction(S, NP, VP), CFGProduction(S, NP, VP, PP),
    ...          CFGProduction(N, 'dog'), CFGProduction(PP, 'in', NP)]
    >>> cfg = CFG(S, prods)
    >>> print cfg
    CFG with 6 productions (start state = S)
        S ->
        S -> NP
        S -> NP VP
        S -> NP VP PP
        N -> 'dog'
        PP -> 'in' NP
        
    >>> print repr(cfg)
    <CFG with 6 productions>

The start symbol and production list are accessed via methods:

    >>> print `cfg.start()`
    <S>
    >>> for prod in cfg.productions():
    ...     print `prod`
    [Production: S ->]
    [Production: S -> NP]
    [Production: S -> NP VP]
    [Production: S -> NP VP PP]
    [Production: N -> 'dog']
    [Production: PP -> 'in' NP]

CFGs can be constructed from strings with the L{CFG.parse} static
method.  The start state is taken to be the LHS of the first
production.

    >>> cfg = CFG.parse('''
    ...     S   -> NP VP
    ...     VP  -> V | V NP | VP PP
    ...     PP  -> P NP
    ...     NP  -> Det N | 'John' | 'Mary'
    ...     N   -> 'dog' | 'cat'
    ...     Det -> 'the' | 'a' | 'an'
    ...     V   -> 'saw' | 'met'
    ...     ''')
    >>> print cfg
    CFG with 15 productions (start state = S)
        S -> NP VP
        VP -> V
        VP -> V NP
        VP -> VP PP
        PP -> P NP
        NP -> Det N
        NP -> 'John'
        NP -> 'Mary'
        N -> 'dog'
        N -> 'cat'
        Det -> 'the'
        Det -> 'a'
        Det -> 'an'
        V -> 'saw'
        V -> 'met'

It is an error to give C{parse} an empty string:

    >>> CFG.parse('')
    Traceback (most recent call last):
      [...]
    ValueError: No productions found!

Or a mal-formed string:

    >>> CFG.parse('A <- B')
    Traceback (most recent call last):
      [...]
    ValueError: Unable to parse line 0
"""

def test_PCFGProduction(): """
Unit tests for L{PCFGProduction}.
    
PCFGProduction is a probabilistic version of CFGProduction:

    >>> S,NP,VP,PP,P,N,V = nonterminals('S,NP,VP,PP,P,N,V')
    >>> PCFGProduction(0.1, S)
    [Production: S -> (p=0.1)]
    >>> PCFGProduction(0.8, S, NP, VP)
    [Production: S -> NP VP (p=0.8)]

It is hashable and comparable:

    >>> prod1 = PCFGProduction(0.1, S)
    >>> prod2 = PCFGProduction(0.2, S)
    >>> prod1 == prod2
    False
    >>> {prod1: 1}
    {[Production: S -> (p=0.1)]: 1}
"""

def test_PCFG(): """
Unit tests for L{PCFG}.

PCFG is a probabilistic version of CFG.  It uses PCFGProductions
instead of CFGProductions.

    >>> S,NP,VP,PP,P,N,V = nonterminals('S,NP,VP,PP,P,N,V')
    >>> prods = [PCFGProduction(0.1, S),
    ...          PCFGProduction(0.2, S, NP),
    ...          PCFGProduction(0.3, S, NP, VP),
    ...          PCFGProduction(0.4, S, NP, VP, PP),
    ...          PCFGProduction(1.0, N, 'dog'),
    ...          PCFGProduction(1.0, PP, 'in', NP)]
    >>> cfg = PCFG(S, prods)
    >>> print cfg
    CFG with 6 productions (start state = S)
        S -> (p=0.1)
        S -> NP (p=0.2)
        S -> NP VP (p=0.3)
        S -> NP VP PP (p=0.4)
        N -> 'dog' (p=1.0)
        PP -> 'in' NP (p=1.0)

The probability distribution defined by a PCFG is required to be
well-defined.  I.e., the probabilities of the productions with a given
LHS must sum to 1.

    >>> prods[0] = PCFGProduction(0.5, S)
    >>> PCFG(S, prods)
    Traceback (most recent call last):
      [...]
    ValueError: CFGProductions for <S> do not sum to 1
"""

def test_demo(): """
Unit test for L{nltk.cfg.demo}.

    >>> mark_stdout_newlines(demo)
    Some nonterminals: [<S>, <NP>, <VP>, <PP>, <N>, <V>, <P>, <Det>, <VP/NP>]
        S.symbol() => 'S'
    <--BLANKLINE-->
    A CFG production: [Production: NP -> Det N]
        prod.lhs() => <NP>
        prod.rhs() => (<Det>, <N>)
    <--BLANKLINE-->
    A CFG grammar: <CFG with 14 productions>
        cfg.start()       => <S>
        cfg.productions() => ([Production: S -> NP VP],
                              [Production: PP -> P NP],
                              [Production: NP -> Det N],
                              [Production: NP -> NP PP],
                              [Production: VP -> V NP],
                              [Production: VP -> VP PP],
                              [Production: Det -> 'a'],
                              [Production: Det -> 'the'],
                              [Production: N -> 'dog'],
                              [Production: N -> 'cat'],
                              [Production: V -> 'chased'],
                              [Production: V -> 'sat'],
                              [Production: P -> 'on'],
                              [Production: P -> 'in'])
    <--BLANKLINE-->
    A PCFG production: [Production: B -> B 'b' (p=0.5)]
        pcfg_prod.lhs()  => <B>
        pcfg_prod.rhs()  => (<B>, 'b')
        pcfg_prod.prob() => 0.5
    <--BLANKLINE-->
    A PCFG grammar: <CFG with 6 productions>
        pcfg.start()       => <S>
        pcfg.productions() => ([Production: A -> B B (p=0.3)],
                               [Production: A -> C B C (p=0.7)],
                               [Production: B -> B 'b' (p=0.5)],
                               [Production: B -> C (p=0.5)],
                               [Production: C -> 'a' (p=0.1)],
                               [Production: C -> 'b' (p=0.9)])
    <--BLANKLINE-->
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
