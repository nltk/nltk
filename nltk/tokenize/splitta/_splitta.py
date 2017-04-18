# Natural Language Toolkit: Splitta sentence tokenizer
#
# Copyright (C) 2001-2015 NLTK Project
# Algorithm: Gillick (2009)
# Author: Dan Gillick <dgillick@gmail.com> (original Python implementation)
#         Sam Raker <sam.raker@gmail.com> (NLTK-compatible version)
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT
"""
Low-level interface for Splitta tokenization
"""
from nltk.tokenize.api import TokenizerI

from splitta.feature_extractor import FeatureExtractor
from splitta import pair_iter


# pylint: disable=abstract-method
class SplittaTokenizer(TokenizerI):
    """
    A class combining a tokenizer,
    :py:class:`feature_extractor.FeatureExtractor`,
    and trained classifier to split sentences according to the Splitta
    algorithm
    """
    def __init__(self, tokenizer, feature_extractor, classifier):
        """
        :param tokenizer: the object to tokenize text with
        :type tokenizer: any class that inherits from
                         :py:class:`nltk.tokenize.api.TokenizerI` or
                         implements a `tokenize` method
        :param feature_extractor: the object used to extract Splitta features
                                  for the classifier
        :type feature_extractor: :py:class:`feature_extractor.FeatureExtractor`
        :param classifier: a trained classifier to label potential sentence
                           boundaries
        :type classifier: any class that inherits from
                          :py:class:`nltk.classify.api.ClassifierI` or
                          implements a `classify` method
        """
        self.tokenizer = tokenizer
        self.feature_extractor = feature_extractor
        self.raw_pair_iter = pair_iter.RawPairIter(tokenizer)
        self.features_pair_iter = pair_iter.TokenizingPairIter(tokenizer)
        self.classifier = classifier
        # word-level tokenization delegated to self.tokenizer
        self.tokenize = self.tokenizer.tokenize
        self.span_tokenize = self.tokenizer.span_tokenize

    def tokenize_sents(self, text):
        """
        Split a given text into sentences according to the Splitta
        algorithm. This requires extracting features for each candidate
        boundary, which are then fed to the trained classifier.

        :param str text: the text to split into sentences
        """
        sents = []
        raw_pairs = self.raw_pair_iter.pair_iter(text)
        token_pairs = self.features_pair_iter.pair_iter(text)
        features = self.feature_extractor.get_features(token_pairs)
        sent = []
        while True:
            try:
                pair = raw_pairs.next()
                feats = features.next()
            except StopIteration:
                break
            else:
                label = self.classifier.classify(feats[0])
                if label == 'boundary':
                    sent.append(pair[0])
                    sents.append(' '.join((str(token) for token in sent
                                           if token is not None)))
                    sent = [pair[1]]
                elif label in ('non_boundary', 'non_candidate'):
                    sent.extend(pair.tokens)
        return sents

# pylint: disable=too-few-public-methods,anomalous-backslash-in-string
class SplittaTrainer(object):
    """
    A class to combine a tokenizer and a
    :py:class:`feature_extractor.FeatureExtractor` to train a classifier
    according to the Splitta algorithm
    """
    def __init__(self, tokenizer, classifier, feature_extractor=None):
        """
        :param tokenizer: the object used to tokenize the text
        :type tokenizer: any class inheriting from
                         :py:class:`nltk.tokenizer.api.TokenizerI` or
                         implementing a `tokenize` method
        :param classifier: a classifier to train
        :type classifier: any class that inherits from
                          :py:class:`nltk.classify.api.ClassifierI` and/or
                          implements `train` and `classify` methods
                          :NB: `classifier` must be a *class*, not an
                               instance
        :param feature_extractor: a :py:class:`FeatureExtractor` object to use
                                  to extract features from training texts. If
                                  not provided, a new
                                  :py:class:`FeatureExtractor` will be created
        """
        self.tokenizer = tokenizer
        self.feature_extractor = feature_extractor or FeatureExtractor(None, None)
        self.features_pair_iter = pair_iter.TrainingPairIter(tokenizer)
        self.classifier = classifier

    def train(self, training_text, **classifier_kwargs):
        """
        Train the classifier. The supplied text is tokenized by the instance's
        tokenizer. Features and labels extracted from the tokens are fed to
        the classifier's .train method. Additional keyword arguments can be
        passed through this method to the classifier's .train method as well.

        :param str training_text: the text to train from
        :param \**classifier_kwargs: passed through to
                                     :py:method:`.classifier.train`
        """
        if not self.feature_extractor.has_counts:
            self.feature_extractor.train(
                self.tokenizer.tokenize(training_text))
        features = list(self.feature_extractor.get_features(
            self.features_pair_iter.pair_iter(training_text)))
        self.classifier.train(features, **classifier_kwargs)

