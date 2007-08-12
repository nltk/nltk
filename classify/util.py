# Natural Language Toolkit: Classifier Utility Functions
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au> (minor additions)
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Utility functions for classifiers.
"""

######################################################################
#{ Feature Encodings
######################################################################

class SparseVectorEncodingI:
    """
    A feature encoding which maps feature dictionaries to vectors with
    a fixed length.  Since these vectors are typically zero at most
    locations, they are encoded in a sparse format.  In particular,
    the L{encode()} method converts a feature dictionary to a list of
    C{(index, value)} tuples, specifying the location and value of
    each non-zero vector component.  The length of the sparsely
    encoded vector is specified by the L{length()} method.
    """
    def encode(self, feature_dict):
        """
        Given a feature dictionary, return a corresponding sparse
        vector.  This sparse vector is encoded as a list of C{(index,
        value)} tuples, specifying the location and value of each
        non-zero vector component.  The length of this sparse vector
        can be found using the L{length()} method.
        
        @type feature_dict: C{dict}
        @rtype: C{list} of C{(int, number)}
        """

    def length(self):
        """
        @return: The size of the fixed-length vectors that are
        generated by this encoding.
        @rtype: C{int}
        """
        raise AssertionError('Not implemented')

class SparseBinaryVectorEncoding(SparseVectorEncodingI):
    """
    A sparse vector encoding which contains a single index for each
    possible feature value.  When used to encode a feature dictionary,
    the sparse vector will contain C{1} at the indices corresponding
    to feature values in the feature dictionary; and C{0} at all other
    indices.

    The feature value C{None} is used for 'unseen feature values' --
    if there is no index corresponding with a given feature value,
    then the encoding will instead use an index corresponding to the
    feature value of C{None} for the given feature.
    """
    def __init__(self, mapping, include_alwayson=True):
        """
        Construct a new sparse binary vector encoding, based on a
        dictionary mapping from C{(feature_name,feature_value)} tuples
        to sparse vector indices.

        @param include_alwayson: If true, then add an extra index which
            will always have a value of 1 for inputs.

        @require: The values of C{mapping} must be exactly the set of
            integers from 0 through C{len(mapping)}.  I.e.:

            >>> set(mapping.values()) == set(range(len(mapping)))
        """
        if set(mapping.values()) != set(range(len(mapping))):
            raise ValueError('Mapping values must be exactly the '
                             'set of integers from 0...len(mapping)')
        self._mapping = mapping # maps (fname,fval) -> fid
        self._alwayson = include_alwayson

    def encode(self, feature_dict):
        # Inherit docs.
        encoding = []
        for fname, fval in feature_dict.items():
            if (fname, fval) in self._mapping:
                encoding.append( (self._mapping[fname, fval], 1) )
            elif (fname, None) in self._mapping:
                #print 'unseen feature', (fname, fval)
                encoding.append( (self._mapping[fname, None], 1) )
        if self._alwayson:
            encoding.append( (len(self._mapping), 1) )
        return encoding

    def length(self):
        if self._alwayson:
            return len(self._mapping)+1
        else:
            return len(self._mapping)

    @classmethod
    def train(this_class, feature_dicts):
        """
        Construct and return a new sparse binary vector encoding,
        based on the given list of feature dictionaries.  In
        particular, the new encoding will contain a single index for
        each feature value seen in the given list of feature
        dictionaries; and an additional index for each feature name,
        which is reserved for unseen feature values.  (Unseen feature
        values are encoded using a value of C{None}.)
        """
        mapping = {}
        for (tok, label) in feature_dicts:
            for (fname, fval) in tok.items():
                if (fname, fval) not in mapping:
                    mapping[fname, fval] = len(mapping)
                if (fname, None) not in mapping:
                    mapping[fname, None] = len(mapping)
        return this_class(mapping)

class GISEncoding(SparseBinaryVectorEncoding):
    """
    A sparse binary vector encoding which adds two new indices, in
    addition to the indices for individual feature values:

      - An index which always has a value of 1.
      - An correction index, whose value is chosen to ensure that
        the sparse vector always sums to a constant non-negative
        number.

    These two new indices are used to ensure two preconditions for the
    GIS training algorithm:

      - At least one feature vector index must be nonzero for every
        token.
      - The feature vector must sum to a constant non-negative number
        for every token.
    """
    def __init__(self, mapping, C=None):
        SparseBinaryVectorEncoding.__init__(self, mapping, True)
        if C is None:
            self._C = len(set([fname for (fname,fval) in mapping]))+1
        else:
            self._C = C

    def C(self):
        """Return the non-negative constant that all encoded feature
        vectors will sum to."""
        return self._C

    def encode(self, feature_dict):
        encoding = SparseBinaryVectorEncoding.encode(self, feature_dict)
        # Add a correction feature.
        total = sum([v for (f,v) in encoding])
        if total > self._C:
            #print total, self._C, encoding
            raise ValueError('Correction feature is not high enough!')
        encoding.append( (len(self._mapping)+1, self._C-total) )
        # Return the result
        return encoding

    def length(self):
        return len(self._mapping) + 2
        
                

######################################################################
#{ Helper Functions
######################################################################

def attested_labels(tokens):
    """
    @return: A list of all labels that are attested in the given list
        of tokens.
    @rtype: C{list} of (immutable)
    @param tokens: The list of classified tokens from which to extract
        labels.  A classified token has the form C{(token, label)}.
    @type tokens: C{list}
    """
    return tuple(set([label for (tok,label) in tokens]))

def classifier_log_likelihood(classifier, gold):
    results = classifier.probdist([fs for (fs,l) in gold])
    ll = [pdist.prob(l) for ((fs,l), pdist) in zip(gold, results)]
    return float(sum(ll))/len(ll)

def classifier_accuracy(classifier, gold):
    results = classifier.classify([fs for (fs,l) in gold])
    correct = [l==r for ((fs,l), r) in zip(gold, results)]
    return float(sum(correct))/len(correct)

######################################################################
#{ Demos
######################################################################

def names_demo_features(name):
    features = {}
    features['alwayson'] = True
    features['startswith'] = name[0].lower()
    features['endswith'] = name[-1].lower()
    for letter in 'abcdefghijklmnopqrstuvwxyz':
        features['count(%s)' % letter] = name.lower().count(letter)
        features['has(%s)' % letter] = letter in name.lower()
    return features

def binary_names_demo_features(name):
    features = {}
    features['alwayson'] = True
    features['startswith(vowel)'] = name[0].lower() in 'aeiouy'
    features['endswith(vowel)'] = name[-1].lower() in 'aeiouy'
    for letter in 'abcdefghijklmnopqrstuvwxyz':
        features['count(%s)' % letter] = name.lower().count(letter)
        features['has(%s)' % letter] = letter in name.lower()
        features['startswith(%s)' % letter] = (letter==name[0].lower())
        features['endswith(%s)' % letter] = (letter==name[-1].lower())
    return features

def names_demo(trainer, features=names_demo_features):
    from nltk.corpus import names
    import random

    # Construct a list of classified names, using the names corpus.
    namelist = ([(name, 'male') for name in names.words('male')] + 
                [(name, 'female') for name in names.words('female')])

    # Randomly split the names into a test & train set.
    random.seed(123456)
    random.shuffle(namelist)
    train = namelist[:5000]
    test = namelist[5000:5500]

    # Train up a classifier.
    print 'Training classifier...'
    classifier = trainer( [(features(n), g) for (n,g) in train] )

    # Run the classifier on the test data.
    print 'Testing classifier...'
    acc = classifier_accuracy(classifier, [(features(n),g) for (n,g) in test])
    print 'Accuracy: %6.4f' % acc

    # For classifiers that can find probabilities, show the log
    # likelihood and some sample probability distributions.
    try:
        test_featuresets = [features(n) for (n,g) in test]
        pdists = classifier.probdist(test_featuresets)
        ll = [pdist.logprob(gold)
              for ((name, gold), pdist) in zip(test, pdists)]
        print 'Avg. log likelihood: %6.4f' % (sum(ll)/len(test))
        print
        print 'Unseen Names      P(Male)  P(Female)\n'+'-'*40
        for ((name, gender), pdist) in zip(test, pdists)[:5]:
            if gender == 'male':
                fmt = '  %-15s *%6.4f   %6.4f'
            else:
                fmt = '  %-15s  %6.4f  *%6.4f'
            print fmt % (name, pdist.prob('male'), pdist.prob('female'))
    except NotImplementedError:
        pass
    
    # Return the classifier
    return classifier

_inst_cache = {}
def wsd_demo(trainer, word, features, n=1000):
    from nltk.corpus import senseval
    import random

    # Get the instances.
    print 'Reading data...'
    global _inst_cache
    if word not in _inst_cache:
        _inst_cache[word] = [(i, i.senses[0]) for i in senseval.instances(word)]
    instances = _inst_cache[word][:]
    if n> len(instances): n = len(instances)
    senses = list(set(l for (i,l) in instances))
    print '  Senses: ' + ' '.join(senses)

    # Randomly split the names into a test & train set.
    print 'Splitting into test & train...'
    random.seed(123456)
    random.shuffle(instances)
    train = instances[:int(.8*n)]
    test = instances[int(.8*n):n]

    # Train up a classifier.
    print 'Training classifier...'
    classifier = trainer( [(features(i), l) for (i,l) in train] )

    # Run the classifier on the test data.
    print 'Testing classifier...'
    acc = classifier_accuracy(classifier, [(features(i),l) for (i,l) in test])
    print 'Accuracy: %6.4f' % acc

    # For classifiers that can find probabilities, show the log
    # likelihood and some sample probability distributions.
    try:
        test_featuresets = [features(i) for (i,n) in test]
        pdists = classifier.probdist(test_featuresets)
        ll = [pdist.logprob(gold)
              for ((name, gold), pdist) in zip(test, pdists)]
        print 'Avg. log likelihood: %6.4f' % (sum(ll)/len(test))
    except NotImplementedError:
        pass
    
    # Return the classifier
    return classifier

