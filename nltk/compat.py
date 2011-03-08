# Natural Language Toolkit: Compatibility Functions
#
# Copyright (C) 2001-2011 NLTK Project
# Author: Steven Bird <sb@csse.unimelb.edu.au>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Backwards compatibility with previous versions of Python.

This module provides backwards compatibility by defining
functions and classes that were not available in earlier versions of
Python.  Intented usage:

    >>> from nltk.compat import *

Currently, NLTK requires Python 2.4 or later.
"""

######################################################################
# New in Python 2.5
######################################################################

# ElementTree

try:
    from xml.etree import ElementTree
except ImportError:
    from nltk.etree import ElementTree

# collections.defaultdict
# originally contributed by Yoav Goldberg <yoav.goldberg@gmail.com>
# new version by Jason Kirtland from Python cookbook.
# <http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/523034>
try:
    from collections import defaultdict
except ImportError:
    class defaultdict(dict):
        def __init__(self, default_factory=None, *a, **kw):
            if (default_factory is not None and
                not hasattr(default_factory, '__call__')):
                raise TypeError('first argument must be callable')
            dict.__init__(self, *a, **kw)
            self.default_factory = default_factory
        def __getitem__(self, key):
            try:
                return dict.__getitem__(self, key)
            except KeyError:
                return self.__missing__(key)
        def __missing__(self, key):
            if self.default_factory is None:
                raise KeyError(key)
            self[key] = value = self.default_factory()
            return value
        def __reduce__(self):
            if self.default_factory is None:
                args = tuple()
            else:
                args = self.default_factory,
            return type(self), args, None, None, self.iteritems()
        def copy(self):
            return self.__copy__()
        def __copy__(self):
            return type(self)(self.default_factory, self)
        def __deepcopy__(self, memo):
            import copy
            return type(self)(self.default_factory,
                              copy.deepcopy(self.items()))
        def __repr__(self):
            return 'defaultdict(%s, %s)' % (self.default_factory,
                                            dict.__repr__(self))

    # [XX] to make pickle happy in python 2.4:
    import collections
    collections.defaultdict = defaultdict

# all, any

try:
    all([True])
    all = all
except NameError:
    def all(iterable):
        for i in iterable:
            if not i:
                return False
        else:
            return True

try:
    any([True])
    any = any
except NameError:
    def any(iterable):
        for i in iterable:
            if i:
                return True
        else:
            return False


__all__ = ['ElementTree', 'defaultdict', 'all', 'any']
