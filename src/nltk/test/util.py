# Natural Language Toolkit: Test Code for Tokens and Tokenizers
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
Unit testing for L{nltk.util}.

@group Sparse Lists: test_SparseList, test_SparseList*, metatest_SparseList*
"""

import sys
from nltk.util import *

def test_SparseListRepr(): """
Unit tests for L{SparseList.__repr__}.  These tests are separated out
from L{test_SparseList}, to make it easier to define
L{metatest_SparseList}.

Create some sparse lists:

    >>> sparselist0 = SparseList({}, 0, 'a')
    >>> sparselist1 = SparseList({0:1, 1:2}, 3, 'b')
    >>> sparselist2 = SparseList({0:'x', 2:'y'}, 5, 'b')
    >>> sparselist3 = SparseList({3:8, 1:8, 2:'c'}, 7, 'c')
    >>> sparselist4 = SparseList({}, 9, 'c')
    >>> sparselist5 = SparseList({0:'a', 1:'b', 2:'c'}, 3, 'x')

Printing Sparse Lists
=====================
Sparse lists' repr is a constructor call that will recreate them:

    >>> sparselist0
    SparseList({}, 0, 'a')
    >>> sparselist1
    SparseList({0: 1, 1: 2}, 3, 'b')
    >>> sparselist2
    SparseList({0: 'x', 2: 'y'}, 5, 'b')
    >>> sparselist3
    SparseList({1: 8, 2: 'c', 3: 8}, 7, 'c')
    >>> sparselist4
    SparseList({}, 9, 'c')
    >>> sparselist5
    SparseList({0: 'a', 1: 'b', 2: 'c'}, 3, 'x')

"""

def test_SparseList(): """
Unit tests for L{SparseList}.

C{SparseList} is a dictionary-backed replacement for C{list}.  Any
positions whose values are not specified by the dictionary are given a
default value.

Sparse List Constructor
=======================
A C{SparseList} is constructed from a dictionary mapping indices to
values, a length, and a default value:

    >>> sparselist = SparseList({1:10, 5:12}, 15, 0)
    >>> print sparselist
    [0, 10, 0, 0, 0, 12, 0, 0, 0, 0, 0, 0, 0, 0, 0]

Create some sparse lists for testing:

    >>> sparselist0 = SparseList({}, 0, 'a')
    >>> sparselist1 = SparseList({0:1, 1:2}, 3, 'b')
    >>> sparselist2 = SparseList({0:'x', 2:'y'}, 5, 'b')
    >>> sparselist3 = SparseList({3:8, 1:8, 2:'c'}, 7, 'c')
    >>> sparselist4 = SparseList({}, 9, 'c')
    >>> sparselist5 = SparseList({0:'a', 1:'b', 2:'c'}, 3, 'x')

List Conversion
===============
Sparse lists can be converted to lists:

    >>> print sparselist0
    []
    >>> print sparselist1
    [1, 2, 'b']
    >>> print sparselist2
    ['x', 'b', 'y', 'b', 'b']
    >>> print sparselist3
    ['c', 8, 'c', 8, 'c', 'c', 'c']
    >>> print sparselist4
    ['c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c']
    >>> print sparselist5
    ['a', 'b', 'c']

Examining Sparse Lists
======================
The len operator tests the length of a sparse list:

    >>> print len(sparselist0), len(sparselist1), len(sparselist2)
    0 3 5
    >>> print len(sparselist3), len(sparselist4), len(sparselist5)
    7 9 3

Sparse lists can be indexed:

    >>> print [sparselist0[i] for i in range(len(sparselist0))]
    []
    >>> print [sparselist1[i] for i in range(len(sparselist1))]
    [1, 2, 'b']
    >>> print [sparselist2[i] for i in range(len(sparselist2))]
    ['x', 'b', 'y', 'b', 'b']
    >>> print [sparselist3[i] for i in range(len(sparselist3))]
    ['c', 8, 'c', 8, 'c', 'c', 'c']
    >>> print [sparselist4[i] for i in range(len(sparselist4))]
    ['c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c']
    >>> print [sparselist5[i] for i in range(len(sparselist5))]
    ['a', 'b', 'c']

