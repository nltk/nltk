# Natural Language Toolkit: Utility functions
#
# Copyright (C) 2001-2016 NLTK Project
# Author: Steven Bird <stevenbird1@gmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT
from __future__ import print_function

import locale
import re
import types
import textwrap
import pydoc
import bisect
import os

from itertools import islice, chain, combinations
from pprint import pprint
from collections import defaultdict, deque
from sys import version_info

from nltk.internals import slice_bounds, raise_unorderable_types
from nltk.compat import (class_types, text_type, string_types, total_ordering,
                         python_2_unicode_compatible, getproxies,
			 ProxyHandler, build_opener, install_opener,
			 HTTPPasswordMgrWithDefaultRealm,
			 ProxyBasicAuthHandler, ProxyDigestAuthHandler)

######################################################################
# Short usage message
######################################################################

def usage(obj, selfname='self'):
    import inspect
    str(obj) # In case it's lazy, this will load it.

    if not isinstance(obj, class_types):
        obj = obj.__class__

    print('%s supports the following operations:' % obj.__name__)
    for (name, method) in sorted(pydoc.allmethods(obj).items()):
        if name.startswith('_'): continue
        if getattr(method, '__deprecated__', False): continue

        args, varargs, varkw, defaults = inspect.getargspec(method)
        if (args and args[0]=='self' and
            (defaults is None or len(args)>len(defaults))):
            args = args[1:]
            name = '%s.%s' % (selfname, name)
        argspec = inspect.formatargspec(
            args, varargs, varkw, defaults)
        print(textwrap.fill('%s%s' % (name, argspec),
                            initial_indent='  - ',
                            subsequent_indent=' '*(len(name)+5)))

##########################################################################
# IDLE
##########################################################################

def in_idle():
    """
    Return True if this function is run within idle.  Tkinter
    programs that are run in idle should never call ``Tk.mainloop``; so
    this function should be used to gate all calls to ``Tk.mainloop``.

    :warning: This function works by checking ``sys.stdin``.  If the
        user has modified ``sys.stdin``, then it may return incorrect
        results.
    :rtype: bool
    """
    import sys
    return sys.stdin.__class__.__name__ in ('PyShell', 'RPCProxy')

##########################################################################
# PRETTY PRINTING
##########################################################################

def pr(data, start=0, end=None):
    """
    Pretty print a sequence of data items

    :param data: the data stream to print
    :type data: sequence or iter
    :param start: the start position
    :type start: int
    :param end: the end position
    :type end: int
    """
    pprint(list(islice(data, start, end)))

def print_string(s, width=70):
    """
    Pretty print a string, breaking lines on whitespace

    :param s: the string to print, consisting of words and spaces
    :type s: str
    :param width: the display width
    :type width: int
    """
    print('\n'.join(textwrap.wrap(s, width=width)))

def tokenwrap(tokens, separator=" ", width=70):
    """
    Pretty print a list of text tokens, breaking lines on whitespace

    :param tokens: the tokens to print
    :type tokens: list
    :param separator: the string to use to separate tokens
    :type separator: str
    :param width: the display width (default=70)
    :type width: int
    """
    return '\n'.join(textwrap.wrap(separator.join(tokens), width=width))


##########################################################################
# Python version
##########################################################################

def py25():
    return version_info[0] == 2 and version_info[1] == 5
def py26():
    return version_info[0] == 2 and version_info[1] == 6
def py27():
    return version_info[0] == 2 and version_info[1] == 7


##########################################################################
# Indexing
##########################################################################

class Index(defaultdict):

    def __init__(self, pairs):
        defaultdict.__init__(self, list)
        for key, value in pairs:
            self[key].append(value)


######################################################################
## Regexp display (thanks to David Mertz)
######################################################################

def re_show(regexp, string, left="{", right="}"):
    """
    Return a string with markers surrounding the matched substrings.
    Search str for substrings matching ``regexp`` and wrap the matches
    with braces.  This is convenient for learning about regular expressions.

    :param regexp: The regular expression.
    :type regexp: str
    :param string: The string being matched.
    :type string: str
    :param left: The left delimiter (printed before the matched substring)
    :type left: str
    :param right: The right delimiter (printed after the matched substring)
    :type right: str
    :rtype: str
    """
    print(re.compile(regexp, re.M).sub(left + r"\g<0>" + right, string.rstrip()))


##########################################################################
# READ FROM FILE OR STRING
##########################################################################

# recipe from David Mertz
def filestring(f):
    if hasattr(f, 'read'):
        return f.read()
    elif isinstance(f, string_types):
        with open(f, 'r') as infile:
            return infile.read()
    else:
        raise ValueError("Must be called with a filename or file-like object")

##########################################################################
# Breadth-First Search
##########################################################################

def breadth_first(tree, children=iter, maxdepth=-1):
    """Traverse the nodes of a tree in breadth-first order.
    (No need to check for cycles.)
    The first argument should be the tree root;
    children should be a function taking as argument a tree node
    and returning an iterator of the node's children.
    """
    queue = deque([(tree, 0)])

    while queue:
        node, depth = queue.popleft()
        yield node

        if depth != maxdepth:
            try:
                queue.extend((c, depth + 1) for c in children(node))
            except TypeError:
                pass

