######################################################################
##
##  Guess an unseen name's gender!
##

from nltk.classify.naivebayes import NaiveBayesClassifier
from nltk.classify.util import names_demo

# Feature Extraction:
def name_features(name):
    features = {}
    return features

# Test the classifier:
classifier = names_demo(NaiveBayesClassifier.train, name_features)

# Feature Analysis:
#classifier.show_most_informative_features()
