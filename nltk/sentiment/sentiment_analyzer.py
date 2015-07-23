# coding: utf-8
#
# Natural Language Toolkit: Sentiment Analyzer
#
# Copyright (C) 2001-2015 NLTK Project
# Author: Pierpaolo Pantone <24alsecondo@gmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

from __future__ import print_function
from collections import defaultdict

from nltk.classify.util import apply_features, accuracy
from nltk.collocations import BigramCollocationFinder
from nltk.metrics import BigramAssocMeasures
from nltk.probability import FreqDist
from util import (save_file, timer)
import nltk


class SentimentAnalyzer(object):
    """
    A Sentiment Analysis tool based on different modular approaches.
    """
    def __init__(self, classifier=None):
        self.feat_extractors = defaultdict(list)
        self.classifier = classifier

    def all_words(self, documents):
        """
        Return all words from the documents.
        """
        all_words = []
        for words, sentiment in documents:
            all_words.extend(words)
        return all_words

    def all_bigrams(self, documents):
        """
        Return all bigrams from the documents.
        """
        all_bigrams = []
        for text, sentiment in documents:
            all_bigrams.extend(nltk.bigrams(text))
        return all_bigrams

    def apply_features(self, documents, labeled=None):
        """
        Apply all feature extractor functions to the documents.
        If ``labeled=False`` return featuresets as:
            [feature_func(doc) for doc in documents]
        If ``labeled=True`` return featuresets as:
            [(feature_func(tok), label) for (tok, label) in toks]
        """
        return apply_features(self.extract_features, documents, labeled)

    def unigram_word_feats(self, words, top_n=None, min_freq=0):
        """
        Return most common top_n word features.
        """
        # Stopwords are not removed
        unigram_feats_freqs = FreqDist(word for word in words)
        return [w for w, f in unigram_feats_freqs.most_common(top_n)
                if unigram_feats_freqs[w] > min_freq]

    @timer
    def bigram_collocation_feats(self, documents, top_n=None, min_freq=3,
                                 assoc_measure=BigramAssocMeasures.pmi):
        """
        Return ``top_n`` bigram features (using ``assoc_measure``).
        Note that this method is based on bigram collocations, and not on simple
        bigram frequency.
        :param min_freq: the minimum number of occurrencies of bigrams to take into consideration
        :param assoc_measure: bigram association measures
        """
        finder = BigramCollocationFinder.from_documents(documents)
        finder.apply_freq_filter(min_freq)
        return finder.nbest(assoc_measure, top_n)

    def bigram_word_feats(self, bigrams, top_n=None, min_freq=0):
        """
        Return most common top_n bigram features.
        """
        bigram_feats_freqs = FreqDist(bigram for bigram in bigrams)
        return [(b[0], b[1]) for b, f in bigram_feats_freqs.most_common(top_n)
                if bigram_feats_freqs[b] > min_freq]

    def add_feat_extractor(self, function, **kwargs):
        """
        Add a new function to extract features from a document. This function will
        be used in extract_features().
        Important: in this step our kwargs are only representing additional parameters,
        and NOT the document we have to parse. The document will always be the first
        parameter in the parameter list, and it will be added in the extract_features()
        function.
        """
        self.feat_extractors[function].append(kwargs)

    def extract_features(self, document):
        """
        Apply extractor functions (and their parameters) to the present document.
        """
        all_features = {}
        for extractor in self.feat_extractors:
            # We pass document as the first parameter of the function.
            # If we want to use the same extractor function multiple times, we
            # have to consider multiple sets of parameters (one for each call).
            for param_set in self.feat_extractors[extractor]:
                feats = extractor(document, **param_set)
            all_features.update(feats)
        return all_features

    @timer
    def train(self, trainer, training_set, save_classifier=None, **kwargs):
        """
        Train classifier on the training set, eventually saving the output.
        Additional arguments depend on the specific trainer we are using.
        """
        print("Training classifier")
        self.classifier = trainer(training_set, **kwargs)
        if save_classifier:
            save_file(self.classifier, save_classifier)

        return self.classifier

    @timer
    def evaluate(self, classifier, test_set):
        """
        Test classifier accuracy (more evaluation metrics should be added)
        """
        print("Evaluating {} accuracy...".format(type(classifier).__name__))
        accuracy_score = accuracy(classifier, test_set)
        return accuracy_score