##########################################################################
# Guess Character Encoding
##########################################################################

# adapted from io.py in the docutils extension module (http://docutils.sourceforge.net)
# http://www.pyzine.com/Issue008/Section_Articles/article_Encodings.html

def guess_encoding(data):
    """
    Given a byte string, attempt to decode it.
    Tries the standard 'UTF8' and 'latin-1' encodings,
    Plus several gathered from locale information.

    The calling program *must* first call::

        locale.setlocale(locale.LC_ALL, '')

    If successful it returns ``(decoded_unicode, successful_encoding)``.
    If unsuccessful it raises a ``UnicodeError``.
    """
    successful_encoding = None
    # we make 'utf-8' the first encoding
    encodings = ['utf-8']
    #
    # next we add anything we can learn from the locale
    try:
        encodings.append(locale.nl_langinfo(locale.CODESET))
    except AttributeError:
        pass
    try:
        encodings.append(locale.getlocale()[1])
    except (AttributeError, IndexError):
        pass
    try:
        encodings.append(locale.getdefaultlocale()[1])
    except (AttributeError, IndexError):
        pass
    #
    # we try 'latin-1' last
    encodings.append('latin-1')
    for enc in encodings:
        # some of the locale calls
        # may have returned None
        if not enc:
            continue
        try:
            decoded = text_type(data, enc)
            successful_encoding = enc

        except (UnicodeError, LookupError):
            pass
        else:
            break
    if not successful_encoding:
         raise UnicodeError(
        'Unable to decode input data.  Tried the following encodings: %s.'
        % ', '.join([repr(enc) for enc in encodings if enc]))
    else:
         return (decoded, successful_encoding)


##########################################################################
# Remove repeated elements from a list deterministcally
##########################################################################

def unique_list(xs):
    seen = set()
    # not seen.add(x) here acts to make the code shorter without using if statements, seen.add(x) always returns None.
    return [x for x in xs if x not in seen and not seen.add(x)]

##########################################################################
# Invert a dictionary
##########################################################################

def invert_dict(d):
    inverted_dict = defaultdict(list)
    for key in d:
        if hasattr(d[key], '__iter__'):
            for term in d[key]:
                inverted_dict[term].append(key)
        else:
            inverted_dict[d[key]] = key
    return inverted_dict


##########################################################################
# Utilities for directed graphs: transitive closure, and inversion
# The graph is represented as a dictionary of sets
##########################################################################

def transitive_closure(graph, reflexive=False):
    """
    Calculate the transitive closure of a directed graph,
    optionally the reflexive transitive closure.

    The algorithm is a slight modification of the "Marking Algorithm" of
    Ioannidis & Ramakrishnan (1998) "Efficient Transitive Closure Algorithms".

    :param graph: the initial graph, represented as a dictionary of sets
    :type graph: dict(set)
    :param reflexive: if set, also make the closure reflexive
    :type reflexive: bool
    :rtype: dict(set)
    """
    if reflexive:
        base_set = lambda k: set([k])
    else:
        base_set = lambda k: set()
    # The graph U_i in the article:
    agenda_graph = dict((k, graph[k].copy()) for k in graph)
    # The graph M_i in the article:
    closure_graph = dict((k, base_set(k)) for k in graph)
    for i in graph:
        agenda = agenda_graph[i]
        closure = closure_graph[i]
        while agenda:
            j = agenda.pop()
            closure.add(j)
            closure |= closure_graph.setdefault(j, base_set(j))
            agenda |= agenda_graph.get(j, base_set(j))
            agenda -= closure
    return closure_graph


def invert_graph(graph):
    """
    Inverts a directed graph.

    :param graph: the graph, represented as a dictionary of sets
    :type graph: dict(set)
    :return: the inverted graph
    :rtype: dict(set)
    """
    inverted = {}
    for key in graph:
        for value in graph[key]:
            inverted.setdefault(value, set()).add(key)
    return inverted



##########################################################################
# HTML Cleaning
##########################################################################

def clean_html(html):
    raise NotImplementedError ("To remove HTML markup, use BeautifulSoup's get_text() function")

def clean_url(url):
    raise NotImplementedError ("To remove HTML markup, use BeautifulSoup's get_text() function")

##########################################################################
# FLATTEN LISTS
##########################################################################

def flatten(*args):
    """
    Flatten a list.

        >>> from nltk.util import flatten
        >>> flatten(1, 2, ['b', 'a' , ['c', 'd']], 3)
        [1, 2, 'b', 'a', 'c', 'd', 3]

    :param args: items and lists to be combined into a single list
    :rtype: list
    """

    x = []
    for l in args:
        if not isinstance(l, (list, tuple)): l = [l]
        for item in l:
            if isinstance(item, (list, tuple)):
                x.extend(flatten(item))
            else:
                x.append(item)
    return x

##########################################################################
# Ngram iteration
##########################################################################

