# Natural Language Toolkit: Utility functions
#
# Copyright (C) 2001-2008 NLTK Project
# Author: Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://nltk.org>
# For license information, see LICENSE.TXT

import locale
import re
import types
import textwrap
import pydoc
import bisect
from itertools import islice
from pprint import pprint
from nltk.internals import Deprecated, slice_bounds

######################################################################
# Short usage message
######################################################################

def usage(obj, selfname='self'):
    import inspect
    str(obj) # In case it's lazy, this will load it.
    
    if not isinstance(obj, (types.TypeType, types.ClassType)):
        obj = obj.__class__

    print '%s supports the following operations:' % obj.__name__
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
        print textwrap.fill('%s%s' % (name, argspec),
                            initial_indent='  - ',
                            subsequent_indent=' '*(len(name)+5))

##########################################################################
# PRETTY PRINTING
##########################################################################

def pr(data, start=0, end=None):
    """
    Pretty print a sequence of data items

    @param data: the data stream to print
    @type data: C{sequence} or C{iterator}
    @param start: the start position
    @type start: C{int}
    @param end: the end position
    @type end: C{int}
    """
    pprint(list(islice(data, start, end)))

def print_string(s, width=70):
    """
    Pretty print a string, breaking lines on whitespace

    @param s: the string to print, consisting of words and spaces
    @type s: C{string}
    @param width: the display width
    @type width: C{int}
    """
    while s:
        s = s.strip()
        try:
            i = s[:width].rindex(' ')
        except ValueError:
            print s
            return
        print s[:i]
        s = s[i:]

##########################################################################
# MINIMAL SETS
##########################################################################

class MinimalSet(object):
    """
    Find contexts where more than one possible target value can
    appear.  E.g. if targets are word-initial letters, and contexts
    are the remainders of words, then we would like to find cases like
    "fat" vs "cat", and "training" vs "draining".  If targets are
    parts-of-speech and contexts are words, then we would like to find
    cases like wind (noun) 'air in rapid motion', vs wind (verb)
    'coil, wrap'.
    """
    def __init__(self, parameters=None):
        """
        Create a new minimal set.

        @param parameters: The (context, target, display) tuples for the item
        @type parameters: C{list} of C{tuple} of C{string}
        """
        self._targets = set()  # the contrastive information
        self._contexts = set() # what we are controlling for
        self._seen = {}        # to record what we have seen
        self._displays = {}    # what we will display

        if parameters:
            for context, target, display in parameters:
                self.add(context, target, display)

    def add(self, context, target, display):
        """
        Add a new item to the minimal set, having the specified
        context, target, and display form.

        @param context: The context in which the item of interest appears
        @type context: C{string}
        @param target: The item of interest
        @type target: C{string}
        @param display: The information to be reported for each item
        @type display: C{string}
        """
        # Store the set of targets that occurred in this context
        if context not in self._seen:
           self._seen[context] = set()
        self._seen[context].add(target)

        # Keep track of which contexts and targets we have seen
        self._contexts.add(context)
        self._targets.add(target)

        # For a given context and target, store the display form
        self._displays[(context, target)] = display

    def contexts(self, minimum=2):
        """
        Determine which contexts occurred with enough distinct targets.

        @param minimum: the minimum number of distinct target forms
        @type minimum: C{int}
        @rtype C{list}
        """
        return [c for c in self._contexts if len(self._seen[c]) >= minimum]

    def display(self, context, target, default=""):
        if (context, target) not in self._displays:
            return self._displays[(context, target)]
        else:
            return default

    def display_all(self, context):
        result = []
        for target in self._targets:
            x = self.display(context, target)
            if x: result.append(x)
        return result

    def targets(self):
        return self._targets


######################################################################
## Regexp display (thanks to David Mertz)
######################################################################

