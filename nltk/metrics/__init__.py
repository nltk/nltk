# Natural Language Toolkit: Metrics
#
# Copyright (C) 2001-2011 NLTK Project
# Author: Steven Bird <sb@csse.unimelb.edu.au>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT
#

"""
Classes and methods for scoring processing modules.
"""

from scores import *
from confusionmatrix import *
from distance import *
from windowdiff import *
from agreement import *
from association import *
from spearman import *

__all__ = ['ConfusionMatrix', 'accuracy',
           'f_measure', 'log_likelihood', 'precision', 'recall',
           'approxrand', 'edit_distance', 'windowdiff',
           'AnnotationTask', 'spearman_correlation',
           'ranks_from_sequence', 'ranks_from_scores',
           'NgramAssocMeasures', 'BigramAssocMeasures',
           'TrigramAssocMeasures', 'ContingencyMeasures',
           'binary_distance', 'jaccard_distance',
           'masi_distance', 'interval_distance',
           'custom_distance',
           'presence', 'fractional_presence']