def pad_sequence(sequence, n, pad_left=False, pad_right=False, 
                 left_pad_symbol=None, right_pad_symbol=None):
    """
    Returns a padded sequence of items before ngram extraction.
    
        >>> list(pad_sequence([1,2,3,4,5], 2, pad_left=True, pad_right=True, left_pad_symbol='<s>', right_pad_symbol='</s>'))
        ['<s>', 1, 2, 3, 4, 5, '</s>']
        >>> list(pad_sequence([1,2,3,4,5], 2, pad_left=True, left_pad_symbol='<s>'))
        ['<s>', 1, 2, 3, 4, 5]
        >>> list(pad_sequence([1,2,3,4,5], 2, pad_right=True, right_pad_symbol='</s>'))
        [1, 2, 3, 4, 5, '</s>']
    
    :param sequence: the source data to be padded
    :type sequence: sequence or iter
    :param n: the degree of the ngrams
    :type n: int
    :param pad_left: whether the ngrams should be left-padded
    :type pad_left: bool
    :param pad_right: whether the ngrams should be right-padded
    :type pad_right: bool
    :param left_pad_symbol: the symbol to use for left padding (default is None)
    :type left_pad_symbol: any
    :param right_pad_symbol: the symbol to use for right padding (default is None)
    :type right_pad_symbol: any
    :rtype: sequence or iter
    """
    sequence = iter(sequence)
    if pad_left:
        sequence = chain((left_pad_symbol,) * (n-1), sequence)
    if pad_right:
        sequence = chain(sequence, (right_pad_symbol,) * (n-1))
    return sequence

# add a flag to pad the sequence so we get peripheral ngrams?

def ngrams(sequence, n, pad_left=False, pad_right=False, 
           left_pad_symbol=None, right_pad_symbol=None):
    """
    Return the ngrams generated from a sequence of items, as an iterator.
    For example:

        >>> from nltk.util import ngrams
        >>> list(ngrams([1,2,3,4,5], 3))
        [(1, 2, 3), (2, 3, 4), (3, 4, 5)]

    Use ngrams for a list version of this function.  Set pad_left
    or pad_right to true in order to get additional ngrams:

        >>> list(ngrams([1,2,3,4,5], 2, pad_right=True))
        [(1, 2), (2, 3), (3, 4), (4, 5), (5, None)]
        >>> list(ngrams([1,2,3,4,5], 2, pad_right=True, right_pad_symbol='</s>'))
        [(1, 2), (2, 3), (3, 4), (4, 5), (5, '</s>')]
        >>> list(ngrams([1,2,3,4,5], 2, pad_left=True, left_pad_symbol='<s>'))
        [('<s>', 1), (1, 2), (2, 3), (3, 4), (4, 5)]
        >>> list(ngrams([1,2,3,4,5], 2, pad_left=True, pad_right=True, left_pad_symbol='<s>', right_pad_symbol='</s>'))
        [('<s>', 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, '</s>')]


    :param sequence: the source data to be converted into ngrams
    :type sequence: sequence or iter
    :param n: the degree of the ngrams
    :type n: int
    :param pad_left: whether the ngrams should be left-padded
    :type pad_left: bool
    :param pad_right: whether the ngrams should be right-padded
    :type pad_right: bool
    :param left_pad_symbol: the symbol to use for left padding (default is None)
    :type left_pad_symbol: any
    :param right_pad_symbol: the symbol to use for right padding (default is None)
    :type right_pad_symbol: any
    :rtype: sequence or iter
    """
    sequence = pad_sequence(sequence, n, pad_left, pad_right,
                            left_pad_symbol, right_pad_symbol)
        
    history = []
    while n > 1:
        history.append(next(sequence))
        n -= 1
    for item in sequence:
        history.append(item)
        yield tuple(history)
        del history[0]

def bigrams(sequence, **kwargs):
    """
    Return the bigrams generated from a sequence of items, as an iterator.
    For example:

        >>> from nltk.util import bigrams
        >>> list(bigrams([1,2,3,4,5]))
        [(1, 2), (2, 3), (3, 4), (4, 5)]

    Use bigrams for a list version of this function.

    :param sequence: the source data to be converted into bigrams
    :type sequence: sequence or iter
    :rtype: iter(tuple)
    """

    for item in ngrams(sequence, 2, **kwargs):
        yield item

def trigrams(sequence, **kwargs):
    """
    Return the trigrams generated from a sequence of items, as an iterator.
    For example:

        >>> from nltk.util import trigrams
        >>> list(trigrams([1,2,3,4,5]))
        [(1, 2, 3), (2, 3, 4), (3, 4, 5)]

    Use trigrams for a list version of this function.

    :param sequence: the source data to be converted into trigrams
    :type sequence: sequence or iter
    :rtype: iter(tuple)
    """

    for item in ngrams(sequence, 3, **kwargs):
        yield item

def everygrams(sequence, min_len=1, max_len=-1, **kwargs):
    """
    Returns all possible ngrams generated from a sequence of items, as an iterator.
    
        >>> sent = 'a b c'.split()
        >>> list(everygrams(sent))
        [('a',), ('b',), ('c',), ('a', 'b'), ('b', 'c'), ('a', 'b', 'c')]
        >>> list(everygrams(sent, max_len=2))
        [('a',), ('b',), ('c',), ('a', 'b'), ('b', 'c')]
        
    :param sequence: the source data to be converted into trigrams
    :type sequence: sequence or iter
    :param min_len: minimum length of the ngrams, aka. n-gram order/degree of ngram
    :type  min_len: int
    :param max_len: maximum length of the ngrams (set to length of sequence by default)
    :type  max_len: int
    :rtype: iter(tuple)
    """
    
    if max_len == -1:
        max_len = len(sequence)
    for n in range(min_len, max_len+1):
        for ng in ngrams(sequence, n, **kwargs):
            yield ng

