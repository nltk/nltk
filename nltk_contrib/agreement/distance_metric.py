# Natural Language Toolkit: Agreement Metrics
#
# Copyright (C) 2001-2008 University of Pennsylvania
# Author: Tom Lippincott <tom@cs.columbia.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#

# function prototype?


def binary(set1,set2):
    """Simple equality test.

    0.0 if the labels are identical, 1.0 if they are different.
    """

    if(set1==set2):
        return 0.0
    else:
        return 1.0


def masi(set1,set2):
    """Distance metric that takes into account partial agreement when multiple
    labels are assigned.

    Passonneau 2005, Measuring Agreement on Set-Valued Items (MASI) for Semantic and Pragmatic Annotation.
    """

    return 1 - float(len(set1.intersection(set2)))/float(max(len(set1),len(set2)))


def interval(set1,set2):
    """

    Krippendorff 1980, Content Analysis: An Introduction to its Methodology
    """
    try:
        return pow(int(list(set1)[0])-int(list(set2)[0]),2)
    except:
        print "non-numeric labels not supported with interval distance"
