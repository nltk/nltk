# Natural Language Toolkit: Translation metrics
#
# Copyright (C) 2001-2015 NLTK Project
# Author: Will Zhang <wilzzha@gmail.com>
#         Guan Gui <ggui@student.unimelb.edu.au>
#         Steven Bird <stevenbird1@gmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

def alignment_error_rate(reference, hypothesis, possible=None):
    """
    Return the Alignment Error Rate (AER) of an alignment
    with respect to a "gold standard" reference alignment.
    Return an error rate between 0.0 (perfect alignment) and 1.0 (no
    alignment).

        >>> from nltk.translate import Alignment
        >>> s = Alignment([(0, 0), (1, 1)])
        >>> s = Alignment([(0, 0), (1, 1)])
        >>> a.alignment_error_rate(s)
        0.0

    :type reference: Alignment
    :param reference: A gold standard alignment (sure alignments)
    :type hypothesis: Alignment
    :param hypothesis: A hypothesis alignment (aka. candidate alignments)
    :type possible: Alignment or None
    :param possible: A gold standard reference of possible alignments
        (defaults to *reference* if None)
    :rtype: float or None
    """

    if possible is None:
        possible = reference
    else:
        assert(reference.issubset(possible)) # sanity check

    return (1.0 - float(len(hypothesis & reference) + len(hypothesis & possible)) /
            float(len(hypothesis) + len(reference)))
