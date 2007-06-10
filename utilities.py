# Natural Language Toolkit: Utility functions
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT


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
    from pprint import pprint
    from itertools import islice
    pprint(list(islice(data, start, end)))

def print_string(s, width=70):
    """
    Pretty print a string, breaking lines on whitespace

    @param s: the string to print, consisting of words and spaces
    @type s: C{string}
    @param width: the display width
    @type width: C{int}
    """
    import re
    while s:
        s = s.strip()
        try:
            i = s[:width].rindex(' ')
        except ValueError:
            print s
            return
        print s[:i]
        s = s[i:]

class SortedDict(dict):
    """
    A very rudamentary sorted dictionary, whose main purpose is to
    allow dictionaries to be displayed in a consistent order in
    regression tests.  keys(), items(), values(), iter*(), and
    __repr__ all sort their return values before returning them.
    (note that the sort order for values() does *not* correspond to
    the sort order for keys().  I.e., zip(d.keys(), d.values()) is not
    necessarily equal to d.items().
    """
    def keys(self): return sorted(dict.keys(self))
    def items(self): return sorted(dict.items(self))
    def values(self): return sorted(dict.values(self))
    def iterkeys(self): return iter(sorted(dict.keys(self)))
    def iteritems(self): return iter(sorted(dict.items(self)))
    def itervalues(self): return iter(sorted(dict.values(self)))
    def __iter__(self): return iter(sorted(dict.keys(self)))
    def repr(self):
        items = ['%s=%s' % t for t in sorted(self.items())]
        return '{%s}' % ', '.join(items)
    
# OrderedDict: Written Doug Winter
# http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/438823

class OrderedDict(dict):
    """
    This implementation of a dictionary keeps track of the order
    in which keys were inserted.
    """

    def __init__(self, d={}):
        self._keys = d.keys()
        dict.__init__(self, d)

    def __delitem__(self, key):
        dict.__delitem__(self, key)
        self._keys.remove(key)

    def __setitem__(self, key, item):
        dict.__setitem__(self, key, item)
        # a peculiar sharp edge from copy.deepcopy
        # we'll have our set item called without __init__
        if not hasattr(self, '_keys'):
            self._keys = [key,]
        if key not in self._keys:
            self._keys.append(key)

    def clear(self):
        dict.clear(self)
        self._keys = []

    def items(self):
        for i in self._keys:
            yield i, self[i]

    def keys(self):
        return self._keys

    def popitem(self):
        if len(self._keys) == 0:
            raise KeyError('dictionary is empty')
        else:
            key = self._keys[-1]
            val = self[key]
            del self[key]
            return key, val

    def setdefault(self, key, failobj = None):
        dict.setdefault(self, key, failobj)
        if key not in self._keys:
            self._keys.append(key)

    def update(self, d):
        for key in d.keys():
            if not self.has_key(key):
                self._keys.append(key)
        dict.update(self, d)

    def values(self):
        for i in self._keys:
            yield self[i]

    def move(self, key, index):

        """ Move the specified to key to *before* the specified index. """

        try:
            cur = self._keys.index(key)
        except ValueError:
            raise KeyError(key)
        self._keys.insert(index, key)
        # this may have shifted the position of cur, if it is after index
        if cur >= index: cur = cur + 1
        del self._keys[cur]

    def index(self, key):
        if not self.has_key(key):
            raise KeyError(key)
        return self._keys.index(key)




##########################################################################
# EDIT DISTANCE (LEVENSHTEIN)
##########################################################################

def _edit_dist_init(len1, len2):
    lev = []
    for i in range(len1):
        lev.append([0] * len2)  # initialize 2-D array to zero
    for i in range(len1):
        lev[i][0] = i           # column 0: 0,1,2,3,4,...
    for j in range(len2):
        lev[0][j] = j           # row 0: 0,1,2,3,4,...
    return lev

def _edit_dist_step(lev, i, j, c1, c2):
    a = lev[i-1][j  ] + 1            # skipping s1[i]
    b = lev[i-1][j-1] + (c1 != c2)   # matching s1[i] with s2[j]
    c = lev[i  ][j-1] + 1            # skipping s2[j]
    lev[i][j] = min(a,b,c)           # pick the cheapest

