# Natural Language Toolkit: Evaluation
#
# Copyright (C) 2004 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT


"""
Utility functions for evaluating processing modules.
"""

def accuracy(list1, list2):
    """
    What fraction of the items in list2 are found in list1.
    This function counts the number of instances where
    list1[i] == list2[i] and returns this as a fraction of
    the size of list1.

    @type list1: C{list}
    @param list1: A list.
    @type list2: C{list}
    @param list2: A list.
    @rtype: C{float}
    """

    if len(list1) != len(list2):
        raise ValueError("Lists must have the same length.")
    num_correct = [1 for x,y in zip(list1,list2) if x==y]
    return float(len(num_correct)) / len(list1)

