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

To form these estimates, it examines the probabilities of labels; and
the probabilities of feature value assignments, given labels::

    P(label)
    P(vi|fi, label)

C{NBClassifier}s can be built from training data with the
C{NBClassifierTrainer} class.
"""

from nltk.classifier import *
from nltk.classifier.feature import *
from nltk.probability import *
from nltk.token import Token, WSTokenizer
from nltk.chktype import chktype as _chktype
import types

##//////////////////////////////////////////////////////
##  Naive Bayes Classifier
##//////////////////////////////////////////////////////

class NBClassifier(AbstractFeatureClassifier):
    """
    A text classifier model based on the Naive Bayes assumption.  In
    particular, we assume that the feature value assignments of a
    given text are mutually independant, given the label.  This
    assumption justifies the following approximation for the
    probabilitiy of a labeled text::

      P(labeled_text) = P(f1=v1, f2=v2, ..., fn=vn)
                      = P(f1=v1|l) * P(f2=v2|l) * ... * P(fn=vn|l) *
                        P(l)

    Where C{fi=vi} are the feature values assignments for
    C{labeled_text}; and C{l} is its label.  This approximation helps
    solve the sparse data problem, since our estimates for the
    probabilities of individual features (C{P(fi=vi)}) are much more
    reliable than our joint estimates for all features (C{P(f1=v1,
    f2=v2, ..., fn=vn)}).

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
    on feature value type beyond those imposed by the probability
    distributions used to construct the classifier.
    """
    
#    # The following no longer true; but we probably want to do some
#    # similar optimization, because the current implementation is not
#    # efficient for sparse feature value lists...
#    """
#    Optimizations
#    =============
#
#    Factoring out zero-feature-values
#    ---------------------------------
#    The formula given above for estimating P(text, label) is
#    inefficient for sparse feature value lists.  Since most feature
#    value lists are sparse, we can improve performance by finding
#    P(labeled_text) with the following equivalant formulation::
#
#      P(labeled_text) = P(f1=0, f2=0, ..., fn=0) * P(Fi=1)/P(Fi=0)
#
#      P(f1=0, f2=0, ..., fn=0) = P(f1=0) * ... * P(fn=0)
#
#    Where C{Fi} are the set of features whose value is 1.  This
#    reformulation is useful because C{P(f1=0, f2=0, ..., fn=0)} does
#    not depend on the text in any way.  
#
#    Since C{P(f1=0, f2=0, ..., fn=0)} does not depend on the text in
#    any way, we don't need to calculate it at all if we want to find
#    the most likely label for a given text::
#
#      ARGMAX[label] P(label|text)
#              = ARGMAX[label] P(labeled_text)
#              = ARGMAX[label] P(f1=0, f2=0, ..., fn=0) * P(Fi=1)/P(Fi=0)
#              = ARGMAX[label] P(Fi=1)/P(Fi=0)
#
#    Also, since we are normalizing C{P(label=l|text)} by summing over
#    all values of l, we don't need to find C{P(f1=0, f2=0, ..., fn=0)}
#    to calculate C{P(label|text)}::
#
#                                      P(text, label=l)
#      P(label=l|text) = ---------------------------------------------
#                         P(text, label=l1) + ... + P(text, label=lm)
#
#    Thus, we never actually need to evaluate
#    C{P(f1=0, f2=0, ..., fn=0)}.  
#    """
    def __init__(self, fd_list, labels, label_probdist, fval_probdist):
        """
        Construct a new Naive Bayes classifier model.  Typically, new
        classifier models are created by C{ClassifierTrainer}s.

        @type fd_list: C{FeatureDetectorListI}
        @param fd_list: The feature detector list defining
            the features that are used by the C{NBClassifier}.  This
            should be the same feature detector list that was used to
            construct the feature value lists that are the samples of
            C{prob_dist}.
        @type labels: C{list} of (immutable)
        @param labels: A list of the labels that should be considered
            by this C{NBClassifier}.  Typically, labels are C{string}s
            or C{int}s.

        @type label_probdist: C{ProbDistI}
        @param label_probdist: A probability distribution that
            specifies the probability that a randomly chosen text will
            have each label.  In particular,
            C{label_probdist.prob(M{l})} is the probability that a text
            has label M{l}.
        @type fval_probdist: C{ConditionalProbDist}
        @param fval_probdist: A conditional probability distribution
            that specifies the probability of each feature value,
            given a label and a feature id.  In particular,
            C{fval_probdist[M{l}, M{fid}].prob(M{fval})} is the
            probability that a text with label M{l} will assign
            feature value M{fval} to the feature whose id is M{fid}. 
        """
        assert _chktype(1, fd_list, FeatureDetectorListI)
        assert _chktype(2, labels, [], ())
        assert _chktype(3, label_probdist, ProbDistI)
        assert _chktype(4, fval_probdist, ConditionalProbDist)
                        
        self._label_probdist = label_probdist
        self._fval_probdist = fval_probdist
        AbstractFeatureClassifier.__init__(self, fd_list, labels)

    def fv_list_likelihood(self, fv_list, label):
        # Inherit docs from AbstractFeatureClassifier
        assert _chktype(1, fv_list, FeatureValueListI)
        p = self._label_probdist.prob(label)
        #DEBUG = '%20s' % label
        for fid in range(len(fv_list)):
            #z = self._fval_probdist[label,fid].prob(fv_list[fid])
            #DEBUG += '%10.5f' % z
            p *= self._fval_probdist[label,fid].prob(fv_list[fid])
        #if p > 0.00001: print DEBUG, '=> %10.8f' % p
        return p

    def label_probdist(self):
        """
        @rtype: C{ProbDistI}
        @return: The probability distribution that this
            C{NBClassifier} uses to estimate the probability that a
            randomly chosen text will have each label.  In particular,
            C{label_probdist.prob(M{l})} is the probability that a text
            has label M{l}.
        """
        return self._label_probdist

    def fval_probdist(self):
        """
        @rtype: C{ConditionalProbDist}
        @return: The conditional robability distribution that this
            C{NBClassifier} uses to estimate the probability of each
            feature value, given a label and a feature id.  In
            particular, C{fval_probdist[M{l}, M{fid}].prob(M{fval})}
            is the probability that a text with label M{l} will assign
            feature value M{fval} to the feature whose id is M{fid}.
        """
        return self._fval_probdist

    def __repr__(self):
        """
        @rtype: C{string}
        @return: A string representation of this Naive Bayes
            classifier.  
        """
        return ('<NBClassifier: %d labels, %d features>' %
                (len(self.labels()), len(self.fd_list())))

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
    def __init__(self, fd_list):
        """
        Construct a new classifier trainer, using the given feature
        detector list.

        @type fd_list: C{FeatureDetectorListI}
        @param fd_list: A feature detector llist defining
            the features that are used by the C{NBClassifier}s
            generated by this C{NBClassifierTrainer}.
        """
        assert _chktype(1, fd_list, FeatureDetectorListI)
        self._fd_list = fd_list

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
                - C{'ELE'}: The expected likelihood estimation.  This
                  is curently the default value.
                - C{'MLE'}: The maximum likelihood estimation.  This
                  does not apply any smoothing.  
                - C{'Laplace'}: The Laplace estimation.
                - C{('Lidstone', lambda)}: The Lidstone estimation.
                  Lambda is a parameter to that estimation; it is a
                  positive float, typically between 0 and 1.
        @return: A new classifier, trained from the given labeled
            tokens.
        @rtype: C{ClassifierI}
        """
        assert _chktype(1, labeled_tokens, [Token], (Token,))
        
        # Process the keyword arguments
        estimator = 'ELE'
        labels = None
        for (key, val) in kwargs.items():
            if key == 'estimator': estimator = val
            elif key == 'labels': labels = val
            else: raise TypeError('Unknown keyword arg %s' % key)
        if labels is None:
            labels = find_labels(labeled_tokens)
                
        # Construct a frequency distribution from the training data
        label_freqdist = FreqDist()
        fval_freqdist = ConditionalFreqDist()
        for labeled_token in labeled_tokens:
            labeled_type = labeled_token.type()
            label = labeled_type.label()
            label_freqdist.inc(label)
            fv_list = self._fd_list.detect(labeled_type)
            for fid in range(len(fv_list)):
                fval_freqdist[label, fid].inc(fv_list[fid])

        # Construct a probability distribution from the freq dist
        if type(estimator) != type(""):
            if estimator[0].lower() == 'lidstone':
                l = estimator[1]
                label_probdist = LidstoneProbDist(label_freqdist, l)
                def f(fdist, l=l): return LidstoneProbDist(fdist, l)
                fval_probdist = ConditionalProbDist(fval_freqdist, f)
        elif estimator.lower() == 'mle':
            label_probdist = MLEProbDist(label_freqdist)
            fval_probdist = ConditionalProbDist(fval_freqdist, MLEProbDist)
        elif estimator.lower() == 'laplace':
            label_probdist = LaplaceProbDist(label_freqdist)
            fval_probdist = ConditionalProbDist(fval_freqdist, LaplaceProbDist)
        elif estimator.lower() == 'ele':
            label_probdist = ELEProbDist(label_freqdist)
            fval_probdist = ConditionalProbDist(fval_freqdist, ELEProbDist)
        else:
            raise ValueError('Unknown estimator type %r' % estimator)

        return NBClassifier(self._fd_list, labels,
                            label_probdist, fval_probdist)

    def __repr__(self):
        return '<NBClassifierTrainer: %d features>' % len(self._fd_list)
            
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

#from math import exp
#class _MultinomialNBClassifierProbDist(ProbDistI):
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
#        _chktype('NBClassifierFreqDist.freq', 1, event, (AssignmentEvent,))
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
#class _MultinomialNBClassifierTrainer(ClassifierTrainerI):
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
#        probdist = MultinomialNBClassifierProbDist(self._fd_list,
#                                                   labeled_tokens)
#        return NBClassifier(self._fd_list, labels, probdist)
#
#    def __repr__(self):
#        return '<NBClassifierTrainer: %d features>' % len(self._fd_list)


##//////////////////////////////////////////////////////
##  Test code
##//////////////////////////////////////////////////////

import time
_t0=0
def _resettime():
    global _t0
    _t0 = time.time()
def _timestamp():
    return '%8.2fs ' % (time.time()-_t0)

def demo(labeled_tokens, n_words=5, n_lens=20, debug=1):
    assert _chktype(1, labeled_tokens, [Token], (Token,))
    assert _chktype(2, n_words, types.IntType)
    assert _chktype(3, n_lens, types.IntType)
    assert _chktype(4, debug, types.IntType)
    _resettime()
    
    if debug: print _timestamp(), 'getting a list of labels...'
    labelmap = {}
    for ltok in labeled_tokens:
        labelmap[ltok.type().label()] = 1
    labels = labelmap.keys()
    if debug: print _timestamp(), '  got %d labels.' % len(labels)
    
    if debug: print _timestamp(), 'constructing feature list...'
    f_range = [chr(i) for i in (range(ord('a'), ord('z'))+[ord("'")])]
    feature_detectors = [
        FunctionFeatureDetector(lambda tok:ord(tok.text()[0:1])),
        FunctionFeatureDetector(lambda tok:ord(tok.text()[-2:-1] or ' ')),
        FunctionFeatureDetector(lambda tok:ord(tok.text()[-1:])),
        FunctionFeatureDetector(lambda tok:len(tok.text())),
        ]
    fd_list = SimpleFDList(feature_detectors)
    #fd_list += TextFunctionFDList(lambda w:w[0:1], f_range, labels)
    #fd_list = TextFunctionFDList(lambda w:w[0:1], f_range, labels)
    #fd_list += TextFunctionFDList(lambda w:w[-2:-1], f_range, labels)
    #fd_list += TextFunctionFDList(lambda w:w[-1:], f_range, labels)
    #fd_list += TextFunctionFDList(lambda w:w, ["atlanta's"], labels)
    #fd_list += TextFunctionFDList(lambda w:len(w), range(n_lens), labels)

    if debug: print _timestamp(), '  got %d features' % len(fd_list)

    if debug: print _timestamp(), 'training on %d samples...' % len(labeled_tokens)

    trainer = NBClassifierTrainer(fd_list)
    classifier = trainer.train(labeled_tokens, estimator='ELE')

    #trainer = MultinomialNBClassifierTrainer(fd_list)
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
        
def _get_toks(file='/cdrom/data/brown/ca01', debug=0):
    """
    Load tokens from the given file.  
    """
    assert _chktype(1, file, types.StringType)
    assert _chktype(2, debug, types.IntType)
    
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
