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
from copy import deepcopy

import codecs
import itertools
import pdb
import random
import re
import sys

from nltk.classify.util import apply_features, accuracy
from nltk.classify.naivebayes import NaiveBayesClassifier
from nltk.classify.maxent import MaxentClassifier
from nltk.collocations import *
from nltk.metrics import BigramAssocMeasures
from nltk.probability import FreqDist
from nltk.tokenize import word_tokenize, treebank, regexp, casual
from util import output_markdown, parse_dataset, save_file, timer

import nltk

# Regular expression by Christopher Potts
NEGATION = r"""
    (?:
        ^(?:never|no|nothing|nowhere|noone|none|not|
            havent|hasnt|hadnt|cant|couldnt|shouldnt|
            wont|wouldnt|dont|doesnt|didnt|isnt|arent|aint
        )$
    )
    |
    n't"""

CLAUSE_PUNCT = r'^[.:;!?]$'

NEGATION_RE = re.compile(NEGATION, re.VERBOSE)
CLAUSE_PUNCT_RE = re.compile(CLAUSE_PUNCT)


class SentimentAnalyzer(object):
    '''
    A Sentiment Analysis tool based on different modular approaches
    '''
    def __init__(self):
        self.feat_extractors = defaultdict(list)

    def get_all_words(self, documents):
        all_words = []
        for words, sentiment in documents:
            all_words.extend(words)
        return all_words

    def get_all_bigrams(self, documents):
        all_bigrams = []
        for text, sentiment in documents:
            all_bigrams.extend(nltk.bigrams(text))
        return all_bigrams

    def unigram_word_feats(self, words, top_n=None):
        '''
        Return most common top_n word features.
        '''
        # This method could be put outside the class, and the unigram_feats variable
        # can be made more generic (e.g. a list of feature lists for bigrams, trigrams, etc.)
        unigram_feats_freqs = FreqDist(word for word in words) # Stopwords are not removed
        return [w for w,f in unigram_feats_freqs.most_common(top_n)]

    @timer
    def bigram_collocation_feats(self, documents, assoc_measure=BigramAssocMeasures.pmi, top_n=None, min_freq=3):
        '''
        Return top_n bigram features (using assoc_measure).
        Note that this method is based on bigram collocations, and not on simple
        bigram frequency.
        :param min_freq: the minimum number of occurrencies of bigrams to take into consideration
        :param assoc_measure: bigram association measures
        '''
        # This method could be put outside the class
        finder = BigramCollocationFinder.from_documents(documents)
        finder.apply_freq_filter(min_freq)
        return finder.nbest(assoc_measure, top_n)

    def bigram_word_feats(self, bigrams, top_n=None):
        '''
        Return most common top_n bigram features.
        '''
        # This method could be put outside the class
        bigram_feats_freqs = FreqDist(bigram for bigram in bigrams)
        return [(b[0],b[1]) for b,f in bigram_feats_freqs.most_common(top_n)]

    def add_feat_extractor(self, function, **kwargs):
        '''
        Add a new function to extract features from a document. This function will
        be used in extract_features().
        Important: in this step our kwargs are only representing additional parameters,
        and NOT the document we have to parse. The document will always be the first
        parameter in the parameter list, and it will be added in the extract_features()
        function.
        '''
        self.feat_extractors[function].append(kwargs)

    def extract_features(self, tweet):
        '''
        Apply extractor functions (and their parameters) to the present tweet.
        '''
        all_features = {}
        for extractor in self.feat_extractors:
            # We pass tweet as the first parameter of the function.
            # If we want to use the same extractor function multiple times, we
            # have to consider multiple sets of parameters (one for each call).
            for param_set in self.feat_extractors[extractor]:
                feats = extractor(tweet, **param_set)
            all_features.update(feats)
        return all_features

    @timer
    def train(self, trainer, training_set, save_classifier=None, **kwargs):
        print("Training classifier")
        # Additional arguments depend on the specific trainer we are using.
        # Is there a more elegant way to achieve the same result? I think
        # this might be confusing, especially for teaching purposes.
        classifier = trainer(training_set, **kwargs)
        if save_classifier:
            save_file(classifier, save_classifier)

        return classifier

    @timer
    def evaluate(self, classifier, test_set):
        '''
        Test classifier accuracy (more evaluation metrics should be added)
        '''
        print("Evaluating {} accuracy...".format(type(classifier).__name__))
        accuracy_score = accuracy(classifier, test_set)
        print("Accuracy: ", accuracy_score)
        return accuracy_score


def split_train_test(all_instances, n):
    # Randomly split n instances of the dataset into train and test sets
    random.seed(12345)
    random.shuffle(all_instances)
    train_set = all_instances[:int(.8*n)]
    test_set = all_instances[int(.8*n):n]

    return train_set, test_set