Negative indices can be used:

    >>> print [sparselist0[-i] for i in range(1, 1+len(sparselist0))]
    []
    >>> print [sparselist1[-i] for i in range(1, 1+len(sparselist1))]
    ['b', 2, 1]
    >>> print [sparselist2[-i] for i in range(1, 1+len(sparselist2))]
    ['b', 'b', 'y', 'b', 'x']
    >>> print [sparselist3[-i] for i in range(1, 1+len(sparselist3))]
    ['c', 'c', 'c', 8, 'c', 8, 'c']
    >>> print [sparselist4[-i] for i in range(1, 1+len(sparselist4))]
    ['c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c']
    >>> print [sparselist5[-i] for i in range(1, 1+len(sparselist5))]
    ['c', 'b', 'a']

Sparse lists can be indexed with slices:

    >>> print sparselist0[:2], sparselist1[:2], sparselist2[:2]
    [] [1, 2] ['x', 'b']
    >>> print sparselist3[:2], sparselist4[:2], sparselist5[:2]
    ['c', 8] ['c', 'c'] ['a', 'b']
    >>> print sparselist0[2:], sparselist1[2:], sparselist2[2:]
    [] ['b'] ['y', 'b', 'b']
    >>> print sparselist3[2:], sparselist4[2:], sparselist5[2:]
    ['c', 8, 'c', 'c', 'c'] ['c', 'c', 'c', 'c', 'c', 'c', 'c'] ['c']
    >>> print sparselist0[2:4], sparselist1[2:4], sparselist2[2:4]
    [] ['b'] ['y', 'b']
    >>> print sparselist3[2:4], sparselist4[2:4], sparselist5[2:4]
    ['c', 8] ['c', 'c'] ['c']
    >>> print sparselist0[-2:4], sparselist1[-2:4], sparselist2[-2:4]
    [] [2, 'b'] ['b']
    >>> print sparselist3[-2:4], sparselist4[-2:4], sparselist5[-2:4]
    [] [] ['b', 'c']
    >>> print sparselist0[1:-1], sparselist1[1:-1], sparselist2[1:-1]
    [] [2] ['b', 'y', 'b']
    >>> print sparselist3[1:-1], sparselist4[1:-1], sparselist5[1:-1]
    [8, 'c', 8, 'c', 'c'] ['c', 'c', 'c', 'c', 'c', 'c', 'c'] ['b']
    >>> print sparselist0[:-4], sparselist1[:-4], sparselist2[:-4]
    [] [] ['x']
    >>> print sparselist3[:-4], sparselist4[:-4], sparselist5[:-4]
    ['c', 8, 'c'] ['c', 'c', 'c', 'c', 'c'] []

Sparse lists can be iterated over:

    >>> for elt in sparselist0:
    ...     print elt,
    >>> for elt in sparselist1:
    ...     print elt,
    1 2 b
    >>> for elt in sparselist2:
    ...     print elt,
    x b y b b
    >>> for elt in sparselist3:
    ...     print elt,
    c 8 c 8 c c c
    >>> for elt in sparselist4:
    ...     print elt,
    c c c c c c c c c
    >>> for elt in sparselist5:
    ...     print elt,
    a b c

Two lists are equal iff all of their elements are equal.  

    >>> sparselist1 == SparseList({0:1, 1:2}, 3, 'b')
    True
    >>> sparselist1 == SparseList({0:1, 1:2}, 3, 'c')
    False
    >>> sparselist1 == SparseList({0:1, 1:3}, 3, 'b')
    False
    >>> sparselist1 == SparseList({0:1, 1:2}, 4, 'b')
    False

Note that the two lists don't have to have equal representations,
though.  In particular, they might use different defaults.

    >>> sparselist1 == SparseList({0: 1, 2: 'b'}, 3, 2)
    True
    >>> sparselist0 == SparseList({}, 0, 'z')
    True

Sparse list ordering is identical to list ordering.  In particular,
the elements are compared, from left to right; and the first element
that differs is used for comparison.

    >>> def test_cmp(a, b):
    ...     for (op, result) in (('<', a<b),
    ...                          ('<=', a<=b),
    ...                          ('==', a==b),
    ...                          ('>=', a>=b),
    ...                          ('>', a>b)):
    ...         print '%s:%-5s' % (op, result),

    >>> test_cmp(sparselist1, sparselist1)
    <:False <=:True  ==:True  >=:True  >:False
    >>> test_cmp(sparselist1, sparselist2)
    <:True  <=:True  ==:False >=:False >:False
    >>> test_cmp(sparselist1, sparselist3)
    <:True  <=:True  ==:False >=:False >:False
    >>> test_cmp(sparselist1, sparselist4)
    <:True  <=:True  ==:False >=:False >:False
    >>> test_cmp(sparselist1, sparselist5)
    <:True  <=:True  ==:False >=:False >:False

