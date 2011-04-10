# Natural Language Toolkit: Distance Metrics
#
# Copyright (C) 2001-2011 NLTK Project
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au>
#         Tom Lippincott <tom@cs.columbia.edu>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT
#

"""
Distance Metrics.

Compute the distance between two items (usually strings).
As metrics, they must satisfy the following three requirements:

1. d(a, a) = 0
2. d(a, b) >= 0
3. d(a, c) <= d(a, b) + d(b, c)
 
"""

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

def edit_distance(s1, s2):
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


def binary_distance(label1, label2):
    """Simple equality test.

    0.0 if the labels are identical, 1.0 if they are different.

    >>> binary_distance(1,1)
    0.0

    >>> binary_distance(1,3)
    1.0
    """

    if label1 == label2:
        return 0.0
    else:
        return 1.0


def jaccard_distance(label1, label2):
    """Distance metric comparing set-similarity.

    """
    return (len(label1.union(label2)) - len(label1.intersection(label2)))/float(len(label1.union(label2)))


def masi_distance(label1, label2):
    """Distance metric that takes into account partial agreement when multiple
    labels are assigned.

    >>> masi_distance(set([1,2]),set([1,2,3,4]))
    0.5

    Passonneau 2005, Measuring Agreement on Set-Valued Items (MASI) for Semantic and Pragmatic Annotation.
    """

    return 1 - float(len(label1.intersection(label2)))/float(max(len(label1),len(label2)))


def interval_distance(label1,label2):
    """Krippendorff'1 interval distance metric

    >>> interval_distance(1,10)
    81

    Krippendorff 1980, Content Analysis: An Introduction to its Methodology
    """
    try:
        return pow(label1-label2,2)
#        return pow(list(label1)[0]-list(label2)[0],2)
    except:
        print "non-numeric labels not supported with interval distance"


def presence(label):
    """Higher-order function to test presence of a given label

    """
    return lambda x,y: 1.0*((label in x) == (label in y))


def fractional_presence(label):
    return lambda x,y:abs((float(1.0/len(x)) - float(1.0/len(y))))*(label in x and label in y) or 0.0*(label not in x and label not in y) or abs((float(1.0/len(x))))*(label in x and label not in y) or ((float(1.0/len(y))))*(label not in x and label in y)


def custom_distance(file):
    data = {}
    for l in open(file):
        labelA, labelB, dist = l.strip().split("\t")
        labelA = frozenset([labelA])
        labelB = frozenset([labelB])
        data[frozenset([labelA,labelB])] = float(dist)
    return lambda x,y:data[frozenset([x,y])]


def demo():
    s1 = "rain"
    s2 = "shine"
    print "Edit distance between '%s' and '%s':" % (s1,s2), edit_distance(s1, s2)
    
    s1 = set([1,2,3,4])
    s2 = set([3,4,5])
    print "s1:", s1
    print "s2:", s2
    print "Binary distance:", binary_distance(s1, s2)
    print "Jaccard distance:", jaccard_distance(s1, s2)
    print "MASI distance:", masi_distance(s1, s2)

if __name__ == '__main__':
    demo()