def mark_negation(document, double_neg_flip=False, shallow=False):
    '''
    Append a specific suffix to words that appear in the scope between a negation
    and a punctuation mark.
    :param shallow: if True, the method will modify the original document in place.
    :param double_neg_flip: if True, double negation is considered affirmation (we
        activate/deactivate negation scope everytime we find a negation).
    '''
    if not shallow:
        document = deepcopy(document)
    # check if the document is labeled. If so, only consider the unlabeled document
    labeled = document and isinstance(document[0], (tuple, list))
    if labeled:
        doc = document[0]
    else:
        doc = document
    neg_scope = False
    for i,word in enumerate(doc):
        if NEGATION_RE.search(word):
            if not neg_scope or (neg_scope and double_neg_flip):
                neg_scope = not neg_scope
                continue
            else:
                doc[i] += '_NEG'
        elif neg_scope and CLAUSE_PUNCT_RE.search(word):
            neg_scope = not neg_scope
        elif neg_scope and not CLAUSE_PUNCT_RE.search(word):
            doc[i] += '_NEG'

    return document

def extract_unigram_feats(document, unigrams, handle_negation=False):
    # This function is declared outside the class because the user should have the
    # possibility to create his/her own feature extractors without modifying the
    # SentimentAnalyzer class.
    features = {}
    if handle_negation:
        document = mark_negation(document)
    for word in unigrams:
        features['contains({})'.format(word)] = word in set(document)
    return features

def extract_bigram_feats(document, bigrams):
    # This function is declared outside the class because the user should have the
    # possibility to create his/her own feature extractors without modifying the
    # SentimentAnalyzer class.
    features = {}
    for bigr in bigrams:
        features['contains({})'.format(bigr)] = bigr in nltk.bigrams(document)
    return features

def extract_bigram_coll_feats(document, bigrams):
    features = {}
    for bigram in bigrams:
        # Important: this function DOES NOT consider the order of the words in
        # the bigram. It is useful for collocations, but not for idiomatic forms.
        features['contains({} - {})'.format(bigram[0], bigram[1])] = set(bigram) in [set(b) for b in itertools.combinations(document, r=2)]
    return features

def demo(dataset_name, classifier_type, n=None):
    '''
    :param dataset_name: 'labeled_tweets', 'sent140'
    :param n: the number of the corpus instances to use. Default: use all instances
    :param classifier_type: 'maxent', 'naivebayes'
    '''
    # tokenizer = word_tokenize # This will not work using CategorizedPlaintextCorpusReader
    # tokenizer = treebank.TreebankWordTokenizer()
    # tokenizer = regexp.WhitespaceTokenizer()
    # tokenizer = regexp.WordPunctTokenizer()
    tokenizer = casual.TweetTokenizer()
    try:
        all_docs = parse_dataset(dataset_name, tokenizer)
    except ValueError as ve:
        sys.exit(ve)

    if not n or n > len(all_docs):
        n = len(all_docs)

    training_tweets, testing_tweets = split_train_test(all_docs, n)

    sa = SentimentAnalyzer()
    all_words = sa.get_all_words(training_tweets)

    # Add simple unigram word features
    unigram_feats = sa.unigram_word_feats(all_words, top_n=1000)
    sa.add_feat_extractor(extract_unigram_feats, unigrams=unigram_feats)

    # Add unigram word features handling negation
    # all_words_neg = sa.get_all_words([mark_negation(tweet) for tweet in training_tweets])
    # unigram_feats = sa.unigram_word_feats(all_words_neg, top_n=1000)
    # sa.add_feat_extractor(extract_unigram_feats, unigrams=unigram_feats, handle_negation=True)

    # Note that the all_words variable is a list of ordered words. Since order is
    # captured, we can get bigram features from the list.

    # Add bigram collocation features
    bigram_collocs_feats = sa.bigram_collocation_feats([tweet[0] for tweet in training_tweets], top_n=100, min_freq=12)
    sa.add_feat_extractor(extract_bigram_coll_feats, bigrams=bigram_collocs_feats)

    # Add bigram word features
    # all_bigrams = sa.get_all_bigrams(training_tweets)
    # bigram_feats = sa.bigram_word_feats(all_bigrams, top_n=10)
    # sa.add_feat_extractor(extract_bigram_feats, bigrams=bigram_feats)

    training_set = apply_features(sa.extract_features, training_tweets)
    test_set = apply_features(sa.extract_features, testing_tweets)

    if classifier_type == 'naivebayes':
        trainer = NaiveBayesClassifier.train
    elif classifier_type == 'maxent':
        trainer = MaxentClassifier.train

    filename = '{}_{}_{}.pickle'.format(dataset_name, classifier_type, n)
    # classifier = sa.train(trainer, training_set, save_classifier=filename, max_iter=4)
    classifier = sa.train(trainer, training_set, save_classifier=filename)
    accuracy = sa.evaluate(classifier, test_set)

    extr = [f.__name__ for f in sa.feat_extractors]
    output_markdown('results.md', Dataset=dataset_name, Classifier=classifier_type,
        Instances=n, Tokenizer=tokenizer.__class__.__name__, Feats=extr, Accuracy=accuracy)

if __name__ == '__main__':
    demo(dataset_name='labeled_tweets', classifier_type='naivebayes', n=8000)
    # demo(dataset_name='labeled_tweets', classifier_type='naivebayes')
    # demo(dataset_name='labeled_tweets', classifier_type='maxent', n=8000)
    # demo(dataset_name='sent140', classifier_type='naivebayes', n=8000)