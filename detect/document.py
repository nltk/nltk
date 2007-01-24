# Natural Language Toolkit: Feature Extraction for Documents
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au> (porting)
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id: document.py 2975 2006-04-03 07:00:11Z stevenbird $

"""
Feature extractors for documents.
"""

from nltk_lite.detect import *

class BagOfContainedWordsFeatureDetector(FeatureDetectorI):
    """
    A feature detector that extracts the C{TEXT} of each token in a
    document, and stores them (preserving duplicates) in the C{BOW}
    feature.
    """
    def __init__(self):
        pass
        
    def get_features(self, tokens):
        return {'bow': tokens}
    
    def features(self):
        return ['bow']

class SetOfContainedWordsFeatureDetector(FeatureDetectorI):
    """
    A feature detector that extracts the C{TEXT} of each subtoken in a
    document, and stores them (discarding duplicates) in the C{SOW}
    feature.
    """
    def __init__(self):
        pass
        
    def get_features(self, tokens):
        return {'sow': set(tokens)}
    
    def features(self):
        return ['sow']