def re_show(regexp, string, left="{", right="}"):
    """
    Search C{string} for substrings matching C{regexp} and wrap
    the matches with braces.  This is convenient for learning about
    regular expressions.

    @param regexp: The regular expression.
    @type regexp: C{string}
    @param string: The string being matched.
    @type string: C{string}
    @param left: The left delimiter (printed before the matched substring)
    @type left: C{string}
    @param right: The right delimiter (printed after the matched substring)
    @type right: C{string}
    @rtype: C{string}
    @return: A string with markers surrounding the matched substrings.
    """
    print re.compile(regexp, re.M).sub(left + r"\g<0>" + right, string.rstrip())


##########################################################################
# READ FROM FILE OR STRING
##########################################################################

# recipe from David Mertz
def filestring(f):
    if hasattr(f, 'read'):
        return f.read()
    elif isinstance(f, basestring):
        return open(f).read()
    else:
        raise ValueError, "Must be called with a filename or file-like object"

##########################################################################
# Breadth-First Search
##########################################################################

def breadth_first(tree, children=iter, depth=-1, queue=None):
    """Traverse the nodes of a tree in breadth-first order.
    (No need to check for cycles.)
    The first argument should be the tree root;
    children should be a function taking as argument a tree node
    and returning an iterator of the node's children.
    """
    if queue == None:
        queue = []
    queue.append(tree)
    
    while queue:
        node = queue.pop(0)
        yield node
        if depth != 0:
            try:
                queue += children(node)
                depth -= 1
            except:
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

    If successful it returns C{(decoded_unicode, successful_encoding)}.
    If unsuccessful it raises a C{UnicodeError}.
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
            decoded = unicode(data, enc)
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
# Invert a dictionary
##########################################################################

def invert_dict(d):
    from nltk import defaultdict
    inverted_dict = defaultdict(list)
    for key in d:
        for term in d[key]:
            inverted_dict[term].append(key)
    return inverted_dict


##########################################################################
# HTML Cleaning
##########################################################################

from HTMLParser import HTMLParser
skip = ['script', 'style']   # non-nesting tags to skip

class HTMLCleaner(HTMLParser):
    def __init__(self):
        self.reset()
        self.fed = []
        self._flag = True
    def handle_data(self, d):
        if self._flag:
            self.fed.append(d)
    def handle_starttag(self, tag, attrs):
        if tag in skip:
            self._flag = False
    def handle_endtag(self, tag):
        if tag in skip:
            self._flag = True
    def clean_text(self):
        return ''.join(self.fed)

def clean_html(html):
    """
    Remove HTML markup from the given string.

    @param html: the HTML string to be cleaned
    @type html: C{string}
    @rtype: C{string}
    """
    
    cleaner = HTMLCleaner()
    cleaner.feed(html)
    return cleaner.clean_text()

def clean_url(url):
   from urllib import urlopen
   html = urlopen(url).read()
   return clean_html(html)

##########################################################################
# Ngram iteration
##########################################################################

def ngram(sequence, n):
    """
    A utility that produces a sequence of ngrams from a sequence of items.
    For example:
    
    >>> ngram([1,2,3,4,5], 3)
    [(1, 2, 3), (2, 3, 4), (3, 4, 5)]
    
    Use ingram for an iterator version of this function.

    @param sequence: the source data to be converted into ngrams
    @type sequence: C{sequence} or C{iterator}
    @param n: the degree of the ngram
    @type n: C{int}
    @return: The ngrams
    @rtype: C{list} of C{tuple}s
    """

    count = max(0, len(list(sequence)) - n + 1)
    return [tuple(sequence[i:i+n]) for i in range(count)]

def ingram(sequence, n):
    """
    A utility that produces an iterator over ngrams generated from a sequence of items.
    
    For example:
    
    >>> list(ingram([1,2,3,4,5], 3))
    [(1, 2, 3), (2, 3, 4), (3, 4, 5)]
    
    Use ngram for a list version of this function.

    @param sequence: the source data to be converted into ngrams
    @type sequence: C{sequence} or C{iterator}
    @param n: the degree of the ngram
    @type n: C{int}
    @return: The ngrams
    @rtype: C{iterator} of C{tuple}s
        """

    sequence = iter(sequence)
    history = []
    while n > 1:
        history.append(sequence.next())
        n -= 1
    for item in sequence:
        history.append(item)
        yield tuple(history)
        del history[0]

