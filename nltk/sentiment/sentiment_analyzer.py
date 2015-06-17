from __future__ import print_function
from nltk.tokenize import word_tokenize
from nltk.probability import FreqDist
from nltk.classify.util import apply_features, accuracy
from nltk.classify.naivebayes import NaiveBayesClassifier
import pdb
import csv
import sys
import time
import io
import pickle
import random
# To improve flexibility we could later abstract from tweets to generic documents

class SentimentAnalyzer(object):

  def parse_labeled_set(self, filename, max_entries=None):
    '''Parse training file and output train and test sets in (text, label) format'''
    start = time.time()

    labeled_tweets = []
    with io.open(filename, 'rt', encoding='utf-8', errors='replace') as csvfile:
    # with io.open(filename, 'rt', encoding='latin-1') as csvfile:
    # with io.open(filename, 'rt', encoding='utf-8') as csvfile:
      reader = csv.reader(csvfile)
      i = 0
      # for label, text, score in reader:
      for row in reader:
        if max_entries and reader.line_num == max_entries:
          break
        # print(row[0], row[5])
        sys.stderr.write("Loaded %d sentences\r" % (reader.line_num))

        i += 1
        tokenized_tweet = [w.lower() for w in word_tokenize(row[5])] # We are creating a list of training tokenized tweets
        # tokenized_tweet = [w.lower() for w in word_tokenize(text)] # We are creating a list of training tokenized tweets
        # print(row[1])
        labeled_tweets.append((tokenized_tweet, row[0]))

    end = time.time()
    # print("time: ", end - start)
    print("Loaded {} sentences".format(i+1))
    return labeled_tweets

  def get_all_words(self, tweets):
    # all_words = FreqDist(word.lower() for word,sent in tweets)
    all_words = []
    for words, sentiment in tweets:
      all_words.extend(words)
    return all_words

  def get_word_features(self, words):
    # This method could be put outside the class, and the word_features variable
    # can be made more generic (e.g. a list of feature lists for bigrams, trigrams, etc.)
    self.word_features = FreqDist(word.lower() for word in words)
    # print(word_features.most_common(5))
    # print(list(word_features)[:5]) # With NLTK 3 this would not output a sorted result
    return [w for w,f in self.word_features.most_common()]

  def extract_features(self, tweet):
    # Questo metodo utilizza word_features che viene creato fuori. Devo renderlo
    # piu modulare
    # tokenized_tweet = word_tokenize(tweet) # The tweet is already a tokenized list
    features = {}
    for word in self.word_features:
      features['contains({})'.format(word)] = word in set(tweet)

    return features

  def classify_nb(self, training_set, test_set, load_file=None, save_file=None):
    print("Training NaiveBayesClassifier")
    # pdb.set_trace()
    if load_file:
      nb_classifier = load_classifier(load_file)
    else:
      nb_classifier = NaiveBayesClassifier.train(training_set)
    # classifier2 = NaiveBayesClassifier.train(training_set2)
    # print("fine NaiveBayesClassifier.train(training_set)")

    # pdb.set_trace()

    print("Accuracy: ", accuracy(nb_classifier, test_set))

    if save_file:
      save_classifier(nb_classifier, save_file)

def save_classifier(classifier, filename):
  print("Saving", filename)
  with io.open(filename, 'wb') as storage_file:
    classifier = pickle.dump(classifier, storage_file)

def load_classifier(filename):
  print("Loading", filename)
  with io.open(filename, 'rb') as storage_file:
    classifier = pickle.load(storage_file)

  return classifier

def shuffle_csv(source_csv, output_csv):
  # This method is temporary. It can be used to overcome the limitations of a
  # training set whose rows are sorted by label, in case we want to use only its
  # first n rows.
  print("Shuffling", source_csv)
  with open(source_csv,'r', encoding='latin-1') as source:
      data = [(random.random(), line) for line in source]
  data.sort()
  with open(output_csv,'w') as target:
      for _, line in data:
          target.write(line)

def main():
  # Sentiment140 training set can be found at: http://help.sentiment140.com/for-students
  # sentiment140_train = '../../../sentiment140/training.1600000.processed.noemoticon.csv'
  sentiment140_train_shuffled = '../../../sentiment140/shuffled_training_ppp.csv'
  # training_tweets = parse_labeled_set("sentiment140/training.1600000.processed.noemoticon.csv", max_entries=20000)
  # training_tweets = parse_labeled_set("sentiment140/shuffled_training_ppp.csv", max_entries=2)
  sa = SentimentAnalyzer()
  # shuffle_csv('sentiment140/training.1600000.processed.noemoticon.csv', 'sentiment140/shuffled_training_ppp.csv')
  training_tweets = sa.parse_labeled_set(sentiment140_train_shuffled, max_entries=20000)
  testing_tweets = sa.parse_labeled_set("sentiment140/testdata.manual.2009.06.14.csv")

  all_words = sa.get_all_words(training_tweets)
  # global word_features # We declare word_features as global so that extract_features() can use it.
  sa.get_word_features(all_words)
  # sa.word_features = sa.get_word_features(all_words)
  # print(word_features)
  training_set = apply_features(sa.extract_features, training_tweets)
  # training_set2 = apply_features(extract_features, training_tweets2)
  test_set = apply_features(sa.extract_features, testing_tweets) # Aggiunto ora
  # pdb.set_trace()
  # classify_nb(training_tweets, testing_tweets)
  # classify_nb(training_set, test_set, load_file='nb_classifier.pickle')
  # classify_nb(training_set, test_set, save_file='stored_classifiers/nb_classifier_train-2.pickle')
  # classify_nb(training_set, test_set, save_file='nb_classifier_train-20000.pickle')
  start = time.time()
  sa.classify_nb(training_set, test_set, load_file='nb_classifier_train-20000.pickle')
  end = time.time()
  tot_time = end - start
  # print(tot_time)
  mins = int(tot_time / 60)
  secs = int(round(tot_time % 60)) # in Python 2.x round() will return a float, so we also convert it to int
  print('{} mins and {} secs'.format(mins, secs))

if __name__ == '__main__':
  main()