def skipgrams(sequence, n, k, **kwargs):
    """
    Returns all possible skipgrams generated from a sequence of items, as an iterator.
    Skipgrams are ngrams that allows tokens to be skipped.
    Refer to http://homepages.inf.ed.ac.uk/ballison/pdf/lrec_skipgrams.pdf
    
        >>> sent = "Insurgents killed in ongoing fighting".split()
        >>> list(skipgrams(sent, 2, 2))
        [('Insurgents', 'killed'), ('Insurgents', 'in'), ('Insurgents', 'ongoing'), ('killed', 'in'), ('killed', 'ongoing'), ('killed', 'fighting'), ('in', 'ongoing'), ('in', 'fighting'), ('ongoing', 'fighting')]
        >>> list(skipgrams(sent, 3, 2))
        [('Insurgents', 'killed', 'in'), ('Insurgents', 'killed', 'ongoing'), ('Insurgents', 'killed', 'fighting'), ('Insurgents', 'in', 'ongoing'), ('Insurgents', 'in', 'fighting'), ('Insurgents', 'ongoing', 'fighting'), ('killed', 'in', 'ongoing'), ('killed', 'in', 'fighting'), ('killed', 'ongoing', 'fighting'), ('in', 'ongoing', 'fighting')]
    
    :param sequence: the source data to be converted into trigrams
    :type sequence: sequence or iter
    :param n: the degree of the ngrams
    :type n: int
    :param k: the skip distance
    :type  k: int
    :rtype: iter(tuple)
    """
    
    # Pads the sequence as desired by **kwargs.
    if 'pad_left' in kwargs or 'pad_right' in kwargs:
        sequence = pad_sequence(sequence, n, **kwargs)
    
    # Note when iterating through the ngrams, the pad_right here is not
    # the **kwargs padding, it's for the algorithm to detect the SENTINEL 
    # object on the right pad to stop inner loop.
    SENTINEL = object()
    for ngram in ngrams(sequence, n + k, pad_right=True, right_pad_symbol=SENTINEL):
        head = ngram[:1]
        tail = ngram[1:]
        for skip_tail in combinations(tail, n - 1):
            if skip_tail[-1] is SENTINEL:
                continue
            yield head + skip_tail

##########################################################################
# Ordered Dictionary
##########################################################################

class OrderedDict(dict):
    def __init__(self, data=None, **kwargs):
        self._keys = self.keys(data, kwargs.get('keys'))
        self._default_factory = kwargs.get('default_factory')
        if data is None:
            dict.__init__(self)
        else:
            dict.__init__(self, data)

    def __delitem__(self, key):
        dict.__delitem__(self, key)
        self._keys.remove(key)

    def __getitem__(self, key):
        try:
            return dict.__getitem__(self, key)
        except KeyError:
            return self.__missing__(key)

    def __iter__(self):
        return (key for key in self.keys())

    def __missing__(self, key):
        if not self._default_factory and key not in self._keys:
            raise KeyError()
        return self._default_factory()

    def __setitem__(self, key, item):
        dict.__setitem__(self, key, item)
        if key not in self._keys:
            self._keys.append(key)

    def clear(self):
        dict.clear(self)
        self._keys.clear()

    def copy(self):
        d = dict.copy(self)
        d._keys = self._keys
        return d

    def items(self):
        # returns iterator under python 3 and list under python 2
        return zip(self.keys(), self.values())

    def keys(self, data=None, keys=None):
        if data:
            if keys:
                assert isinstance(keys, list)
                assert len(data) == len(keys)
                return keys
            else:
                assert isinstance(data, dict) or \
                       isinstance(data, OrderedDict) or \
                       isinstance(data, list)
                if isinstance(data, dict) or isinstance(data, OrderedDict):
                    return data.keys()
                elif isinstance(data, list):
                    return [key for (key, value) in data]
        elif '_keys' in self.__dict__:
            return self._keys
        else:
            return []

    def popitem(self):
        if not self._keys:
            raise KeyError()

        key = self._keys.pop()
        value = self[key]
        del self[key]
        return (key, value)

    def setdefault(self, key, failobj=None):
        dict.setdefault(self, key, failobj)
        if key not in self._keys:
            self._keys.append(key)

    def update(self, data):
        dict.update(self, data)
        for key in self.keys(data):
            if key not in self._keys:
                self._keys.append(key)

    def values(self):
        # returns iterator under python 3
        return map(self.get, self._keys)

######################################################################
# Lazy Sequences
######################################################################

