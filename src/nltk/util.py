# Natural Language Toolkit: Utilities
#
# Copyright (C) 2003 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
A collection of basic utility classes and functions that are used
by the toolkit.
"""

import itertools, sys, re

######################################################################
## Frozen Dictionary
######################################################################

class FrozenDict(dict):
    """
    An immutable (and hashable) dictionary.
    """
    __slots__ = ('_hash',)
    def __init__(self, *args, **kwargs):
        """
        Create a new immutable dictionary.
        @param args, kwargs: Initialization arguments, passed
            on to the C{dict} constructor.
        """
        super(FrozenDict, self).__init__(*args, **kwargs)
        self._hash = hash(sum([hash(i) for i in self.items()]))
    def __setitem__(self, key, value):
        "Raise TypeError (FrozenDict objects are immutable)"
        raise TypeError('FrozenDict objects are immutable')
    def __delitem__(self, key):
        "Raise TypeError (FrozenDict objects are immutable)"
        raise TypeError('FrozenDict objects are immutable')
    def clear(self):
        "Raise TypeError (FrozenDict objects are immutable)"
        raise TypeError('FrozenDict objects are immutable')
    def pop(self, key, default=None):
        "Raise TypeError (FrozenDict objects are immutable)"
        raise TypeError('FrozenDict objects are immutable')
    def popitem(self):
        "Raise TypeError (FrozenDict objects are immutable)"
        raise TypeError('FrozenDict objects are immutable')
    def setdefault(self, key, default=None):
        "Raise TypeError (FrozenDict objects are immutable)"
        raise TypeError('FrozenDict objects are immutable')
    def update(self, src):
        "Raise TypeError (FrozenDict objects are immutable)"
        raise TypeError('FrozenDict objects are immutable')
    def copy(self):
        "Return a new copy of this FrozenDict"
        return self.__class__(self)
    def __hash__(self):
        return self._hash
        
######################################################################
## Lazy List
######################################################################

class LazyList(list):
    """
    A list wrapper for iterators that expands the iterator only when
    necessary.  I.e., LazyList(it) acts just like list(it), except
    that it tries to wait to expand it until it needs to.

    The following methods are lazy: __contains__, __getitem__,
    __setitem__, __delitem__, __getslice__, __setslice__,
    __delslice__, insert, pop (when an index is specified), remove,
    index.

    The following methods will append to the iterator, if it's not yet
    exhausted: __iadd__, extend, append.

    The remaining methods expand the iterator completely before
    operating.
    """
    def __init__(self, iterator):
        """
        Create a new lazy list that wraps the given iterator.
        """
        self._iter = iter(iterator)
        self._iter_exhausted = False

    #/////////////////////////////////////////////////////////////////
    # Helper functions: these are used to expand the iterator
    
    def _expand_to_index(self, i):
        """
        - If i<0, then expand the entire iterator.
        - If i>=0, then expand the iterator until the length of
          the expanded list is greater than i, or the iterator
          is exhausted.
        """
        if self._iter_exhausted: return
        if i < 0: self._expand_all()
        
        while list.__len__(self) <= i:
            try: list.append(self, self._iter.next())
            except StopIteration:
                self._iter_exhausted = True
                return

    def _expand_to_value(self, value, stop=None):
        """
        Expand the iterator until the given value is encountered,
        or the iterator is exhausted.  Return true iff the given
        value was encountered.
        """
        if self._iter_exhausted: return
        while stop is None or list.__len__(self) < stop:
            try: val = self._iter.next()
            except StopIteration:
                self._iter_exhausted = True
                return False
            list.append(self, val)
            if val == value: return True
        return False

    def _expand_all(self):
        """
        Expand the iterator until it is exhausted.
        """
        if self._iter_exhausted: return
        list.extend(self, self._iter)
        self._iter_exhausted = True

    #/////////////////////////////////////////////////////////////////
    # These methods append to the iterator:

    def __iadd__(self, other):
        if self._iter_exhausted:
            list.__iadd__(self, other)
        else:
            self._iter = itertools.chain(self._iter, other)

    def extend(self, other):
        if self._iter_exhausted:
            list.extend(self, other)
        else:
            self._iter = itertools.chain(self._iter, other)
    
    def append(self, other):
        if self._iter_exhausted:
            list.append(self, other)
        else:
            self._iter = itertools.chain(self._iter, [other])

    #/////////////////////////////////////////////////////////////////
    # These methods expand self as much as needed, then operate.

    def __getitem__(self, i):
        self._expand_to_index(i)
        return list.__getitem__(self, i)

    def __setitem__(self, i, value):
        self._expand_to_index(i)
        return list.__setitem__(self, i, value)

    def __delitem__(self,i):
        self._expand_to_index(i)
        return list.__delitem__(self, i)

    def __getslice__(self, i, j):
        self._expand_to_index(i)
        self._expand_to_index(j)
        return list.__getslice__(self, i,j)

    def __setslice__(self, i, j, value):
        self._expand_to_index(i)
        self._expand_to_index(j)
        return list.__setslice__(self, i,j,value)

    def __delslice__(self, i, j):
        self._expand_to_index(i)
        self._expand_to_index(j)
        return list.__delslice__(self, i,j)

    def insert(self, index, value):
        self._expand_to_index(index)
        return list.insert(self, index, value)

    def pop(self, index=None):
        if index is not None:
            self._expand_to_index(index)
            return list.pop(self, index)
        else:
            return list.pop(self)

    #/////////////////////////////////////////////////////////////////
    # These methods expand until they find a value, then operate.

    def __contains__(self, value):
        # First, check the expanded list.
        if list.__contains__(self, value): return True
        # Then, check the iterator.
        return self._expand_to_value(value)
    
    def remove(self, value):
        try:
            # First, try the expanded list.
            list.remove(self, value)
        except ValueError:
            # Then, try the iterator.
            self._expand_to_value(value)
            list.remove(self, value)

    def index(self, value, start=0, stop=None):
        # Special case: if stop<0, then expand completely & operate.
        if stop is not None and stop < 0:
            self._expand_all()
            return list.index(self, value, start, stop)
            
        self._expand_to_index(start)
        try:
            # First, check the expanded list.
            if stop is not None:
                return list.index(self, value, start, stop)
            else:
                return list.index(self, value, start)
        except ValueError:
            # Then, check the iterator.
            if self._expand_to_value(value, stop):
                return list.__len__(self)-1
            else:
                raise ValueError, 'list.index(x): x not in list'

    #/////////////////////////////////////////////////////////////////
    # These methods expand self completely, then operate.

    def __len__(self):
        self._expand_all(); return list.__len__(self)
    def __add__(self, other):
        self._expand_all(); return list.__add__(self, other)
    def __eq__(self, other):
        self._expand_all(); return list.__eq__(self, other)
    def __ne__(self, other):
        self._expand_all(); return list.__ne__(self, other)
    def __gt__(self, other):
        self._expand_all(); return list.__gt__(self, other)
    def __lt__(self, other):
        self._expand_all(); return list.__lt__(self, other)
    def __ge__(self, other):
        self._expand_all(); return list.__ge__(self, other)
    def __le__(self, other):
        self._expand_all(); return list.__le__(self, other)
    def __hash__(self):
        self._expand_all(); return list.__hash__(self)
    def __mul__(self, other):
        self._expand_all(); return list.__mul__(self, other)
    def __imul__(self, other):
        self._expand_all(); return list.__imul__(self, other)
    def __repr__(self):
        self._expand_all(); return list.__repr__(self)
    def __str__(self):
        self._expand_all(); return list.__str__(self)
    def count(self, value):
        self._expand_all(); return list.count(self, value)
    def sort(self):
        self._expand_all(); return list.sort(self)
    def reverse(self):
        self._expand_all(); return list.reverse(self)
    def __reduce__(self):
        self._expand_all(); return list.__reduce__(self)
    def __reduce_ex__(self, protocol):
        self._expand_all(); return list.__reduce_ex__(self, protocol)
        

    #/////////////////////////////////////////////////////////////////
    # Right-hand operations.  These are needed to make sure that
    # other+self doesn't ignore the iter portion.

    def __radd__(self, other):
        self._expand_all()
        return other.__add__(self)

    def __rmul__(self, other):
        self._expand_all()
        return other.__mul__(self)

    #/////////////////////////////////////////////////////////////////
    # Iteration over a lazy list
    
    def __iter__(self):
        for i in itertools.count():
            try: yield self[i]
            except IndexError: return

######################################################################
## A Simple Interpreter for Demonstrations
######################################################################

class DemoInterpreter:
    """
    A simple eval-print loop, that can be useful for creating quick
    demonstrations.
    """
    class _OutWrapper:
        def __init__(self, out, indent):
            self._out = out
            self._indent = indent
            
        def write(self, str):
            str = str.replace('\n', '\n'+self._indent)
            self._out.write(str)
            
        #def writelines(self, lines):
        #    lines = [self._indent+line for line in lines]
        #    self._out.writelines(lines)
            
        def __getattr__(self, attr):
            return getattr(self._out, attr)

    _out = _OutWrapper(sys.stdout, '* ')
    
    def __init__(self):
        self._locals = {}

    def start(self, s):
        sys.stdout = self._out
        print '*'*(38-len(s)/2), s, '*'*(37-(len(s)+1)/2)

    def end(self):
        sys.stdout = sys.__stdout__
        print
        print '*'*75

    def hline(self, char='-'):
        print char*75

    def blankline(self):
        print

    def silent(self, cmd):
        exec(cmd, globals(), self._locals)

    def __call__(self, cmd):
        print '>>> '+'\n... '.join(cmd.split('\n'))
        cmd = cmd.replace('\n', ' ')
        try:
            out = eval(cmd, globals(), self._locals)
            if out is not None: print repr(out)
        except:
            try:
                exec(cmd, globals(), self._locals)
            except Exception, e:
                out = '%s: %s' % (e.__class__.__name__, e)
                print '  '+'\n  '.join(out.split('\n'))

######################################################################
## Doctest Helpers
######################################################################

def capture_stdout(func, *args, **kwargs):
    """

    Call C{func} with the given arguments, and capture anything it
    writes to standard output to a string.

    @param func: The function to call
    @param args, kwargs: The argumens that should be passed to C{func}
        when it is called.
    @rtype: C{string}
    @return: A string containing everything written by C{func} to
        standard output.
    """
    import StringIO
    old_stdout = sys.stdout
    sys.stdout = StringIO.StringIO()
    func(*args, **kwargs)
    out = sys.stdout.getvalue()
    sys.stdout = old_stdout
    return out

def mark_stdout_newlines(func, *args, **kwargs):
    r"""
    Call C{func} with the given arguments, and replace any blank lines
    that it writes to standard output with the string
    C{'<--BLANKLINE-->'}.  This is used in DocTest suites, since
    DocTest can't handle output that contains blank lines.  E.g.:

        >>> def f(x): print 'first line\n\nthird line'
        >>> mark_stdout_newlines(f)
        first line
        <--BLANKLINE-->
        third line
    
    """
    print re.sub(r'\n[ \t]*\n', '\n<--BLANKLINE-->\n',
                 capture_stdout(func, *args, **kwargs)).rstrip()
    
