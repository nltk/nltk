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

def test_Token(): """
Unit testing for L{Token}.

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
    
    >>> tok.get('TAG', 'VB')
    'NN'
    >>> tok.get('TOG', 'VB')
    'VB'
    
    >>> tok.update({'TOG': 'XYZ'})
    >>> print tok
    <ACCENT=3, TAG='NN', TEXT='watch', TOG='XYZ'>

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

By default, a deep copy is made:

    >>> tok1 = Token(A=[1,2,3], B=Token(C=12))
    >>> tok2 = tok1.copy()
    >>> tok1 is tok2
    False
    >>> tok1['A'] is tok2['A']
    False
    >>> tok1['B'] is tok2['B']
    False

To make a shallow copy, use C{deep=False}:

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

Any contained objects are also frozen.  Lists are automatically
converted to tuples, and dicts to FrozenDicts.

    >>> Token(A=Token(B=12)).freeze()
    <A=<B=12>>
    >>> Token(A=[1, Token(B=12)]).freeze()
    <A=(1, <B=12>)>
    >>> Token(A=(1, Token(B=12))).freeze()
    <A=(1, <B=12>)>
    >>> Token(A={1: Token(B=12)}).freeze()
    <A={1: <B=12>}>
    >>> type(Token(A={1: Token(B=12)}).freeze()['A'])
    <class 'nltk.util.FrozenDict'>

Iterators are automatically converted to tuples:

    >>> tokiter = iter([1, Token(B='x', C='y')])
    >>> Token(A=tokiter).freeze()
    <A=(1, <B='x', C='y'>)>

Cyclic tokens can be frozen:

    >>> tok1, tok2 = Token(), Token()
    >>> tok1['A'] = tok2
    >>> tok2['B'] = tok1
    >>> print tok1.freeze(), tok2.freeze()
    <A=<B=...>> <B=<A=...>>

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

This includes subtokens included in lists, tuples, and dictionaries:

    >>> Token(A=[1, Token(B='x', C='y')]).exclude('B')
    <A=[1, <C='y'>]>
    >>> Token(A=(1, Token(B='x', C='y'))).exclude('B')
    <A=(1, <C='y'>)>
    >>> Token(A={1: Token(B='x', C='y')}).exclude('B')
    <A={1: <C='y'>}>

It also includes iterators:

    >>> tokiter = iter([1, Token(B='x', C='y')])
    >>> tok = Token(A=tokiter).exclude('B')
    >>> for elt in tok['A']:
    ...     print elt
    1
    <C='y'>
    
C{exclude} and C{project} both work with cyclic tokens:

    >>> tok1, tok2 = Token(), Token()
    >>> tok1['A'] = tok2
    >>> tok2['B'] = tok1
    >>> tok2['C'] = tok1
    >>> print tok1
    <A=<B=..., C=...>>
    >>> print tok1.exclude('B')
    <A=<C=...>>
"""

def test_TokenReprLocError(): """
Currently, the generic repr function checks that the C{LOC} property
is actually a location:

    >>> Token.USE_SAFE_TOKEN = False
    >>> print Token(A='x', LOC='y')
    Traceback (most recent call last):
      [...]
    AssertionError: self['LOC'] is not a location!

"""

def test_FrozenToken(): """
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

def test_SafeToken_checks(): """
Additional unit tests for C{SafeToken}.

    >>> Token.USE_SAFE_TOKENS=True

The C{LOC} property must contain a location:

    >>> Token(TEXT='dog', LOC=CharSpanLocation(0,2))
    <dog>@[0:2c]
    >>> Token(TEXT='dog', LOC=(0,2))
    Traceback (most recent call last):
      [...]
    TypeError: The 'LOC' property must contain a Location
    >>> Token(TEXT='dog')['LOC'] = (0,2)
    Traceback (most recent call last):
      [...]
    TypeError: The 'LOC' property must contain a Location
    >>> Token(TEXT='dog').setdefault('LOC', (0,2))
    Traceback (most recent call last):
      [...]
    TypeError: The 'LOC' property must contain a Location
    >>> Token(TEXT='dog').update({'LOC': (0,2)})
    Traceback (most recent call last):
      [...]
    TypeError: The 'LOC' property must contain a Location

