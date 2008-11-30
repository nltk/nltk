# Natural Language Toolkit: Agreement Metrics
#
# Copyright (C) 2001-2008 NLTK Project
# Author: Tom Lippincott <tom@cs.columbia.edu>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT
#

# function prototype?


def binary(label1,label2):
    """Simple equality test.

    0.0 if the labels are identical, 1.0 if they are different.

    >>> binary(1,1)
    0.0

    >>> binary(1,3)
    1.0
    """

    if(label1==label2):
        return 0.0
    else:
        return 1.0


def jaccard(label1,label2):
    """Distance metric comparing set-similarity.

    """
    return (len(label1.union(label2)) - len(label1.intersection(label2)))/float(len(label1.union(label2)))


def masi(label1,label2):
    """Distance metric that takes into account partial agreement when multiple
    labels are assigned.

    >>> masi(set([1,2]),set([1,2,3,4]))
    0.5

    Passonneau 2005, Measuring Agreement on Set-Valued Items (MASI) for Semantic and Pragmatic Annotation.
    """

    return 1 - float(len(label1.intersection(label2)))/float(max(len(label1),len(label2)))


def interval(label1,label2):
    """Krippendorff'1 interval distance metric

    >>> interval(1,10)
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
    print "test"
    return lambda x,y: 1.0*((label in x) == (label in y))


def fractional_presence(label):
    return lambda x,y:abs((float(1.0/len(x)) - float(1.0/len(y))))*(label in x and label in y) or 0.0*(label not in x and label not in y) or abs((float(1.0/len(x))))*(label in x and label not in y) or ((float(1.0/len(y))))*(label not in x and label in y)


def custom(file):
    data = {}
    for l in open(file):
        labelA,labelB,dist = l.strip().split("\t")
        labelA = frozenset([labelA])
        labelB = frozenset([labelB])
        data[frozenset([labelA,labelB])] = float(dist)
    return lambda x,y:data[frozenset([x,y])]


if __name__ == "__main__":
    import doctest
    doctest.testmod()
