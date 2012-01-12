# Natural Language Toolkit: Windowdiff
#
# Copyright (C) 2001-2012 NLTK Project
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

##########################################################################
# Windowdiff
# Pevzner, L., and Hearst, M., A Critique and Improvement of
#   an Evaluation Metric for Text Segmentation,
# Computational Linguistics,, 28 (1), March 2002, pp. 19-36
##########################################################################

def windowdiff(seg1, seg2, k, boundary="1"):
    """
    Compute the windowdiff score for a pair of segmentations.  A segmentation is any sequence
    over a vocabulary of two items (e.g. "0", "1"), where the specified boundary value is used
    to mark the edge of a segmentation.

    >>> from nltk.metrics.windowdiff import windowdiff
    >>> s1 = "00000010000000001000000"
    >>> s2 = "00000001000000010000000"
    >>> s3 = "00010000000000000001000"
    >>> windowdiff(s1, s1, 3)
    0
    >>> windowdiff(s1, s2, 3)
    4
    >>> windowdiff(s2, s3, 3)
    16

    :param seg1: a segmentation
    :type seg1: str or list
    :param seg2: a segmentation
    :type seg2: str or list
    :param k: window width
    :type k: int
    :param boundary: boundary value
    :type boundary: str or int or bool
    :rtype: int
    """

    if len(seg1) != len(seg2):
        raise ValueError, "Segmentations have unequal length"
    wd = 0
    for i in range(len(seg1) - k):
        wd += abs(seg1[i:i+k+1].count(boundary) - seg2[i:i+k+1].count(boundary))
    return wd

def demo():
    s1 = "00000010000000001000000"
    s2 = "00000001000000010000000"
    s3 = "00010000000000000001000"
    print "s1:", s1
    print "s2:", s2
    print "s3:", s3

    print "windowdiff(s1, s1, 3) = ", windowdiff(s1, s1, 3)
    print "windowdiff(s1, s2, 3) = ", windowdiff(s1, s2, 3)
    print "windowdiff(s2, s3, 3) = ", windowdiff(s2, s3, 3)