Exclude and project can't be given bad options:

    >>> Token().project(x=1)
    Traceback (most recent call last):
      [...]
    ValueError: Bad option 'x'
    >>> Token().exclude(x=1)
    Traceback (most recent call last):
      [...]
    ValueError: Bad option 'x'
"""

def test_Location(): """
Unit tests for L{LocationI} and its implementations.

C{LocationI} is an abstract interface for locations.  It can't be
instantiated directly:

    >>> LocationI()
    Traceback (most recent call last):
      [...]
    AssertionError: Interfaces can't be instantiated

It declares 3 methods, which must be implemented by derived classes:

    >>> class BrokenLocation(LocationI):
    ...     pass
    >>> BrokenLocation().source()
    Traceback (most recent call last):
      [...]
    AssertionError
    >>> cmp(BrokenLocation(), 1)
    Traceback (most recent call last):
      [...]
    AssertionError
    >>> hash(BrokenLocation())
    Traceback (most recent call last):
      [...]
    AssertionError

C{SpanLocation} is an abstract base class for locations that are based
on spans.  It can't be instantiated directly:

    >>> SpanLocation(0,1)
    Traceback (most recent call last):
      [...]
    AssertionError: Abstract classes can't be instantiated

CharSpanLocation
================

C{CharSpanLocation} is a location class derived from C{SpanLocation}.
A C{CharSpanLocation} is constructed from a start, an end, and an
optional source:

    >>> loc1 = CharSpanLocation(0, 5, 'foo.txt')
    >>> loc2 = CharSpanLocation(0, 5)
    >>> loc3 = CharSpanLocation(8, 12)
    >>> print loc1, loc2, loc3
    [0:5c]@foo.txt [0:5c] [8:12c]

The start, end, and source are accessed via methods:

    >>> print loc1.start(), loc1.end(), loc1.source()
    0 5 foo.txt

The length is available via a C{length} method, and the C{len}
operator:

    >>> print loc1.length(), len(loc1)
    5 5
    >>> print loc3.length(), len(loc3)
    4 4

C{CharSpanLocations} are equal if their start, end, and source are
equal:

    >>> loc1 = CharSpanLocation(0,5,'foo.txt')
    >>> loc2 = CharSpanLocation(1,5,'foo.txt')
    >>> loc3 = CharSpanLocation(0,6,'foo.txt')
    >>> loc4 = CharSpanLocation(0,5)
    >>> loc5 = CharSpanLocation(0,5,'bar.txt')
    >>> print loc1==loc1, loc1==loc2, loc1==loc3, loc1==loc4, loc1==loc5
    True False False False False

    >>> loc1 == CharSpanLocation(0,5,'foo.txt')
    True

C{CharSpanLocations} are hashable, and so they can be used as
dictionary keys:

    >>> {loc1: 10}
    {[0:5c]: 10}

Ordering
--------
A total ordering on C{CharSpanLocations} is defined by preceeds,
succeeds, and overlaps.

Two locations overlap if one's start falls between the other's start
and end:

    >>> loc1 = CharSpanLocation(8,12)
    >>> loc2 = CharSpanLocation(10,14)
    >>> print loc1.overlaps(loc2), loc2.overlaps(loc1)
    True True

Two locations are also considered to overlap if they are both
zero-length locations at the same index:
    
    >>> loc1 = CharSpanLocation(8,8)
    >>> loc2 = CharSpanLocation(8,8)
    >>> print loc1.overlaps(loc2)
    True

Two locations are I{not} considered to overlap if they share a common
boundary:

    >>> loc1 = CharSpanLocation(8, 12)
    >>> loc2 = CharSpanLocation(12, 14)
    >>> print loc1.overlaps(loc2), loc2.overlaps(loc1)
    False False

Note that this definition of I{overlaps} is symmetric and reflexive,
but not transitive:

    >>> loc1 = CharSpanLocation(8, 12)
    >>> loc2 = CharSpanLocation(11, 15)
    >>> loc3 = CharSpanLocation(14, 20)
    >>> print loc1.overlaps(loc2), loc2.overlaps(loc3), loc1.overlaps(loc3)
    True True False

