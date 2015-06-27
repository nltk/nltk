from __future__ import print_function
from nltk.classify.util import apply_features, accuracy
from nltk.classify.naivebayes import NaiveBayesClassifier
from nltk.classify.maxent import MaxentClassifier
from nltk.collocations import *
from nltk.corpus.reader import CategorizedPlaintextCorpusReader
from nltk.metrics import BigramAssocMeasures
from nltk.probability import FreqDist
from nltk.tokenize import word_tokenize, treebank, regexp
from nltk.util import bigrams
from collections import defaultdict
import csv
import io
import itertools
import os, os.path
import pdb
import pickle
import random
import sys
import time

# Define @timer decorator
def timer(method):
    def timed(*args, **kw):
        start = time.time()
        result = method(*args, **kw)
        end = time.time()
        tot_time = end - start
        hours = int(tot_time / 3600)
        mins = int((tot_time / 60) % 60)
        secs = int(round(tot_time % 60)) # in Python 2.x round() will return a float, so we also convert it to int
        if hours == 0 and mins == 0 and secs < 10:
            print('[TIMER] {}(): {:.3f} seconds'.format(method.__name__, tot_time))
        else:
            print('[TIMER] {}(): {}h {}m {}s'.format(method.__name__, hours, mins, secs))
        return result

    return timed

class SentimentAnalyzer(object):
    '''
    A Sentiment Analysis tool based on different modular approaches
    '''
    def __init__(self):
        self.feat_extractors = defaultdict(list)

    def parse_labeled_set(self, filename, max_entries=None):
        '''
        DEPRECATED. This method has to be removed: it will not be used anymore
        after the proper conversion of datasets into NLTK corpora.
        Parse training file and output train and test sets in (text, label) format
        '''
        labeled_tweets = []
        with io.open(filename, 'rt', encoding='utf-8', errors='replace') as csvfile:
            reader = csv.reader(csvfile)
            i = 0
            for row in reader:
                if max_entries and reader.line_num == max_entries:
                    break
                sys.stdout.write("Loaded %d sentences\r" % (reader.line_num))
                i += 1
                # Create a list of tokenized tweets
                tokenized_tweet = [w.lower() for w in word_tokenize(row[5])]
                labeled_tweets.append((tokenized_tweet, row[0]))
        print("Loaded {} sentences".format(i+1))

        return labeled_tweets

    def get_all_words(self, tweets):
        all_words = []
        for words, sentiment in tweets:
            all_words.extend(words)
        return all_words

    def unigram_word_feats(self, words, top_n=None):
        '''
        Return most common top_n word features.
        '''
        # This method could be put outside the class, and the unigram_feats variable
        # can be made more generic (e.g. a list of feature lists for bigrams, trigrams, etc.)
        unigram_feats_freqs = FreqDist(word.lower() for word in words) # Stopwords are not removed
        return [w for w,f in unigram_feats_freqs.most_common(top_n)]

    @timer
    def bigram_collocation_feats(self, words, assoc_measure=BigramAssocMeasures.pmi, top_n=None, min_freq=3):
        '''
        Return top_n bigram features (using assoc_measure).
        Note that this method is based on bigram collocations, and not on simple
        bigram frequency.
        :param min_freq: the minimum number of occurrencies of bigrams to take into consideration
        :param assoc_measure: bigram association measures
        '''
        # This method could be put outside the class
        finder = BigramCollocationFinder.from_words(words)
        finder.apply_freq_filter(min_freq)
        return finder.nbest(assoc_measure, top_n)

    @timer
    def bigram_word_feats(self, words, top_n=None):
        '''
        Return most common top_n bigram features.
        '''
        # This method could be put outside the class
        bigram_feats_freqs = FreqDist(bigrams(word.lower() for word in words))
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

def save_file(content, filename):
    print("Saving", filename)
    with io.open(filename, 'wb') as storage_file:
        # pickle.dump(content, storage_file) # This will break on python2.x
        pickle.dump(content, storage_file, protocol=2) # protocol = 2 is for python2 compatibility

def load_file(filename):
    print("Loading", filename)
    with io.open(filename, 'rb') as storage_file:
        # The file has to be saved using protocol=2 if we need to read it using python2.x
        content = pickle.load(storage_file)
    return content

def parse_tweets_set(filename='labeled_tweets.csv'):
    '''Parse training file and output train and test sets in (text, label) format'''
    tweets = []
    with open(filename, 'rt') as csvfile:
        reader = csv.reader(csvfile)
        i = 0
        for label, text, score in reader:
            i += 1
            sys.stdout.write('Loaded {} tweets\r'.format(i))
            # Tokenize using simple word_tokenize
            tokenized_tweet = [w.lower() for w in word_tokenize(text)] # We are creating a list of training tokenized tweets
            tweets.append((tokenized_tweet, label))
    print("Loaded {} tweets".format(i))
    return tweets

def split_train_test(all_instances, n):
    # Randomly split n instances of the dataset into train and test sets
    random.seed(12345)
    random.shuffle(all_instances)
    train_set = all_instances[:int(.8*n)]
    test_set = all_instances[int(.8*n):n]

    return train_set, test_set

