# Natural Language Toolkit: Edit Distance
#
# Copyright (C) 2001-2009 NLTK Project
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT


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
    @type s1: C{string}
    @type s2: C{string}
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

def demo():
    s1 = "rain"
    s2 = "shine"
    print "Edit distance between '%s' and '%s':", edit_dist(s1, s2)

if __name__ == '__main__':
    demo()
