# Natural Language Toolkit: Naive Bayes Classifiers
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
A text classifier model based on the naive bayes assumption.  
In particular, this classifier assumes that each feature is
independant.  This assumption allows us to construct reliable
estimates of the probability that a given text has a given label.

See C{NBClassifier} for more information on the approximation
algorithms used by the classifier.

The Naive Bayes Classifier Model
================================

C{NBClassifier} is a naive bayes classifier model.  This model is
based on a C{ProbDist} whose samples are C{FeatureValueList}s.  It
uses this probability distribution to estimate the probability that a
given text should be classified with a label::

    P(label|text)

To form these estimates, it examines the probabilities of individual
feature-value assignments::

    P(fi=vi)

It uses C{AssignmentEvent}s to encode the event that a feature has a
given value.  An C{AssignmentEvent} is an event consisting of all
C{FeatureValueList}s that contain a given assignment.  The probability
distribution used to define a C{NBClassifier} should therefore be
capable of efficiently calculating the probability of
C{AssignmentEvent}s.

---- cut here ----

The Naive Bayes Classifier Frequency Distribution
=================================================
This module defines a frequency distribution, C{NBClassifierFreqDist},
which is designed to efficiently find the frequencies corresponding to
these probabilities.  In particular, it can efficiently calculate::

    fdist.freq(LabelEvent(...))
    fdist.cond_frob(AssignmentEvent(...), LabelEvent(...))

See C{NBClassifierFreqDist} for more information.

The Naive Bayes Classifier Trainer
==================================
C{NBClassifierTrainer} uses training data to construct a new
C{NBClassifier}.  From the training data, it builds a
C{NBClassifierFreqDist}.  This frequency distribution is used as the
basis for a probability distribution, which is used to construct the
C{NBClassifier}.