######################################################################
# Lazy Sequences
######################################################################

class AbstractLazySequence(object):
    """
    An abstract base class for read-only sequences whose values are
    computed as needed.  Lazy sequences act like tuples -- they can be
    indexed, sliced, and iterated over; but they may not be modified.

    The most common application of lazy sequences in NLTK is for
    I{corpus view} objects, which provide access to the contents of a
    corpus without loading the entire corpus into memory, by loading
    pieces of the corpus from disk as needed.
    
    The result of modifying a mutable element of a lazy sequence is
    undefined.  In particular, the modifications made to the element
    may or may not persist, depending on whether and when the lazy
    sequence caches that element's value or reconstructs it from
    scratch.

    Subclasses are required to define two methods:
    
      - L{__len__()}
      - L{iterate_from()}.
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
        C{start}.  If C{start>=len(self)}, then this iterator will
        generate no tokens.
        """
        raise NotImplementedError('should be implemented by subclass')
    
    def __getitem__(self, i):
        """
        Return the C{i}th token in the corpus file underlying this
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
                return self.iterate_from(i).next()
            except StopIteration:
                raise IndexError('index out of range')

    def __iter__(self):
        """Return an iterator that generates the tokens in the corpus
        file underlying this corpus view."""
        return self.iterate_from(0)

    def count(self, value):
        """Return the number of times this list contains C{value}."""
        return sum(1 for elt in self if elt==value)
    
    def index(self, value, start=None, stop=None):
        """Return the index of the first occurance of C{value} in this
        list that is greater than or equal to C{start} and less than
        C{stop}.  Negative start & stop values are treated like negative
        slice bounds -- i.e., they count from the end of the list."""
        start, stop = slice_bounds(self, slice(start, stop))
        for i, elt in enumerate(islice(self, start, stop)):
            if elt == value: return i+start
        raise ValueError('index(x): x not in list')

    def __contains__(self, value):
        """Return true if this list contains C{value}."""
        return bool(self.count(value))
    
    def __add__(self, other):
        """Return a list concatenating self with other."""
        return LazyConcatenation([self, other])
    
    def __radd__(self, other):
        """Return a list concatenating other with self."""
        return LazyConcatenation([other, self])
    
    def __mul__(self, count):
        """Return a list concatenating self with itself C{count} times."""
        return LazyConcatenation([self] * count)
    
    def __rmul__(self, count):
        """Return a list concatenating self with itself C{count} times."""
        return LazyConcatenation([self] * count)

    _MAX_REPR_SIZE = 60
    def __repr__(self):
        """
        @return: A string representation for this corpus view that is
        similar to a list's representation; but if it would be more
        than 60 characters long, it is truncated.
        """
        pieces = []
        length = 5
        for elt in self:
            pieces.append(repr(elt))
            length += len(pieces[-1]) + 2
            if length > self._MAX_REPR_SIZE and len(pieces) > 2:
                return '[%s, ...]' % ', '.join(pieces[:-1])
        else:
            return '[%s]' % ', '.join(pieces)

    def __cmp__(self, other):
        """
        Return a number indicating how C{self} relates to other.

          - If C{other} is not a corpus view or a C{list}, return -1.
          - Otherwise, return C{cmp(list(self), list(other))}.

        Note: corpus views do not compare equal to tuples containing
        equal elements.  Otherwise, transitivity would be violated,
        since tuples do not compare equal to lists.
        """
        if not isinstance(other, (AbstractCorpusView, list)): return -1
        return cmp(list(self), list(other))

    def __hash__(self):
        """
        @raise ValueError: Corpus view objects are unhashable.
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
    """The minimum size for which lazy slices should be created.  If
       C{LazySubsequence()} is called with a subsequence that is
       shorter than C{MIN_SIZE}, then a tuple will be returned
       instead."""
    
    def __new__(cls, source, start, stop):
        """
        Construct a new slice from a given underlying sequence.  The
        C{start} and C{stop} indices should be absolute indices --
        i.e., they should not be negative (for indexing from the back
        of a list) or greater than the length of C{source}.
        """
        # If the slice is small enough, just use a tuple.
        if stop-start < cls.MIN_SIZE:
            return list(islice(source.iterate_from(start), stop-start))
        else:
            return object.__new__(cls, source, start, stop)
        
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
    underlying list of lists may itself be lazy.  C{LazyConcatenation}
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
    list, C{LazyMap} will calculate that value by applying its
    function to the underlying lists' value(s).  C{LazyMap} is
    essentially a lazy version of the Python primitive function
    C{map}.  In particular, the following two expressions are
    equivalent:

        >>> map(f, sequences...)
        >>> list(LazyMap(f, sequences...))

    Like the Python C{map} primitive, if the source lists do not have
    equal size, then the value C{None} will be supplied for the
    'missing' elements.
    
    Lazy maps can be useful for conserving memory, in cases where
    individual values take up a lot of space.  This is especially true
    if the underlying list's values are constructed lazily, as is the
    case with many corpus readers.

    A typical example of a use case for this class is performing
    feature detection on the tokens in a corpus.  Since featuresets
    are encoded as dictionaries, which can take up a lot of memory,
    using a C{LazyMap} can significantly reduce memory usage when
    training and running classifiers.
    """
    def __init__(self, function, *lists, **config):
        """
        @param function: The function that should be applied to
            elements of C{lists}.  It should take as many arguments
            as there are C{lists}.
        @param lists: The underlying lists.
        @kwparam cache_size: Determines the size of the cache used
            by this lazy map.  (default=5)
        """
        if not lists:
            raise TypeError('LazyMap requires at least two args')
        
        self._lists = lists
        self._func = function
        self._cache_size = config.get('cache_size', 5)
        if self._cache_size > 0:
            self._cache = {}
        else:
            self._cache = None

    def iterate_from(self, index):
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
            try: val = self.iterate_from(index).next()
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
    
class LazyMappedList(Deprecated, LazyMap):
    """Use LazyMap instead."""
    def __init__(self, lst, func):
        LazyMap.__init__(self, func, lst)

# Consider replacing lazy mapped chain, basically as follows:?
#def LazyMappedChain(lst, func):
#    return LazyConcatenation(LazyMap(func, lst))

class LazyMappedChain(object):
    """
    A chained read-only list of the values generated by applying a 
    function to an underlying list of lists.  The function is applied 
    lazily to each list -- i.e., when you read a value from the list, 
    C{LazyMappedChain} will calculate that value by applying its function 
    to the underlying list of list's value.

    This can be very useful for conserving memory, in cases where the
    individual values take up a lot of space.  This is especially true
    if the underlying list of list's values are constructed lazily, as 
    is the case with many corpus readers.

    A typical use case for this class is performing lazy tagging or 
    chunking of a corpus using a sequence model such as an HMM and 
    reading each token as from a single list.  C{LazyMappedChain}
    applied in this way allows on-the-fly, lazy tagging word or token
    views.  This makes it possible to decorate C{CorpusReader} classes
    with tagged_words() without first tagging every sentence. 
    """
    def __init__(self, lst, func):
        self._lst = lst
        self._func = func

    def _indices(self):
        i = -1
        for j in xrange(len(self._lst)):
            for k in xrange(len(self._lst[j])):
                i += 1
                yield (i, (j, k))
        return

    def __getitem__(self, index):
        if isinstance(index, slice):
            index_range = range(*index.indices(len(self)))
            return [self._func(self._lst[j])[k] 
                    for i, (j, k) in self._indices() if i in index_range]
        else:
            for i, (j, k) in self._indices():
                if i == index:
                    return self._func(self._lst[j])[k]

    def __iter__(self):
        return (self._func(self._lst[j])[k] for i, (j, k) in self._indices())

    def __len__(self):
        return sum(len(lst) for lst in self._lst)
