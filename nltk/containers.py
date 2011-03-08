# Natural Language Toolkit: Miscellaneous container classes
#
# Copyright (C) 2001-2011 NLTK Project
# Author: Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

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
            if key not in self:
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
        if key not in self:
            raise KeyError(key)
        return self._keys.index(key)


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

    def __ne__(self, other):
        return not (self == other)

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