@total_ordering
@python_2_unicode_compatible
class AbstractLazySequence(object):
    """
    An abstract base class for read-only sequences whose values are
    computed as needed.  Lazy sequences act like tuples -- they can be
    indexed, sliced, and iterated over; but they may not be modified.

    The most common application of lazy sequences in NLTK is for
    corpus view objects, which provide access to the contents of a
    corpus without loading the entire corpus into memory, by loading
    pieces of the corpus from disk as needed.

    The result of modifying a mutable element of a lazy sequence is
    undefined.  In particular, the modifications made to the element
    may or may not persist, depending on whether and when the lazy
    sequence caches that element's value or reconstructs it from
    scratch.

    Subclasses are required to define two methods: ``__len__()``
    and ``iterate_from()``.
    """
    def __len__(self):
        """
        Return the number of tokens in the corpus file underlying this
        corpus view.
        """
        raise NotImplementedError('should be implemented by subclass')

    def iterate_from(self, start):
        """
        Return an iterator that generates the tokens in the corpus
        file underlying this corpus view, starting at the token number
        ``start``.  If ``start>=len(self)``, then this iterator will
        generate no tokens.
        """
        raise NotImplementedError('should be implemented by subclass')

    def __getitem__(self, i):
        """
        Return the *i* th token in the corpus file underlying this
        corpus view.  Negative indices and spans are both supported.
        """
        if isinstance(i, slice):
            start, stop = slice_bounds(self, i)
            return LazySubsequence(self, start, stop)
        else:
            # Handle negative indices
            if i < 0: i += len(self)
            if i < 0: raise IndexError('index out of range')
            # Use iterate_from to extract it.
            try:
                return next(self.iterate_from(i))
            except StopIteration:
                raise IndexError('index out of range')

    def __iter__(self):
        """Return an iterator that generates the tokens in the corpus
        file underlying this corpus view."""
        return self.iterate_from(0)

    def count(self, value):
        """Return the number of times this list contains ``value``."""
        return sum(1 for elt in self if elt==value)

    def index(self, value, start=None, stop=None):
        """Return the index of the first occurrence of ``value`` in this
        list that is greater than or equal to ``start`` and less than
        ``stop``.  Negative start and stop values are treated like negative
        slice bounds -- i.e., they count from the end of the list."""
        start, stop = slice_bounds(self, slice(start, stop))
        for i, elt in enumerate(islice(self, start, stop)):
            if elt == value: return i+start
        raise ValueError('index(x): x not in list')

    def __contains__(self, value):
        """Return true if this list contains ``value``."""
        return bool(self.count(value))

    def __add__(self, other):
        """Return a list concatenating self with other."""
        return LazyConcatenation([self, other])

    def __radd__(self, other):
        """Return a list concatenating other with self."""
        return LazyConcatenation([other, self])

    def __mul__(self, count):
        """Return a list concatenating self with itself ``count`` times."""
        return LazyConcatenation([self] * count)

    def __rmul__(self, count):
        """Return a list concatenating self with itself ``count`` times."""
        return LazyConcatenation([self] * count)

    _MAX_REPR_SIZE = 60
    def __repr__(self):
        """
        Return a string representation for this corpus view that is
        similar to a list's representation; but if it would be more
        than 60 characters long, it is truncated.
        """
        pieces = []
        length = 5
        for elt in self:
            pieces.append(repr(elt))
            length += len(pieces[-1]) + 2
            if length > self._MAX_REPR_SIZE and len(pieces) > 2:
                return '[%s, ...]' % text_type(', ').join(pieces[:-1])
        else:
            return '[%s]' % text_type(', ').join(pieces)

    def __eq__(self, other):
        return (type(self) == type(other) and list(self) == list(other))

    def __ne__(self, other):
        return not self == other

    def __lt__(self, other):
        if type(other) != type(self):
            raise_unorderable_types("<", self, other)
        return list(self) < list(other)

    def __hash__(self):
        """
        :raise ValueError: Corpus view objects are unhashable.
        """
        raise ValueError('%s objects are unhashable' %
                         self.__class__.__name__)


class LazySubsequence(AbstractLazySequence):
    """
    A subsequence produced by slicing a lazy sequence.  This slice
    keeps a reference to its source sequence, and generates its values
    by looking them up in the source sequence.
    """

    MIN_SIZE = 100
    """
    The minimum size for which lazy slices should be created.  If
    ``LazySubsequence()`` is called with a subsequence that is
    shorter than ``MIN_SIZE``, then a tuple will be returned instead.
    """

    def __new__(cls, source, start, stop):
        """
        Construct a new slice from a given underlying sequence.  The
        ``start`` and ``stop`` indices should be absolute indices --
        i.e., they should not be negative (for indexing from the back
        of a list) or greater than the length of ``source``.
        """
        # If the slice is small enough, just use a tuple.
        if stop-start < cls.MIN_SIZE:
            return list(islice(source.iterate_from(start), stop-start))
        else:
            return object.__new__(cls)

    def __init__(self, source, start, stop):
        self._source = source
        self._start = start
        self._stop = stop

    def __len__(self):
        return self._stop - self._start

    def iterate_from(self, start):
        return islice(self._source.iterate_from(start+self._start),
                      max(0, len(self)-start))


