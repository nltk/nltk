# Natural Language Toolkit: Test Code for Tokens and Tokenizers
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
Unit testing for L{nltk.token}.
"""

from nltk.token import *
from nltk.util import mark_stdout_newlines

def test_Token():
    """
Unit testing for L{nltk.token.Token}.

    >>> Token.USE_SAFE_TOKENS=False

Token Basics
============
A token is a mapping from properties to values.  It can be constructed
via keyword arguments, or from an initial dictionary:

    >>> tok = Token(A='foo', B=12)
    >>> tok
    <A='foo', B=12>
    >>> tok2 = Token({'A':'foo', 'B':12})
    >>> tok2
    <A='foo', B=12>
    >>> tok3 = Token({'A':'foo'}, B=12)
    >>> tok3
    <A='foo', B=12>

A token can define zero or more properties:

    >>> print Token()
    <>
    
    >>> print Token(A='foo')
    <A='foo'>
    
    >>> print Token(A='foo', B=12, C='bar', D='baz')
    <A='foo', B=12, C='bar', D='baz'>

Properties are accessed via indexing:

    >>> tok['A']
    'foo'
    >>> tok['B']
    12

Properties may be added, modified, or deleted:

    >>> tok['C'] = 'baz'
    >>> tok
    <A='foo', B=12, C='baz'>
    
    >>> tok['B'] = 'bar'
    >>> tok
    <A='foo', B='bar', C='baz'>
    
    >>> del tok['A']
    >>> tok
    <B='bar', C='baz'>

The list of defined properties can be accessed via L{Token.properties}
and L{Token.has}:

    >>> props = tok.properties()
    >>> props.sort()
    >>> props
    ['B', 'C']
    
    >>> tok.has('B')
    True
    >>> tok.has('TEXT')
    False

Tokens may contain nested tokens.  In particular, a property can
contain a single token:

   >>> tok1 = Token(A=12)
   >>> tok2 = Token(SUBTOK=tok1, SIZE=144)
   >>> print tok2
   <SIZE=144, SUBTOK=<A=12>>

Or a list of tokens:

    >>> words = [Token(TEXT=word) for word in 'on the table'.split()]
    >>> phrase = Token(WORDS=words, TYPE='PP')
    >>> print phrase
    <TYPE='PP', WORDS=[<on>, <the>, <table>]>

Or a tuple of tokens:

    >>> phrase = Token(WORDS=tuple(words), TYPE='PP')
    >>> print phrase
    <TYPE='PP', WORDS=(<on>, <the>, <table>)>

Or a dictionary containing tokens:

    >>> tokdict = {'X': Token(TEXT='X')}
    >>> tok = Token(TOKDICT=tokdict)
    >>> print tok
    <TOKDICT={'X': <X>}>

Tokens can be nested to arbirary depth:

    >>> Token(A=Token(B=Token(C=Token(D=Token(E=12)))))
    <A=<B=<C=<D=<E=12>>>>>

Tokens can be connected in cycles:

    >>> tok1, tok2 = Token(), Token()
    >>> tok1['A'] = tok2
    >>> tok2['B'] = tok1
    >>> print tok1, tok2
    <A=<B=...>> <B=<A=...>>
    >>> tok1['A']['B'] is tok1
    True
    >>> tok1['A']['B']['A']['B']['A']['B']['A']['B'] is tok1
    True

Tokens can be compared for equality and ordering.  Results should be
identical to comparing the corresponding dictionaries:

    >>> tok1 = Token(A=[1], B=12)
    >>> tok2 = Token(A=[1], B=12)
    >>> tok3 = Token(A=[4], B=12)
    >>> print tok1 == tok2, tok2 == tok3, tok3 == tok1
    True False False
    >>> print tok1 != tok2, tok2 != tok3, tok3 != tok1
    False True True
    >>> tok1 < tok2 or tok1 > tok2
    False
    >>> tok2 < tok3 or tok3 > tok2
    True

Tokens are a subclass of dict, and support all the standard dict
methods.

    >>> tok = Token(TEXT='watch', TAG='NN', SPEAKER='FRAN')
    >>> tok
    <SPEAKER='FRAN', TAG='NN', TEXT='watch'>
    
    >>> keys = tok.keys(); keys.sort(); print keys
    ['SPEAKER', 'TAG', 'TEXT']
    >>> items = tok.items(); items.sort(); print items
    [('SPEAKER', 'FRAN'), ('TAG', 'NN'), ('TEXT', 'watch')]
    
    >>> tok.setdefault('TAG', 'JJ')
    'NN'
    >>> tok.setdefault('ACCENT', 3)
    3
    >>> tok.pop('SPEAKER')
    'FRAN'
    >>> print tok.pop('SPEAKER', None)
    None
    >>> print tok
    <ACCENT=3, TAG='NN', TEXT='watch'>

