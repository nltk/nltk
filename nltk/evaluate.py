# Natural Language Toolkit: Evaluation
#
# Copyright (C) 2001-2008 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT


"""
Utility functions for evaluating processing modules.
"""

import math

def accuracy(reference, test):
    """
    Given a list of reference values and a corresponding list of test
    values, return the percentage of corresponding values that are
    equal.  In particular, return the percentage of indices
    C{0<i<=len(test)} such that C{test[i] == reference[i]}.

    @type reference: C{list}
    @param reference: An ordered list of reference values.
    @type test: C{list}
    @param test: A list of values to compare against the corresponding
        reference values.
    @raise ValueError: If C{reference} and C{length} do not have the
        same length.
    """
    if len(reference) != len(test):
        raise ValueError("Lists must have the same length.")
    num_correct = [1 for x,y in zip(reference, test) if x==y]
    return float(len(num_correct)) / len(reference)

def precision(reference, test):
    """
    Given a set of reference values and a set of test values, return
    the percentage of test values that appear in the reference set.
    In particular, return |C{reference}S{cap}C{test}|/|C{test}|.
    If C{test} is empty, then return C{None}.
    
    @type reference: C{Set}
    @param reference: A set of reference values.
    @type test: C{Set}
    @param test: A set of values to compare against the reference set.
    @rtype: C{float} or C{None}
    """
    if len(test) == 0:
        return None
    else:
        return float(len(reference.intersection(test)))/len(test)

def recall(reference, test):
    """
    Given a set of reference values and a set of test values, return
    the percentage of reference values that appear in the test set.
    In particular, return |C{reference}S{cap}C{test}|/|C{reference}|.
    If C{reference} is empty, then return C{None}.
    
    @type reference: C{Set}
    @param reference: A set of reference values.
    @type test: C{Set}
    @param test: A set of values to compare against the reference set.
    @rtype: C{float} or C{None}
    """
    if len(reference) == 0:
        return None
    else:
        return float(len(reference.intersection(test)))/len(reference)

def f_measure(reference, test, alpha=0.5):
    """
    Given a set of reference values and a set of test values, return
    the f-measure of the test values, when compared against the
    reference values.  The f-measure is the harmonic mean of the
    L{precision} and L{recall}, weighted by C{alpha}.  In particular,
    given the precision M{p} and recall M{r} defined by:
        - M{p} = |C{reference}S{cap}C{test}|/|C{test}|
        - M{r} = |C{reference}S{cap}C{test}|/|C{reference}|
    The f-measure is:
        - 1/(C{alpha}/M{p} + (1-C{alpha})/M{r})
        
    If either C{reference} or C{test} is empty, then C{f_measure}
    returns C{None}.
    
    @type reference: C{Set}
    @param reference: A set of reference values.
    @type test: C{Set}
    @param test: A set of values to compare against the reference set.
    @rtype: C{float} or C{None}
    """
    p = precision(reference, test)
    r = recall(reference, test)
    if p is None or r is None:
        return None
    if p == 0 or r == 0:
        return 0
    return 1.0/(alpha/p + (1-alpha)/r)

def log_likelihood(reference, test):
    """
    Given a list of reference values and a corresponding list of test
    probability distributions, return the average log likelihood of
    the reference values, given the probability distributions.

    @param reference: A list of reference values
    @type reference: C{list}
    @param test: A list of probability distributions over values to
        compare against the corresponding reference values.
    @type test: C{list} of L{ProbDist}
    """
    if len(reference) != len(test):
        raise ValueError("Lists must have the same length.")

    # Return the average value of dist.logprob(val).
    total_likelihood = sum(dist.logprob(val)
                            for (val, dist) in zip(reference, test))
    return total_likelihood/len(reference)