class LazyConcatenation(AbstractLazySequence):
    """
    A lazy sequence formed by concatenating a list of lists.  This
    underlying list of lists may itself be lazy.  ``LazyConcatenation``
    maintains an index that it uses to keep track of the relationship
    between offsets in the concatenated lists and offsets in the
    sublists.
    """
    def __init__(self, list_of_lists):
        self._list = list_of_lists
        self._offsets = [0]

    def __len__(self):
        if len(self._offsets) <= len(self._list):
            for tok in self.iterate_from(self._offsets[-1]): pass
        return self._offsets[-1]

    def iterate_from(self, start_index):
        if start_index < self._offsets[-1]:
            sublist_index = bisect.bisect_right(self._offsets, start_index)-1
        else:
            sublist_index = len(self._offsets)-1

        index = self._offsets[sublist_index]

        # Construct an iterator over the sublists.
        if isinstance(self._list, AbstractLazySequence):
            sublist_iter = self._list.iterate_from(sublist_index)
        else:
            sublist_iter = islice(self._list, sublist_index, None)

        for sublist in sublist_iter:
            if sublist_index == (len(self._offsets)-1):
                assert index+len(sublist) >= self._offsets[-1], (
                        'offests not monotonic increasing!')
                self._offsets.append(index+len(sublist))
            else:
                assert self._offsets[sublist_index+1] == index+len(sublist), (
                        'inconsistent list value (num elts)')

            for value in sublist[max(0, start_index-index):]:
                yield value

            index += len(sublist)
            sublist_index += 1


class LazyMap(AbstractLazySequence):
    """
    A lazy sequence whose elements are formed by applying a given
    function to each element in one or more underlying lists.  The
    function is applied lazily -- i.e., when you read a value from the
    list, ``LazyMap`` will calculate that value by applying its
    function to the underlying lists' value(s).  ``LazyMap`` is
    essentially a lazy version of the Python primitive function
    ``map``.  In particular, the following two expressions are
    equivalent:

        >>> from nltk.util import LazyMap
        >>> function = str
        >>> sequence = [1,2,3]
        >>> map(function, sequence) # doctest: +SKIP
        ['1', '2', '3']
        >>> list(LazyMap(function, sequence))
        ['1', '2', '3']

    Like the Python ``map`` primitive, if the source lists do not have
    equal size, then the value None will be supplied for the
    'missing' elements.

    Lazy maps can be useful for conserving memory, in cases where
    individual values take up a lot of space.  This is especially true
    if the underlying list's values are constructed lazily, as is the
    case with many corpus readers.

    A typical example of a use case for this class is performing
    feature detection on the tokens in a corpus.  Since featuresets
    are encoded as dictionaries, which can take up a lot of memory,
    using a ``LazyMap`` can significantly reduce memory usage when
    training and running classifiers.
    """
    def __init__(self, function, *lists, **config):
        """
        :param function: The function that should be applied to
            elements of ``lists``.  It should take as many arguments
            as there are ``lists``.
        :param lists: The underlying lists.
        :param cache_size: Determines the size of the cache used
            by this lazy map.  (default=5)
        """
        if not lists:
            raise TypeError('LazyMap requires at least two args')

        self._lists = lists
        self._func = function
        self._cache_size = config.get('cache_size', 5)
        self._cache = ({} if self._cache_size > 0 else None)

        # If you just take bool() of sum() here _all_lazy will be true just
        # in case n >= 1 list is an AbstractLazySequence.  Presumably this
        # isn't what's intended.
        self._all_lazy = sum(isinstance(lst, AbstractLazySequence)
                             for lst in lists) == len(lists)

    def iterate_from(self, index):
        # Special case: one lazy sublist
        if len(self._lists) == 1 and self._all_lazy:
            for value in self._lists[0].iterate_from(index):
                yield self._func(value)
            return

        # Special case: one non-lazy sublist
        elif len(self._lists) == 1:
            while True:
                try: yield self._func(self._lists[0][index])
                except IndexError: return
                index += 1

        # Special case: n lazy sublists
        elif self._all_lazy:
            iterators = [lst.iterate_from(index) for lst in self._lists]
            while True:
                elements = []
                for iterator in iterators:
                    try: elements.append(next(iterator))
                    except: elements.append(None)
                if elements == [None] * len(self._lists):
                    return
                yield self._func(*elements)
                index += 1

        # general case
        else:
            while True:
                try: elements = [lst[index] for lst in self._lists]
                except IndexError:
                    elements = [None] * len(self._lists)
                    for i, lst in enumerate(self._lists):
                        try: elements[i] = lst[index]
                        except IndexError: pass
                    if elements == [None] * len(self._lists):
                        return
                yield self._func(*elements)
                index += 1

    def __getitem__(self, index):
        if isinstance(index, slice):
            sliced_lists = [lst[index] for lst in self._lists]
            return LazyMap(self._func, *sliced_lists)
        else:
            # Handle negative indices
            if index < 0: index += len(self)
            if index < 0: raise IndexError('index out of range')
            # Check the cache
            if self._cache is not None and index in self._cache:
                return self._cache[index]
            # Calculate the value
            try: val = next(self.iterate_from(index))
            except StopIteration:
                raise IndexError('index out of range')
            # Update the cache
            if self._cache is not None:
                if len(self._cache) > self._cache_size:
                    self._cache.popitem() # discard random entry
                self._cache[index] = val
            # Return the value
            return val

    def __len__(self):
        return max(len(lst) for lst in self._lists)


