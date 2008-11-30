# Natural Language Toolkit: Agreement Metrics
#
# Copyright (C) 2001-2008 NLTK Project
# Author: Tom Lippincott <tom@cs.columbia.edu>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT
#

"""
Implementations of inter-annotator agreement coefficients surveyed by Artstein
and Poesio (2007), Inter-Coder Agreement for Computational Linguistics.

An agreement coefficient calculates the amount that annotators agreed on label 
assignments beyond what is expected by chance.

In defining the AnnotationTask class, we use naming conventions similar to the 
paper's terminology.  There are three types of objects in an annotation task: 

    the coders (variables "c" and "C")
    the items to be annotated (variables "i" and "I")
    the potential categories to be assigned (variables "k" and "K")

Additionally, it is often the case that we don't want to treat two different 
labels as complete disagreement, and so the AnnotationTask constructor can also
take a distance metric as a final argument.  Distance metrics are simply 
functions that take two arguments, and return a value between 0.0 and 1.0 
indicating the distance between them.  If not supplied, the default is binary 
comparison between the arguments.

The simplest way to initialize an AnnotationTask is with a list of equal-length 
lists, each containing a coder's assignments for all objects in the task:

    task = AnnotationTask([],[],[])

Alpha (Krippendorff 1980)
Kappa (Cohen 1960)
S (Bennet, Albert and Goldstein 1954)
Pi (Scott 1955)


TODO: Describe handling of multiple coders and missing data
"""

from api import *
from util import *
from distance_metric import *
from agreement_coefficient import *

__all__ = [
    ]

if(__name__=='__main__'):
    pass
