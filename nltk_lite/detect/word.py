# Natural Language Toolkit: Feature Extraction for Words
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au> (porting)
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id: word.py 2975 2006-04-03 07:00:11Z stevenbird $

"""
Feature extractors for tokens that encode single words.
"""

from nltk_lite.detect import *

class TextFeatureDetector(PropertyFeatureDetector):
    def __init__(self):
        PropertyFeatureDetector.__init__(self, {'text': lambda t:t})

class StemFeatureDetector(PropertyFeatureDetector):
    def __init__(self, stemmer):
        PropertyFeatureDetector.__init__(self, {'stem': stemmer})

