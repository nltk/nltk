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
In particular, this classifier assumes that the probability of each
feature occuring is independant, given the label.  This allows us to
estimate the probability that a given text has a given label as
follows::

      P(label|text) = P(text,label) / P(text)

      P(text, label) = P(label) * P(fi|label) * (1-P(fj|label))

Where C{text} is the text we are classifiying; C{label} is a potential
label; C{f1}, C{f2}, ..., C{fi}, ..., C{fN} are the 

blah blah..

Approach:
  - define useful events
  - NBClassifier gets a single PDF over LabeledFeatureValueLists.

"""

from nltk.classifier import *
from nltk.probability import FreqDistI
from nltk.probability import SimpleFreqDist
from nltk.probability import CFFreqDist, CFSample, ContextEvent
from nltk.probability import MLEProbDist, ELEProbDist
from nltk.probability import ProbDistI, EventI
from nltk.token import Token, WSTokenizer
from nltk.chktype import chktype as _chktype

import time
from Numeric import zeros

##//////////////////////////////////////////////////////
##  Events for LabeledFeatureValueList
##//////////////////////////////////////////////////////

class LabelEvent(EventI):
    """
    An event defined over C{LabeledFeatureValueList}s which is true
    when the C{LabeledFeatureValueList}'s label has a given value.
    """
    def __init__(self, label):
        self._label = label
    def contains(self, sample):
        return sample._label == self._label
    def label(self):
        return self._label
    def __repr__(self):
        return ('{Event x: x=LabeledFeatureValueList' +
                ' with label %r}' % self._label)

class AssignmentEvent(EventI):
    """
    An event defined over C{LabeledFeatureValueList}s which is true
    when the C{LabeledFeatureValueList}'s feature value list contains
    a given assignment.  An assignment is an (id, value) pair which
    gives a feature identifier and the value of that feature.
    """
    def __init__(self, assignment):
        """
        Construct a new C{AssignmentEvent}, which is true for any
        C{LabeledFeatureValueList} whose feature value list contains
        the given assignment.

        @param assignment: The assignment to check for.  This (id,
            value) pair specifies a feature's identifier and a value
            for that feature.  For Naive Bayes classifiers, values are
            treated as binary values.
        @type assignment: C{tuple} of C{int} and (immutable)
        """
        self._assignment = assignment
        
    def assignment(self):
        return self._assignment
    def contains(self, sample):
        return sample._assignment == self._assignment
    def __repr__(self):
        return ('{Event x: x=LabeledFeatureValueList' +
                ' with assignment %r}' % self._assignment)

##//////////////////////////////////////////////////////
##  Specialized frequency distribution.
##//////////////////////////////////////////////////////

class NBClassifierFreqDist(FreqDistI):
    """
    A frequency distribution whose samples are labeled feature value
    lists; and which is specialized for finding the following
    frequencies:
    
        - freq(label)
        - freq(assignment|label)

    Assumes binary features (for now).

    Internally, maintain a 2d array of features x labels, which we use
    to count the number of times each feature is active with a label.
    Use a single global N.
    
    """
    def __init__(self, labels, features):
        self._features = features
        self._num_features = len(features)
        self._labels = labels
        
        # Map from labels -> indices.
        self._num_labels = len(labels)
        self._label_map = {}
        i = 0
        for label in labels:
            self._label_map[label] = i
            i += 1

        # Keep two arrays..
        self._fcounts = zeros( (self._num_labels, self._num_features) )
        self._lcounts = zeros(self._num_labels)
        self._N = 0.0

        # Cache...
        self._ffreqs = None
        self._lfreqs = None

    def B(self):
        #?!?!?
        return self._num_labels * (2L**self._num_features)

    def N(self):
        return self._N

    def inc(self, sample):
        _chktype('NBClassifierFreqDist.inc', 1, sample, (LabeledFeatureValueList,))

        # Increment the total count.
        self._N += 1

        # Get the label index.
        label_index = self._label_map[sample.label()]

        # Increment the label count array
        self._lcounts[label_index] += 1

        # Increment the feature count array
        for (feature_id,val) in sample.feature_values().assignments():
            self._fcounts[label_index, feature_id] += 1

    def freq(self, event):
        # EFFICIENCY TEST:
        #return 0
        
        _chktype('NBClassifierFreqDist.freq', 1, event, (LabelEvent,))
        label_index = self._label_map[event.label()]
        return self._lcounts[label_index] / self._N

    def cond_freq(self, event, condition):
        # EFFICIENCY TEST:
        #return 0
        
        #_chktype('NBClassifierFreqDist.cond_freq', 1, event, (AssignmentEvent,))
        #_chktype('NBClassifierFreqDist.cond_freq', 2, condition, (LabelEvent,))
        label_index = self._label_map[condition.label()]
        (feature_id, value) = event.assignment()

        if value:
            return self._fcounts[label_index, feature_id] / self._N
        else:
            return 1 - (self._fcounts[label_index, feature_id] / self._N)

    def cheat(self, text):
        if self._ffreqs is None: self._ffreqs = self._fcounts / self._N
        if self._lfreqs is None: self._lfreqs = self._lcounts / self._N
        
        # Convert the feature values into an array.
        fvals = zeros( (self._num_labels, self._num_features) )
        for label_id in range(self._num_labels):
            label = self._labels[label_id]
            values = self._features.detect(LabeledText(text, label))
            for (feature_id, val) in values.assignments():
                fvals[label_id][feature_id] = val

        # Copy it num_labels times.
        fvals = fvals * ones( (self._num_labels, 1) )

        # Do element-wise multiplication
        fplus = self._ffreqs * fvals
        fminus = (1-self._ffreqs) * (1-fvals)
        ftot = fplus + fminus

        fprobs = product(transpose(ftot))
        probs = fprobs * self._lfreqs

        return self._labels[argmax(probs)]


##//////////////////////////////////////////////////////
##  Naive Bayes Classifier
##//////////////////////////////////////////////////////

class NBClassifier(ClassifierI):
    """
    A Naive Bayes classifier::

      P(inst, label) = P(label) * P(fi|label) * (1-P(fj|label))

    Where fi are the features that fired; and fj are the features that
    did not fire.

    Model parameters:
      - FeatureDetectorList
      - A list of labels
      - A PDF whose samples are C{LabeledFeatureValueList}s
    """
    def __init__(self, featuredetectors, labels, pdist):
        self._featuredetectors = featuredetectors
        self._labels = labels
        self._pdist = pdist

    def prob(self, labeled_token):
        """
        Find the probability of the given labeled instance, using the
        naive bayes assumption.
        """
        labeled_text = labeled_token.type()
        label = labeled_text.label()
        text = labeled_text.text()
        
        p = self._pdist.prob(LabelEvent(label))
        featurevalues = self._featuredetectors.detect(labeled_text)
        #for feature_id in range(len(featurevalues)):
        #    assignment = (feature_id, featurevalues[feature_id])
        #    p *= self._pdist.cond_prob(AssignmentEvent(assignment),
        #                               LabelEvent(label))
        for assignment in featurevalues.assignments():
            p *= self._pdist.cond_prob(AssignmentEvent(assignment),
                                       LabelEvent(label))

        return p

    def classify(self, token):
        ## Much more efficient..  But this is cheating!
        #if isinstance(self._pdist._freqdist, NBClassifierFreqDist):
        #    return self._pdist._freqdist.cheat(token.type())
        
        max_p = -1
        max_label = None
        for label in self._labels:
            labeled_tok = Token(LabeledText(token.type(), label),
                                token.loc())
            p = self.prob(labeled_tok)
            if p > max_p:
                max_p = p
                max_label = label
        return max_label

##//////////////////////////////////////////////////////
##  Naive Bayes Classifier Trainer
##//////////////////////////////////////////////////////

class NBClassifierTrainer(ClassifierTrainerI):
    def __init__(self, features, labels):
        self._features = features
        self._labels = labels

    def train(self, labeled_tokens):
        fdist = NBClassifierFreqDist(self._labels, self._features)
        
        for labeled_token in labeled_tokens:
            labeled_type = labeled_token.type()
            label = labeled_type.label()
            text = labeled_type.text()
            feature_values = self._features.detect(labeled_type)
            lfvl = LabeledFeatureValueList(feature_values, label)
            fdist.inc(lfvl)

        pdist = MLEProbDist(fdist)
        return NBClassifier(self._features, self._labels, pdist)
            
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
    
    if debug: print timestamp(), 'constructing feature list...'
    features = (
        AlwaysFeatureDetectorList() +
        FunctionFeatureDetectorList(lambda w:w.text()[0],
                           [chr(i) for i in range(ord('a'), ord('z'))]) +
        FunctionFeatureDetectorList(lambda w:w.text()[-1],
                           [chr(i) for i in range(ord('a'), ord('z'))]) +
        FunctionFeatureDetectorList(lambda w:len(w.text()), range(n_lens)) +
        ValueFeatureDetectorList(("Atlanta's",))
        )
    if debug: print timestamp(), '  got %d features' % len(features)

    if debug: print timestamp(), 'getting a list of labels...'
    labelmap = {}
    for ltok in labeled_tokens:
        labelmap[ltok.type().label()] = 1
    labels = labelmap.keys()
    if debug: print timestamp(), '  got %d labels.' % len(labels)
    
    if debug: print timestamp(), 'training on %d samples...' % len(labeled_tokens)
    trainer = NBClassifierTrainer(features, labels)
    classifier = trainer.train(labeled_tokens)
    if debug: print timestamp(), '  done training'
    
    if debug: print timestamp(), ('%d tokens, %d labels' % (len(labeled_tokens), 
                                     len(classifier._labels)))
    toks = WSTokenizer().tokenize("jury the reports aweerdr "+
                                  "Atlanta's")
    
    #import time
    #for i in range(20):
    #    for word in toks:
    #        classifier.classify(word)
    #if debug: print timestamp(), '100 classifications: %0.4f secs' % (time.time()-t)

    t = time.time()
    toks = toks * (n_words/len(toks))
    for word in toks:
        if debug: print timestamp(), word
        label = classifier.classify(word)
        if debug: print timestamp(), '  =>', label

    return time.time()-t
        
def get_toks(debug=0):
    resettime()
    from nltk.tagger import TaggedTokenizer
    file = '/mnt/cdrom2/data/brown/ca01'
    text = open(file).read()

    if debug: print timestamp(), 'tokenizing %d chars' % len(text)
    ttoks = TaggedTokenizer().tokenize(text)
    labeled_tokens = [Token(LabeledText(tok.type().base(),
                                           tok.type().tag()),
                               tok.loc())
                         for tok in ttoks]
    if debug: print timestamp(), '  done tokenizing'
    return labeled_tokens
    
    

# Time for 5 texts with 10,000 features: 4.3 secs/feature
if __name__ == '__main__':
    toks = get_toks(1)
    print
    t1 = demo(toks, 5, 10000)

  # T = .148
  # F = .00106
  #
  # time = (T texts+alpha)*(F features+beta)
