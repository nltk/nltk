# Natural Language Toolkit: Naive Bayes Classifiers
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""

                     P(class) * P(features|class)
P(class|features) = ------------------------------
                           P(features)

"""

from nltk.classifier import *
from nltk.feature import *
from nltk.probability import *
from nltk.token import Token
from nltk.corpus import brown
from nltk.chktype import chktype as _chktype
import types

##//////////////////////////////////////////////////////
##  Naive Bayes Classifier
##//////////////////////////////////////////////////////

class NaiveBayesClassifier(ClassifierI, PropertyIndirectionMixIn):
    def __init__(self, class_probdist, feature_probdist, **property_names):
        """
        @param class_probdist: P(cls)
        @param feature_probdist: P(fval|cls,fid)
        """
        PropertyIndirectionMixIn.__init__(self, **property_names)
        self._class_probdist = class_probdist
        self._feature_probdist = feature_probdist
        self._classes = class_probdist.samples()

    def classes(self):
        return self._classes

    def classify(self, token):
        # Get the token's features.
        FEATURES = self.property('FEATURES')
        CLASS_PROBS = self.property('CLASS_PROBS')
        CLASS = self.property('CLASS')

        # Find the log probabilty of each class, given the features.
        logprob_dict = {}
        for cls in self._classes:
            logprob_dict[cls] = self._class_probdist.logprob(cls)
        for (cls, fname) in self._feature_probdist.conditions():
            probdist = self._feature_probdist[cls, fname]
            if fname not in token[FEATURES]: continue # [XX] is this right?
            fval = token[FEATURES][fname]
            logprob_dict[cls] += probdist.logprob(token[FEATURES][fname])

        probs = DictionaryProbDist(logprob_dict, normalize=True, log=True)
        token[CLASS_PROBS] = probs
        token[CLASS] = probs.max()

##//////////////////////////////////////////////////////
##  Naive Bayes Classifier Trainer
##//////////////////////////////////////////////////////

class NaiveBayesClassifierTrainer(ClassifierTrainerI,
                                  PropertyIndirectionMixIn):
    
    def train(self, tokens):
        FEATURES = self.property('FEATURES')
        CLASS = self.property('CLASS')
        
        class_freqdist = FreqDist()
        feature_freqdist = ConditionalFreqDist()
        feature_values = {}

        for token in tokens:
            cls = token[CLASS]
            class_freqdist.inc(cls)
            for fname, fval in token[FEATURES].items():
                # Recod the value in the freq(fval|cls, fname) distribution.
                feature_freqdist[cls, fname].inc(fval)
                # Record that fname can take the value fval.
                if fname not in feature_values: feature_values[fname] = Set()
                feature_values[fname].add(fval)

        # Create the P(cls) distribution
        class_probdist = ELEProbDist(class_freqdist)

        # Create the P(fval|cls, fname) distribution
        def make_probdist(freqdist, (cls, fname)):
            return ELEProbDist(freqdist, bins=len(feature_values[fname]))
        feature_probdist = ConditionalProbDist(feature_freqdist, make_probdist, True)

        # [xx] property indirection?
        return NaiveBayesClassifier(class_probdist, feature_probdist)
        
##//////////////////////////////////////////////////////
##  Multinomial play
##//////////////////////////////////////////////////////

# Features can fire multiple times.  Probability that a feature fires
# n times is p^n, where p is the probability that it fires once.  So
# we already know E(u)/n.  That's the freq dist we made.  Well,
# kinda...  Not really.  But to do that, we just need to inc by val,
# not by 1, in NaiveBayesClassifierFreqDist.

# So then we have E(fid)/n.  That is, p(fid).  So when we're asked to
# estimate P(id=val), take P(id=1)^val...

# Doing this to the freq-dist streight is playing a little fast &
# loose, though..  But doing it in a wrapper pdf seems fine.
# Hm.. still might be tricky, though.  I'll have to think about it.

#from math import exp
#class _MultinomialNaiveBayesClassifierProbDist(ProbDistI):
#    """
#    This class is not currently functional.
#    """
#    def __init__(self, fd_list, labeled_tokens, l=0.5):
#        fcounts = zeros(len(fd_list), 'd')
#        self._N = 0
#        fcounts += l
#        self._N += l*len(fcounts)
#
#        for tok in labeled_tokens:
#            self._N += 1
#            for (fid, val) in fd_list.detect(tok.type()).assignments():
#                fcounts[fid] += val
#
#        # Expected value for each feature
#        self._exp = fcounts / self._N
#
#    def prob(self, event):
#        # Inherit docs from FreqDistI
#        _chktype('NaiveBayesClassifierFreqDist.freq', 1, event, (AssignmentEvent,))
#        (fid, value) = event.assignment()
#
#        # valfact = value!
#        valfact = reduce( lambda x,y:x*y, range(2,value+1), 1.0 )
#
#        multinomial = ((self._exp[fid] ** value) / valfact)
#        poisson = ((self._exp[fid] ** value) * exp(-self._exp[fid]) /
#                   valfact)
#        return poisson
#
#class _MultinomialNaiveBayesClassifierTrainer(ClassifierTrainerI):
#    """
#    This class is not currently functional.
#    """
#    def __init__(self, fd_list):
#        self._fd_list = fd_list
#
#    def train(self, labeled_tokens, **kwargs):
#        labels = None
#        for (key, val) in kwargs.items():
#            if key == 'labels': labels = val
#            else: raise TypeError('Unknown keyword arg %s' % key)
#        if labels is None:
#            labels = find_labels(labeled_tokens)
#                
#        probdist = MultinomialNaiveBayesClassifierProbDist(self._fd_list,
#                                                   labeled_tokens)
#        return NaiveBayesClassifier(self._fd_list, labels, probdist)
#
#    def __repr__(self):
#        return '<NaiveBayesClassifierTrainer: %d features>' % len(self._fd_list)