If one sparse list is a (proper) prefix of the other, then the longer
list is considered greater.

    >>> test_cmp(sparselist0, sparselist2)
    <:True  <=:True  ==:False >=:False >:False
    >>> test_cmp(sparselist1, sparselist1+[1,2,3])
    <:True  <=:True  ==:False >=:False >:False

C{count} returns the number of times that a given value appears in the
list:

    >>> sparselist0.count(0)
    0
    >>> sparselist0.count('a')
    0
    >>> sparselist1.count(1)
    1
    >>> sparselist1.count('b')
    1
    >>> sparselist2.count('x')
    1
    >>> sparselist2.count('b')
    3
    >>> sparselist3.count(8)
    2
    >>> sparselist3.count('c')
    5
    >>> sparselist4.count(0)
    0
    >>> sparselist4.count('c')
    9
    >>> sparselist5.count('a')
    1
    >>> sparselist5.count('x')
    0

C{index()} returns the first index at which a given value appears:
 
    >>> sparselist1.index(1)
    0
    >>> sparselist1.index('b')
    2
    >>> sparselist2.index('x')
    0
    >>> sparselist2.index('b')
    1
    >>> sparselist3.index(8)
    1
    >>> sparselist3.index('c')
    0
    >>> sparselist4.index('c')
    0
    >>> sparselist5.index('a')
    0

If the value doesn't appear in the list, C{index()} raises a
C{ValueError}:

    >>> sparselist0.index(0)
    Traceback (most recent call last):
    ValueError: list.index(x): x not in list
    >>> sparselist0.index('a')
    Traceback (most recent call last):
    ValueError: list.index(x): x not in list
    >>> sparselist4.index(0)
    Traceback (most recent call last):
    ValueError: list.index(x): x not in list
    >>> sparselist5.index('x')
    Traceback (most recent call last):
    ValueError: list.index(x): x not in list
    
Sparse lists are not hashable:

    >>> hash(sparselist0)
    Traceback (most recent call last):
    TypeError: list objects are unhashable
    >>> hash(sparselist5)
    Traceback (most recent call last):
    TypeError: list objects are unhashable

Sparse lists can be tested for containership:

    >>> print 1 in sparselist0, 1 in sparselist1, 1 in sparselist2
    False True False

A sparse list contains its default if any value isn't explicitly
specified:

    >>> print 'c' in sparselist4, 'b' in sparselist1
    True True
    >>> print 'x' in sparselist5
    False

Transforming/Creating Sparse Lists
==================================
Sparse lists can be concatenated to each other or to normal lists:

    >>> print sparselist0 + sparselist1
    [1, 2, 'b']
    >>> print sparselist2 + sparselist3
    ['x', 'b', 'y', 'b', 'b', 'c', 8, 'c', 8, 'c', 'c', 'c']
    
    >>> print sparselist1 + [1,2,3]
    [1, 2, 'b', 1, 2, 3]
    >>> print [1,2,3] + sparselist1
    [1, 2, 3, 1, 2, 'b']

Sparse lists can be multiplied by integers:

    >>> print sparselist1*3
    [1, 2, 'b', 1, 2, 'b', 1, 2, 'b']
    >>> print 2*sparselist2
    ['x', 'b', 'y', 'b', 'b', 'x', 'b', 'y', 'b', 'b']

