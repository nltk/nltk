from __future__ import print_function
from nltk.tokenize import word_tokenize, treebank, regexp
from nltk.probability import FreqDist
from nltk.classify.util import apply_features, accuracy
from nltk.classify.naivebayes import NaiveBayesClassifier
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
        mins = int(tot_time / 60)
        secs = int(round(tot_time % 60)) # in Python 2.x round() will return a float, so we also convert it to int
        if mins == 0:
            print('{}(): {:.3f} seconds'.format(method.__name__, tot_time))
        else:
            print('{}(): {}:{} minutes'.format(method.__name__, mins, secs))
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

    def get_word_features(self, words):
        # This method could be put outside the class, and the word_features variable
        # can be made more generic (e.g. a list of feature lists for bigrams, trigrams, etc.)
        self.word_features = FreqDist(word.lower() for word in words)
        # print(list(word_features)[:5]) # In NLTK 3 this does not output a sorted result
        # return [w for w,f in self.word_features.most_common(5)] # To return top 5 features
        return [w for w,f in self.word_features.most_common()]

    def extract_features(self, tweet):
        features = {}
        for word in self.word_features:
            features['contains({})'.format(word)] = word in set(tweet)
        return features

    @timer
    def classify_nb(self, training_set, test_set, load_classifier=None, save_classifier=None):
        if load_classifier:
            nb_classifier = load_file(load_classifier)
        else:
            print("Training NaiveBayesClassifier")
            nb_classifier = NaiveBayesClassifier.train(training_set)

        self.evaluate(nb_classifier, test_set)

        if save_classifier:
            save_file(nb_classifier, save_classifier)

    @timer
    def evaluate(self, classifier, test_set):
        print("Evaluating accuracy...")
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

def demo_tweets():
    '''
    This is an example using labeled_tweets.csv. Tweets are tokenized using the
    simple word_tokenize.
    '''

    print("Demo using labeled_tweets.csv")
    tokenizer = treebank.TreebankWordTokenizer()
    # tokenizer = regexp.WhitespaceTokenizer()

    all_tweets = parse_tweets_set()
    n = 8000 # The number of corpus instances to use
    # n = len(all_tweets)
    # Randomly split dataset into train and test set
    random.seed(12345)
    random.shuffle(all_tweets)
    training_tweets = all_tweets[:int(.8*n)]
    testing_tweets = all_tweets[int(.8*n):n]

    sa = SentimentAnalyzer()
    all_words = sa.get_all_words(training_tweets)
    sa.get_word_features(all_words)

    training_set = apply_features(sa.extract_features, training_tweets)
    test_set = apply_features(sa.extract_features, testing_tweets)

    print("Starting classification")
    # sa.classify_nb(training_set, test_set, load_classifier='nb_classifier_labeledtweets-8000.pickle')
    sa.classify_nb(training_set, test_set, save_classifier='nb_classifier_labeledtweets-8000.pickle')
    # sa.classify_nb(training_set, test_set, save_classifier='nb_classifier_labeledtweets-ALL.pickle')

def demo_sent140():
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

    # start1 = time.time()
    # all_tweets = list(corpus.sents())

    cache_path = 'all_tweets140_cache.pickle'
    if not os.path.exists(cache_path):
        print('Parsing corpus.sents()')
        all_tweets = ([(tweet, 'pos') for tweet in corpus.sents('sent140_pos.txt')] +
                      [(tweet, 'neg') for tweet in corpus.sents('sent140_neg.txt')])
        save_file(all_tweets, cache_path)
    else:
        all_tweets = load_file(cache_path)

    # end1 = time.time()
    # tot_time1 = end1 - start1
    # print('LIST: {} mins and {} secs'.format(int(tot_time1 / 60), int(round(tot_time1 % 60))))

    # Randomly split dataset into train and test set
    random.seed(12345)
    random.shuffle(all_tweets)
    training_tweets = all_tweets[:int(.8*n)]
    testing_tweets = all_tweets[int(.8*n):n]

    sa = SentimentAnalyzer()
    all_words = sa.get_all_words(training_tweets)
    sa.get_word_features(all_words)

    training_set = apply_features(sa.extract_features, training_tweets)
    test_set = apply_features(sa.extract_features, testing_tweets) # Aggiunto ora

    print("Starting classification")
    start = time.time()
    sa.classify_nb(training_set, test_set, load_classifier='nb_classifier-8000.pickle')
    # sa.classify_nb(training_set, test_set, save_classifier='nb_classifier-8000.pickle')
    end = time.time()
    tot_time = end - start
    mins = int(tot_time / 60)
    secs = int(round(tot_time % 60)) # in Python 2.x round() will return a float, so we also convert it to int
    print('Classification completed in {} mins and {} secs'.format(mins, secs))

if __name__ == '__main__':
    # demo_sent140()
    demo_tweets()