##//////////////////////////////////////////////////////
##  Test code
##//////////////////////////////////////////////////////

from nltk.feature import *
from nltk.feature.word import *

def demo():
    import nltk.corpus
    
    # Load the training data, and split it into test & train.
    print 'reading data...'
    toks = []
    for item in nltk.corpus.brown.items()[:30]:
        text = nltk.corpus.brown.tokenize(item, addcontexts=True)
        toks += text['SUBTOKENS']
    toks = toks
    split = len(toks)-20
    train, test = toks[:split], toks[split:]

    # We're using TAG as our CLASS
    for tok in toks:
        cls = tok['TAG']
        if '-' in cls and cls != '--': cls = cls.split('-')[0]
        if '+' in cls: cls = cls.split('+')[0]
        tok['CLASS'] = cls

    # Create the feature detector.
    detector = MergedFeatureDetector(
        TextFeatureDetector(),                 # word's text
        ContextWordFeatureDetector(offset=-1), # previous word's text
        ContextWordFeatureDetector(offset=1),  # next word's text
        )

    # Run feature detection on the training data.
    print 'feature detection...'
    for tok in train: detector.detect_features(tok)

    # Train a new classifier
    print 'training...'
    classifier = NaiveBayesClassifierTrainer().train(train)

    # Use it to classify the test words.
    print 'classifying...'
    print
    print 'correct? |     token     | cls | class distribution'
    print '---------+---------------+-----+-------------------------------------'
    for tok in test:
        s = '%22s' % tok.exclude('CONTEXT', 'CLASS')
        c = tok['CLASS']
        detector.detect_features(tok)
        classifier.classify(tok)
        if c == tok['CLASS']: s = '   '+s
        else: s = '[X]' + s
        s += ' %-4s  ' % tok['CLASS']
        pdist = tok['CLASS_PROBS']
        probs = [(pdist.prob(val),val) for val in pdist.samples()]
        
        probs.sort(); probs.reverse()
        for prob,val in probs[:3]:
            s += '%5s=%.3f' % (val,prob)
        print s + ' ...'
    
if __name__ == '__main__': demo()
