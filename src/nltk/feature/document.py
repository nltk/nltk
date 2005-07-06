# Natural Language Toolkit: Feature Extraction for Documents
#
# Copyright (C) 2004 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
Feature extractors for tokens that encode documents.
"""

from nltk.feature import *

class BagOfContainedWordsFeatureDetector(AbstractFeatureDetector):
    """
    A feature detector that extracts the C{TEXT} of each subtoken in a
    document, and stores them (preserving duplicates) in the C{BOW}
    feature.
    """
    def __init__(self, **property_names):
        AbstractFeatureDetector.__init__(self, **property_names)
        
    def get_features(self, token):
        return {'BOW': [tok['TEXT'] for tok in token['SUBTOKENS']]}
    
    def features(self):
        return ['BOW']

class SetOfContainedWordsFeatureDetector(AbstractFeatureDetector):
    """
    A feature detector that extracts the C{TEXT} of each subtoken in a
    document, and stores them (discarding duplicates) in the C{SOW}
    feature.
    """
    def __init__(self, **property_names):
        AbstractFeatureDetector.__init__(self, **property_names)
        
    def get_features(self, token):
        return {'SOW': Set([tok['TEXT'] for tok in token['SUBTOKENS']])}
    
    def features(self):
        return ['SOW']