To avoid confusion, tokens raise exceptions when tested for length or
truth value:

    >>> len(tok)
    Traceback (most recent call last):
      [...]
    TypeError: len() of unsized Token object
    >>> bool(tok)
    Traceback (most recent call last):
      [...]
    TypeError: Token objects cannot be used as booleans
    
Token Representations
=====================
Special string representations can be registered for specific sets of
properties.  By default, special representations are registered for
combinations of the C{TEXT}, C{TAG}, and C{LOC} properties:

    >>> Token(TEXT='movie')
    <movie>
    >>> Token(TEXT='movie', TAG='NN')
    <movie/NN>
    >>> Token(TEXT='movie', LOC=CharSpanLocation(0,5))
    <movie>@[0:5c]
    >>> Token(TEXT='movie', TAG='NN', LOC=CharSpanLocation(0,5))
    <movie/NN>@[0:5c]

New representations can be registered with L{Token.register_repr},
which takes a tuple of properties and a string or function
representation:

    >>> Token.register_repr(('APPLE', 'BAG'), '{{%(APPLE)s::%(BAG)s}}')
    >>> Token(APPLE='foo', BAG=12)
    {{foo::12}}

    >>> def reprfunc(tok):
    ...     props = tok.properties()
    ...     props.sort()
    ...     return '>=<'.join(props)
    >>> Token.register_repr(('BAG','CAR'), reprfunc)
    >>> Token(BAG='zippy', CAR='dooh dah')
    BAG>=<CAR

To deregister a representation, register it as C{None}:

    >>> Token.register_repr(('APPLE', 'BAG'), None)
    >>> Token.register_repr(('BAG', 'CAR'), None)
    >>> Token(APPLE='foo', BAG=12)
    <APPLE='foo', BAG=12>
    >>> Token(BAG='zippy', CAR='dooh dah')
    <BAG='zippy', CAR='dooh dah'>

Copying Tokens
==============
C{Token.copy} creates a new copy of an existing token:

    >>> tok1 = Token(TEXT='car', TAG='NN')
    >>> tok2 = tok1.copy()
    >>> print tok1, tok2
    <car/NN> <car/NN>
    
    >>> tok1 is tok2
    False
    >>> tok1['TEXT'] = 'boat'
    >>> print tok1, tok2
    <boat/NN> <car/NN>

By default, a deep copy is made.  To make a shallow copy, use
C{deep=False}:

    >>> tok1 = Token(A=[1,2,3], B=Token(C=12))
    >>> tok2 = tok1.copy(deep=False)
    >>> tok1 is tok2
    False
    >>> tok1['A'] is tok2['A']
    True
    >>> tok1['B'] is tok2['B']
    True

Freezing Tokens
===============
Tokens are not hashable, and so they can not be used as dictionary
keys:

    >>> tok = Token(TEXT='cold', TAG='JJ')
    >>> {tok:1}
    Traceback (most recent call last):
      [...]
    TypeError: Token objects are unhashable

L{Token.freeze} creates an immutable copy of a token, which I{can} be
as a dictionary key:

    >>> frozen_tok = Token(TEXT='cold', TAG='JJ').freeze()
    >>> {frozen_tok:1}
    {<cold/JJ>: 1}

Frozen tokens are immutable, and can not be modified:

    >>> frozen_tok['TAG'] = 'NN'
    Traceback (most recent call last):
      [...]
    TypeError: FrozenToken objects are immutable

Freezing a cyclic token is currently BROKEN!  I.e., the following code
will I{not} work:

    >>> # tok1, tok2 = Token(), Token()
    >>> # tok1['A'] = tok2
    >>> # tok2['B'] = tok1
    >>> # print tok1.freeze(), tok2.freeze()

Exclude and Project
===================

L{Token.exclude} and L{Token.project} can be used to create a new
token with a restricted set of properties.  C{exclude} creates a new
token that excludes the given list of properties:

    >>> tok1 = Token(TEXT='car', TAG='NN', SPEAKER='Joe')
    >>> tok2 = tok1.exclude('SPEAKER')
    >>> tok3 = tok1.exclude('TEXT', 'TAG')
    >>> print tok1, tok2, tok3
    <SPEAKER='Joe', TAG='NN', TEXT='car'> <car/NN> <SPEAKER='Joe'>

C{project} creates a new token that I{only} includes the given list of
properties:

    >>> tok1 = Token(TEXT='car', TAG='NN', SPEAKER='Joe')
    >>> tok2 = tok1.project('SPEAKER')
    >>> tok3 = tok1.project('TEXT', 'TAG')
    >>> print tok1, tok2, tok3
    <SPEAKER='Joe', TAG='NN', TEXT='car'> <SPEAKER='Joe'> <car/NN>

