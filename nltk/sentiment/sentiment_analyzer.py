from __future__ import print_function
from nltk.tokenize import word_tokenize, treebank, regexp
from nltk.probability import FreqDist
from nltk.classify.util import apply_features, accuracy
from nltk.classify.naivebayes import NaiveBayesClassifier
from nltk.classify.maxent import MaxentClassifier
from nltk.corpus.reader import CategorizedPlaintextCorpusReader
import pdb
import csv
import sys
import time
import io
import pickle
import random
import os, os.path

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
        # This method is probably poorly implemented. We need to store word_features
        # in an instance or global variable because we have to pass it to extract_features(),
        # but that method cannot have more parameters.
        # This method could be put outside the class, and the word_features variable
        # can be made more generic (e.g. a list of feature lists for bigrams, trigrams, etc.)
        # self.word_features = FreqDist(word.lower() for word in words)
        word_features_freqs = FreqDist(word.lower() for word in words) # Stopwords are not removed
        # word_features_freqs.plot()
        self.word_features = [w for w,f in word_features_freqs.most_common(top_n)]
        # print(list(word_features)[:5]) # In NLTK 3 this does not output a sorted result
        return self.word_features

    def bigram_word_feats(self, words, top_n=None):
        '''
        Return most common top_n word features.
        '''
        word_features_freqs = FreqDist(word.lower() for word in words)
        # word_features_freqs.plot()
        self.word_features = [w for w,f in word_features_freqs.most_common(top_n)]
        return self.word_features

    def extract_features(self, tweet):
        features = {}
        for word in self.word_features:
            features['contains({})'.format(word)] = word in set(tweet)
        return features

    @timer
    def train(self, trainer, training_set, save_classifier=None, **kwargs):
        print("Training classifier")
        # classifier = trainer(training_set)
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
        # N.B.: The file had to be saved using protocol=2 if we need to read it using python2.x
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

def demo_tweets(classifier_type):
    '''
    This is an example using labeled_tweets.csv. Tweets are tokenized using the
    simple word_tokenize.
    :param classifier_type: A string. Options: 'naivebayes', 'maxent'
    '''

    print("Demo using labeled_tweets.csv")
    # We are now using a basic tokenizing strategy inside parse_tweets_set()
    all_tweets = parse_tweets_set()
    n = 1000 # The number of corpus instances to use
    # n = len(all_tweets)
    training_tweets, testing_tweets = split_train_test(all_tweets, n)

    sa = SentimentAnalyzer()
    all_words = sa.get_all_words(training_tweets)
    sa.unigram_word_feats(all_words,top_n=100) # Use only 100 most common words

    training_set = apply_features(sa.extract_features, training_tweets)
    test_set = apply_features(sa.extract_features, testing_tweets)

    if classifier_type == 'naivebayes':
        filename = 'nb_labeledtweets-{}.pickle'.format(n)
        trainer = NaiveBayesClassifier.train
    elif classifier_type == 'maxent':
        filename = 'maxent_labeledtweets-{}.pickle'.format(n)
        trainer = MaxentClassifier.train
    # classifier = sa.train(trainer, training_set, save_classifier=filename)

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

    # Randomly split dataset into train and test set
    training_tweets, testing_tweets = split_train_test(all_tweets, n)

    sa = SentimentAnalyzer()
    all_words = sa.get_all_words(training_tweets)
    sa.unigram_word_feats(all_words, top_n=100)

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
    # demo_tweets(classifier_type='naivebayes')
    demo_sent140(classifier_type='naivebayes')