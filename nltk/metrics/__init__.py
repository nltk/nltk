# Natural Language Toolkit: Metrics
#
# Copyright (C) 2001-2008 NLTK Project
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
from editdistance import *
from windowdiff import *

__all__ = ['ConfusionMatrix', 'accuracy',
           'f_measure', 'log_likelihood', 'precision', 'recall',
           'approxrand', 'edit_dist', 'windowdiff']