By default, both C{exclude} and C{project} are recursively applied to
any contained subtokens:

    >>> tok = Token(A=Token(B='x', C=Token(D='d'), E='e'))
    >>> print tok
    <A=<B='x', C=<D='d'>, E='e'>>
    
    >>> print tok.exclude('A')
    <>
    >>> print tok.exclude('B')
    <A=<C=<D='d'>, E='e'>>
    >>> print tok.exclude('C')
    <A=<B='x', E='e'>>
    >>> print tok.exclude('D')
    <A=<B='x', C=<>, E='e'>>
    >>> print tok.exclude('B', 'E')
    <A=<C=<D='d'>>>

    >>> print tok.project('A')
    <A=<>>
    >>> print tok.project('A', 'D')
    <A=<>>
    >>> print tok.project('A', 'C', 'D')
    <A=<C=<D='d'>>>

C{exclude} and C{project} should both work with cyclic properties; but
currently, they do I{NOT}.

    >>> # tok1, tok2 = Token(), Token()
    >>> # tok1['A'] = tok2
    >>> # tok2['B'] = tok1
    >>> # tok2['C'] = tok1
    >>> # print tok1.exclude('B')
"""

def test_FrozenToken():
    """
Unit testing for L{FrozenToken}.

Frozen tokens can be contructed via freezing a normal token, or
directly:

    >>> tok1 = Token(A='a', B=99).freeze()
    >>> tok2 = FrozenToken(A='a', B=99)

Frozen tokens are immutable:

    >>> tok1['A'] = 'newval'
    Traceback (most recent call last):
      [...]
    TypeError: FrozenToken objects are immutable
    >>> del tok1['A']
    Traceback (most recent call last):
      [...]
    TypeError: FrozenToken objects are immutable
    >>> tok1.clear()
    Traceback (most recent call last):
      [...]
    TypeError: FrozenToken objects are immutable
    >>> tok1.pop('A')
    Traceback (most recent call last):
      [...]
    TypeError: FrozenToken objects are immutable
    >>> tok1.popitem()
    Traceback (most recent call last):
      [...]
    TypeError: FrozenToken objects are immutable
    >>> tok1.setdefault('C', 'c')
    Traceback (most recent call last):
      [...]
    TypeError: FrozenToken objects are immutable
    >>> tok1.update({'C': 'c'})
    Traceback (most recent call last):
      [...]
    TypeError: FrozenToken objects are immutable
    
"""

# Copy test_Token, but use SafeTokens instead of Tokens.
def test_SafeToken(): pass
test_SafeToken.__doc__ = test_Token.__doc__.replace(
    'Token.USE_SAFE_TOKENS=False',
    'Token.USE_SAFE_TOKENS=True').replace(
    'Unit testing for L{Token}.',
    'Unit testing for L{SafeToken}.').replace(
    'TypeError: Token objects are unhashable',
    'TypeError: SafeToken objects are unhashable').replace(
    'TypeError: Token objects cannot be used as booleans',
    'TypeError: SafeToken objects cannot be used as booleans').replace(
    'TypeError: len() of unsized Token object',
    'TypeError: len() of unsized SafeToken object')

def test_demo():
    r"""
    >>> mark_stdout_newlines(demo)
    ______________________________________________________________________
    loc  = CharSpanLocation(3, 13, source='corpus.txt')
    loc2 = CharSpanLocation(20, 25, source='corpus.txt')
    <--BLANKLINE-->
    print loc                      => [3:13c]@corpus.txt
    print loc.start                => 3
    print loc.end                  => 13
    print loc.length()             => 10
    print loc.source               => corpus.txt
    print loc2                     => [20:25c]@corpus.txt
    print loc.precedes(loc2)       => True
    print loc.succeeds(loc2)       => False
    print loc.overlaps(loc2)       => False
    ______________________________________________________________________
    tok  = Token(TEXT='flattening', TAG='VBG', LOC=loc)
    tok2 = Token(SIZE=12, WEIGHT=83, LOC=loc2)
    <--BLANKLINE-->
    print tok                      => <flattening/VBG>@[3:13c]
    print tok['LOC']               => [3:13c]@corpus.txt
    print tok.exclude('LOC')       => <flattening/VBG>
    print tok.exclude('TEXT')      => <TAG='VBG'>@[3:13c]
    print tok.project('TEXT')      => <flattening>
    print tok2                     => <SIZE=12, WEIGHT=83>@[20:25c]
    print tok2['LOC']              => [20:25c]@corpus.txt
    print tok == tok2              => False
    print tok == tok.copy()        => True
    """

#######################################################################
# Test Runner
#######################################################################

import sys, os, os.path
if __name__ == '__main__': sys.path[0] = None
import unittest, doctest, trace

def testsuite():
    import doctest, nltk.test.token
    reload(nltk.test.token)
    return doctest.DocTestSuite(nltk.test.token)

def test(verbosity=2):
    runner = unittest.TextTestRunner(verbosity=verbosity)
    runner.run(testsuite())

if __name__ == '__main__':
    test()
