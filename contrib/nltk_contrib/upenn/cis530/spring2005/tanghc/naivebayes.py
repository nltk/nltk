from nltk import PropertyIndirectionMixIn
from nltk.token import Token
from nltk.feature import *
from nltk.probability import *
from nltk.classifier import *

######################################################################
## Trainer
######################################################################
class NaiveBayesDocumentClassifierTrainer(ClassifierTrainerI,
                                          PropertyIndirectionMixIn):
    """
    Inherits nltk.classifier.ClassifierTrainerI and serves as the easier way to
    construct a NaiveBayesDocumentClassifier object. For more information please
    see NaiveBayesDocumentClassifier.
    """
    def __init__(self, **property_names):
        PropertyIndirectionMixIn.__init__(self, **property_names)
    
    def train(self, tokens):
        """
        Training process for creating the classifier. All tokens are parsed and
        both class and word frequencies are recorded.

        @param tokens: a list of nltk.token.Token objects with property FEATURES
            which is a dictionary with key BOW and value a list of string and
            property CLASS which is the class the token belongs to.
        @rtype: NaiveBayesDocumentClassifier
        @return: the classifier
        """
        class_freq_dist = FreqDist()
        word_freq_dist = FreqDist()
        class_word_freq_dist = ConditionalFreqDist()
        for tok in tokens:
            class_freq_dist.inc(tok['CLASS'])
            for word in Set(tok['FEATURES']['BOW']):
                class_word_freq_dist[tok['CLASS']].inc(word)
                word_freq_dist.inc(word)

        return NaiveBayesDocumentClassifier(class_freq_dist,
                                            class_word_freq_dist)


######################################################################
## Classifier
######################################################################
class NaiveBayesDocumentClassifier(ClassifierI, PropertyIndirectionMixIn):
    """
    Inherits nltk.classifier.ClassifierI, implementing the naive bayes algorithm
    to do the text classification, primarily for document classification.
    Namely,
        class(d) = argmax(c) { log P(c) + sigma { log P(x|c) | x in d } }
    where c is all classes and x is all words (subtokens) in the document.
    
    The original nltk.classifier.naivebayes.NaiveBayesClassifier in nltk 1.4.3
    is both faulty and cannot deal with documents -- which could have unfixed
    number of features (depending on number of words). This class tries to fix
    this problem.

    Similar from other classifiers defined in nltk.classifier, this classifier
    classifies nltk.token.Token objects with FEATURE property. However, it is
    required that the FEATURE property should be a dictionary with one key 'BOW'
    and its corresponding value a bag of words, which is a list of string.

    It is recommended to use NaiveBayesDocumentClassifierTrainer to generate
    the classifier instead of constructing it explicitly.

    Example:
        train = [ some tokens with TEXT and CLASS property ]
        test = [ some other tokens with TEXT property ]
        detector = DocumentFeatureDetector()
        for tok in train: detector.detect_features(tok)
        for tok in test:  detector.detect_features(tok)

        bayes_classifier = NaiveBayesDocumentClassifierTrainer().train(train)
        for tok in test: print bayes_classifier.get_class(tok)
    """
    def __init__(self, class_freq_dist, class_word_freq_dist, **property_names):
        """
        Construct the Naive Bayes classifier object. Again, it is recommended to
        use NaiveBayesDocumentClassifierTrainer().train() to generate the
        classifier.

        @param class_freq_dist: an nltk.probability.FreqDist object which stores
            each class's frequency
        @param class_word_freq_dist: an nltk.probability.ConditionalFreqDist
            object which stores each word's frequency given a class name.
        """
        PropertyIndirectionMixIn.__init__(self, **property_names)
        self._class_freq_dist = class_freq_dist
        self._class_prob_dist = MLEProbDist(class_freq_dist)
        self._class_word_freq_dist = class_word_freq_dist

    def classes(self):
        """
        Lists the possible classes for classification.
        @rtype: list of string
        @return: the list of possible classes
        """
        return self._class_freq_dist.samples()

    def get_class_scores(self, token):
        """
        Get the score for the token classified to each classes. This is the
        function implementing Naive Bayes algorithm. All scores are negative
        due to log likelihood. However, the greatest value (closest to zero)
        still represents the highest probability.
        
        @param token: an object of type nltk.token.Token with property FEATURES
            which is a dictionary with key BOW and value a list of string.
        @rtype: dict
        @return: all classes and their scores (all negative)
        """
        class_prob = {}
        for cls in self.classes():
            # P(c) = documents in category / all documents
            log_likelihood = self._class_prob_dist.logprob(cls)
            # P(x | c) = number of docs containing x in c / documents in c
            class_cnt = float(self._class_freq_dist.count(cls))
            for word in token['FEATURES']['BOW']:
                p = float(self._class_word_freq_dist[cls].count(word)) \
                / class_cnt
                assert p <= 1
                if p > 0: log_likelihood += math.log(p)
                else: log_likelihood += -30     # log(0) = neg infinite, we just
                                                # choose a small number instead
            class_prob[cls] = log_likelihood

        return class_prob

    def get_class(self, token):
        """
        Get the most probable classification for the given token. Simply calls
        get_class_scores() and picks up the greatest value.
        
        @param token: an object of type nltk.token.Token with property
            FEATURES which is a dictionary with key BOW and value a list
            of string.
        @rtype: string
        @return: the most probable classification for the given token
        """
        classes = self.get_class_scores(token)
        return max([(s, c) for (c, s) in classes.items()])[1]

    def classify(self, token):
        """
        Get the most probable classification for the given token by calling
        get_class() and store the result to the token's CLASS property.
        
        @param token: an object of type nltk.token.Token with at least one
            property FEATURE_VECTOR which is a SparseList and is normalized.        
        """
        token['CLASS'] = self.get_class(token)