Item Deletion
=============
Items can be deleted from lists:

    >>> # All default values.
    >>> sparselist = SparseList({}, 9, 'd')
    >>> print sparselist
    ['d', 'd', 'd', 'd', 'd', 'd', 'd', 'd', 'd']
    >>> del sparselist[-1]; print sparselist
    ['d', 'd', 'd', 'd', 'd', 'd', 'd', 'd']
    >>> del sparselist[0]; print sparselist
    ['d', 'd', 'd', 'd', 'd', 'd', 'd']
    >>> del sparselist[3]; print sparselist
    ['d', 'd', 'd', 'd', 'd', 'd']

    >>> # Some default values.
    >>> sparselist = SparseList({0:0, 2:2}, 3, 'd')
    >>> print sparselist
    [0, 'd', 2]
    >>> del sparselist[0]; print sparselist
    ['d', 2]
    >>> del sparselist[-1]; print sparselist
    ['d']
    >>> del sparselist[0]; print sparselist
    []

    >>> # No default values.
    >>> sparselist = SparseList({0:0, 1:1, 2:2}, 3, 'd')
    >>> print sparselist
    [0, 1, 2]
    >>> del sparselist[0]; print sparselist
    [1, 2]
    >>> del sparselist[-1]; print sparselist
    [1]
    >>> del sparselist[-1]; print sparselist
    []

Deleting out-of-range items raises an exception:

    >>> sparselist = SparseList({0:0, 1:1, 2:2}, 3, 'd')
    >>> del sparselist[6]
    Traceback (most recent call last):
    IndexError: list assignment index out of range
    >>> del sparselist[-6]
    Traceback (most recent call last):
    IndexError: list assignment index out of range

Slices can be deleted from lists:

    >>> # All default values.
    >>> sparselist = SparseList({}, 9, 'd')
    >>> print sparselist
    ['d', 'd', 'd', 'd', 'd', 'd', 'd', 'd', 'd']
    >>> del sparselist[0:2]; print sparselist
    ['d', 'd', 'd', 'd', 'd', 'd', 'd']
    >>> del sparselist[-3:-1]; print sparselist
    ['d', 'd', 'd', 'd', 'd']
    >>> del sparselist[2:2]; print sparselist
    ['d', 'd', 'd', 'd', 'd']
    >>> del sparselist[:]; print sparselist
    []
    
    >>> # Some default values.
    >>> sparselist = SparseList({0:0, 6:2}, 10, 'd')
    >>> print sparselist
    [0, 'd', 'd', 'd', 'd', 'd', 2, 'd', 'd', 'd']
    >>> del sparselist[1:3]; print sparselist
    [0, 'd', 'd', 'd', 2, 'd', 'd', 'd']
    >>> del sparselist[-3:-1]; print sparselist
    [0, 'd', 'd', 'd', 2, 'd']
    >>> del sparselist[2:2]; print sparselist
    [0, 'd', 'd', 'd', 2, 'd']
    >>> del sparselist[:]; print sparselist
    []

    >>> # No default values.
    >>> sparselist = SparseList({0:0, 1:1, 2:2, 3:3, 4:4, 5:5}, 6, 'd')
    >>> print sparselist
    [0, 1, 2, 3, 4, 5]
    >>> del sparselist[1:3]; print sparselist
    [0, 3, 4, 5]
    >>> del sparselist[-3:-1]; print sparselist
    [0, 5]
    >>> del sparselist[2:2]; print sparselist
    [0, 5]
    >>> del sparselist[:]; print sparselist
    []

Deleting slices that extend out-of-range deletes those elements that
are in-range:

    >>> sparselist = SparseList({0:0, 1:1, 2:2, 3:3, 4:4, 5:5}, 6, 'd')
    >>> print sparselist
    [0, 1, 2, 3, 4, 5]
    >>> del sparselist[10:15]; print sparselist
    [0, 1, 2, 3, 4, 5]
    >>> del sparselist[-15:-10]; print sparselist
    [0, 1, 2, 3, 4, 5]
    >>> del sparselist[-9:2]; print sparselist
    [2, 3, 4, 5]
    >>> del sparselist[1:1000]; print sparselist
    [2]