class ConfusionMatrix(object):
    """
    The confusion matrix between a list of reference values and a
    corresponding list of test values.  Entry [M{r},M{t}] of this
    matrix is a count of the number of times that the reference value
    M{r} corresponds to the test value M{t}.  E.g.:

        >>> ref  = 'DET NN VB DET JJ NN NN IN DET NN'.split()
        >>> test = 'DET VB VB DET NN NN NN IN DET NN'.split()
        >>> cm = ConfusionMatrix(ref, test)
        >>> print cm['NN', 'NN']
        3

    Note that the diagonal entries (M{Ri}=M{Tj}) of this matrix
    corresponds to correct values; and the off-diagonal entries
    correspond to incorrect values.
    """
    def __init__(self, reference, test):
        """
        Construct a new confusion matrix from a list of reference
        values and a corresponding list of test values.
        
        @type reference: C{list}
        @param reference: An ordered list of reference values.
        @type test: C{list}
        @param test: A list of values to compare against the
            corresponding reference values.
        @raise ValueError: If C{reference} and C{length} do not have
            the same length.
        """
        if len(reference) != len(test):
            raise ValueError('Lists must have the same length.')
            
        # Get a list of all values.
        values = sorted(set(reference+test))

        # Construct a value->index dictionary
        indices = dict((val,i) for (i,val) in enumerate(values))

        # Make a confusion matrix table.
        confusion = [[0 for val in values] for val in values]
        max_conf = 0 # Maximum confusion
        for w,g in zip(reference, test):
            confusion[indices[w]][indices[g]] += 1
            max_conf = max(max_conf, confusion[indices[w]][indices[g]])

        #: A list of all values in C{reference} or C{test}.
        self._values = values
        #: A dictionary mapping values in L{self._values} to their indices.
        self._indices = indices
        #: The confusion matrix itself (as a list of lists of counts).
        self._confusion = confusion
        #: The greatest count in L{self._confusion} (used for printing).
        self._max_conf = 0
        #: The total number of values in the confusion matrix.
        self._total = len(reference)
        #: The number of correct (on-diagonal) values in the matrix.
        self._correct = sum(confusion[i][i] for i in range(len(values)))

    def __getitem__(self, (li,lj)):
        """
        @return: The number of times that value C{li} was expected and
        value C{lj} was given.
        @rtype: C{int}
        """
        i = self._indices[li]
        j = self._indices[lj]
        return self._confusion[i][j]

    def __repr__(self):
        return '<ConfusionMatrix: %s/%s correct>' % (self._correct,
                                                     self._total)

    def __str__(self):
        return self.pp()
    
    def pp(self, show_percents=False, values_in_chart=True):
        """
        @return: A multi-line string representation of this confusion
        matrix.
        @todo: add marginals?
        """
        confusion = self._confusion

        if values_in_chart:
            values = self._values
        else:
            values = range(len(self._values))

        # Construct a format string for row values
        valuelen = max(len(str(val)) for val in values)
        value_format = '%' + `valuelen` + 's |'
        # Construct a format string for matrix entries
        if show_percents:
            entrylen = 6
            entry_format = '%5.1f%%'
        else:
            entrylen = len(`self._max_conf`)
            entry_format = '%' + `entrylen` + 'd'

        # Write the column values.
        value_strings = [str(val) for val in values]
        s = ''
        for i in range(valuelen):
            s += (' '*valuelen)+' |'
            for val in value_strings:
                if i >= valuelen-len(val):
                    s += val[i-valuelen+len(val)].rjust(entrylen+1)
                else:
                    s += ' '*(entrylen+1)
            s += ' |\n'

        # Write a dividing line
        s += '%s-+-%s+\n' % ('-'*valuelen, '-'*((entrylen+1)*len(values)))

        # Write the entries.
        for i in range(len(values)):
            s += value_format % values[i]
            for j in range(len(values)):
                s += ' '
                if show_percents:
                    s += entry_format % (100.0*confusion[i][j]/self._total)
                else:
                    s += entry_format % confusion[i][j]
            s += ' |\n'
            
        # Write a dividing line
        s += '%s-+-%s+\n' % ('-'*valuelen, '-'*((entrylen+1)*len(values)))

        # Write a key
        s += '(row = reference; col = test)\n'
        if not values_in_chart:
            s += 'Value key:\n'
            for i, value in enumerate(self._values):
                s += '%6d: %s\n' % (i, value)

        return s
        
    def key(self):
        values = self._values
        str = 'Value key:\n'
        indexlen = len(`len(values)-1`)
        key_format = '  %'+`indexlen`+'d: %s\n'
        for i in range(len(values)):
            str += key_format % (i, values[i])

        return str

##########################################################################
# Windowdiff
# Pevzner, L., and Hearst, M., A Critique and Improvement of an Evaluation Metric for Text Segmentation,
# Computational Linguistics,, 28 (1), March 2002, pp. 19-36
##########################################################################

def windowdiff(seg1, seg2, k, boundary="1"):
    """
    Compute the windowdiff score for a pair of segmentations.  A segmentation is any sequence
    over a vocabulary of two items (e.g. "0", "1"), where the specified boundary value is used
    to mark the edge of a segmentation.

    @param seg1: a segmentation
    @type seg1: C{string} or C{list}
    @param seg2: a segmentation
    @type seg2: C{string} or C{list}
    @param k: window width
    @type k: C{int}
    @param boundary: boundary value
    @type boundary: C{string} or C{int} or C{bool}
    @rtype: C{int}
    """

    if len(seg1) != len(seg2):
        raise ValueError, "Segmentations have unequal length"
    wd = 0
    for i in range(len(seg1) - k):
        wd += abs(seg1[i:i+k+1].count(boundary) - seg2[i:i+k+1].count(boundary))
    return wd

# Edit Distance (Levenshtein)

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


def demo():
    print '-'*75
    reference = 'DET NN VB DET JJ NN NN IN DET NN'.split()
    test    = 'DET VB VB DET NN NN NN IN DET NN'.split()
    print 'Reference =', reference
    print 'Test    =', test
    print 'Confusion matrix:'
    print ConfusionMatrix(reference, test)
    print 'Accuracy:', accuracy(reference, test)

    print '-'*75
    reference_set = set(reference)
    test_set = set(test)
    print 'Reference =', reference_set
    print 'Test =   ', test_set
    print 'Precision:', precision(reference_set, test_set)
    print '   Recall:', recall(reference_set, test_set)
    print 'F-Measure:', f_measure(reference_set, test_set)
    print '-'*75

if __name__ == '__main__':
    demo()

__all__ = ['ConfusionMatrix', 'accuracy', 'demo',
           'f_measure', 'log_likelihood', 'precision', 'recall',
           'edit_dist', 'windowdiff']