"""

from nltk.classifier import *
from nltk.probability import *
from nltk.token import Token, WSTokenizer
from nltk.chktype import chktype as _chktype

import time
from Numeric import zeros, product, nonzero, take

##//////////////////////////////////////////////////////
##  AssignmentEvent
##//////////////////////////////////////////////////////

class AssignmentEvent(EventI):
    """
    An event containing all C{FeatureValueList}s that contain a given
    assignment.  An assignment is an (id, value) pair which gives a
    feature identifier and the value of that feature.
    """
    def __init__(self, assignment):
        """
        Construct a new C{AssignmentEvent}, containing all
        C{FeatureValueList}s that contain C{assignment}.

        @param assignment: The assignment to check for.  This (id,
            value) pair specifies a feature's identifier and a value
            for that feature.  For Naive Bayes classifiers, values are
            treated as boolean values.
        @type assignment: C{tuple} of C{int} and (immutable)
        """
        self._assignment = assignment
        
    def assignment(self):
        """
        @return: the assignment that defines this C{AssignmentEvent}.
            This (id, value) pair specifies a feature's identifier and
            a value for that feature.  For Naive Bayes classifiers,
            values are treated as boolean values.
        @rtype assignment: C{tuple} of C{int} and (immutable)
        """
        return self._assignment
    def contains(self, sample):
        """
        @type sample: C{FeatureValueList}
        """
        # !!! This needs a real definition !!!
        (id, val) = self._assignment
        return (sample[id] == val)
    
    def __repr__(self):
        return ('{Event x: x=FeatureValueList' +
                ' with assignment %r}' % self._assignment)

##//////////////////////////////////////////////////////
##  Naive Bayes Classifier
##//////////////////////////////////////////////////////

class NBClassifier(ClassifierI):
    """

    A text classifier model based on the Naive Bayes assumption.  In
    particular, we assume that the feature value assignments of a
    given text are mutually independant.  This assumption justifies
    the following approximation for the probabilitiy of a labeled
    text:

      P(labeled_text) = P(f1=v1, f2=v2, ..., fn=vn)
                      = P(f1=v1) * P(f2=v2) * ... * P(fn=vn)

    Where C{fi=vi} are the feature values assignments for a given
    labeled text.  This approximation helps solve the sparse data
    problem, since our estimates for the probabilities of individual
    features (C{P(fi=vi)}) are much more reliable than our joint
    estimates for all features (C{P(f1=v1, f2=v2, ..., fn=vn)}).

    Using this approximation, we can find the most likely label for a
    given text::

                                                    P(labeled_text)
      ARGMAX[label] P(label|text) = ARGMAX[label] -------------------
                                                       P(text)
                                                       
                                  = ARGMAX[label] P(labeled_text)

    We can also use this approximation to find C{P(label|text)}::

                                      P(text, label=l)
      P(label=l|text) = ---------------------------------------------
                         P(text, label=l1) + ... + P(text, label=lm)
   
    Optimizations
    =============

    Factoring out zero-feature-values
    ---------------------------------
    The formula given above for estimating P(text, label) is
    inefficient for sparse feature value lists.  Since most feature
    value lists are sparse, we can improve performance by finding
    P(labeled_text) with the following equivalant formulation::

      P(f1=0, f2=0, ..., fn=0) = P(f1=0) * ... * P(fn=0)

      P(text, label) = P(f1=0, f2=0, ..., fn=0) * P(Fi=1)/P(Fi=0)

    Where C{Fi} are the set of features whose value is 1.  This
    reformulation is useful because C{P(f1=0, f2=0, ..., fn=0)} does
    not depend on the text in any way.  

    Note also that since C{P(f1=0, f2=0, ..., fn=0)} does not depend
    on the text in any way, we don't need to calculate it at all if we
    want to find the most likely label for a given text::

      ARGMAX[label] P(label|text)
              = ARGMAX[label] P(labeled_text)
              = ARGMAX[label] P(f1=0, f2=0, ..., fn=0) * P(Fi=1)/P(Fi=0)
              = ARGMAX[label] P(Fi=1)/P(Fi=0)

    Also, since we are normalizing C{P(label=l|text)} by summing over
    all values of l, we don't need to find C{P(f1=0, f2=0, ..., fn=0)}
    to calculate C{P(label|text)}:

                                      P(text, label=l)
      P(label=l|text) = ---------------------------------------------
                         P(text, label=l1) + ... + P(text, label=lm)

    Thus, we never actually need to find C{P(f1=0, f2=0, ..., fn=0)}. 
    """
    def __init__(self, featuredetectors, labels, pdist):
        """
        Construct a new Naive Bayes classifier model.  Typically, new
        classifier models are created by C{ClassifierTrainer}s.

        @type featuredetectors: C{FeatureDetectorListI}
        @param featuredetectors: The feature detector list defining
            the features that are used by the C{NBClassifier}.  This
            should be the same feature detector list that was used to
            construct the feature value lists that are the samples of
            C{pdist}.
        @type labels: C{list} of (immutable)
        @param labels: A list of the labels that should be considered
            by this C{NBClassifier}.  Typically, labels are C{string}s
            or C{int}s.
        @type pdist: C{ProbDistI}
        @param pdist: A probability distribution whose samples are
            C{FeatureValueList}s.  This probability distribution is
            used to estimate the probabilities of labels for texts.
            C{pdist.prob()} must support C{AssignmentEvent}s.  If the
            C{NBClassifier} is to be efficient, then C{pdist.prob()}
            should be capable of efficiently finding the probability
            of C{AssignmentEvent}s.
        """
        self._featuredetectors = featuredetectors
        self._labels = labels
        self._pdist = pdist

    def _estimate(self, labeled_text, min_p=0.0):
        """
        Give a non-normalized estimate for P(label, text).  If the
        probability gets below min_p, then abort and return 0.
        """
        # Find the feature values for this text.
        featurevalues = self._featuredetectors.detect(labeled_text)

        # Estimate P(label, text) (not normalized)
        p = 1.0
        for assignment in featurevalues.assignments():
            prob = self._pdist.prob(AssignmentEvent(assignment))
            if prob != 1:
                p *= prob / (1-prob)
            if p <= min_p:
                return 0.0
        return p

    def distribution(self, token):
        # Inherit docs.
        total_p = 0.0
        dist = {}

        # Find the non-normalized probability estimates
        for label in self._labels:
            p = self._estimate(LabeledText(token.type(), label))
            dist[label] = p
            total_p += p

        # What should we do if nothing is possible?
        if total_p == 0: return {}

        # Normalize our probability estimates
        for (label, p) in dist.items():
            dist[label] = p / total_p

        return dist

    def classify(self, token):
        # Inherit docs
        max_p = -1
        max_label = None

        # Find the label that maximizes the non-normalized probability
        # estimates.
        for label in self._labels:
            p = self._estimate(LabeledText(token.type(), label), max_p)
            if p > max_p:
                max_p = p
                max_label = label
                
        return max_label

##//////////////////////////////////////////////////////
##  Specialized frequency distribution.
##//////////////////////////////////////////////////////


class NBClassifierFreqDist(FreqDistI):
    """
    A frequency distribution optimized for use with C{NBClassifier}s.
    In particular, C{NBClassifierFreqDist} is a frequency distribution
    whose samples are C{FeatureValueList}s; and which is specialized
    for finding the frequencies of C{AssignmentEvent}s.

    Currently, C{NBClassifierFreqDist} only supports the following
    methods:

      - C{inc(FeatureValueListI)}
      - C{freq(AssignmentEvent)}
      - C{count(AssignmentEvent)}
      - C{N()}
      - C{B()}
      - C{bins(AssignmentEvent)}
    """
    def __init__(self, labels, features):
        self._features = features
        self._num_features = len(features)
        
        self._fcounts = zeros(self._num_features)
        self._N = 0.0

        # Cache values to avoid re-computing them.
        self._ffreqs = None
        self._B = (2L**self._num_features)

    def B(self):
        return self._B

    def bins(self, event):
        _chktype('NBClassifierFreqDist.bins', 1, event, (AssignmentEvent,))
        # Is this right?!?
        return self._B/2
        
    def N(self):
        return self._N

    def inc(self, sample):
        _chktype('NBClassifierFreqDist.inc', 1, sample,
                 (FeatureValueListI,)) 

        # Increment the total count.
        self._N += 1

        # Increment the feature count array
        for (feature_id,val) in sample.assignments():
            self._fcounts[feature_id] += 1

    def freq(self, event):
        _chktype('NBClassifierFreqDist.freq', 1, event, (AssignmentEvent,))
        (feature_id, value) = event.assignment()
        if value:
            return (self._fcounts[feature_id] / self._N)
        else:
            return 1 - (self._fcounts[feature_id] / self._N)

    def count(self, event):
        _chktype('NBClassifierFreqDist.count', 1, event, (AssignmentEvent,))
        (feature_id, value) = event.assignment()
        if value:
            return self._fcounts[feature_id]
        else:
            return self._N - self._fcounts[feature_id]

    def max(self):
        # !! HACK !!
        return AssignmentEvent((argmax(self._fcounts), 1))


class NBClassifierLidstoneProbDist(ProbDistI):
    def __init__(self, freqdist, bins, l):
        self._freqdist = freqdist
        self._l = l
        self._bins = bins

    def prob(self, event):
        _chktype('NBClassifierLidstoneProbDist.prob',
                 1, event, (AssignmentEvent,))
        c = self._freqdist.count(event)
        return (c + self._l) / self._bins

##//////////////////////////////////////////////////////
##  Naive Bayes Classifier Trainer
##//////////////////////////////////////////////////////

class NBClassifierTrainer(ClassifierTrainerI):
    def __init__(self, features, labels=None):
        self._features = features
        self._labels = labels

    def _find_labels(self, labeled_tokens):
        labelmap = {}
        for token in labeled_tokens:
            labelmap[token.type().label()] = 1
        return labelmap.keys()

    def train(self, labeled_tokens):
        if self._labels is None:
            labels = self._find_labels(labeled_tokens)
        else:
            labels = self._labels
        features = self._features

        N = len(labeled_tokens)*2/3
        traindata = labeled_tokens[:N]
        hodata = labeled_tokens[N:]
        
        train_fdist = NBClassifierFreqDist(labels, features)
        for labeled_token in traindata:
            labeled_type = labeled_token.type()
            feature_values = features.detect(labeled_type)
            train_fdist.inc(feature_values)
            
        ho_fdist = NBClassifierFreqDist(labels, features)
        for labeled_token in hodata:
            labeled_type = labeled_token.type()
            feature_values = features.detect(labeled_type)
            ho_fdist.inc(feature_values)

        return HeldOutProbDist(train_fdist, ho_fdist)

    def _train(self, labeled_tokens):
        if self._labels is None:
            labels = self._find_labels(labeled_tokens)
        else:
            labels = self._labels
        features = self._features
        
        fdist = NBClassifierFreqDist(labels, features)
        
        for labeled_token in labeled_tokens:
            labeled_type = labeled_token.type()
            feature_values = features.detect(labeled_type)
            fdist.inc(feature_values)

        #pdist = LidstoneProbDist(fdist, 0.0**len(features))
        #nf = len(self._features)
        #pdist = NBClassifierLidstoneProbDist(fdist, nf, 0.5)
        #pdist = MLEProbDist(fdist)
        return NBClassifier(features, labels, pdist)
            
##//////////////////////////////////////////////////////
##  Test code
##//////////////////////////////////////////////////////

t0=0
def resettime():
    global t0
    t0 = time.time()
def timestamp():
    return '%8.2fs ' % (time.time()-t0)

def demo(labeled_tokens, n_words=5, n_lens=20, debug=1):
    resettime()
    
    if debug: print timestamp(), 'getting a list of labels...'
    labelmap = {}
    for ltok in labeled_tokens:
        labelmap[ltok.type().label()] = 1
    labels = labelmap.keys()
    if debug: print timestamp(), '  got %d labels.' % len(labels)
    
    if debug: print timestamp(), 'constructing feature list...'
    features = AlwaysFeatureDetectorList()
    f_range = [(chr(i),l)
             for i in (range(ord('a'), ord('z'))+[ord("'")])
             for l in labels]
    func = lambda w:(w.text()[0:1], w.label())
    features += FunctionFeatureDetectorList(func, f_range)
    func = lambda w:(w.text()[-1:], w.label())
    features += FunctionFeatureDetectorList(func, f_range)
    func = lambda w:(w.text()[-2:-1], w.label())
    features += FunctionFeatureDetectorList(func, f_range)
    f_vals = [LabeledText("Atlanta's", l) for l in labels]
    features += ValueFeatureDetectorList(f_vals)
    f_range = [(n, l) for n in range(n_lens) for l in labels]
    func = lambda w:(len(w.text()), w.label())
    features += ValueFeatureDetectorList(f_vals)

    if debug: print timestamp(), '  got %d features' % len(features)

    if debug: print timestamp(), 'training on %d samples...' % len(labeled_tokens)
    trainer = NBClassifierTrainer(features)
    classifier = trainer.train(labeled_tokens)
    if debug: print timestamp(), '  done training'
    
    if debug: print timestamp(), ('%d tokens, %d labels' % (len(labeled_tokens), 
                                     len(classifier._labels)))
    toks = WSTokenizer().tokenize("jury the reports aweerdr "+
                                  "atlanta's atlanta_s moowerp's")
    
    #import time
    #for i in range(20):
    #    for word in toks:
    #        classifier.classify(word)
    #if debug: print timestamp(), '100 classifications: %0.4f secs' % (time.time()-t)

    toks = toks * (1+((n_words-1)/len(toks)))
    if debug:print timestamp(), 'Testing on %d tokens' % len(toks)
    t = time.time()
    for word in toks:
        if debug: print timestamp(), word
        if 1:
            items = classifier.distribution(word).items()
            items.sort(lambda x,y:cmp(y[1], x[1]))
            for (label,p) in items:
                if p > 0.01:
                    print timestamp(), '    %3.5f %s' % (p, label)
        label = classifier.classify(word)
        if debug: print timestamp(), '  =>', label

    return time.time()-t
        
def get_toks(debug=0):
    resettime()
    from nltk.tagger import TaggedTokenizer
    file = '/mnt/cdrom2/data/brown/ca01'
    text = open(file).read()[:10000]

    if debug: print timestamp(), 'tokenizing %d chars' % len(text)
    ttoks = TaggedTokenizer().tokenize(text)
    labeled_tokens = [Token(LabeledText(tok.type().base().lower(),
                                           tok.type().tag()),
                               tok.loc())
                         for tok in ttoks]
    if debug: print timestamp(), '  done tokenizing'
    return labeled_tokens
    
    

if __name__ == '__main__':
    n_words = 7
    toks = get_toks(1)
    print
    t1 = demo(toks, n_words, 15)
    print
    print 'Classified %d words in %3.2f seconds' % (n_words, t1)
    print '  (%3.2f seconds/word)' % (t1/n_words)