C{precedes} and C{succeeds} test if a location occurs entirely before
or after another location.

    >>> loc1 = CharSpanLocation(8,12)
    >>> loc2 = CharSpanLocation(14,15)
    >>> print loc1.precedes(loc2), loc2.succeeds(loc1)
    True True
    >>> print loc1.succeeds(loc2), loc2.precedes(loc1)
    False False
    >>> loc1.succeeds(loc1)
    False

loc1 precedes loc2 if they share a common boundary:

    >>> loc1 = CharSpanLocation(8, 12)
    >>> loc2 = CharSpanLocation(12, 14)
    >>> loc1.precedes(loc2)
    True

loc1 can preceed loc2 if I{either} is zero-length:

    >>> loc1 = CharSpanLocation(12,12)
    >>> loc2 = CharSpanLocation(12,14)
    >>> loc3 = CharSpanLocation(14,14)
    >>> print loc1.precedes(loc2), loc2.precedes(loc3)
    True True

But not if both are zero-length:
    
    >>> loc1 = CharSpanLocation(12,12)
    >>> print loc1.precedes(loc1)
    False

Note that I{precedes} and I{succeds} are anti-symmetric,
anti-reflexive, and transitive.

For any two locations, exactly one of the following will always be
true:

  - C{loc1.precedes(loc2)}
  - C{loc1.succeeds(loc2)}
  - C{loc1.overlaps(loc2)}

To compare locations with precedes, succeeds, and overlaps, they must
have compatible sources and location types:

    >>> loc1 = CharSpanLocation(8,12, source='foo.txt')
    >>> loc2 = CharSpanLocation(8,12, source='bar.txt')
    >>> loc3 = WordIndexLocation(1, source='foo.txt')
   
    >>> loc1.precedes(loc2)
    Traceback (most recent call last):
      [...]
    ValueError: Locations have incompatible sources
    >>> loc1.precedes(loc3)
    Traceback (most recent call last):
      [...]
    ValueError: Locations have incompatible types

    >>> loc1.succeeds(loc2)
    Traceback (most recent call last):
      [...]
    ValueError: Locations have incompatible sources
    >>> loc1.succeeds(loc3)
    Traceback (most recent call last):
      [...]
    ValueError: Locations have incompatible types

    >>> loc1.overlaps(loc2)
    Traceback (most recent call last):
      [...]
    ValueError: Locations have incompatible sources
    >>> loc1.overlaps(loc3)
    Traceback (most recent call last):
      [...]
    ValueError: Locations have incompatible types

Contiguous Locations & Union
----------------------------
Two locations are contiguous if they share a common boundary:

    >>> loc1 = CharSpanLocation(8,12)
    >>> loc2 = CharSpanLocation(12,14)
    >>> print loc1.contiguous(loc2), loc2.contiguous(loc1)
    True True
    
    >>> loc3 = CharSpanLocation(13, 14)
    >>> loc1.contiguous(loc3)
    False

Either location can be zero-length:

    >>> loc1 = CharSpanLocation(8,8)
    >>> loc2 = CharSpanLocation(8,12)
    >>> loc3 = CharSpanLocation(12,12)
    >>> print loc1.contiguous(loc2), loc2.contiguous(loc3)
    True True

Or both can be:

    >>> loc1 = CharSpanLocation(8,8)
    >>> print loc1.contiguous(loc1)
    True

If two locations are contiguous, then they can be joined via C{union},
which returns a new location spanning both of them:

    >>> loc1 = CharSpanLocation(8,12)
    >>> loc2 = CharSpanLocation(12,14)
    >>> print loc1.union(loc2)
    [8:14c]
    >>> print loc2.union(loc1)
    [8:14c]

    # Union can also be written as addition
    >>> print loc1 + loc2
    [8:14c]

