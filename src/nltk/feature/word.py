"""
Feature extractors for tokens that encode single words.
"""

from nltk.feature import *

class TextFeatureExtractor(FeatureStringFeatureExtractor):
    def __init__(self, words, count=False, **property_names):
        StringFeatureExtractor.__init__(self, words, count,
                                        **property_names)

    def extract_feature_strings(self, token):
        TEXT = self.property_name('TEXT')
        return token[TEXT]
    
    def feature_description(self, fid):
        return 'Word is %r' % self.fid2string(fid)

class StemFeatureExtractor(FeatureStringFeatureExtractor):
    def __init__(self, stems, count=False, **property_names):
        StringFeatureExtractor.__init__(self, stems, count,
                                        **property_names)

    def extract_feature_strings(self, token):
        STEM = self.property_name('STEM')
        return token[STEM]
    
    def feature_description(self, fid):
        return 'Stem is %r' % self.fid2string(fid)

