from nltk import PropertyIndirectionMixIn
from nltk.token import Token
from nltk.feature import *
from nltk.classifier import *

def _similarity(token1, token2):
    """
    Measures the similarity of two feature vectors by calculating the cosine
    value between two vectors.
    Note that the tokens should have the property FEATURE_VECTOR which is a
    SparseList

    @param token1, token2: objects of type nltk.token.Token with a property
        FEATURE_VECTOR which is a nltk.util.SparseList
    @rtype: float
    @return: the similarity between two vectors measured by cosine.
    """
    sum = 0.0
    for (i, v) in token1['FEATURE_VECTOR'].assignments():
        sum += v * token2['FEATURE_VECTOR'].__getitem__(i)
    return sum

######################################################################
## Classifier
######################################################################
class KNNClassifier(ClassifierI, PropertyIndirectionMixIn):
    """
    Inherits nltk.classifier.ClassifierI, implementing k-nearest-neighbors
    algorithm to do text classification. We first keep some already classified
    tokens. Then for each unclassified token, we find a few classified tokens
    (k) which are 'most similar' to it, and classify it accordingly. 

    Namely, if we want to classify y based on training set X,
    we fist find k classified tokens with greatest similarity:
        set A = {x | x in X, sim(x, y) > sim(x', y) for all x' in (X-A)  }
        with size(A) = k.
    The score for y classified to class C is:
        score(C) = sum { sim(x, y) | x in A, x is classified to C }
    We simply classify y to:
        class(y) = argmax score(C)

    According to nltk 1.4 infrasturcture, classifiers do not implement feature
    detection/encoding in itself. Hence, this class only picks up similar tokens,
    and it does not involve the construction of feature vectors.

    It is recommended to use DocumentFeatureDetector and TFIDFFeatureEncoder
    to do the feature detecting/encoding work. However it is not required,
    every token with feature vector built in it can make use of this classifier.

    Example:
        train = [ some tokens with TEXT and CLASS property ]
        test = [ some other tokens with TEXT property ]
        detector = DocumentFeatureDetector()
        for tok in train: detector.detect_features(tok)
        for tok in test:  detector.detect_features(tok)

        encoder = TFIDFFeatureEncoder(train)
        for tok in train: encoder.encode_features(tok)
        for tok in test:  encoder.encode_features(tok)

        knn_classifier = KNNClassifier(train)
        for tok in test: knn_classifier.classify(tok)
    """
    def __init__(self, tokens, k=1, **property_names):
        """
        Construct the KNN classifier object. KNN classification does not really
        need a training process, so there is no corresponding Trainer class.
        However, some classified tokens still should be provided as training
        data.

        @param tokens: list of nltk.token.Token with at least two properties:
            FEATURE_VECTOR: a nltk.util.SparseList object, and the vector should
                            be normalized in advance.
            CLASS: the classification of the token.
        @param k: the parameter k in KNN. Specifies the number of nearest
            neighbors to look at.
        """
        PropertyIndirectionMixIn.__init__(self, **property_names)
        self._k = k
        self._train_tokens = tokens
        self._classes = Set()
        for tok in tokens:
            self._classes.add(tok['CLASS'])

    def classes(self):
        """
        Lists the possible classes for classification.
        @rtype: list of string
        @return: the list of possible classes
        """
        return list(self._classes)

    def get_class_scores(self, token):
        """
        Get the score for the token classified to each classes. All the tokens
        in the training set would be compared to this token. This is a rather
        slow function.
        
        @param token: an object of type nltk.token.Token with at least one
            property FEATURE_VECTOR which is a SparseList and is normalized.
        @rtype: dict
        @return: all classes and their scores if it's greater than zero
        """
        #record similarity for each training data and sort them
        sim_list = []
        for tok in self._train_tokens:
            sim_list.append((tok['CLASS'], _similarity(tok, token)))
        sorted_list = [(-s, t) for (t, s) in sim_list]
        sorted_list.sort()

        #pick up k highest neighbors and record their classes
        classes = {}
        for i in range(self._k):        # just look at k foremost tokens
            v = -sorted_list[i][0]      # we added negative sign in sorted_list
            c = sorted_list[i][1]
            classes[c] = classes.get(c, 0.0) + v

        return classes

    def get_class(self, token):
        """
        Get the most probable classification for the given token. Simply calls
        get_class_scores() and picks up the greatest value.
        
        @param token: an object of type nltk.token.Token with at least one
            property FEATURE_VECTOR which is a SparseList and is normalized.
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
