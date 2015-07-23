from copy import deepcopy
import codecs
import csv
import itertools
import os
import pickle
import random
import re
import sys
import time
try:
    import matplotlib.pyplot as plt
except ImportError:
    import warnings
    warnings.warn("matplotlib not installed. Graph generation not available.")

import nltk
from nltk.corpus import CategorizedPlaintextCorpusReader
from nltk.data import load

#////////////////////////////////////////////////////////////
#{ Regular expressions
#////////////////////////////////////////////////////////////

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


# Define @timer decorator
def timer(method):
    def timed(*args, **kw):
        start = time.time()
        result = method(*args, **kw)
        end = time.time()
        tot_time = end - start
        hours = int(tot_time / 3600)
        mins = int((tot_time / 60) % 60)
        # in Python 2.x round() will return a float, so we convert it to int
        secs = int(round(tot_time % 60))
        if hours == 0 and mins == 0 and secs < 10:
            print('[TIMER] {}(): {:.3f} seconds'.format(method.__name__, tot_time))
        else:
            print('[TIMER] {}(): {}h {}m {}s'.format(method.__name__, hours, mins, secs))
        return result
    return timed

#////////////////////////////////////////////////////////////
#{ Feature extractor functions
#////////////////////////////////////////////////////////////

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

def extract_bigram_coll_feats(document, bigrams):
    features = {}
    for bigram in bigrams:
        # Important: this function DOES NOT consider the order of the words in
        # the bigram. It is useful for collocations, but not for idiomatic forms.
        bigrams_set = set(bigram) in [set(b) for b in itertools.combinations(
            document, r=2)]
        features['contains({} - {})'.format(bigram[0], bigram[1])] = bigrams_set
    return features

def extract_bigram_feats(document, bigrams):
    # This function is declared outside the class because the user should have the
    # possibility to create his/her own feature extractors without modifying the
    # SentimentAnalyzer class.
    features = {}
    for bigr in bigrams:
        features['contains({})'.format(bigr)] = bigr in nltk.bigrams(document)
    return features

#////////////////////////////////////////////////////////////
#{ Helper Functions
#////////////////////////////////////////////////////////////

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
    for i, word in enumerate(doc):
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

def output_markdown(filename, **kwargs):
    with codecs.open(filename, 'at') as outfile:
        text = '\n*** \n\n'
        text += '{} \n\n'.format(time.strftime("%d/%m/%Y, %H:%M"))
        for k in sorted(kwargs):
            text += '  - **{}:** {} \n'.format(k, kwargs[k])
        outfile.write(text)

def parse_dataset(dataset_name, tokenizer):
    '''
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
    '''
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
                tokenized_tweet = [w for sent in sent_tokenizer.tokenize(text)
                                   for w in word_tokenizer.tokenize(sent)]
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
                tokenized_tweet = [w.encode('utf8') for sent in
                                   sent_tokenizer.tokenize(text) for w in
                                   word_tokenizer.tokenize(sent)]
                tweets.append((tokenized_tweet, label))
    print("Loaded {} tweets".format(i))
    return tweets

def parse_subjectivity_dataset(filename, word_tokenizer, label=None):
    with codecs.open(filename, 'rb') as inputfile:
        docs = []
        for line in inputfile:
            tokenized_line = word_tokenizer.tokenize(line.decode('latin-1'))
            docs.append((tokenized_line, label))
    return docs


def save_file(content, filename):
    print("Saving", filename)
    with codecs.open(filename, 'wb') as storage_file:
        # pickle.dump(content, storage_file) # This will break on python2.x
        pickle.dump(content, storage_file, protocol=2) # protocol = 2 is for python2 compatibility

def split_train_test(all_instances, n=None):
    # Randomly split n instances of the dataset into train and test sets
    random.seed(12345)
    random.shuffle(all_instances)
    if not n or n > len(all_instances):
        n = len(all_instances)
    train_set = all_instances[:int(.8*n)]
    test_set = all_instances[int(.8*n):n]

    return train_set, test_set

def _show_plot(x_values, y_values, x_labels=None, y_labels=None):
    plt.locator_params(axis='y', nbins=3)
    axes = plt.axes()
    axes.yaxis.grid()
    plt.plot(x_values, y_values, 'ro', color='red')
    plt.ylim(ymin=-1.2, ymax=1.2)
    plt.tight_layout(pad=5)
    if x_labels:
        plt.xticks(x_values, x_labels, rotation='vertical')
    if y_labels:
        plt.yticks([-1, 0, 1], y_labels, rotation='horizontal')
    # Pad margins so that markers don't get clipped by the axes
    plt.margins(0.2)
    plt.show()

