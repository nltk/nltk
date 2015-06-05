# Natural Language Toolkit: Splitta sentence tokenizer
#
# Copyright (C) 2001-2015 NLTK Project
# Algorithm: Gillick (2009)
# Author: Dan Gillick <dgillick@gmail.com> (original Python implementation)
#         Sam Raker <sam.raker@gmail.com> (NLTK-compatible version)
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT
"""
Extract Splitta features from TokenPairs to use in training classifiers
"""
import collections
import cPickle
import math
import os


class FeatureExtractor(object):
    """
    A class to extract features from TokenPairs in a format that can be passed
    to ```nltk.classifier.api.ClassifierI.train```. The features are:
        1) the first token
        2) the second token
        3) both words
        4) the length of the first word
        5) whether the second word is titlecased
        6) the log count of occurrences of the first word occurring without
            a final period
        7) the log count of lower-cased occurrences of the second word
        8) the first word and whether the second word is titlecased

    Features 6 and 7 are determined based on counts extracted from
    a text, which should ideally be the same text the classifier is
    trained on. These counts can independently be serialized to and
    retrieved from pickle files, or can be extracted from a training text.
    """

    def __init__(self, model_non_abbrs, model_lower_words):
        self.model_non_abbrs = model_non_abbrs
        self.model_lower_words = model_lower_words

    @property
    def has_counts(self):
        """
        Whether the FeatureExtractor's model counts have been
        set.
        """
        return all([count for count in (self.model_non_abbrs,
                                        self.model_lower_words)
                    if count is not None])

    def train(self, tokenized_text):
        """
        'Train' the FeatureExtractor by setting its model counts.
        :param tokenized_text: the tokenized version of the text to train
                               from
        :type tokenized_text: list of strings
        """
        non_abbrs = collections.Counter()
        lower_words = collections.Counter()
        for token in tokenized_text:
            if not token.endswith('.'):
                non_abbrs[token] += 1
            if token.islower():
                lower_words[token.replace('.', '')] += 1
        self.model_non_abbrs = non_abbrs
        self.model_lower_words = lower_words

    def save_model(self, dest_dir=None):
        """
        Save the FeatureExtractor's model counts to either the current
        directory or a destination directory
        """
        dest_dir = dest_dir or ''
        with open(os.path.join(dest_dir, 'non_abbrs'), 'wb') as out_file:
            cPickle.dump(self.model_non_abbrs, out_file)
        with open(os.path.join(dest_dir, 'lower_words'), 'wb') as out_file:
            cPickle.dump(self.model_lower_words, out_file)

    def load_model(self, non_abbrs_file, lower_words_file):
        """
        Load model counts
        """
        with open(non_abbrs_file, 'rb') as in_file:
            self.model_non_abbrs = cPickle.load(in_file)
        with open(lower_words_file, 'rb') as in_file:
            self.model_lower_words = cPickle.load(in_file)

    @staticmethod
    def save_features(features, dest):
        """
        Serialize features
        """
        with open(dest, 'wb') as out_file:
            cPickle.dump(features, out_file)

    def get_features(self, pair_iter):
        """
        Extract features from TokenPair objects and yield (features, label)
        tuples.
        """
        if not self.has_counts:
            raise AttributeError("Can't get features without counts")
        for token_pair in pair_iter:
            if token_pair.label != 'non_candidate':
                feats = self.features_from_token_pair(token_pair)
                yield (feats, token_pair.label)

    def features_from_token_pair(self, token_pair):
        """
        Extract features from a TokenPair
        """
        word1 = token_pair.tokens[0]
        word2 = token_pair.tokens[1]
        features = {'word1': word1,
                    'word2': word2,
                    'word1_word2': token_pair.tokens,
                    'word1_len': len(word1),
                    'word2_istitle': word2.istitle(),
                    'word1_abbr': self.get_log_count(self.model_non_abbrs,
                                                     word1.rstrip('.')),
                    'word2_lower': self.get_log_count(self.model_lower_words,
                                                      word2),
                    'word1_word2_istitle': (word1, word2.istitle())
                   }
        return features

    @staticmethod
    def get_log_count(model_count, key):
        """
        Get the normalized log of a count from one of our model counts
        """
        count = model_count.get(key)
        if count is None:
            return math.log(1)
        else:
            return math.log(1 + count)