class LazyZip(LazyMap):
    """
    A lazy sequence whose elements are tuples, each containing the i-th
    element from each of the argument sequences.  The returned list is
    truncated in length to the length of the shortest argument sequence. The
    tuples are constructed lazily -- i.e., when you read a value from the
    list, ``LazyZip`` will calculate that value by forming a tuple from
    the i-th element of each of the argument sequences.

    ``LazyZip`` is essentially a lazy version of the Python primitive function
    ``zip``.  In particular, an evaluated LazyZip is equivalent to a zip:

        >>> from nltk.util import LazyZip
        >>> sequence1, sequence2 = [1, 2, 3], ['a', 'b', 'c']
        >>> zip(sequence1, sequence2) # doctest: +SKIP
        [(1, 'a'), (2, 'b'), (3, 'c')]
        >>> list(LazyZip(sequence1, sequence2))
        [(1, 'a'), (2, 'b'), (3, 'c')]
        >>> sequences = [sequence1, sequence2, [6,7,8,9]]
        >>> list(zip(*sequences)) == list(LazyZip(*sequences))
        True

    Lazy zips can be useful for conserving memory in cases where the argument
    sequences are particularly long.

    A typical example of a use case for this class is combining long sequences
    of gold standard and predicted values in a classification or tagging task
    in order to calculate accuracy.  By constructing tuples lazily and
    avoiding the creation of an additional long sequence, memory usage can be
    significantly reduced.
    """
    def __init__(self, *lists):
        """
        :param lists: the underlying lists
        :type lists: list(list)
        """
        LazyMap.__init__(self, lambda *elts: elts, *lists)

    def iterate_from(self, index):
        iterator = LazyMap.iterate_from(self, index)
        while index < len(self):
            yield next(iterator)
            index += 1
        return

    def __len__(self):
        return min(len(lst) for lst in self._lists)


class LazyEnumerate(LazyZip):
    """
    A lazy sequence whose elements are tuples, each ontaining a count (from
    zero) and a value yielded by underlying sequence.  ``LazyEnumerate`` is
    useful for obtaining an indexed list. The tuples are constructed lazily
    -- i.e., when you read a value from the list, ``LazyEnumerate`` will
    calculate that value by forming a tuple from the count of the i-th
    element and the i-th element of the underlying sequence.

    ``LazyEnumerate`` is essentially a lazy version of the Python primitive
    function ``enumerate``.  In particular, the following two expressions are
    equivalent:

        >>> from nltk.util import LazyEnumerate
        >>> sequence = ['first', 'second', 'third']
        >>> list(enumerate(sequence))
        [(0, 'first'), (1, 'second'), (2, 'third')]
        >>> list(LazyEnumerate(sequence))
        [(0, 'first'), (1, 'second'), (2, 'third')]

    Lazy enumerations can be useful for conserving memory in cases where the
    argument sequences are particularly long.

    A typical example of a use case for this class is obtaining an indexed
    list for a long sequence of values.  By constructing tuples lazily and
    avoiding the creation of an additional long sequence, memory usage can be
    significantly reduced.
    """

    def __init__(self, lst):
        """
        :param lst: the underlying list
        :type lst: list
        """
        LazyZip.__init__(self, range(len(lst)), lst)


######################################################################
# Binary Search in a File
######################################################################

# inherited from pywordnet, by Oliver Steele
def binary_search_file(file, key, cache={}, cacheDepth=-1):
    """
    Return the line from the file with first word key.
    Searches through a sorted file using the binary search algorithm.

    :type file: file
    :param file: the file to be searched through.
    :type key: str
    :param key: the identifier we are searching for.
    """

    key = key + ' '
    keylen = len(key)
    start = 0
    currentDepth = 0

    if hasattr(file, 'name'):
        end = os.stat(file.name).st_size - 1
    else:
        file.seek(0, 2)
        end = file.tell() - 1
        file.seek(0)

    while start < end:
        lastState = start, end
        middle = (start + end) // 2

        if cache.get(middle):
            offset, line = cache[middle]

        else:
            line = ""
            while True:
                file.seek(max(0, middle - 1))
                if middle > 0:
                    file.readline()
                offset = file.tell()
                line = file.readline()
                if line != "": break
                # at EOF; try to find start of the last line
                middle = (start + middle)//2
                if middle == end -1:
                    return None
            if currentDepth < cacheDepth:
                cache[middle] = (offset, line)

        if offset > end:
            assert end != middle - 1, "infinite loop"
            end = middle - 1
        elif line[:keylen] == key:
            return line
        elif line > key:
            assert end != middle - 1, "infinite loop"
            end = middle - 1
        elif line < key:
            start = offset + len(line) - 1

        currentDepth += 1
        thisState = start, end

        if lastState == thisState:
            # Detects the condition where we're searching past the end
            # of the file, which is otherwise difficult to detect
            return None

    return None

######################################################################
# Proxy configuration
######################################################################

def set_proxy(proxy, user=None, password=''):
    """
    Set the HTTP proxy for Python to download through.

    If ``proxy`` is None then tries to set proxy from environment or system
    settings.

    :param proxy: The HTTP proxy server to use. For example:
        'http://proxy.example.com:3128/'
    :param user: The username to authenticate with. Use None to disable
        authentication.
    :param password: The password to authenticate with.
    """
    from nltk import compat

    if proxy is None:
        # Try and find the system proxy settings
        try:
            proxy = getproxies()['http']
        except KeyError:
            raise ValueError('Could not detect default proxy settings')

    # Set up the proxy handler
    proxy_handler = ProxyHandler({'http': proxy})
    opener = build_opener(proxy_handler)

    if user is not None:
        # Set up basic proxy authentication if provided
        password_manager = HTTPPasswordMgrWithDefaultRealm()
        password_manager.add_password(realm=None, uri=proxy, user=user,
                passwd=password)
        opener.add_handler(ProxyBasicAuthHandler(password_manager))
        opener.add_handler(ProxyDigestAuthHandler(password_manager))

    # Overide the existing url opener
    install_opener(opener)


