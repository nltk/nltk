# Natural Language Toolkit: Naive Bayes Classifiers
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
A text classifier model based on the naive Bayes assumption.  In
particular, this classifier assumes that each feature is independant.
This assumption allows us to construct reliable estimates of the
probability that a given text has a given label.  See C{NBClassifier}
for more information on the approximation algorithms used by the
classifier.

C{NBClassifier} is a naive Bayes classifier model.  This model is
based on a C{ProbDist} whose samples are C{FeatureValueList}s.  It
uses this probability distribution to estimate the probability that a
given text should be classified with a label::

    P(label|text)

To form these estimates, it examines the probabilities of individual
feature-value assignments::

    P(fi=vi)

It uses C{AssignmentEvent}s to encode the event that a feature has a
given value.  An C{AssignmentEvent} is an event consisting of all
C{FeatureValueList}s that contain a given feature-value assignment.
The probability distribution used to define a C{NBClassifier} should
therefore be capable of efficiently calculating the probability of
C{AssignmentEvent}s.

This module defines a frequency distribution, C{NBClassifierFreqDist},
which is designed to efficiently find the frequencies of
C{AssignmentEvent}s.  This frequency distribution can be used to build
an efficient C{ProbDist} for C{NBClassifier}.

C{NBClassifier}s can be built from training data with the
C{NBClassifierTrainer} class.
"""

from nltk.classifier import *
from nltk.classifier.feature import *
from nltk.probability import *
from nltk.token import Token, WSTokenizer
from nltk.chktype import chktype as _chktype

import time
from Numeric import zeros, product, nonzero, take, argmax
from math import exp

##//////////////////////////////////////////////////////
##  AssignmentEvent
##//////////////////////////////////////////////////////

class AssignmentEvent(EventI):
    """
    An event containing all C{FeatureValueList}s that contain a given
    assignment.  An assignment is an (id, value) pair which gives a
    feature id and the value of that feature.
    """
    def __init__(self, assignment):
        """
        Construct a new C{AssignmentEvent}, containing all
        C{FeatureValueList}s that contain C{assignment}.

        @param assignment: The assignment to check for.  This (id,
            value) pair specifies a feature's id and a value
            for that feature.
        @type assignment: C{tuple} of C{int} and (immutable)
        """
        self._assignment = assignment
        
    def assignment(self):
        """
        @return: the assignment that defines this C{AssignmentEvent}.
            This (id, value) pair specifies a feature's id and
            a value for that feature.  
        @rtype: C{tuple} of C{int} and (immutable)
        """
        return self._assignment

    def contains(self, fvlist):
        """
        @return: C{true} iff the given feature value list contains
            this C{AssignmentEvent}'s assignment.  In particular,
            if C{(id, val)} is this C{AssignmentEvent}'s assignment,
            then return true iff C{fvlist[id]==val}.
        @type fvlist: C{FeatureValueList}
        """
        (id, val) = self._assignment
        return (fvlist[id] == val)
    
    def __repr__(self):
        """
        @rtype: C{string}
        @return: A C{string} representation of this
            C{AssignmentEvent}, of the form::

                {Event fvlist: fvlist[12]=1}
        """
        return '{Event fvlist: fvlist[%r]=%r}' % self._assignment

##//////////////////////////////////////////////////////
##  Naive Bayes Classifier
##//////////////////////////////////////////////////////

class NBClassifier(AbstractFeatureClassifier):
    """
    A text classifier model based on the Naive Bayes assumption.  In
    particular, we assume that the feature value assignments of a
    given text are mutually independant.  This assumption justifies
    the following approximation for the probabilitiy of a labeled
    text::

      P(labeled_text) = P(f1=v1, f2=v2, ..., fn=vn)
                      = P(f1=v1) * P(f2=v2) * ... * P(fn=vn)

    Where C{fi=vi} are the feature values assignments for
    C{labeled_text}.  This approximation helps solve the sparse data
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

    Feature Requirements
    ====================

    The naive bayes classifier model does not place any restrictions
    on feature value type beyond those caused by the underlying
    probability distribution.  Note, however, that the estimates of
    C{P(fi=vi)} may be unreliable for certain types feature value
    (e.g., real values).
   
    Optimizations
    =============

    Factoring out zero-feature-values
    ---------------------------------
    The formula given above for estimating P(text, label) is
    inefficient for sparse feature value lists.  Since most feature
    value lists are sparse, we can improve performance by finding
    P(labeled_text) with the following equivalant formulation::

      P(labeled_text) = P(f1=0, f2=0, ..., fn=0) * P(Fi=1)/P(Fi=0)

      P(f1=0, f2=0, ..., fn=0) = P(f1=0) * ... * P(fn=0)

    Where C{Fi} are the set of features whose value is 1.  This
    reformulation is useful because C{P(f1=0, f2=0, ..., fn=0)} does
    not depend on the text in any way.  

    Since C{P(f1=0, f2=0, ..., fn=0)} does not depend on the text in
    any way, we don't need to calculate it at all if we want to find
    the most likely label for a given text::

      ARGMAX[label] P(label|text)
              = ARGMAX[label] P(labeled_text)
              = ARGMAX[label] P(f1=0, f2=0, ..., fn=0) * P(Fi=1)/P(Fi=0)
              = ARGMAX[label] P(Fi=1)/P(Fi=0)

    Also, since we are normalizing C{P(label=l|text)} by summing over
    all values of l, we don't need to find C{P(f1=0, f2=0, ..., fn=0)}
    to calculate C{P(label|text)}::

                                      P(text, label=l)
      P(label=l|text) = ---------------------------------------------
                         P(text, label=l1) + ... + P(text, label=lm)

    Thus, we never actually need to evaluate
    C{P(f1=0, f2=0, ..., fn=0)}.  
    """
    def __init__(self, fdlist, labels, prob_dist):
        """
        Construct a new Naive Bayes classifier model.  Typically, new
        classifier models are created by C{ClassifierTrainer}s.

        @type fdlist: C{FeatureDetectorListI}
        @param fdlist: The feature detector list defining
            the features that are used by the C{NBClassifier}.  This
            should be the same feature detector list that was used to
            construct the feature value lists that are the samples of
            C{prob_dist}.
        @type labels: C{list} of (immutable)
        @param labels: A list of the labels that should be considered
            by this C{NBClassifier}.  Typically, labels are C{string}s
            or C{int}s.
        @type prob_dist: C{ProbDistI}
        @param prob_dist: A probability distribution whose samples are
            C{FeatureValueList}s.  This probability distribution is
            used to estimate the probabilities of labels for texts.
            C{prob_dist.prob()} must support C{AssignmentEvent}s.  If the
            C{NBClassifier} is to be efficient, then C{prob_dist.prob()}
            should be capable of efficiently finding the probability
            of C{AssignmentEvent}s.
        """
        self._prob_dist = prob_dist
        AbstractFeatureClassifier.__init__(self, fdlist, labels)

    def fvlist_likelihood(self, fvlist):
        # Inherit docs from AbstractFeatureClassifier
        p = 1.0
        default = fvlist.default()
        for (fid, val) in fvlist.assignments():
            p1 = self._prob_dist.prob(AssignmentEvent((fid, val)))
            p2 = self._prob_dist.prob(AssignmentEvent((fid, default)))
            if p2 != 0:
                p *= p1 / p2
        return p

    def prob_dist(self):
        """
        @rtype: C{ProbDistI}
        @return: The probability distribution that this
            C{NBClassifier} uses to estimate the probabilities for
            text labels. 
        """
        return self._prob_dist

    def __repr__(self):
        """
        @rtype: C{string}
        @return: A string representation of this Naive Bayes
            classifier.  
        """
        return ('<NBClassifier: %d labels, %d features>' %
                (len(self.labels()), len(self.fdlist())))

##//////////////////////////////////////////////////////
##  Specialized frequency distribution.
##//////////////////////////////////////////////////////


class NBClassifierFreqDist(FreqDistI):
    """
    A frequency distribution optimized for use with C{NBClassifier}s.
    In particular, C{NBClassifierFreqDist} is a frequency distribution
    whose samples are C{FeatureValueList}s; and which is specialized
    for finding the frequencies of C{AssignmentEvent}s.

    Some C{NBClassifierFreqDist} methods can only be used with certain
    types of arguments.  In particular, C{NBClassifierFreqDist} only
    supports the following methods:
      - C{inc(FeatureValueListI)}
      - C{freq(AssignmentEvent)}
      - C{count(AssignmentEvent)}
      - C{N()}

    C{NBClassifierFreqDist} requires that all sample
    C{FeatureValueList}s be binary valued, and have a default value of
    C{0}.

    @ivar _fcounts: An array recording the number of times each
        feature has occured.
    @ivar _N: The total number of samples recorded.
    @ivar _ffreqs: A cached value for _fcounts/_N.
    """
    def __init__(self, fvlist_size):
        """
        Construct a new, empty C{NBClassifierFreqDist}.  The samples
        in this new frequency distribution must be
        C{FeatureValueList}s with C{fvlist_size} feature values.
        Usually, all of the C{FeatureValueList} samples are generated
        by the same C{FeatureDetectorList}.

        @type fvlist_size: C{int}
        @param fvlist_size: The number of features values contained in
            the C{FeatureValueList} samples.
        """
        self._fcounts = zeros(fvlist_size)
        self._N = 0.0

    def N(self):
        # Inherit docs from FreqDistI
        return self._N

    def inc(self, sample):
        # Inherit docs from FreqDistI
        _chktype('NBClassifierFreqDist.inc', 1, sample,
                 (FeatureValueListI,)) 

        # Increment the total count.
        self._N += 1

        # Increment the feature count array
        for (fid,val) in sample.assignments():
            if val != 0:
                self._fcounts[fid] += 1

    def freq(self, event):
        # Inherit docs from FreqDistI
        _chktype('NBClassifierFreqDist.freq', 1, event, (AssignmentEvent,))
        (fid, value) = event.assignment()
        if value:
            return (self._fcounts[fid] / self._N)
        else:
            return 1 - (self._fcounts[fid] / self._N)

    def count(self, event):
        # Inherit docs from FreqDistI
        _chktype('NBClassifierFreqDist.count', 1, event, (AssignmentEvent,))
        (fid, value) = event.assignment()
        if value:
            return self._fcounts[fid]
        else:
            return self._N - self._fcounts[fid]

    def fvlist_size(self):
        """
        The samples of this frequency distribution are
        C{FeatureValueList}s of a constant size.  This method returns
        this size.
        
        @return: the number of features values contained in
            this frequency distribution's C{FeatureValueList}
            samples.
        @rtype: C{int}
        """
        return len(self._fcounts)

class NBClassifierLidstoneProbDist(ProbDistI):
    """
    A simple implementation of a Lidstone probability distribution,
    specialized for C{NBClassifierFreqDist}.  This is intended as a
    temporary solution until we re-design the general-purpose
    probability distributions to correctly perform smoothing over
    events (rather than just over samples).

    C{NBClassifierLidstoneProbDist} only implements one method:
    C{prob}, which requires that its argument be an
    C{AssignmentEvent}. 
    """
    def __init__(self, freqdist, l):
        """
        @param l: The lambda-value for the lidstone probability
            distribution.  C{l=0} gives Maximum Likelihood Estimation
            smoothing; C{l=1} gives Laplace smoothing; and C{l=0.5}
            gives Expected Likelihood Estimation smoothing.
        """
        _chktype('NBClassifierLidstoneProbDist',
                 1, freqdist, (NBClassifierFreqDist,))
        self._freqdist = freqdist
        self._l = l
        self._bins = freqdist.fvlist_size()

    def prob(self, event):
        _chktype('NBClassifierLidstoneProbDist.prob',
                 1, event, (AssignmentEvent,))
        c = self._freqdist.count(event)
        return float(c + self._l) / self._bins

##//////////////////////////////////////////////////////
##  Naive Bayes Classifier Trainer
##//////////////////////////////////////////////////////

class NBClassifierTrainer(ClassifierTrainerI):
    """
    A factory class that builds naive bayes classifiers from training
    data.  C{NBClassifierTrainer} uses the training data to produce
    estimates of the probability for each feature value assignment;
    and uses these estimates to construct a new C{NBClassifier}.

    C{NBClassifierTrainer} estimates the probability of a feature
    value assignment by examining the frequency with which it appears
    in the training data.  In the simplest case, the probability of a
    feature value assignment is estimated to be the number of training
    tokens with that feature value assignment divided by the total
    number of trainin tokens.

    However, a variety of smoothing algorithms can be specified, which
    can improve these probability estimates.  For information about
    which smoothing algorithms are available, see C{train()}.

    The current implementation of C{NBClassifierTrainer} requires that
    all feature detectors produce binary feature values; and use a
    default of C{0}.
    """
    def __init__(self, fdlist):
        """
        Construct a new classifier trainer, using the given feature
        detector list.

        @type fdlist: C{FeatureDetectorListI}
        @param fdlist: A feature detector llist defining
            the features that are used by the C{NBClassifier}s
            generated by this C{NBClassifierTrainer}.
        """
        self._fdlist = fdlist

    def train(self, labeled_tokens, **kwargs):
        """
        Build a new C{NBClassifier} from the given training data.

        @type labeled_tokens: C{list} of (C{Token} with type C{LabeledText})
        @param labeled_tokens: A list of correctly labeled texts.
            These texts will be used as training samples to construct
            new classifiers.
        @param kwargs: Keyword arguments.
            - C{labels}: The set of possible labels.  If none is
              given, then the set of all labels attested in the
              training data will be used instead.  (type=C{list} of
              (immutable)).
            - C{estimator}: The smoothing algorithm that should be
              applied to the probability estimates for feature value
              assignments.  Currently, the possible values are:
                - C{'MLE'}: The maximum likelihood estimation.  This
                  does not apply any smoothing.  This is the default
                  value. 
                - C{'Laplace'}: The Laplace estimation.
                - C{'ELE'}: The expected likelihood estimation.
                - C{('Lidstone', lambda)}: The Lidstone estimation.
                  Lambda is a parameter to that estimation; it is a
                  positive float, typically between 0 and 1.
        @return: A new classifier, trained from the given labeled
            tokens.
        @rtype: C{ClassifierI}
        """
        # Process the keyword arguments
        estimator = 'MLE'
        labels = None
        for (key, val) in kwargs.items():
            if key == 'estimator': estimator = val
            elif key == 'labels': labels = val
            else: raise TypeError('Unknown keyword arg %s' % key)
        if labels is None:
            labels = find_labels(labeled_tokens)
                
        # Construct a frequency distribution from the training data
        freqdist = NBClassifierFreqDist(len(self._fdlist))
        for labeled_token in labeled_tokens:
            labeled_type = labeled_token.type()
            fvlist = self._fdlist.detect(labeled_type)
            freqdist.inc(fvlist)

        # Construct a probability distribution from the freq dist
        if type(estimator) != type(""):
            if estimator[0].lower() == 'lidstone':
                l = estimator[1]
                probdist = NBClassifierLidstoneProbDist(freqdist, l)
        elif estimator.lower() == 'mle':
            probdist = MLEProbDist(freqdist)
        elif estimator.lower() == 'laplace':
            probdist = NBClassifierLidstoneProbDist(freqdist, 1.0)
        elif estimator.lower() == 'ele':
            probdist = NBClassifierLidstoneProbDist(freqdist, 0.5)
        else:
            raise ValueError('Unknown estimator type %r' % estimator)
        
        return NBClassifier(self._fdlist, labels, probdist)

    def __repr__(self):
        return '<NBClassifierTrainer: %d features>' % len(self._fdlist)
            
##//////////////////////////////////////////////////////
##  Multinomial play
##//////////////////////////////////////////////////////

# Features can fire multiple times.  Probability that a feature fires
# n times is p^n, where p is the probability that it fires once.  So
# we already know E(u)/n.  That's the freq dist we made.  Well,
# kinda...  Not really.  But to do that, we just need to inc by val,
# not by 1, in NBClassifierFreqDist.

# So then we have E(fid)/n.  That is, p(fid).  So when we're asked to
# estimate P(id=val), take P(id=1)^val...

# Doing this to the freq-dist streight is playing a little fast &
# loose, though..  But doing it in a wrapper pdf seems fine.
# Hm.. still might be tricky, though.  I'll have to think about it.

class MultinomialNBClassifierProbDist(ProbDistI):
    """
    This is a dirty trick: we're not a real prob dist!!
    """
    def __init__(self, fdlist, labeled_tokens, l=0.5):
        fcounts = zeros(len(fdlist), 'd')
        self._N = 0
        fcounts += l
        self._N += l*len(fcounts)

        for tok in labeled_tokens:
            self._N += 1
            for (fid, val) in fdlist.detect(tok.type()).assignments():
                fcounts[fid] += val

        # Expected value for each feature
        self._exp = fcounts / self._N

    def prob(self, event):
        # Inherit docs from FreqDistI
        _chktype('NBClassifierFreqDist.freq', 1, event, (AssignmentEvent,))
        (fid, value) = event.assignment()

        # valfact = value!
        valfact = reduce( lambda x,y:x*y, range(2,value+1), 1.0 )

        multinomial = ((self._exp[fid] ** value) / valfact)
        poisson = ((self._exp[fid] ** value) * exp(-self._exp[fid]) /
                   valfact)
        return poisson

class MultinomialNBClassifierTrainer(ClassifierTrainerI):
    def __init__(self, fdlist):
        self._fdlist = fdlist

    def train(self, labeled_tokens, **kwargs):
        labels = None
        for (key, val) in kwargs.items():
            if key == 'labels': labels = val
            else: raise TypeError('Unknown keyword arg %s' % key)
        if labels is None:
            labels = find_labels(labeled_tokens)
                
        probdist = MultinomialNBClassifierProbDist(self._fdlist,
                                                   labeled_tokens)
        return NBClassifier(self._fdlist, labels, probdist)

    def __repr__(self):
        return '<NBClassifierTrainer: %d features>' % len(self._fdlist)
            

##//////////////////////////////////////////////////////
##  Test code
##//////////////////////////////////////////////////////

t0=0
def _resettime():
    global t0
    t0 = time.time()
def _timestamp():
    return '%8.2fs ' % (time.time()-t0)

def demo(labeled_tokens, n_words=5, n_lens=20, debug=1):
    _resettime()
    
    if debug: print _timestamp(), 'getting a list of labels...'
    labelmap = {}
    for ltok in labeled_tokens:
        labelmap[ltok.type().label()] = 1
    labels = labelmap.keys()
    if debug: print _timestamp(), '  got %d labels.' % len(labels)
    
    if debug: print _timestamp(), 'constructing feature list...'
    fdlist = AlwaysOnFDList()
    f_range = [chr(i) for i in (range(ord('a'), ord('z'))+[ord("'")])]
    fdlist += TextFunctionFDList(lambda w:w[0:1], f_range, labels)
    fdlist += TextFunctionFDList(lambda w:w[-1:], f_range, labels)
    fdlist += TextFunctionFDList(lambda w:w[-2:-1], f_range, labels)
    fdlist += TextFunctionFDList(lambda w:w, ["atlanta's"], labels)
    fdlist += TextFunctionFDList(lambda w:len(w), range(n_lens), labels)

    if debug: print _timestamp(), '  got %d features' % len(fdlist)

    if debug: print _timestamp(), 'training on %d samples...' % len(labeled_tokens)

    trainer = NBClassifierTrainer(fdlist)
    classifier = trainer.train(labeled_tokens, estimator='ELE')

    #trainer = MultinomialNBClassifierTrainer(fdlist)
    #classifier = trainer.train(labeled_tokens)
    
    if debug: print _timestamp(), '  done training'
    
    if debug: print _timestamp(), ('%d tokens, %d labels' % (len(labeled_tokens), 
                                     len(classifier.labels())))
    toks = WSTokenizer().tokenize("jury the reports aweerdr "+
                                  "atlanta's atlanta_s moowerp's")
    
    #import time
    #for i in range(20):
    #    for word in toks:
    #        classifier.classify(word)
    #if debug: print _timestamp(), '100 classifications: %0.4f secs' % (time.time()-t)

    toks = toks * (1+((n_words-1)/len(toks)))
    if debug:print _timestamp(), 'Testing on %d tokens' % len(toks)
    t = time.time()
    for word in toks:
        if debug: print _timestamp(), word
        if 0:
            items = classifier.distribution_dictionary(word).items()
            items.sort(lambda x,y:cmp(y[1], x[1]))
            for (label,p) in items:
                if p > 0.01:
                    print _timestamp(), '    %3.5f %s' % (p, label)
        label = classifier.classify(word)
        if debug: print _timestamp(), '  =>', label

    return time.time()-t
        
def _get_toks(file='/mnt/cdrom2/data/brown/ca01', debug=0):
    """
    Load tokens from the given file.  
    """
    _resettime()
    from nltk.tagger import TaggedTokenizer
    text = open(file).read()

    if debug: print _timestamp(), 'tokenizing %d chars' % len(text)
    ttoks = TaggedTokenizer().tokenize(text)
    labeled_tokens = [Token(LabeledText(tok.type().base().lower(),
                                           tok.type().tag()),
                               tok.loc())
                         for tok in ttoks]
    if debug: print _timestamp(), '  done tokenizing'
    return labeled_tokens
    
    

if __name__ == '__main__':
    n_words = 7
    toks = _get_toks()
    print
    t1 = demo(toks, n_words, 15)
    print
    print 'Classified %d words in %3.2f seconds' % (n_words, t1)
    print '  (%3.2f seconds/word)' % (t1/n_words)
