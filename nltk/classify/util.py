# Natural Language Toolkit: Classifier Utility Functions
#
# Copyright (C) 2001-2009 NLTK Project
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au> (minor additions)
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Utility functions and classes for classifiers.
"""
import math

#from nltk.util import Deprecated
import nltk.classify.util # for accuracy & log_likelihood
from nltk.util import LazyMappedList

######################################################################
#{ Helper Functions
######################################################################

# alternative name possibility: 'map_featurefunc()'?
# alternative name possibility: 'detect_features()'?
# alternative name possibility: 'map_featuredetect()'?
# or.. just have users use LazyMappedList directly?
def apply_features(feature_func, toks, labeled=None):
    """
    Use the L{LazyMappedList} class to construct a lazy list-like
    object that is analogous to C{map(feature_func, toks)}.  In
    particular, if C{labeled=False}, then the returned list-like
    object's values are equal to::

        [feature_func(tok) for tok in toks]

    If C{labeled=True}, then the returned list-like object's values
    are equal to::

        [(feature_func(tok), label) for (tok, label) in toks]

    The primary purpose of this function is to avoid the memory
    overhead involved in storing all the featuresets for every token
    in a corpus.  Instead, these featuresets are constructed lazily,
    as-needed.  The reduction in memory overhead can be especially
    significant when the underlying list of tokens is itself lazy (as
    is the case with many corpus readers).

    @param feature_func: The function that will be applied to each
        token.  It should return a featureset -- i.e., a C{dict}
        mapping feature names to feature values.
    @param toks: The list of tokens to which C{feature_func} should be
        applied.  If C{labeled=True}, then the list elements will be
        passed directly to C{feature_func()}.  If C{labeled=False},
        then the list elements should be tuples C{(tok,label)}, and
        C{tok} will be passed to C{feature_func()}.
    @param labeled: If true, then C{toks} contains labeled tokens --
        i.e., tuples of the form C{(tok, label)}.  (Default:
        auto-detect based on types.)
    """
    if labeled is None:
        labeled = toks and isinstance(toks[0], (tuple, list))
    if labeled:
        def lazy_func(labeled_token):
            return (feature_func(labeled_token[0]), labeled_token[1])
        return LazyMappedList(toks, lazy_func)
    else:
        return LazyMappedList(toks, feature_func)

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

def log_likelihood(classifier, gold):
    results = classifier.batch_prob_classify([fs for (fs,l) in gold])
    ll = [pdist.prob(l) for ((fs,l), pdist) in zip(gold, results)]
    return math.log(float(sum(ll))/len(ll))

def accuracy(classifier, gold):
    results = classifier.batch_classify([fs for (fs,l) in gold])
    correct = [l==r for ((fs,l), r) in zip(gold, results)]
    return float(sum(correct))/len(correct)

class CutoffChecker(object):
    """
    A helper class that implements cutoff checks based on number of
    iterations and log likelihood.

    Accuracy cutoffs are also implemented, but they're almost never
    a good idea to use.
    """
    def __init__(self, cutoffs):
        self.cutoffs = cutoffs.copy()
        if 'min_ll' in cutoffs:
            cutoffs['min_ll'] = -abs(cutoffs['min_ll'])
        if 'min_lldelta' in cutoffs:
            cutoffs['min_lldelta'] = abs(cutoffs['min_lldelta'])
        self.ll = None
        self.acc = None
        self.iter = 1
        
    def check(self, classifier, train_toks):
        cutoffs = self.cutoffs
        self.iter += 1
        if 'max_iter' in cutoffs and self.iter >= cutoffs['max_iter']:
            return True # iteration cutoff.
        
        if 'min_ll' in cutoffs or 'min_lldelta' in cutoffs:
            new_ll = nltk.classify.util.log_likelihood(classifier, train_toks)
            if 'min_ll' in cutoffs and new_ll >= cutoffs['min_ll']:
                return True # log likelihood cutoff
            if ('min_lldelta' in cutoffs and self.ll and
                ((new_ll - self.ll) <= abs(cutoffs['min_lldelta']))):
                return True # log likelihood delta cutoff
            self.ll = new_ll

        if 'max_acc' in cutoffs or 'min_accdelta' in cutoffs:
            new_acc = nltk.classify.util.log_likelihood(
                classifier, train_toks)
            if 'max_acc' in cutoffs and new_acc >= cutoffs['max_acc']:
                return True # log likelihood cutoff
            if ('min_accdelta' in cutoffs and self.acc and
                ((new_acc - self.acc) <= abs(cutoffs['min_accdelta']))):
                return True # log likelihood delta cutoff
            self.acc = new_acc

            return False # no cutoff reached.

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
    namelist = ([(name, 'male') for name in names.words('male.txt')] + 
                [(name, 'female') for name in names.words('female.txt')])

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
    acc = accuracy(classifier, [(features(n),g) for (n,g) in test])
    print 'Accuracy: %6.4f' % acc

    # For classifiers that can find probabilities, show the log
    # likelihood and some sample probability distributions.
    try:
        test_featuresets = [features(n) for (n,g) in test]
        pdists = classifier.batch_prob_classify(test_featuresets)
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
    acc = accuracy(classifier, [(features(i),l) for (i,l) in test])
    print 'Accuracy: %6.4f' % acc

    # For classifiers that can find probabilities, show the log
    # likelihood and some sample probability distributions.
    try:
        test_featuresets = [features(i) for (i,n) in test]
        pdists = classifier.batch_prob_classify(test_featuresets)
        ll = [pdist.logprob(gold)
              for ((name, gold), pdist) in zip(test, pdists)]
        print 'Avg. log likelihood: %6.4f' % (sum(ll)/len(test))
    except NotImplementedError:
        pass
    
    # Return the classifier
    return classifier

