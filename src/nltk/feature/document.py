"""
Feature extractors for tokens that encode documents.
"""

from nltk.feature import *

class BagOfWordsFeatureExtractor(FeatureStringFeatureExtractor):
    def __init__(self, words, count=False, **property_names):
        StringFeatureExtractor.__init__(self, words, count,
                                        **property_names)

    def extract_feature_strings(self, token):
        SUBTOKENS = self.property_name('SUBTOKENS')
        TEXT = self.property_name('TEXT')
        return [subtok[TEXT] for subtok in token[SUBTOKENS]]

    def feature_description(self, fid):
        return 'Contains word %r' % self.fid2string(fid)