Item Modification:
==================
Items can be modified:

    >>> # All default values.
    >>> sparselist = SparseList({}, 9, 'd')
    >>> print sparselist
    ['d', 'd', 'd', 'd', 'd', 'd', 'd', 'd', 'd']
    >>> sparselist[-1] = 1; print sparselist
    ['d', 'd', 'd', 'd', 'd', 'd', 'd', 'd', 1]
    >>> sparselist[0] = 2; print sparselist
    [2, 'd', 'd', 'd', 'd', 'd', 'd', 'd', 1]
    >>> sparselist[3] = 'd'; print sparselist
    [2, 'd', 'd', 'd', 'd', 'd', 'd', 'd', 1]
    >>> sparselist[0] = 4; print sparselist
    [4, 'd', 'd', 'd', 'd', 'd', 'd', 'd', 1]
    
    >>> # Some default values.
    >>> sparselist = SparseList({0:0, 2:2}, 3, 'd')
    >>> print sparselist
    [0, 'd', 2]
    >>> sparselist[0] = 2; print sparselist
    [2, 'd', 2]
    >>> sparselist[-1] = 0; print sparselist
    [2, 'd', 0]
    >>> sparselist[0] = 'd'; print sparselist
    ['d', 'd', 0]
    
    >>> # No default values.
    >>> sparselist = SparseList({0:0, 1:1, 2:2}, 3, 'd')
    >>> print sparselist
    [0, 1, 2]
    >>> sparselist[0] = 0; print sparselist
    [0, 1, 2]
    >>> sparselist[-1] = 4; print sparselist
    [0, 1, 4]
    >>> sparselist[-1] = 2; print sparselist
    [0, 1, 2]

Modifying out-of-range items raises an exception:

    >>> sparselist = SparseList({0:0, 1:1, 2:2}, 3, 'd')
    >>> sparselist[6] = 0
    Traceback (most recent call last):
    IndexError: list assignment index out of range
    >>> sparselist[-6] = 0
    Traceback (most recent call last):
    IndexError: list assignment index out of range

Slices can be modified:

    >>> # All default values.
    >>> sparselist = SparseList({}, 9, 'd')
    >>> print sparselist
    ['d', 'd', 'd', 'd', 'd', 'd', 'd', 'd', 'd']
    >>> sparselist[0:2] = []; print sparselist
    ['d', 'd', 'd', 'd', 'd', 'd', 'd']
    >>> sparselist[-3:-1] = [1,2]; print sparselist
    ['d', 'd', 'd', 'd', 1, 2, 'd']
    >>> sparselist[2:2] = [3]; print sparselist
    ['d', 'd', 3, 'd', 'd', 1, 2, 'd']
    >>> sparselist[:] = [1,2,3]; print sparselist
    [1, 2, 3]
    
    >>> # Some default values.
    >>> sparselist = SparseList({0:0, 6:2}, 10, 'd')
    >>> print sparselist
    [0, 'd', 'd', 'd', 'd', 'd', 2, 'd', 'd', 'd']
    >>> sparselist[1:3] = []; print sparselist
    [0, 'd', 'd', 'd', 2, 'd', 'd', 'd']
    >>> sparselist[-3:-1] = [1,2]; print sparselist
    [0, 'd', 'd', 'd', 2, 1, 2, 'd']
    >>> sparselist[2:2] = [3]; print sparselist
    [0, 'd', 3, 'd', 'd', 2, 1, 2, 'd']

    >>> # No default values.
    >>> sparselist = SparseList({0:0, 1:1, 2:2, 3:3, 4:4, 5:5}, 6, 'd')
    >>> print sparselist
    [0, 1, 2, 3, 4, 5]
    >>> sparselist[1:3] = []; print sparselist
    [0, 3, 4, 5]
    >>> sparselist[-3:-1] = [1,2]; print sparselist
    [0, 1, 2, 5]
    >>> sparselist[2:2] = [3]; print sparselist
    [0, 1, 3, 2, 5]

Slices can extend out-of-range for modification; they are rounded to
the list boundaries:

    >>> sparselist = SparseList({0:0, 1:1, 2:2, 3:3, 4:4, 5:5}, 6, 'd')
    >>> print sparselist
    [0, 1, 2, 3, 4, 5]
    >>> sparselist[10:15] = [6, 7]; print sparselist
    [0, 1, 2, 3, 4, 5, 6, 7]
    >>> sparselist[-20:-15] = [-2, -1]; print sparselist
    [-2, -1, 0, 1, 2, 3, 4, 5, 6, 7]
    >>> sparselist[-20:2] = [0, 0]; print sparselist
    [0, 0, 0, 1, 2, 3, 4, 5, 6, 7]
    >>> sparselist[1:1000] = [99]; print sparselist
    [0, 99]