#////////////////////////////////////////////////////////////
#{ Demos
#////////////////////////////////////////////////////////////

def demo_tweets(trainer, n=None):
    '''
    Train Naive Bayes classifier on 8000 instances of labeled_tweets dataset,
    using TweetTokenizer.
    Features are composed of:
        - 1000 most frequent unigrams
        - 100 top bigram collocations (using BigramAssocMeasures.pmi)
    '''
    from nltk.tokenize import casual
    from sentiment_analyzer import SentimentAnalyzer
    from nltk.corpus import stopwords

    tokenizer = casual.TweetTokenizer()
    all_docs = parse_dataset('labeled_tweets', tokenizer)

    if not n or n > len(all_docs):
        n = len(all_docs)

    training_tweets, testing_tweets = split_train_test(all_docs, n)

    stopwords = stopwords.words('english')
    sa = SentimentAnalyzer()
    all_words = [word for word in sa.all_words(training_tweets) if word.lower() not in stopwords]

    # Add simple unigram word features
    unigram_feats = sa.unigram_word_feats(all_words, top_n=1000)
    sa.add_feat_extractor(extract_unigram_feats, unigrams=unigram_feats)

    # Add bigram collocation features
    bigram_collocs_feats = sa.bigram_collocation_feats([tweet[0] for tweet in
        training_tweets], top_n=100, min_freq=12)
    sa.add_feat_extractor(extract_bigram_coll_feats, bigrams=bigram_collocs_feats)

    training_set = sa.apply_features(training_tweets)
    test_set = sa.apply_features(testing_tweets)

    classifier = sa.train(trainer, training_set)
    # classifier = sa.train(trainer, training_set, max_iter=4)
    try:
        classifier.show_most_informative_features()
    except AttributeError:
        print('Your classifier does not provide a show_most_informative_features() method.')
    accuracy = sa.evaluate(classifier, test_set)
    print('Accuracy:', accuracy)

    extr = [f.__name__ for f in sa.feat_extractors]
    output_markdown('results.md', Dataset='labeled_tweets', Classifier=type(classifier).__name__,
                    Tokenizer=tokenizer.__class__.__name__, Feats=extr, Accuracy=accuracy,
                    Notes='Remove stopwords')

def demo_movie_reviews(trainer):
    '''
    Train Naive Bayes classifier on all instances of the Movie Reviews dataset.
    The corpus has been preprocessed using the default sentence tokenizer and
    WordPunctTokenizer.
    Features are composed of:
        - 1000 most frequent unigrams
    '''
    from nltk.corpus import movie_reviews
    from sentiment_analyzer import SentimentAnalyzer

    pos_docs = [(list(movie_reviews.words(pos_id)), 'pos') for pos_id in
                movie_reviews.fileids('pos')]
    neg_docs = [(list(movie_reviews.words(neg_id)), 'neg') for neg_id in
                movie_reviews.fileids('neg')]

    # We separately split positive and negative instances to keep a balanced
    # uniform class distribution in both train and test sets.
    train_pos_docs, test_pos_docs = split_train_test(pos_docs)
    train_neg_docs, test_neg_docs = split_train_test(neg_docs)

    training_docs = train_pos_docs+train_neg_docs
    testing_docs = test_pos_docs+test_neg_docs

    sa = SentimentAnalyzer()
    all_words = sa.all_words(training_docs)

    # Add simple unigram word features
    unigram_feats = sa.unigram_word_feats(all_words, min_freq=4)
    sa.add_feat_extractor(extract_unigram_feats, unigrams=unigram_feats)

    # Apply features to obtain a feature-value representation of our datasets
    training_set = sa.apply_features(training_docs)
    test_set = sa.apply_features(testing_docs)

    classifier = sa.train(trainer, training_set)
    try:
        classifier.show_most_informative_features()
    except AttributeError:
        print('Your classifier does not provide a show_most_informative_features() method.')
    accuracy = sa.evaluate(classifier, test_set)
    print('Accuracy:', accuracy)

    extr = [f.__name__ for f in sa.feat_extractors]
    output_markdown('results.md', Dataset='Movie_reviews', Classifier=type(classifier).__name__,
                    Tokenizer='WordPunctTokenizer', Feats=extr, Accuracy=accuracy)