If the locations are not contiguous, they cannot be joined:

    >>> loc1 = CharSpanLocation(8,12)
    >>> loc2 = CharSpanLocation(13,14)
    >>> loc1.union(loc2)
    Traceback (most recent call last):
      [...]
    ValueError: Locations are not contiguous
    
To compare locations with contiguous(), or to take their union, they
must have compatible sources and location types:

    >>> loc1 = CharSpanLocation(8,12, source='foo.txt')
    >>> loc2 = CharSpanLocation(8,12, source='bar.txt')
    >>> loc3 = WordIndexLocation(1, source='foo.txt')
   
    >>> loc1.contiguous(loc2)
    Traceback (most recent call last):
      [...]
    ValueError: Locations have incompatible sources
    >>> loc1.contiguous(loc3)
    Traceback (most recent call last):
      [...]
    ValueError: Locations have incompatible types
    >>> loc1.union(loc2)
    Traceback (most recent call last):
      [...]
    ValueError: Locations have incompatible sources
    >>> loc1.union(loc3)
    Traceback (most recent call last):
      [...]
    ValueError: Locations have incompatible types

Infinity
--------
Under special circumstances, it can be useful to use -INF as a
location's tart, or +INF as its end.  This is done with
C{SpanLocation.MIN} and C{SpanLocation.MAX}:

    >>> loc1 = CharSpanLocation(SpanLocation.MIN, 8)
    >>> loc2 = CharSpanLocation(8, 12)
    >>> loc3 = CharSpanLocation(12, SpanLocation.MAX)
    >>> print loc1, loc2, loc3
    [-INF:8c] [8:12c] [12:+INFc]

    >>> print loc1.precedes(loc2), loc2.precedes(loc3)
    True True
    >>> print loc1+loc2+loc3
    [-INF:+INFc]

Select
------
L{SpanLocation.select} can be used to select the text specified by a
location:

    >>> text = 'a small frog is sleeping'
    >>> loc = CharSpanLocation(8, 12)
    >>> loc.select(text)
    'frog'

IndexLocations
==============
C{IndexLocation} is an abstract base class for locations that are based
on indexes.  It can't be instantiated directly:

    >>> IndexLocation(0)
    Traceback (most recent call last):
      [...]
    AssertionError: Abstract classes can't be instantiated

It is implemented by C{WordIndexLocation}, C{SentIndexLocation}, and
C{ParaIndexLocation}:

    >>> loc1 = WordIndexLocation(1)
    >>> loc2 = SentIndexLocation(2)
    >>> loc3 = ParaIndexLocation(3)
    >>> print loc1, loc2, loc3
    [1w] [2s] [3p]

    >>> print loc1.index(), loc2.index(), loc3.index()
    1 2 3

Index locations can have sources:

    >>> loc1 = WordIndexLocation(1, 'foo.txt')
    >>> loc2 = SentIndexLocation(2, 'bar.txt')
    >>> loc3 = ParaIndexLocation(3, 'baz.txt')
    >>> print loc1, loc2, loc3
    [1w]@foo.txt [2s]@bar.txt [3p]@baz.txt
    >>> loc1.source()
    'foo.txt'

Sometimes it can be useful to use index locations as sources for other
index locations, to provide hierarchical location specifications:

    >>> loc1 = ParaIndexLocation(8, 'foo.txt')
    >>> loc2 = SentIndexLocation(3, loc1)
    >>> loc3 = WordIndexLocation(5, loc2)
    >>> print loc3
    [5w]@[3s]@[8p]@foo.txt

Index locations are hashable, and so can be used as dictionary keys:

    >>> {WordIndexLocation(3): 1}
    {[3w]: 1}

Index locations are ordered, and can be compared with cmp:

    >>> loc1 = WordIndexLocation(3)
    >>> loc2 = WordIndexLocation(5)
    >>> loc1 < loc2
    True

"""

def test_ProbabilisticToken(): """
Probablistic tokens will probably be deprecated.  But in the mean
time, this covers the code in ProbabilisticToken:

    >>> ProbabilisticToken(0.25, TEXT='dog')
    <dog> (p=0.25)
"""
    

def test_demo(): r"""
Unit tests for L{nltk.token.demo}.
    
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
