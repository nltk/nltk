# Natural Language Toolkit: Naive Bayes Classifiers
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

from nltk.classifier import *
from nltk.probability import SimpleFreqDist
from nltk.probability import CFFreqDist, CFSample, ContextEvent
from nltk.probability import MLEProbDist
from nltk.probability import ProbDistI, EventI
from nltk.token import Token, WSTokenizer
from nltk.chktype import chktype as _chktype

from Numeric import zeros

##//////////////////////////////////////////////////////
##  Naive Bayes PDist
##//////////////////////////////////////////////////////

class NBProbDist(ProbDistI):
    def __init__(self, events):
        self._events = events
        self._counts = zeros(len(events))
        self._N = 0
        self._freqs = None

    def inc(self, sample):
        for i in range(len(self._events)):
            if sample in self._events[i]:
                self._counts[i] += 1
        self._N += 1
        self._freqs = None

    def _cache(self):
        #print
        #print 'counts', self._counts
        #print 'N', self._N
        self._freqs = self._counts / float(self._N)
        #print 'freqs', self._freqs

    def prob(self, sample):
        p = 1.0
        if self._freqs is None: self._cache()
        for i in range(len(self._events)):
            if sample in self._events[i]:
                #print 'prob(%s)=%s' % (self._events[i], self._freqs[i])
                p *= self._freqs[i]
        #print 'prob(%s)=%s' % (sample, p)
        return p

##//////////////////////////////////////////////////////
##  Naive Bayes Classifier
##//////////////////////////////////////////////////////

class LabelFeaturesSample:
    def __init__(self, label, features):
        self._label = label
        self._features = features

    def label(self): return self._label
    def features(self): return self._features

class FeatureEvent(EventI):
    def __init__(self, feature):
        self._feature = feature

    def feature(self): return self._feature

    def __contains__(self, sample):
        return self._feature in sample.features()

class ContainsEvent(EventI):
    def __init__(self, val):
        self._val = val
    def __contains__(self, sample):
        return self._val in sample

class LabelEvent(EventI):
    def __init__(self, label):
        self._label = label

    def label(self): return self._label

    def __contains__(self, sample):
        return self._label == sample.label()

class NBProbDistFoo(ProbDistI):
    """
    Calculates P(abcd) as P(a)P(b)P(c)P(d), where abcd are features..

    Samples are tuples of features.  Features are ints from 0..B
    """
    def __init__(self, B):
        self._B = B
        self._counts = zeros(B)
        self._freqs = None
        self._N = 0

    def inc(self, sample):
        for feature in sample:
            self._counts[feature] += 1
        self._N += 1
        self._freqs = None

    def cache(self):
        self._freqs = self._counts / float(N)

    def prob(self, sample_or_event):
        # Expect a list of features.
        p = 1.0
        for feature in sample:
            p *= self._freqs[feature]
        return p
            
        

    

##//////////////////////////////////////////////////////
##  Naive Bayes Classifier
##//////////////////////////////////////////////////////

class NBClassifier(ClassifierI):
    """
    A Naive Bayes classifier::

      P(inst, label) = P(label) P(f0|label) P(f1|label) ... P(fn|label)

    Where fi are the features that fired.

    Model parameters:
      - PDF for labels
      - PDF for feature|label
    """
    def __init__(self, featurelist, labels, label_pdist, feature_pdists):
        self._featurelist = featurelist
        self._labels = labels
        self._label_pdist = label_pdist
        self._feature_pdists = feature_pdists

    def prob(self, labeled_token):
        """
        Find the probability of the given labeled instance, using the
        naive bayes assumption.
        """
        labeled_type = labeled_token.type()
        label = labeled_type.label()
        text = labeled_type.base()
        feature_pdist = self._feature_pdists[label]
        
        p = self._label_pdist.prob(label)
        p *= feature_pdist.prob(self._featurelist.detect(text))

        if p > 0:
            print "P(%s) = %s" % (label, p)
        return p

    def classify(self, token):
        max_p = -1
        max_label = None
        for label in self._labels:
            labeled_tok = Token(LabeledType(token.type(), label),
                                token.loc())
            p = self.prob(labeled_tok)
            if p > max_p:
                max_p = p
                max_label = label
        return max_label

##//////////////////////////////////////////////////////
##  Naive Bayes Classifier Factory
##//////////////////////////////////////////////////////

class NBClassifierFactory(ClassifierFactoryI):
    def __init__(self, features):
        self._features = features

    def create(self, labeled_tokens):
        events = [ContainsEvent(i) for i in range(len(self._features))]
                
        label_fdist = SimpleFreqDist()
        feature_pdists = {}
        
        for labeled_token in labeled_tokens:
            labeled_type = labeled_token.type()
            label = labeled_type.label()
            text = labeled_type.base()

            label_fdist.inc(label)
            features = self._features.detect(text)
            if not feature_pdists.has_key(label):
                feature_pdists[label] = NBProbDist(events)
            feature_pdists[label].inc(features)

        label_pdist = MLEProbDist(label_fdist)
        return NBClassifier(self._features, label_fdist.samples(),
                            label_pdist, feature_pdists)
            
##//////////////////////////////////////////////////////
##  Test code
##//////////////////////////////////////////////////////

if __name__ == '__main__':
    from nltk.tagger import TaggedTokenizer
    file = '/mnt/cdrom2/data/brown/ca01'
    text = open(file).read()
    
    ttoks = TaggedTokenizer().tokenize(text)
    
    features = (
        AlwaysFeatureList() +
        FunctionFeatureList(lambda w:w[0],
                           [chr(i) for i in range(ord('a'), ord('z'))]) +
        FunctionFeatureList(lambda w:w[-1],
                           [chr(i) for i in range(ord('a'), ord('z'))]) +
        FunctionFeatureList(lambda w:len(w), range(15)) +
        ValueFeatureList(("Atlanta's",))
        )

    factory = NBClassifierFactory(features)

    labeled_tokens = [Token(LabeledType(tok.type().base(),
                                           tok.type().tag()),
                               tok.loc())
                         for tok in ttoks]
    
    print 'training...'
    classifier = factory.create(labeled_tokens)
    print 'done training'
    
    print ('%d tokens, %d labels' % (len(labeled_tokens), 
                                     len(classifier._labels)))
    t = time.time()
    toks = WSTokenizer().tokenize("jury the reports taasd aweerdr "+
                                  "Atlanta's")
    
    #import time
    #for i in range(20):
    #    for word in toks:
    #        classifier.classify(word)
    #print '100 classifications: %0.4f secs' % (time.time()-t)
            
    for word in toks:
        print word
        label = classifier.classify(word)
        print '  =>', label
        

    
    

    