def demo_subjectivity(trainer):
    from sentiment_analyzer import SentimentAnalyzer
    from nltk.tokenize import regexp

    word_tokenizer = regexp.WhitespaceTokenizer()

    subj_data = '/home/fievelk/nltk_data/corpora/rotten_imdb/quote.tok.gt9_subj.5000'
    subj_docs = parse_subjectivity_dataset(subj_data, word_tokenizer=word_tokenizer,
                                           label='subj')
    obj_data = '/home/fievelk/nltk_data/corpora/rotten_imdb/plot.tok.gt9_obj.5000'
    obj_docs = parse_subjectivity_dataset(obj_data, word_tokenizer=word_tokenizer,
                                          label='obj')

    # We separately split subjective and objective instances to keep a balanced
    # uniform class distribution in both train and test sets.
    train_subj_docs, test_subj_docs = split_train_test(subj_docs)
    train_obj_docs, test_obj_docs = split_train_test(obj_docs)

    training_docs = train_subj_docs+train_obj_docs
    testing_docs = test_subj_docs+test_obj_docs

    sa = SentimentAnalyzer()
    all_words_neg = sa.all_words([mark_negation(doc) for doc in training_docs])

    # Add simple unigram word features handling negation
    unigram_feats = sa.unigram_word_feats(all_words_neg, min_freq=4)
    sa.add_feat_extractor(extract_unigram_feats, unigrams=unigram_feats)

    # Apply features to obtain a feature-value representation of our datasets
    training_set = sa.apply_features(training_docs)
    test_set = sa.apply_features(testing_docs)

    classifier = sa.train(trainer, training_set)
    try:
        classifier.show_most_informative_features()
    except AttributeError:
        print('Your classifier does not provide a show_most_informative_features() method.')
    accuracy = sa.evaluate(classifier, test_set)
    print('Accuracy:', accuracy)

    # save_file(sa, 'sa_subjectivity.pickle')

    extr = [f.__name__ for f in sa.feat_extractors]
    output_markdown('results.md', Dataset='subjectivity', Classifier=type(classifier).__name__,
                    Instances=2000, Tokenizer=word_tokenizer.__class__.__name__,
                    Feats=extr, Accuracy=accuracy)

def demo_sent_subjectivity(text):
    """
    Classify a single sentence using a stored SentimentAnalyzer
    """
    from nltk.tokenize import regexp
    word_tokenizer = regexp.WhitespaceTokenizer()
    sentim_analyzer = load('sa_subjectivity.pickle')

    # tokenized_text = word_tokenizer.tokenize(text)
    tokenized_text = [word.lower() for word in word_tokenizer.tokenize(text)]
    text_feats = sentim_analyzer.apply_features([tokenized_text], labeled=False)
    print(sentim_analyzer.classifier.classify(text_feats[0]))

def demo_liu_hu_lexicon(sentence, plot=False):
    """
    Very basic example of sentiment classification using Liu and Hu opinion lexicon
    """
    from nltk.corpus import LazyCorpusLoader
    from nltk.corpus import OpinionLexiconCorpusReader
    from nltk.tokenize import treebank

    opinion_lexicon = LazyCorpusLoader('opinion_lexicon', OpinionLexiconCorpusReader,
                                       r'(\w+)\-words\.txt', encoding='ISO-8859-2')

    tokenizer = treebank.TreebankWordTokenizer()
    pos_words = 0
    neg_words = 0
    tokenized_sent = [word.lower() for word in tokenizer.tokenize(sentence)]

    x = list(range(len(tokenized_sent))) # x axis for the plot
    y = []

    for word in tokenized_sent:
        if word in opinion_lexicon.positive():
            pos_words += 1
            y.append(1) # positive
        elif word in opinion_lexicon.negative():
            neg_words += 1
            y.append(-1) # negative
        else:
            y.append(0) # neutral


    if pos_words > neg_words:
        print('Positive')
    elif pos_words < neg_words:
        print('Negative')
    elif pos_words == neg_words:
        print('Neutral')

    if plot == True:
        try:
            _show_plot(x, y, x_labels=tokenized_sent, y_labels=['Negative', 'Neutral', 'Positive'])
        except NameError:
            print("matplotlib not installed. Graph generation not available.")

def demo_vader(text):
    from vader import SentimentIntensityAnalyzer
    sia = SentimentIntensityAnalyzer()
    print(sia.polarity_scores(text))


if __name__ == '__main__':
    from nltk.classify import NaiveBayesClassifier, MaxentClassifier
    from nltk.classify.scikitlearn import SklearnClassifier
    from sklearn.svm import LinearSVC

    naive_bayes = NaiveBayesClassifier.train
    svm = SklearnClassifier(LinearSVC()).train
    maxent = MaxentClassifier.train

    # demo_tweets(naive_bayes, n=80)
    # demo_movie_reviews(svm)
    # demo_subjectivity(svm)
    # demo_sent_subjectivity("she's an artist , but hasn't picked up a brush in a year . ")
    # demo_liu_hu_lexicon("This movie was actually neither that funny, nor super witty.", plot=True)
    demo_vader("This movie was actually neither that funny, nor super witty.")
