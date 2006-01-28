# Natural Language Toolkit: Utility functions
#
# Copyright (C) 2001-2005 University of Pennsylvania
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
    def __init__(self):
        """
        Create a new minimal set.
        """
        self._targets = set()  # the contrastive information
        self._contexts = set() # what we are controlling for
        self._seen = {}        # to record what we have seen
        self._displays = {}    # what we will display

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
    elif type(f) in (StringType, UnicodeType):
        return open(f).read()
    else:
        raise ValueError, "Must be called with a filename or file-like object"