######################################################################
# ElementTree pretty printing from http://www.effbot.org/zone/element-lib.htm
######################################################################


def elementtree_indent(elem, level=0):
    """
    Recursive function to indent an ElementTree._ElementInterface
    used for pretty printing. Run indent on elem and then output
    in the normal way. 
    
    :param elem: element to be indented. will be modified. 
    :type elem: ElementTree._ElementInterface
    :param level: level of indentation for this element
    :type level: nonnegative integer
    :rtype:   ElementTree._ElementInterface
    :return:  Contents of elem indented to reflect its structure
    """

    i = "\n" + level*"  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        for elem in elem:
            elementtree_indent(elem, level+1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

######################################################################
# Mathematical approximations
######################################################################

def choose(n, k):
    """
    This function is a fast way to calculate binomial coefficients, commonly
    known as nCk, i.e. the number of combinations of n things taken k at a time. 
    (https://en.wikipedia.org/wiki/Binomial_coefficient).
    
    This is the *scipy.special.comb()* with long integer computation but this 
    approximation is faster, see https://github.com/nltk/nltk/issues/1181
    
        >>> choose(4, 2)
        6
        >>> choose(6, 2)
        15
    
    :param n: The number of things.
    :type n: int
    :param r: The number of times a thing is taken.
    :type r: int
    """
    if 0 <= k <= n:
        ntok, ktok = 1, 1
        for t in range(1, min(k, n - k) + 1):
            ntok *= n
            ktok *= t
            n -= 1
        return ntok // ktok
    else:
        return 0

######################################################################
# Trie Implementation
######################################################################
class Trie(defaultdict):
    """A Trie implementation for strings"""
    LEAF = True

    def __init__(self, strings=None):
        """Builds a Trie object, which is built around a ``defaultdict``
        
        If ``strings`` is provided, it will add the ``strings``, which
        consist of a ``list`` of ``strings``, to the Trie. 
        Otherwise, it'll construct an empty Trie.

        :param strings: List of strings to insert into the trie 
            (Default is ``None``)
        :type strings: list(str)

        """
        defaultdict.__init__(self, Trie)
        if strings:
            for string in strings:
                self.insert(string)

    def insert(self, string):
        """Inserts ``string`` into the Trie

        :param string: String to insert into the trie
        :type string: str

        :Example:

        >>> from nltk.util import Trie
        >>> trie = Trie(["ab"])
        >>> trie
        defaultdict(<class 'nltk.util.Trie'>, {'a': defaultdict(<class 'nltk.util.Trie'>, {'b': defaultdict(<class 'nltk.util.Trie'>, {True: None})})})

        """
        if len(string):
            self[string[0]].insert(string[1:])
        else:
            # mark the string is complete
            self[Trie.LEAF] = None

    def __str__(self):
        return str(self.as_dict())

    def as_dict(self, d=None):
        """Convert ``defaultdict`` to common ``dict`` representation.

        :param: A defaultdict containing strings mapped to nested defaultdicts.
            This is the structure of the trie. (Default is None)
        :type: defaultdict(str -> defaultdict)
        :return: Even though ``defaultdict`` is a subclass of ``dict`` and thus
            can be converted to a simple ``dict`` using ``dict()``, in our case
            it's a nested ``defaultdict``, so here's a quick trick to provide to
            us the ``dict`` representation of the ``Trie`` without 
            ``defaultdict(<class 'nltk.util.Trie'>, ...``
        :rtype: dict(str -> dict(bool -> None))
            Note: there can be an arbitrarily deeply nested 
            ``dict(str -> dict(str -> dict(..))``, but the last
            level will have ``dict(str -> dict(bool -> None))``

        :Example:

        >>> from nltk.util import Trie
        >>> trie = Trie(["abc", "def"])
        >>> expected = {'a': {'b': {'c': {True: None}}}, 'd': {'e': {'f': {True: None}}}}
        >>> trie.as_dict() == expected
        True

        """
        def _default_to_regular(d):
            """
            Source: http://stackoverflow.com/a/26496899/4760801

            :param d: Nested ``defaultdict`` to convert to regular ``dict``
            :type d: defaultdict(str -> defaultdict(...))
            :return: A dict representation of the defaultdict
            :rtype: dict(str -> dict(str -> ...))

            :Example:

            >>> from collections import defaultdict
            >>> d = defaultdict(defaultdict)
            >>> d["one"]["two"] = "three"
            >>> d
            defaultdict(<type 'collections.defaultdict'>, {'one': defaultdict(None, {'two': 'three'})})
            >>> _default_to_regular(d)
            {'one': {'two': 'three'}}

            """
            if isinstance(d, defaultdict):
                d = {k: _default_to_regular(v) for k, v in d.items()}
            return d
        
        return _default_to_regular(self)