def edit_dist(s1, s2):
    """
    Calculate the Levenshtein edit-distance between two strings.
    The edit distance is the number of characters that need to be
    substituted, inserted, or deleted, to transform s1 into s2.  For
    example, transforming "rain" to "shine" requires three steps,
    consisting of two substitutions and one insertion:
    "rain" -> "sain" -> "shin" -> "shine".  These operations could have
    been done in other orders, but at least three steps are needed.

    @param s1, s2: The strings to be analysed
    @type s1, s2: C{string}
    @rtype C{int}
    """
    # set up a 2-D array
    len1 = len(s1); len2 = len(s2)
    lev = _edit_dist_init(len1+1, len2+1)

    # iterate over the array
    for i in range(len1):
        for j in range (len2):
            _edit_dist_step(lev, i+1, j+1, s1[i], s2[j])
    return lev[len1][len2]


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
        @type minimum: C(int)
        @rtype C(list)
        """
        return [c for c in self._contexts if len(self._seen[c]) >= minimum]

    def display(self, context, target, default=""):
        if self._displays.has_key((context, target)):
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

import re
def re_show(regexp, string):
    """
    Search C{string} for substrings matching C{regexp} and wrap
    the matches with braces.  This is convenient for learning about
    regular expressions.

    @param regexp: The regular expression.
    @param string: The string being matched.
    @rtype: C{string}
    @return: A string with braces surrounding the matched substrings.
    """
    print re.compile(regexp, re.M).sub("{\g<0>}", string.rstrip())


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
# COUNTER, FOR UNIQUE NAMING
##########################################################################

class Counter:
    """
    A counter that auto-increments each time its value is read.
    """
    def __init__(self, initial_value=0):
	self._value = initial_value
    def get(self):
	self._value += 1
	return self._value


##########################################################################
# TRIES
##########################################################################

# Trie structure, by James Tauber and Leonardo Maffi (V. 1.2, July 18 2006)
# Extended by Steven Bird

class Trie:
    """A Trie is like a dictionary in that it maps keys to
    values. However, because of the way keys are stored, it allows
    look up based on the longest prefix that matches.  Keys must be
    strings.
    """

    def __init__(self, trie=None):
        if trie is None:
            self._root = [None, {}, 0]
        else:
            self._root = trie

    def clear(self):
        self._root = [None, {}, 0]

    def isleaf(self, key):
        """Return True if the key is present and it's a leaf of the
        Trie, False otherwise."""

        curr_node = self._root
        for char in key:
            curr_node_1 = curr_node[1]
            if char in curr_node_1:
                curr_node = curr_node_1[char]
            else:
                return False
        return curr_node[0] is not None

    def find_prefix(self, key):
        """Find as much of the key as one can, by using the longest
        prefix that has a value.  Return (value, remainder) where
        remainder is the rest of the given string."""

        curr_node = self._root
        remainder = key
        for char in key:
            if char in curr_node[1]:
                curr_node = curr_node[1][char]
            else:
                return curr_node[0], remainder
            remainder = remainder[1:]
        return curr_node[0], remainder

    def subtrie(self, key):
        curr_node = self._root
        for char in key:
            curr_node = curr_node[1][char]
        return Trie(trie=curr_node)

    def __len__(self):
        return self._root[2]

    def __eq__(self, other):
        return self._root == other._root

    def __setitem__(self, key, value):
        curr_node = self._root
        for char in key:
            curr_node[2] += 1
            curr_node = curr_node[1].setdefault(char, [None, {}, 0])
        curr_node[0] = value
        curr_node[2] += 1

    def __getitem__(self, key):
        """Return the value for the given key if it is present, raises
        a KeyError if key not found, and return None if it is present
        a key2 that starts with key."""

        curr_node = self._root
        for char in key:
            curr_node = curr_node[1][char]
        return curr_node[0]

    def __contains__(self, key):
        """Return True if the key is present or if it is present a
        key2 string that starts with key."""

        curr_node = self._root
        for char in key:
            curr_node_1 = curr_node[1]
            if char in curr_node_1:
                curr_node = curr_node_1[char]
            else:
                return False
        return True

    def __str__(self):
        return str(self._root)

    def __repr__(self):
        return "Trie(%r)" % self._root

##########################################################################
# Breadth-First Search
##########################################################################

# Adapted from a Python cookbook entry; original version by David Eppstein
def breadth_first(tree, children=iter, depth=-1):
    """Traverse the nodes of a tree in breadth-first order.
    The first argument should be the tree root; children
    should be a function taking as argument a tree node and
    returning an iterator of the node's children.
    """
    yield tree
    last = tree
    if depth != 0:
        for node in breadth_first(tree, children, depth-1):
            for child in children(node):
                yield child
                last = child
            if last == node:
                return

##########################################################################
# Guess Character Encoding
##########################################################################

# adapted from io.py in the docutils extension module (http://docutils.sourceforge.net)
# http://www.pyzine.com/Issue008/Section_Articles/article_Encodings.html

import locale
def guess_encoding(data):
    """
    Given a byte string, attempt to decode it.
    Tries the standard 'UTF8' and 'latin-1' encodings,
    Plus several gathered from locale information.

    The calling program *must* first call 
        locale.setlocale(locale.LC_ALL, '')

    If successful it returns 
        (decoded_unicode, successful_encoding)
    If unsuccessful it raises a ``UnicodeError``
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

