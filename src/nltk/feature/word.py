# Natural Language Toolkit: Feature Extraction for Words
#
# Copyright (C) 2004 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
Feature extractors for tokens that encode single words.
"""

from nltk.feature import *

class TextFeatureDetector(PropertyFeatureDetector):
    """
    A feature detector that extracts a token's text from the
    C{TEXT} property, and stores it in the C{TEXT} feature.
    """
    def __init__(self, **property_names):
        PropertyFeatureDetector.__init__(self, 'TEXT', **property_names)

class StemFeatureDetector(PropertyFeatureDetector):
    """
    A feature detector that extracts a token's stem from the
    C{STEM} property, and stores it in the C{STEM} feature.
    """
    def __init__(self, **property_names):
        PropertyFeatureDetector.__init__(self, 'TEXT', **property_names)

class BagOfWordsFeatureDetector(AbstractFeatureDetector):
    """
    A feature detector that extracts the text of the words in a
    token's context, preserving duplicates, and stores it in the
    C{BOW} feature.  In particular, C{BOW} is mapped to a list
    containing the C{TEXT} feature of each word in a fixed-size window
    centered on the token.
    """
    
    def __init__(self, window=5, **property_names):
        """
        @param window: The number of words in the context to add to
            the bag of words.
        """
        AbstractFeatureDetector.__init__(self, **property_names)
        self._window = window
        
    def raw_detect_features(self, token):
        bow = [tok['TEXT'] for tok in
               token['CONTEXT'].getrange(-self._window, 0)+
               token['CONTEXT'].getrange(1, 1+self._window)]
        return {'BOW': bow}
    
    def features(self):
        return ['BOW']

class SetOfWordsFeatureDetector(AbstractFeatureDetector):
    """
    A feature detector that extracts the text of the words in a
    token's context, discarding duplicates, and stores it in the
    C{SOW} feature.  In particular, C{SOW} is mapped to a set
    containing the C{TEXT} feature of each word in a fixed-size window
    centered on the token.
    """
    def __init__(self, window=5, **property_names):
        """
        @param window: The number of words in the context to add to
            the bag of words.
        """
        AbstractFeatureDetector.__init__(self, **property_names)
        self._window = window
        
    def raw_detect_features(self, token):
        sow = Set([tok['TEXT'] for tok in
                   token['CONTEXT'].getrange(-self._window, 0)+
                   token['CONTEXT'].getrange(1, 1+self._window)])
        return {'SOW': sow}
    
    def features(self):
        return ['SOW']