Append and pop can be used to add and remove elements from the end of
a sparse list:

    >>> sparselist = SparseList({0:0, 1:1}, 2, 'd')
    >>> print sparselist
    [0, 1]
    >>> sparselist.append('d'); print sparselist
    [0, 1, 'd']
    >>> sparselist.append(2); print sparselist
    [0, 1, 'd', 2]
    >>> print sparselist.pop(), sparselist
    2 [0, 1, 'd']
    >>> print sparselist.pop(), sparselist
    d [0, 1]
    >>> print sparselist.pop(), sparselist
    1 [0]
    >>> print sparselist.pop(), sparselist
    0 []
    >>> sparselist.pop()
    Traceback (most recent call last):
    IndexError: pop from empty list

Insert and pop(i) can be used to add and remove elements from anywhere
in the list: [XX] fill this in!

Remove can be used to remove specific values: [XX] fill this in

Sparse lists can be concatinated in-place with extend():

    >>> sparselist = SparseList({}, 4, 'd')
    >>> sparselist.extend(['x', 'y', 'z'])
    >>> print sparselist
    ['d', 'd', 'd', 'd', 'x', 'y', 'z']
    >>> lst = [1,2,3]
    >>> lst.extend(sparselist)
    >>> print lst
    [1, 2, 3, 'd', 'd', 'd', 'd', 'x', 'y', 'z']
    
Sparse lists can be sorted:

    >>> sparselist = SparseList({}, 4, 0)
    >>> print sparselist; sparselist.sort(); print sparselist
    [0, 0, 0, 0]
    [0, 0, 0, 0]
    
    >>> sparselist = SparseList({1:-5, 3:5}, 4, 0)
    >>> print sparselist; sparselist.sort(); print sparselist
    [0, -5, 0, 5]
    [-5, 0, 0, 5]

    >>> sparselist = SparseList({0:3, 1:1, 2:0, 3:-4}, 4, 0)
    >>> print sparselist; sparselist.sort(); print sparselist
    [3, 1, 0, -4]
    [-4, 0, 1, 3]
    
    >>> sparselist = SparseList({0:3, 1:1, 2:2, 3:-4}, 4, 0)
    >>> print sparselist; sparselist.sort(); print sparselist
    [3, 1, 2, -4]
    [-4, 1, 2, 3]
    
    >>> sparselist = SparseList({0:3, 1:1, 2:0, 3:-4}, 8, 0)
    >>> print sparselist; sparselist.sort(); print sparselist
    [3, 1, 0, -4, 0, 0, 0, 0]
    [-4, 0, 0, 0, 0, 0, 1, 3]
    
Sparse lists can be reversed:

    >>> sparselist = SparseList({}, 4, 0)
    >>> print sparselist; sparselist.reverse(); print sparselist
    [0, 0, 0, 0]
    [0, 0, 0, 0]
    
    >>> sparselist = SparseList({1:-5, 3:5}, 4, 0)
    >>> print sparselist; sparselist.reverse(); print sparselist
    [0, -5, 0, 5]
    [5, 0, -5, 0]

    >>> sparselist = SparseList({0:3, 1:1, 2:0, 3:-4}, 4, 0)
    >>> print sparselist; sparselist.reverse(); print sparselist
    [3, 1, 0, -4]
    [-4, 0, 1, 3]
    
    >>> sparselist = SparseList({0:3, 1:1, 3:-4}, 4, 0)
    >>> print sparselist; sparselist.reverse(); print sparselist
    [3, 1, 0, -4]
    [-4, 0, 1, 3]
    

"""

def metatest_SparseList(): """
Verify that the tests run by C{test_SparseList} properly reflect the
behavior of C{list}.  To do this, we run the same tests, but use the
following replacement definition of the SparseList constructor:

    >>> _SparseList = SparseList
    >>> def SparseList(*args):
    ...     return list(_SparseList(*args))
    
%s
"""
metatest_SparseList.__doc__ %= test_SparseList.__doc__


#######################################################################
# Test Runner
#######################################################################

import sys, os, os.path
if __name__ == '__main__': sys.path[0] = None
import unittest, doctest, trace

def testsuite():
    import doctest, nltk.test.util
    reload(nltk.test.util)
    return doctest.DocTestSuite(nltk.test.util)

def test(verbosity=2):
    runner = unittest.TextTestRunner(verbosity=verbosity)
    runner.run(testsuite())

if __name__ == '__main__':
    test()
