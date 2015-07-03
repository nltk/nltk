import codecs
import csv
import os
import pickle
import sys
import time

from nltk.corpus.reader import CategorizedPlaintextCorpusReader
from nltk.data import load

def output_markdown(filename, **kwargs):
    with codecs.open(filename, 'at') as outfile:
        text = '\n*** \n\n'
        text += '{} \n\n'.format(time.strftime("%d/%m/%Y, %H:%M"))
        for k in sorted(kwargs):
            text += '  - **{}:** {} \n'.format(k, kwargs[k])
        outfile.write(text)

def parse_dataset(dataset_name, tokenizer):
    r'''
    Parse a dataset and outputs a list of documents.
    Available datasets: 'labeled_tweets', 'sent140'.
    '''
    if dataset_name == 'labeled_tweets':
        # This is an example using labeled_tweets.csv
        return parse_tweets_set('labeled_tweets.csv', tokenizer)

    elif dataset_name == 'sent140':
        #Sentiment140 training set can be found at: http://help.sentiment140.com/for-students
        corpus_path = os.path.expanduser('~/nltk_data/corpora/sentiment140/')
        corpus = CategorizedPlaintextCorpusReader(corpus_path, r'sent140_.*\.txt',
            cat_pattern=r'sent140_(\w+)\.txt', word_tokenizer=tokenizer)

        cache_path = 'sent140tweets_cache.pickle'
        if not os.path.exists(cache_path):
            print('Parsing corpus.sents()')
            all_tweets = ([(tweet, 'pos') for tweet in corpus.sents('sent140_pos.txt')] +
                          [(tweet, 'neg') for tweet in corpus.sents('sent140_neg.txt')])
            save_file(all_tweets, cache_path)
        else:
            all_tweets = load(cache_path)

        return all_tweets
    else:
        raise ValueError('Error while parsing the dataset. Did you specify a valid name?')

def parse_tweets_set(filename, word_tokenizer, sent_tokenizer=None):
    r'''
    Parse training file and output train and test sets in (text, label) format.
    :param tokenizer: the tokenizer method that will be used to tokenize the text
    E.g. WordPunctTokenizer.tokenize
         BlanklineTokenizer.tokenize

    N.B.: word_tokenize is actually a shortcut that combines PunktSentenceTokenizer
    and TreebankWordTokenizer().tokenize
    '''
    tweets = []
    if not sent_tokenizer:
        sent_tokenizer = load('tokenizers/punkt/english.pickle')

    # If we use Python3.x we can proceed using the 'rt' flag
    if sys.version_info[0] == 3:
        with codecs.open(filename, 'rt') as csvfile:
            reader = csv.reader(csvfile)
            i = 0
            for label, text, score in reader:
                i += 1
                sys.stdout.write('Loaded {} tweets\r'.format(i))
                # Apply sentence and word tokenizer to text
                tokenized_tweet = [w for sent in sent_tokenizer.tokenize(text) for w in word_tokenizer.tokenize(sent)]
                tweets.append((tokenized_tweet, label))
    # If we use Python2.x we need to handle encoding problems
    elif sys.version_info[0] < 3:
        with codecs.open(filename) as csvfile:
            reader = csv.reader(csvfile)
            i = 0
            for row in reader:
                unicode_row = [x.decode('utf8') for x in row]
                label = unicode_row[0]
                text = unicode_row[1]
                score = unicode_row[2]
                i += 1
                sys.stdout.write('Loaded {} tweets\r'.format(i))
                # Apply sentence and word tokenizer to text
                tokenized_tweet = [w.encode('utf8') for sent in sent_tokenizer.tokenize(text) for w in word_tokenizer.tokenize(sent)]
                tweets.append((tokenized_tweet, label))
    print("Loaded {} tweets".format(i))
    return tweets

def save_file(content, filename):
    print("Saving", filename)
    with codecs.open(filename, 'wb') as storage_file:
        # pickle.dump(content, storage_file) # This will break on python2.x
        pickle.dump(content, storage_file, protocol=2) # protocol = 2 is for python2 compatibility

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