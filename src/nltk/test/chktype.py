# Natural Language Toolkit: Test Code for Type Checking
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
Unit testing for L{nltk.chktype}.
"""

from nltk.chktype import *
from nltk.util import mark_stdout_newlines
import types

##//////////////////////////////////////////////////////
##  Test code
##//////////////////////////////////////////////////////

def test_chktype(): r"""
Unit test cases for L{nltk.chktype}.

The amount of type checking performed is controlled by the type safety
level, which is set with L{type_safety_level}:

    >>> old_level = type_safety_level(4)

C{chktype} is used by adding calls to C{chktype} at the top of a
function or method, checking the types of the inputs:

    >>> def demo(x, f, s):
    ...     assert chktype(1, x, int, long)
    ...     assert chktype(2, f, float)
    ...     assert chktype(3, s, str)
    ...     return 'ok'

Calls with correct argument types proceed normally:

    >>> demo(1, 1.0, 'hello')
    'ok'
    >>> demo(-5, 1.0, '')
    'ok'
    >>> demo(12L, 1.0, 'hello')
    'ok'

Calls with invalid argument types raise exceptions.  Define a test
function, to capture the exception string & collapse whitespace
(because doctest can't deal w/ multiline exception strings):

    >>> def test(func, *args):
    ...     try: func(*args)
    ...     except TypeError, e: 
    ...         raise TypeError(' '.join(str(e).split()))

Now call the demo function with bad argument types:

    >>> test(demo, 1.0, 1.0, 'hello')
    Traceback (most recent call last):
    TypeError: Argument 1 to demo() must have type: (int or long) (got a float)

    >>> test(demo, 1, 1, 'hello')
    Traceback (most recent call last):
     ...
    TypeError: Argument 2 to demo() must have type: float (got a int)

    >>> test(demo, 1, 1L, 'hello')
    Traceback (most recent call last):
     ...
    TypeError: Argument 2 to demo() must have type: float (got a long)

    >>> test(demo, 1, 'x', 'hello')
    Traceback (most recent call last):
     ...
    TypeError: Argument 2 to demo() must have type: float (got a str)

    >>> test(demo, 'x', 1.0, 'hello')
    Traceback (most recent call last):
    ...
    TypeError: Argument 1 to demo() must have type: (int or long) (got a str)

    >>> test(demo, 0, 0.0, 12)
    Traceback (most recent call last):
    ...
    TypeError: Argument 3 to demo() must have type: str (got a int)

    >>> test(demo, 0, 1.0, ['h', 'i'])
    Traceback (most recent call last):
    ...
    TypeError: Argument 3 to demo() must have type: str (got a list)

    >>> test(demo, [0], 1.0, 'hi')
    Traceback (most recent call last):
    ...
    TypeError: Argument 1 to demo() must have type: (int or long) (got a list)

    >>> test(demo, 0, [1.0], 'hi')
    Traceback (most recent call last):
    ...
    TypeError: Argument 2 to demo() must have type: float (got a list)

List Type Checks
================

    >>> def demo(list1, list2, list3):
    ...     assert chktype(1, list1, [])
    ...     assert chktype(2, list2, [int])
    ...     assert chktype(3, list3, [int, [str]])
    ...     return 'ok'

These should be fine:

    >>> demo([], [], [])
    'ok'
    >>> demo(['x'], [1], [1])
    'ok'
    >>> demo(['a', {}, (), 3], [1,2], [3,4])
    'ok'
    >>> demo([], [], [1, ['x'], 2, ['y', 'z']])
    'ok'

These should raise exceptions:

    >>> test(demo, (), [], [])
    Traceback (most recent call last):
    ...
    TypeError: Argument 1 to demo() must have type: list (got a tuple)
    
    >>> test(demo, [], (), [])
    Traceback (most recent call last):
    ...
    TypeError: Argument 2 to demo() must have type: (list of int) (got a tuple)
    
    >>> test(demo, [], [], ())
    Traceback (most recent call last):
    ...
    TypeError: Argument 3 to demo() must have type: (list of (int or (list of str))) (got a tuple)

    >>> test(demo, {}, [], [])
    Traceback (most recent call last):
    ...
    TypeError: Argument 1 to demo() must have type: list (got a dict)

    >>> test(demo, [], {}, [])
    Traceback (most recent call last):
    ...
    TypeError: Argument 2 to demo() must have type: (list of int) (got a dict)

    >>> test(demo, [], [], {})
    Traceback (most recent call last):
    ...
    TypeError: Argument 3 to demo() must have type: (list of (int or (list of str))) (got a dict)

    >>> test(demo, 1, [], [])
    Traceback (most recent call last):
    ...
    TypeError: Argument 1 to demo() must have type: list (got a int)

    >>> test(demo, [], 1, [])
    Traceback (most recent call last):
    ...
    TypeError: Argument 2 to demo() must have type: (list of int) (got a int)

    >>> test(demo, [], [], 1)
    Traceback (most recent call last):
    ...
    TypeError: Argument 3 to demo() must have type: (list of (int or (list of str))) (got a int)

    >>> test(demo, [], [2,2,2.0], [])
    Traceback (most recent call last):
    ...
    TypeError: Argument 2 to demo() must have type: (list of int) (got a list)

    >>> test(demo, [], [], [2,'x',2.0])
    Traceback (most recent call last):
    ...
    TypeError: Argument 3 to demo() must have type: (list of (int or (list of str))) (got a list)

    >>> test(demo, [], [], [3, [3]])
    Traceback (most recent call last):
    ...
    TypeError: Argument 3 to demo() must have type: (list of (int or (list of str))) (got a list)

    >>> test(demo, [], [], [3, ['x', ['y']]])
    Traceback (most recent call last):
    ...
    TypeError: Argument 3 to demo() must have type: (list of (int or (list of str))) (got a list)

Tuple Type checks:
==================
    >>> def demo(tuple1, tuple2, tuple3):
    ...     assert chktype(1, tuple1, ())
    ...     assert chktype(2, tuple2, (int,))
    ...     assert chktype(3, tuple3, (int, (str,)))
    ...     return 'ok'

These should be fine:

    >>> demo((), (), ())
    'ok'
    >>> demo(('x',), (1,), (1,))
    'ok'
    >>> demo(('a', {}, (), 3), (1,2), (3,4))
    'ok'
    >>> demo((), (), (1, ('x',), 2, ('y', 'z')))
    'ok'

These should raise exceptions:

    >>> test(demo, [], (), ())
    Traceback (most recent call last):
    ...
    TypeError: Argument 1 to demo() must have type: tuple (got a list)
    
    >>> test(demo, (), [], ())
    Traceback (most recent call last):
    ...
    TypeError: Argument 2 to demo() must have type: (tuple of int) (got a list)
    
    >>> test(demo, (), (), [])
    Traceback (most recent call last):
    ...
    TypeError: Argument 3 to demo() must have type: (tuple of (int or (tuple of str))) (got a list)

    >>> test(demo, {}, (), ())
    Traceback (most recent call last):
    ...
    TypeError: Argument 1 to demo() must have type: tuple (got a dict)

    >>> test(demo, (), {}, ())
    Traceback (most recent call last):
    ...
    TypeError: Argument 2 to demo() must have type: (tuple of int) (got a dict)

    >>> test(demo, (), (), {})
    Traceback (most recent call last):
    ...
    TypeError: Argument 3 to demo() must have type: (tuple of (int or (tuple of str))) (got a dict)

    >>> test(demo, 1, (), ())
    Traceback (most recent call last):
    ...
    TypeError: Argument 1 to demo() must have type: tuple (got a int)

    >>> test(demo, (), 1, ())
    Traceback (most recent call last):
    ...
    TypeError: Argument 2 to demo() must have type: (tuple of int) (got a int)

    >>> test(demo, (), (), 1)
    Traceback (most recent call last):
    ...
    TypeError: Argument 3 to demo() must have type: (tuple of (int or (tuple of str))) (got a int)

    >>> test(demo, (), (2,2,2.0), ())
    Traceback (most recent call last):
    ...
    TypeError: Argument 2 to demo() must have type: (tuple of int) (got a tuple)

    >>> test(demo, (), (), (2,'x',2.0))
    Traceback (most recent call last):
    ...
    TypeError: Argument 3 to demo() must have type: (tuple of (int or (tuple of str))) (got a tuple)

    >>> test(demo, (), (), (3, (3,)))
    Traceback (most recent call last):
    ...
    TypeError: Argument 3 to demo() must have type: (tuple of (int or (tuple of str))) (got a tuple)

    >>> test(demo, (), (), (3, ('x', ('y',))))
    Traceback (most recent call last):
    ...
    TypeError: Argument 3 to demo() must have type: (tuple of (int or (tuple of str))) (got a tuple)

Dict Type checks:
=================
    >>> def demo(dict1, dict2, dict3, dict4):
    ...     assert chktype(1, dict1, {})
    ...     assert chktype(2, dict2, {int: [int]})
    ...     assert chktype(3, dict3, {int: [str, int],
    ...                               float: [float]})
    ...     assert chktype(4, dict4, {(int,): [(), []],
    ...                               ((),): [(int,)]})
    ...     return 'ok'

These should be fine:

    >>> demo({}, {}, {}, {})
    'ok'
    >>> demo({1:'x', 'x':1}, {}, {}, {})
    'ok'
    >>> demo({}, {1:2, 3:5}, {}, {})
    'ok'
    >>> demo({}, {}, {1:'x', 1:3, 1:0, 1.1:2.1, -.2:0.0}, {})
    'ok'
    >>> demo({}, {}, {}, {(2,3): ('x',2), (2,3): ['x',2], ((3,'x'),): (1,3)})
    'ok'

These should raise exceptions:
                                                   
    >>> test(demo, [], {}, {}, {})
    Traceback (most recent call last):
    ...
    TypeError: Argument 1 to demo() must have type: dictionary (got a list)
    
    >>> test(demo, {}, [], {}, {})
    Traceback (most recent call last):
    ...
    TypeError: Argument 2 to demo() must have type: (dictionary from int to int) (got a list)
    
    >>> test(demo, {}, {}, [], {})
    Traceback (most recent call last):
    ...
    TypeError: Argument 3 to demo() must have type: (dictionary from float to float or from int to (str or int)) (got a list)
    
    >>> test(demo, {}, {}, {}, [])
    Traceback (most recent call last):
    ...
    TypeError: Argument 4 to demo() must have type: (dictionary from (tuple of int) to (tuple or list) or from (tuple of tuple) to (tuple of int)) (got a list)
    
    >>> test(demo, {}, {1:'x'}, {}, {})
    Traceback (most recent call last):
    ...
    TypeError: Argument 2 to demo() must have type: (dictionary from int to int) (got a dict)
    
    >>> test(demo, {}, {'x':1}, {}, {})
    Traceback (most recent call last):
    ...
    TypeError: Argument 2 to demo() must have type: (dictionary from int to int) (got a dict)
    
    >>> test(demo, {}, {'x':'x'}, {}, {})
    Traceback (most recent call last):
    ...
    TypeError: Argument 2 to demo() must have type: (dictionary from int to int) (got a dict)
    
    >>> test(demo, {}, {}, {1:1.0}, {})
    Traceback (most recent call last):
    ...
    TypeError: Argument 3 to demo() must have type: (dictionary from float to float or from int to (str or int)) (got a dict)
    
    >>> test(demo, {}, {}, {1.0:1}, {})
    Traceback (most recent call last):
    ...
    TypeError: Argument 3 to demo() must have type: (dictionary from float to float or from int to (str or int)) (got a dict)
    
    >>> test(demo, {}, {}, {1.0:'x'}, {})
    Traceback (most recent call last):
    ...
    TypeError: Argument 3 to demo() must have type: (dictionary from float to float or from int to (str or int)) (got a dict)
    
    >>> test(demo, {}, {}, {}, {(): 2})
    Traceback (most recent call last):
    ...
    TypeError: Argument 4 to demo() must have type: (dictionary from (tuple of int) to (tuple or list) or from (tuple of tuple) to (tuple of int)) (got a dict)
    
    >>> test(demo, {}, {}, {}, {3: ()})
    Traceback (most recent call last):
    ...
    TypeError: Argument 4 to demo() must have type: (dictionary from (tuple of int) to (tuple or list) or from (tuple of tuple) to (tuple of int)) (got a dict)
    
    >>> test(demo, {}, {}, {}, {((),): [33]})
    Traceback (most recent call last):
    ...
    TypeError: Argument 4 to demo() must have type: (dictionary from (tuple of int) to (tuple or list) or from (tuple of tuple) to (tuple of int)) (got a dict)
"""
    
#######################################################################
# Test Runner
#######################################################################

import sys, os, os.path
if __name__ == '__main__': sys.path[0] = None
import unittest, doctest, trace

def testsuite(reload_module=False):
    import doctest, nltk.test.chktype
    if reload_module: reload(nltk.test.chktype)
    return doctest.DocTestSuite(nltk.test.chktype)

def test(verbosity=2, reload_module=False):
    runner = unittest.TextTestRunner(verbosity=verbosity)
    runner.run(testsuite(reload_module))

if __name__ == '__main__':
    test(reload_module=True)