def extract_unigram_feats(document, unigrams):
    # This function is declared outside the class because the user should have the
    # possibility to create his/her own feature extractors without modifying the
    # SentimentAnalyzer class.
    features = {}
    for word in unigrams:
        features['contains({})'.format(word)] = word in set(document)
    return features

def extract_bigram_feats(document, bigrams):
    features = {}
    # return dict([(ngram, True) for ngram in itertools.chain(words, bigrams)])
    for bigram in bigrams:
        # Important: this function DOES NOT consider the order of the words in
        # the bigram. It is useful for collocations, but not for idiomatic forms.
        features['contains({} - {})'.format(bigram[0], bigram[1])] = set(bigram) in [set(b) for b in itertools.combinations(document, r=2)]
    return features


def demo_tweets(classifier_type):
    '''
    This is an example using labeled_tweets.csv. Tweets are tokenized using the
    simple word_tokenize.
    :param classifier_type: A string. Options: 'naivebayes', 'maxent'
    '''
    print("Demo using labeled_tweets.csv")
    # We are now using a basic tokenizing strategy inside parse_tweets_set()
    all_tweets = parse_tweets_set()
    n = 8000 # The number of corpus instances to use
    # n = len(all_tweets)
    training_tweets, testing_tweets = split_train_test(all_tweets, n)

    sa = SentimentAnalyzer()
    all_words = sa.get_all_words(training_tweets)
    unigram_feats = sa.unigram_word_feats(all_words, top_n=100)
    sa.add_feat_extractor(extract_unigram_feats, unigrams=unigram_feats)

    # Note that the all_words variable is a list of ordered words. Since order is
    # captured, we can get bigram collocations from the list.

    # bigram_collocs_feats = sa.bigram_collocation_feats(all_words, top_n=100, min_freq=12)
    # sa.add_feat_extractor(extract_bigram_feats, bigrams=bigram_collocs_feats)

    bigram_feats = sa.bigram_word_feats(all_words, top_n=10)
    sa.add_feat_extractor(extract_bigram_feats, bigrams=bigram_feats)

    training_set = apply_features(sa.extract_features, training_tweets)
    test_set = apply_features(sa.extract_features, testing_tweets)

    if classifier_type == 'naivebayes':
        filename = 'nb_labeledtweets-{}.pickle'.format(n)
        trainer = NaiveBayesClassifier.train
    elif classifier_type == 'maxent':
        filename = 'maxent_labeledtweets-{}.pickle'.format(n)
        trainer = MaxentClassifier.train

    # classifier = sa.train(trainer, training_set, save_classifier=filename, max_iter=4)
    classifier = sa.train(trainer, training_set, save_classifier=filename)
    sa.evaluate(classifier, test_set)

def demo_sent140(classifier_type):
    '''
    This is an example using only the first 20000 entries of the shuffled training set
    Sentiment140 training set can be found at: http://help.sentiment140.com/for-students
    '''
    corpus_path = os.path.expanduser('~/nltk_data/corpora/sentiment140/')

    tokenizer = treebank.TreebankWordTokenizer()
    # tokenizer = regexp.WhitespaceTokenizer()
    corpus = CategorizedPlaintextCorpusReader(corpus_path, r'sent140_.*\.txt',
        cat_pattern=r'sent140_(\w+)\.txt', word_tokenizer=tokenizer)

    # n = 2000
    n = 8000 # The number of corpus instances to use

    cache_path = 'all_tweets140_cache.pickle'
    if not os.path.exists(cache_path):
        print('Parsing corpus.sents()')
        all_tweets = ([(tweet, 'pos') for tweet in corpus.sents('sent140_pos.txt')] +
                      [(tweet, 'neg') for tweet in corpus.sents('sent140_neg.txt')])
        save_file(all_tweets, cache_path)
    else:
        all_tweets = load_file(cache_path)

    training_tweets, testing_tweets = split_train_test(all_tweets, n)

    sa = SentimentAnalyzer()
    all_words = sa.get_all_words(training_tweets)
    unigram_feats = sa.unigram_word_feats(all_words, top_n=100)
    sa.add_feat_extractor(extract_unigram_feats, unigrams=unigram_feats)

    training_set = apply_features(sa.extract_features, training_tweets)
    test_set = apply_features(sa.extract_features, testing_tweets)

    if classifier_type == 'naivebayes':
        filename = 'nb_sent140-{}.pickle'.format(n)
        trainer = NaiveBayesClassifier.train
    elif classifier_type == 'maxent':
        filename = 'maxent_sent140-{}.pickle'.format(n)
        trainer = MaxentClassifier.train

    # classifier = load_file(filename)
    classifier = sa.train(trainer, training_set, save_classifier=filename)
    sa.evaluate(classifier, test_set)

if __name__ == '__main__':
    # demo_tweets(classifier_type='maxent')
    demo_tweets(classifier_type='naivebayes')
    # demo_sent140(classifier_type='naivebayes')