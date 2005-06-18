import time
import nltk.corpus
from nltk.token import Token
from nltk.tokenizer import RegexpTokenizer
from nltk.stemmer.porter import PorterStemmer
from documentfeature import *
from knnclassifier import *
from naivebayes import *

# ensure twenty newsgroups is installed
tn = nltk.corpus.twenty_newsgroups
assert tn.installed() != 0, 'Twenty-newsgroups is not installed!'

def Groups():
    """
    Get all group names in twenty newsgroups
    """
    return tn.groups()

def Items(group):
    """
    Get all file names in the specified group.
    This is the substitute function of tn.items() because it does not work.
    """
    return tn._find_files(tn.path('') + group + '/')

def Read(group, item):
    """
    Read the item in the group. Return the Token with TEXT set to the
    content and the CLASS set to the newsgroup name.
    """
    return Token(TEXT=tn.open(group + "/" + item).read(), CLASS=group)

######################################################################
## Demo: Text classification for newsgroup articles
######################################################################
def demo():
    """
    Demonstration program for classifying articles from twenty newsgroups
    using kNN and Naive Bayes classification.
    """
    # read newsgroups
    print 'reading newsgroups........'
    groups = Groups()[:10]                # use first 10 groups
    print "Possible categories: ", groups
    
    train = []; test = []
    for grp in groups:
        for itm in Items(grp)[:100]:     # read from each group as training data
            train.append(Read(grp, itm))
        for itm in Items(grp)[100:110]:  # read from each group as testing data
            test.append(Read(grp, itm))

    # detect features
    print 'detecting features....'
    detector = DocumentFeatureDetector(RegexpTokenizer(r'\w+'), PorterStemmer())
    for tok in train: detector.detect_features(tok)
    for tok in test:  detector.detect_features(tok)

    # encode features (just for knn)
    print 'encoding features.....'
    encoder = TFIDFFeatureEncoder(train, term_scheme='aug', doc_scheme='log')
    for tok in train: encoder.encode_features(tok)
    for tok in test:  encoder.encode_features(tok)

    # creating classifier (training for bayes)
    print 'start bayes training........'; t = time.clock()
    bayes_classifier = NaiveBayesDocumentClassifierTrainer().train(train)
    print 'bayes training took', int(time.clock() - t), 'seconds'
    knn_classifier = KNNClassifier(train, k=5)

    # matching, bayes
    print 'start bayes matching........'; t = time.clock()
    match = 0
    for tok in test:
        if bayes_classifier.get_class(tok) == tok['CLASS']: match = match + 1
    print match, 'bayes matched out of', len(test)
    print 'bayes matching took', int(time.clock() - t), 'seconds'

    # matching, knn
    print 'start knn matching........'; t = time.clock()
    match = 0
    for tok in test:
        if knn_classifier.get_class(tok) == tok['CLASS']: match = match + 1
    print match, 'knn matched out of', len(test)
    print 'knn matching took', int(time.clock() - t), 'seconds'

if __name__ == '__main__': demo()    
