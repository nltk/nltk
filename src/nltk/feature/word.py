"""
Feature extractors for tokens that encode single words.
"""

from nltk.feature import *

class TextFeatureExtractor(FeatureStringFeatureExtractor):
    """
    A binary feature for each word text.
    """
    def extract_feature_strings(self, token):
        TEXT = self.property_name('TEXT')
        return token[TEXT]
    
    def feature_description(self, fid):
        return 'Word is %r' % self.fid2string(fid)

class StemFeatureExtractor(FeatureStringFeatureExtractor):
    """
    A binary feature for each stem.
    """
    def extract_feature_strings(self, token):
        STEM = self.property_name('STEM')
        return token[STEM]
    
    def feature_description(self, fid):
        return 'Stem is %r' % self.fid2string(fid)

