# Natural Language Toolkit: Metrics
#
# Copyright (C) 2001-2021 NLTK Project
# Author: Steven Bird <stevenbird1@gmail.com>
#         Edward Loper <edloper@gmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT
#

"""
NLTK Metrics

Classes and methods for scoring processing modules.
"""

from nltk.metrics.scores import (
    accuracy,
    precision,
    recall,
    f_measure,
    log_likelihood,
    approxrand,
)
from nltk.metrics.confusionmatrix import ConfusionMatrix
from nltk.metrics.distance import (
    edit_distance,
    edit_distance_align,
    binary_distance,
    jaccard_distance,
    masi_distance,
    interval_distance,
    custom_distance,
    presence,
    fractional_presence,
)
from nltk.metrics.paice import Paice
from nltk.metrics.segmentation import windowdiff, ghd, pk
from nltk.metrics.agreement import AnnotationTask
from nltk.metrics.association import (
    NgramAssocMeasures,
    BigramAssocMeasures,
    TrigramAssocMeasures,
    QuadgramAssocMeasures,
    ContingencyMeasures,
)
from nltk.metrics.spearman import (
    spearman_correlation,
    ranks_from_sequence,
    ranks_from_scores,
)
from nltk.metrics.aline import align
