# Natural Language Toolkit: Maxent Classifiers
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
A text classifier model based on maximum entropy modeling framework.
This framework considers all of the probability distributions that are
emperically consistant with the training data; and chooses the
distribution with the highest entropy.  A probability distribution is
X{emperically consistant} with a set of training data if its estimate
for the frequency of each feature is equal to that frequency of the
feature in the training data.  In other words::

  SUM[lt] (fd[i](lt) * P(lt)) = SUM[lt] (fd[i](lt) * freq(lt))
  
For all i, where:
  - M{lt} is a labeled text.
  - M{fd[i]} is the feature detector for the M{i}th feature.
  - M{freq(lt)} is the frequency of M{lt} in the training corpus.
  - M{P(lt)} is the estimated probability of M{lt}.

It can be shown that the emperically consistant distribution that
maximizes entropy must have the form::

  P(l|t) = 1/Z(t) * exp(w[0]*fd[0](LabeledText(t,l)) +
                        w[1]*fd[1](LabeledText(t,l)) +
                        ... +
                        w[n]*fd[n](LabeledText(t,l)))

Where:
  - M{t} is a text.
  - M{l} is a label.
  - M{fd[i]} is the feature detector for the M{i}th feature.
  - M{w[i]} is the weight associated with the M{i}th feature.
  - M{Z(t)} is a normalization factor, computed by summing
    M{P(l|t)} over labels::

        Z(t) = SUM[l] P(l|t)

This form is known as a "conditional exponential model."  The
C{ConditionalExponentialClassier} class implements this model.

C{GISMaxentClassifierTrainer} and C{IISMaxentClassifierTrainer}
implement two different algorithms for training
C{ConditionalExponentialClassifiers}.  Both trainers find the
emperically consistant model which maximizes entropy.
C{GISMaxentClassifierTrainer} uses Generalized Iterative Scaling; and
C{IISMaxentClassifierTrainer} uses Improved Iterative Scaling.
"""

# NOTES TO SELF:
#   - Figure out what to do with FilteredFDList
#   - Add keyword arguments to stop iteration at:
#       - A specified value of log_likelihood
#       - A specified delta value of log_likelihood
#       - A specified value of accuracy
#       - A specified delta value of accuracy
#   - Add keyword arguments for IIS, for when to stop Newton's
#      method. 

from nltk.classifier import *
from nltk.classifier.feature import *
from nltk.classifier.featureselection import *
from nltk.chktype import chktype as _chktype
from nltk.token import Token, WSTokenizer

# Don't use from .. imports, because math and Numeric provide
# different definitions for useful functions (exp, log, etc.)
import math
import Numeric
import time

##//////////////////////////////////////////////////////
##  Maxent Classifier
##//////////////////////////////////////////////////////

class ConditionalExponentialClassifier(AbstractFeatureClassifier):
    """
    A conditional exponential model for document classification.  This
    model associates a real-valued weight M{w[i]} with each feature,
    which indicates the feature's "importance" for classification.  It
    predicts the probability of a label for a given text using the
    formula::

        P(l|t) = 1/Z(t) * (w[0] ** fd[0](LabeledText(t,l))) *
                          (w[1] ** fd[1](LabeledText(t,l))) *
                          ...
                          (w[n] ** fd[n](LabeledText(t,l)))

    Where:
        - M{t} is a text.
        - M{l} is a label.
        - M{fd[i]} is the feature detector for the M{i}th feature.
        - M{w[i]} is the weight associated with the M{i}th feature.
        - M{Z(t)} is a normalization factor, computed by summing
          M{P(l|t)} over labels.

    Similarly, it classifies texts using the formula::
    
        classify(t) = ARGMAX[l] ((w[0] ** fd[0](LabeledText(t,l))) *
                                 (w[1] ** fd[1](LabeledText(t,l))) *
                                 ...
                                 (w[n] ** fd[n](LabeledText(t,l))))

    This model is theoretically significant because it is the only
    model that is emperically consistant and maximizes entropy.

    The feature weights can be informally thought of as the
    "importance" of a feature.  If a weight is zero, then the
    corresponding feature has no effect on classification decisions.
    If the weight is positive, then the feature will increase the
    probability estimates for labels that cause the feature to fire.
    If the weight is negative, then the feature will decrease the 
    probability estimates for labels that cause the feature to fire.

    This model is sometimes written using the following equivalant
    formulation::

        P(l|t) = 1/Z(t) * (e ** (l[0]*fd[0](LabeledText(t,l)) +
                                 l[1]*fd[1](LabeledText(t,l)) +
                                 ... +
                                 l[n]*fd[n](LabeledText(t,l))))

    where M{l[i] = log(w[i])}.  We use the formulation with weights
    M{w[i]} instead of the M{l[i]} formulation because there is no
    obvious value of M{l[i]} corresponding to M{w[i]=0}.
    """
    def __init__(self, fdlist, labels, weights, **kwargs):
        """
        Construct a new conditional exponential classifier model.
        Typically, new classifier models are created by
        C{ClassifierTrainer}s.

        @type fdlist: C{FeatureDetectorListI}
        @param fdlist: The feature detector list defining
            the features that are used by the C{NBClassifier}.  This
            should be the same feature detector list that was used to
            construct the feature value lists that are the samples of
            C{prob_dist}.
        @type labels: C{sequence} of (immutable)
        @param labels: A list of the labels that should be considered
            by this C{NBClassifier}.  Typically, labels are C{string}s
            or C{int}s.
        @type weights: C{sequence} of {float}
        @param weights: The set of feature weights for this
            classifier.  These weights indicate the "importance" of
            each feature for classification.
        """
        # Make sure the weights are an array of floats.
        if type(weights) != Numeric.ArrayType or weights.typecode() != 'd':
            weights = array(weights)

        self._fdlist = fdlist
        self._labels = labels
        self._weights = weights

    def fvlist_likelihood(self, fvlist):
        # Inherit docs from AbstractFeatureClassifier
        prod = 1.0
        for (id, val) in fvlist.assignments():
            prod *= (self._weights[id] ** val)
        return prod

    def weights(self):
        """
        @return: The feature weights that paramaterize this
            classifier.  These weights indicate the "importance" of
            each feature.
        @rtype: C{sequence} of C{float}
        """
        return self._weights

    def set_weights(self, weights):
        """
        Set the feature weights for this classifier.  These weights
        indicate the "importance" of each feature.

        @param weights: The new weight values.
        @type weights: C{sequence} of C{float}
        """
        self._weights = weights

    def __repr__(self):
        """
        @rtype: C{string}
        @return: A string representation of this conditional
            exponential classifier.
        """
        return ('<ConditionalExponentialClassifier: %d labels, %d features>' %
                (len(self._labels), len(self._fdlist)))

##//////////////////////////////////////////////////////
##  Generalized Iterative Scaling
##//////////////////////////////////////////////////////

class GIS_FDList(AbstractFDList):
    """
    A feature detector list which merges a given boolean
    C{FeatureDetectorList} with two new features:

        - A feature whose value is 1 for any C{LabeledText}.
        - A X{correction feature}, whose value is chosen to ensure
          that the feature values returned by C{GIS_FDList} always
          sum to the same non-negative number.

    This feature detector list is used by
    C{GISMaxentClassifierTrainer}, to ensure that two preconditions
    for the C{GIS} algorithm are always met:

        - At least one feature must be active for any C{LabeledText}
        - The feature values must sum to the same non-negative number
          for every C{LabeledText}
    """
    def __init__(self, base_fdlist, C=None):
        """
        Construct a new C{GIS_FDList}.

        @param base_fdlist: The C{FeatureDetectorList} with which to
            merge the two new features.  C{base_fdlist} must contain
            boolean features.
        @type base_fdlist: C{FeatureDetectorListI}

        @param C: The correction constant for this C{GIS_FDList}.  This
            value must be at least as great as the highest sum of
            feature values that could be returned by C{base_fdlist}.
            If no value is given, a default of C{len(base_fdlist)} is
            used.  While this value is safe, it is highly
            conservative, and usually leads to poor performance.
        @type C: C{int}
        """
        self._base_fdlist = base_fdlist
        if C == None: C = len(self._base_fdlist)
        self._C = C
        
    def __len__(self):
        # Inherit docs from FeatureDetectorListI
        return len(self._base_fdlist) + 2

    def detect(self, labeled_text):
        # Inherit docs from FeatureDetectorListI
        values = self._base_fdlist.detect(labeled_text)
        assignments = list(values.assignments())

        # Add the correction feature
        correction = self._C - len(assignments)
        assignments.append( (len(self._base_fdlist)+1, correction) )
        if correction < 0:
            raise ValueError("C value was set too low for GIS_FDList")
        
        # Add the always-on feature
        assignments.append( (len(self._base_fdlist), 1) )

        return SimpleFeatureValueList(assignments, len(self._base_fdlist)+2)

    def C(self):
        """
        @return: The correction constant for this C{GIS_FDList}.  This
            value is at least as great as the highest sum of feature
            values that could be returned by this C{GIS_FDList}'s base
            C{FeatureDetectorList}.
        @rtype: C{int}
        """
        return self._C

class GISMaxentClassifierTrainer(ClassifierTrainerI):
    """
    A Generalized Iterative Scaling implementation of the maximum
    entropy modeling framework.  This framework considers all of the
    probability distributions that are emperically consistant with the
    training data; and chooses the distribution with the highest
    entropy.

    Generalized Iterative Scaling places two constraints its features
    detectors:
    
        - At least one feature must be active for any C{LabeledText}
        - The feature values must sum to the same non-negative number
          for every C{LabeledText}

    These constraints are automatically satisfied by constructing a
    C{GIS_FDList} from the given X{base C{FeatureDetectorList}}.  This
    C{GIS_FDList} takes a X{correction constant} M{C}, which is used
    to ensure the second condition.  M{C} must be greater or equal
    than the maximum number of features that can fire for any labeled
    text.  In other words, the following must be true for every
    labeled text C{lt}::

        len(fdlist.detect(lt).assignments()) <= C

    Lower values of C{C} will cause faster convergance.  However, if
    the above constraint is violated, then GIS may produce incorrect
    results.

    Generalized Iterative Scaling uses an iterative algorithm to find
    the correct weights for a C{ConditionalExponentialClassifier}.  It
    initially sets all weights to zero; it then iteratively updates
    the weights using the formula::

      w[i] := w[i] * (fcount_emperical[i]/fcount_estimated[i]) ** (1/C)

    Where:
    
        - M{w[i]} is the weight of the M{i}th feature.
        - M{C} is the correction constant.
        - C{fcount_emperical}[M{i}] is the sum of the feature values
          for the M{i}th feature over training texts.
        - C{fcount_estimated}[M{i}] is the sum of the feature values
          for the M{i}th feature that is predicted by the current
          model.

    @ivar _fdlist: The feature detector list
    @ivar _labels: The set of labels
    @ivar _debug: The default debug level
    @ivar _iter: The default number of iterations
    """
    def __init__(self, fdlist):
        """
        Construct a new Generalized Iterative Scaling classifier
        trainer for C{ConditionalExponentialClassifier}s.

        @type fdlist: C{FeatureDetectorListI}
        @param fdlist: The base C{FeatureDetectorList} that should be
            used by this classifier.  This C{FeatureDetectorList} will
            be augmented by two additional features: one which is
            always active; and one which ensures that the feature
            values must sum to the same non-negative number for every
            C{LabeledText}
        """
        self._fdlist = fdlist

    def _fcount_emperical(self, fdlist, labeled_tokens):
        """
        Calculate the emperical count for each feature.
        The emperical count for the M{i}th feature
        represents the sum of the feature values for the M{i}th
        feature over the labeled texts in C{labeled_tokens}.  It is
        defined as::

            SUM[lt] fdlist.detect(lt)[i]

        Where M{lt} are the labeled texts from C{labeled_tokens}.

        @type fdlist: C{FeatureDetectorListI}
        @param fdlist: The feature detector list to use to generate
            the emperical counts.
        @type labeled_tokens: C{list} of C{Token} with C{LabeledText}
            type 
        @param labeled_tokens: The tokens whose types should be used to
            calculate emperical counts.
            
        @return: an array containing the emperical count for
            each feature.  The M{i}th element of this array is the
            emperical count for feature M{i}.
        @rtype: C{array} of C{float}
        """
        fcount = Numeric.zeros(len(fdlist), 'd')
        
        for labeled_token in labeled_tokens:
            labeled_text = labeled_token.type()
            values = fdlist.detect(labeled_text)
            for (feature_id, val) in values.assignments():
                fcount[feature_id] += val

        return fcount

    def _fcount_estimated(self, classifier, fdlist,
                          labeled_tokens, labels):
        """
        Calculate the estimated count for each feature.  The
        estimated count for the M{i}th feature represents
        the sum of the feature values for the M{i}th feature over the
        texts in C{labeled_tokens} that is predicted by C{classifier}.
        It is defined as::

            SUM[t] SUM[l] (fdlist.detect(LabeledText(t, l))[i] *
                           classifier.prob(LabeledText(t, l)))

        Where M{t} are the texts from C{labeled_tokens}; and M{l} are
        the elements of C{labels}.
        
        @type classifier: C{ClassifierI}
        @param classifier: The classifier that should be used to
            estimate the probability of labeled texts.
        @type fdlist: C{FeatureDetectorListI}
        @param fdlist: The feature detector list to use to generate
            the estimated counts.
        @type labeled_tokens: C{list} of C{Token} with C{LabeledText}
            type 
        @param labeled_tokens: The tokens whose texts should be used to
            calculate estimated counts.
        @type labels: C{list} of (immutable)
        @param labels: The labels that should be used to
            calculate estimated counts.
            
        @return: an array containing the estimated count for
            each feature.  The M{i}th element of this array is the
            estimated count for feature M{i}.
        @rtype: C{array} of C{float}
        """
        fcount = Numeric.zeros(len(fdlist), 'd')
        for tok in labeled_tokens:
            text = tok.type().text()
            dist = classifier.distribution_list(Token(text, tok.loc()))
            for lnum in range(len(labels)):
                label = labels[lnum]
                p = dist[lnum]
                ltext = LabeledText(text, label)
                fvlist = fdlist.detect(ltext)
                for (fid, val) in fvlist.assignments():
                    fcount[fid] += p * val
        return fcount

    def train(self, labeled_tokens, **kwargs):
        """
        Train a new C{ConditionalExponentialClassifier}, using the
        given training samples.  This
        C{ConditionalExponentialClassifier} should encode the model
        that maximizes entropy from all the models that are
        emperically consistant with C{labeled_tokens}.
        
        @param kwargs: Keyword arguments.
          - C{iterations}: The maximum number of times GIS should
            iterate.  If GIS converges before this number of
            iterations, it may terminate.  Default=C{20}.
            (type=C{int})
          - C{debug}: The debugging level.  Higher values will cause
            more verbose output.  Default=C{0}.  (type=C{int})
          - C{labels}: The set of possible labels.  If none is given,
            then the set of all labels attested in the training data
            will be used instead.  (type=C{list} of (immutable)).
          - C{C}: The correction constant.  This constant is
            required by generalized iterative scaling.  It must be
            greater or equal than the maximum number of features that
            can fire for any labeled text.  In other words, the
            following must be true for every labeled text C{lt}::

                len(fdlist.detect(lt).assignments()) <= C

            Lower values of C{C} will cause faster convergance.
            However, if the above constraint is violated, then GIS may
            produce incorrect results.  Therefore, you should choose
            the lowest value that you are sure obeys the above
            constraint.  Default=C{len(fdlist)}.  (type=C{int})
        """
        # Process the keyword arguments.
        iter = 20
        debug = 0
        C = len(self._fdlist)
        labels = None
        for (key, val) in kwargs.items():
            if key in ('iterations', 'iter'): iter = val
            elif key == 'debug': debug = val
            elif key == 'labels': labels = val
            elif key in ('c', 'C'): C = val
            else: raise TypeError('Unknown keyword arg %s' % key)
        if labels is None:
            labels = find_labels(labeled_tokens)

        # Build the corrected feature detector list
        if debug > 0: print '  ==> Building corrected FDList'
        corrected_fdlist = GIS_FDList(self._fdlist, C)
        Cinv = 1.0 / corrected_fdlist.C()

        # Memoize the feature value lists for training data; this
        # improves speed.
        if debug > 0: print '  ==> Memoizing feature value lists'
        texts = [ltok.type().text() for ltok in labeled_tokens]
        memoized_fdlist = MemoizedFDList(corrected_fdlist,
                                         texts, labels)

        # Count how many times each feature occurs in the training data.
        fcount_emperical = self._fcount_emperical(memoized_fdlist,
                                                  labeled_tokens)
        
        # An array that is 1 whenever fcount_emperical is zero.  In
        # other words, it is one for any feature that's not attested
        # in the data.  This is used to avoid division by zero.
        unattested = Numeric.zeros(len(memoized_fdlist))
        for i in range(len(fcount_emperical)):
            if fcount_emperical[i] == 0: unattested[i] = 1

        # Build the classifier.  Start with weight=1 for each feature,
        # except for the unattested features.  Start those out at
        # zero, since we know that's the correct value.
        weights = Numeric.ones(len(memoized_fdlist), 'd')
        weights -= unattested
        classifier = ConditionalExponentialClassifier(memoized_fdlist, 
                                                      labels, weights)

        if debug > 0: print '  ==> Training (%d iterations)' % iter
        if debug > 2:
            print
            print '      Iteration    Log Likelihood    Accuracy'
            print '      ---------------------------------------'
            
        # Train for a fixed number of iterations.
        for iternum in range(iter):
            if debug > 2:
                print ('     %9d    %14.5f    %9.3f' %
                       (iternum, log_likelihood(classifier, labeled_tokens),
                        accuracy(classifier, labeled_tokens)))
            
            # Use the model to estimate the number of times each
            # feature should occur in the training data.
            fcount_estimated = self._fcount_estimated(classifier,
                                                      memoized_fdlist,
                                                      labeled_tokens,
                                                      labels)
            
            # Avoid division by zero.
            fcount_estimated += unattested
            
            # Update the classifier weights
            weights = classifier.weights()
            weights *= (fcount_emperical / fcount_estimated) ** Cinv
            classifier.set_weights(weights)

        if debug > 2:
            print ('     %9d    %14.5f    %9.3f' %
                   (iternum+1, log_likelihood(classifier, labeled_tokens),
                    accuracy(classifier, labeled_tokens)))
            print

        # Don't use the memoized features.
        return ConditionalExponentialClassifier(corrected_fdlist, labels,
                                                classifier.weights())

    def __repr__(self):
        return '<GISMaxentClassifierTrainer: %d features>' % len(self._fdlist)

##//////////////////////////////////////////////////////
##  IIS
##//////////////////////////////////////////////////////

class IISMaxentClassifierTrainer(ClassifierTrainerI):
    """

    An Improved Iterative Scaling implementation of the maximum
    entropy modeling framework.  This framework considers all of the
    probability distributions that are emperically consistant with the
    training data; and chooses the distribution with the highest
    entropy.

    Improved Iterative Scaling uses an iterative algorithm to find
    the correct weights for a C{ConditionalExponentialClassifier}.  It
    initially sets all weights to zero; it then iteratively updates
    the weights using the formula::

      w[i] := w[i] + (e ** delta[i])

    Where M{delta[i]} is the solution to::

      ffreq_emperical[i] = SUM[t,l] (P(l|t) *
                                      fd[i](LabeledText(l,t)) *
                                      exp(delta[i] *
                                          nf(LabeledText(l,t)))

    Where:
        - C{ffreq_emperical}[M{i}] is the average feature value
          for the M{i}th feature over training texts.
        - M{t} is a text from the training data.
        - M{l} is a label.
        - M{fd[i]} is the feature detector for the M{i}th feature.
        - M{nf}(C{LabeledText(M{l},M{t})}) is the number of
          features that were active for C{LabeledText(M{l},M{t})}.

    C{IISMaxentClassifierTrainer} uses Newton's method to solve for
    M{delta[i]}.
    """
    def __init__(self, fdlist):
        """
        Construct a new Generalized Iterative Scaling classifier
        trainer for C{ConditionalExponentialClassifier}s.

        @type fdlist: C{FeatureDetectorListI}
        @param fdlist: The C{FeatureDetectorList} that should be
            used by this classifier.
        """
        self._fdlist = fdlist

    def _ffreq_emperical(self, fdlist, labeled_tokens):
        """
        Calculate the emperical frequency for each feature.
        The emperical frequency for the M{i}th feature represents the
        average value of the feature values for the M{i}th feature
        over the labeled texts in C{labeled_tokens}.  It is defined
        as::

            SUM[lt] fdlist.detect(lt)[i]/len(labeled_tokens)

        Where M{lt} are the labeled texts from C{labeled_tokens}.

        @type fdlist: C{FeatureDetectorListI}
        @param fdlist: The feature detector list to use to generate
            the emperical frequencies.
        @type labeled_tokens: C{list} of C{Token} with C{LabeledText}
            type 
        @param labeled_tokens: The tokens whose types should be used to
            calculate emperical frequencies.
            
        @return: an array containing the emperical frequency for
            each feature.  The M{i}th element of this array is the
            emperical frequency for feature M{i}.
        @rtype: C{array} of C{float}
        """
        fcount = Numeric.zeros(len(fdlist), 'd')
        
        for labeled_token in labeled_tokens:
            labeled_text = labeled_token.type()
            values = fdlist.detect(labeled_text)
            for (feature_id, val) in values.assignments():
                fcount[feature_id] += val

        return fcount / len(labeled_tokens)

    def _nfmap(self, labeled_tokens, labels, fdlist):
        """
        Construct a map that can be used to compress C{nf} (which is
        typically sparse).

        M{nf(ltext)} is the sum of the feature values for M{ltext}::

            nf(ltext) = SUM[i] fdlist.detect(ltext)[i]

        This represents the number of features that are active for a
        given labeled text.  This method finds all values of M{nf()}
        that are attested for at least one C{LabeledText} whose text
        is derived from C{labeled_tokens} and whose label is an
        element of C{labels}; and constructs a dictionary mapping these
        attested values to a continuous range M{0...N}.  For example,
        if the only values of M{nf()} that were attested were 3, 5,
        and 7, then C{_nfmap} might return the dictionary {3:0, 5:1,
        7:2}.

        @return: A map that can be used to compress C{nf} to a dense
            vector.
        @rtype: C{dictionary} from C{int} to C{int}

        @param labeled_tokens: The set of labeled tokens that should
            be used to decide which values of M{nf()} are attested.
        @type labeled_tokens: C{sequence} of C{Token}
        @param labels: The set of labels that should be used to decide
            which values of M{nf()} are attested.
        @type labels: C{sequence} of (immutable)
        @param fdlist: The feature detector list that should be used
            to find feature value lists for C{LabeledText}s.
        @tyep fdlist: C{FeatureDetectorListI}
        """
        # Map from nf to indices.  This allows us to use smaller arrays. 
        nfmap = {}
        nfnum = 0
        for i in xrange(len(labeled_tokens)):
            for j in xrange(len(labels)):
                nf = 0
                ltext = LabeledText(labeled_tokens[i].type().text(),
                                    labels[j])
                fvlist = fdlist.detect(ltext)
                for (id, val) in fvlist.assignments():
                    nf += val
                if not nfmap.has_key(nf):
                    nfmap[nf] = nfnum
                    nfnum += 1
        return nfmap

    def _deltas(self, fdlist, labeled_tokens, labels,
                classifier, unattested, ffreq_emperical, nfmap,
                nfarray, nftranspose):
        """
        Calculate the update values for the classifier weights for
        this iteration of IIS.  These update weights are the value of
        C{delta} that solves the equation::
        
          ffreq_emperical[i]
                 =
          SUM[t,l] (classifier.prob(LabeledText(t,l)) *
                    fdlist.detect(LabeledText(t,l))[i] *
                    exp(delta[i] * nf(LabeledText(t,l))))

        Where:
            - M{t} is a text C{labeled_tokens}
            - M{l} is an element of C{labels}
            - M{nf(ltext)} = SUM[M{j}] C{fdlist.detect}(M{ltext})[M{j}] 

        This method uses Newton's method to solve this equation for
        M{delta[i]}.  In particular, it starts with a guess of
        C{delta[i]}=1; and iteratively updates C{delta} with::

            delta[i] -= (ffreq_emperical[i] - sum1[i])/(-sum2[i])

        until convergence, where M{sum1} and M{sum2} are defined as::
        
          sum1 = SUM[t,l] (classifier.prob(LabeledText(t,l)) *
                           fdlist.detect(LabeledText(t,l))[i] *
                           exp(delta[i] * nf(LabeledText(t,l))))
          sum2 = SUM[t,l] (classifier.prob(LabeledText(t,l)) *
                           fdlist.detect(LabeledText(t,l))[i] *
                           nf(LabeledText(t,l)) *
                           exp(delta[i] * nf(LabeledText(t,l))))

        Note that M{sum1} and M{sum2} depend on C{delta}; so they need
        to be re-computed each iteration.
        
        The variables C{nfmap}, C{nfarray}, and C{nftranspose} are
        used to generate a dense encoding for M{nf(ltext)}.  This
        allows C{_deltas} to calculate M{sum1} and M{sum2} using
        matrices, which yields a signifigant performance improvement. 

        @param fdlist: The feature detector list for the classifier
            that this C{IISMaxentClassifierTrainer} is training.
        @type fdlist: C{FeatureDetectorListI}
        @param labeled_tokens: The set of training tokens.
        @type labeled_tokens: C{list} of C{Token} with C{LabeledText}
            type
        @param labels: The set of labels that should be considered by
            the classifier constructed by this
            C{IISMaxentClassifierTrainer}. 
        @type labels: C{list} of (immutable)
        @param classifier: The current classifier.
        @type classifier: C{ClassifierI}
        @param ffreq_emperical: An array containing the emperical
            frequency for each feature.  The M{i}th element of this
            array is the emperical frequency for feature M{i}.
        @type ffreq_emperical: C{sequence} of C{float}
        @param unattested: An array that is 1 for features that are
            not attested in the training data; and 0 for features that
            are attested.  In other words, C{unattested[i]==0} iff
            C{ffreq_emperical[i]==0}. 
        @type unattested: C{sequence} of C{int}
        @param nfmap: A map that can be used to compress C{nf} to a dense
            vector.
        @type nfmap: C{dictionary} from C{int} to C{int}
        @param nfarray: An array that can be used to uncompress C{nf}
            from a dense vector.
        @type nfarray: C{array} of C{float}
        @param nftranspose: C{array} of C{float}
        @type nftranspose: The transpose of C{nfarray}
        """
        # These parameters control when we decide that we've
        # converged.  It probably should be possible to set these
        # manually, via keyword arguments to train.
        NEWTON_CONVERGE = 1e-12
        MAX_NEWTON = 30
        
        deltas = Numeric.ones(len(fdlist), 'd')

        # Precompute the A matrix:
        # A[nf][id] = sum ( p(text) * p(label|text) * f(text,label) )
        # over all label,text s.t. num_features[label,text]=nf
        A = Numeric.zeros((len(nfmap),
                           len(fdlist)), 'd')
        for i in xrange(len(labeled_tokens)):
            text = labeled_tokens[i].type().text()
            loc = labeled_tokens[i].loc()
            dist = classifier.distribution_list(Token(text, loc))
            for j in xrange(len(labels)):
                label = labels[j]
                ltext = LabeledText(text, labels[j])
                fvlist = fdlist.detect(ltext)
                assignments = fvlist.assignments()

                # Find the number of active features.
                nf = 0.0
                for (id, val) in assignments:
                    nf += val

                # Update the A matrix.
                for (id, val) in assignments:
                    if dist[j]==0: continue
                    A[nfmap[nf], id] += dist[j] * val
        A /= len(labeled_tokens)
        
        # Iteratively solve for delta.  Use the following variables:
        #   - nf_delta[x][y] = nf[x] * delta[y]
        #   - exp_nf_delta[x][y] = exp(nf[x] * delta[y])
        #   - nf_exp_nf_delta[x][y] = nf[x] * exp(nf[x] * delta[y])
        #   - sum1[i][nf] = sum p(text)p(label|text)f[i](label,text)exp(delta[i]nf)
        #   - sum2[i][nf] = sum p(text)p(label|text)f[i](label,text)nf exp(delta[i]nf)
        for rangenum in range(MAX_NEWTON):
            nf_delta = Numeric.outerproduct(nfarray, deltas)
            exp_nf_delta = Numeric.exp(nf_delta)
            nf_exp_nf_delta = nftranspose * exp_nf_delta
            sum1 = Numeric.sum(exp_nf_delta * A) 
            sum2 = Numeric.sum(nf_exp_nf_delta * A)

            # Avoid division by zero.
            sum2 += unattested

            # Update the deltas.
            deltas -= (ffreq_emperical - sum1) / -sum2

            # We can stop once we converge.
            n_error = (Numeric.sum(abs((ffreq_emperical-sum1)))/
                       Numeric.sum(abs(deltas)))
            if n_error < NEWTON_CONVERGE:
                return deltas

        return deltas

    def train(self, labeled_tokens, **kwargs):
        """
        Train a new C{ConditionalExponentialClassifier}, using the
        given training samples.  This
        C{ConditionalExponentialClassifier} should encode the model
        that maximizes entropy from all the models that are
        emperically consistant with C{labeled_tokens}.
        
        @param kwargs: Keyword arguments.
          - C{iterations}: The maximum number of times IIS should
            iterate.  If IIS converges before this number of
            iterations, it may terminate.  Default=C{20}.
            (type=C{int})
          - C{debug}: The debugging level.  Higher values will cause
            more verbose output.  Default=C{0}.  (type=C{int})
          - C{labels}: The set of possible labels.  If none is given,
            then the set of all labels attested in the training data
            will be used instead.  (type=C{list} of (immutable)).
        """
        # Process the keyword arguments.
        iter = 20
        debug = 0
        labels = None
        for (key, val) in kwargs.items():
            if key in ('iterations', 'iter'):
                iter = val
            elif key == 'debug':
                debug = val
            elif key == 'labels':
                labels = val
            else:
                raise TypeError('Unknown keyword arg %s' % key)
            
        # Find the labels, if necessary.
        if labels is None:
            labels = find_labels(labeled_tokens)

        # Memoize the feature value lists for training data; this
        # improves speed.
        if debug > 0: print '  ==> Memoizing training results'
        texts = [ltok.type().text() for ltok in labeled_tokens]
        memoized_fdlist = MemoizedFDList(self._fdlist,
                                         texts, labels)

        # Find the frequency with which each feature occurs in the
        # training data.
        ffreq_emperical = self._ffreq_emperical(memoized_fdlist,
                                                labeled_tokens)

        # Find the nf map, and related variables nfarray and nfident.
        # nf is the sum of the features for a given labeled text.
        # nfmap compresses this sparse set of values to a dense list.
        # nfarray performs the reverse operation.  nfident is 
        # nfarray multiplied by an identity matrix.
        nfmap = self._nfmap(labeled_tokens, labels, memoized_fdlist)
        nfs = nfmap.items()
        nfs.sort(lambda x,y:cmp(x[1],y[1]))
        nfarray = Numeric.array([nf for (nf, i) in nfs], 'd')
        nftranspose = Numeric.reshape(nfarray, (len(nfarray), 1))

        # An array that is 1 whenever ffreq_emperical is zero.  In
        # other words, it is one for any feature that's not attested
        # in the data.  This is used to avoid division by zero.
        unattested = Numeric.zeros(len(memoized_fdlist))
        for i in range(len(unattested)):
            if ffreq_emperical[i] == 0: unattested[i] = 1

        # Build the classifier.  Start with weight=1 for each feature,
        # except for the unattested features.  Start those out at
        # zero, since we know that's the correct value.
        weights = Numeric.ones(len(memoized_fdlist), 'd')
        weights -= unattested
        classifier = ConditionalExponentialClassifier(memoized_fdlist, 
                                                      labels, weights)
                
        if debug > 0: print '  ==> Training (%d iterations)' % iter
        if debug > 2:
            print
            print '      Iteration    Log Likelihood    Accuracy'
            print '      ---------------------------------------'

        # Train for a fixed number of iterations.
        for iternum in range(iter):
            if debug > 2:
                print ('     %9d    %14.5f    %9.3f' %
                       (iternum, log_likelihood(classifier, labeled_tokens),
                        accuracy(classifier, labeled_tokens)))

            # Calculate the deltas for this iteration, using Newton's method.
            deltas = self._deltas(memoized_fdlist, labeled_tokens,
                                  labels, classifier, unattested,
                                  ffreq_emperical, nfmap, nfarray,
                                  nftranspose)

            # Use the deltas to update our weights.
            weights = classifier.weights()
            weights *= Numeric.exp(deltas)
            classifier.set_weights(weights)
                        
        if debug > 2:
            print ('     %9d    %14.5f    %9.3f' %
                   (iternum+1, log_likelihood(classifier, labeled_tokens),
                    accuracy(classifier, labeled_tokens)))
            print
                   
        # Don't use memoized features.
        return ConditionalExponentialClassifier(self._fdlist, labels,
                                                classifier.weights())

    def __repr__(self):
        return '<IISMaxentClassifierTrainer: %d features>' % len(self._fdlist)
        

##//////////////////////////////////////////////////////
##  Test code
##//////////////////////////////////////////////////////

def simple_test(trainer_class):
    """
    Train the given maxent classifier on a task with a known solution;
    and test the classifier's results for that task.  Print a
    diagnostic message indicating whether the classifier produced the
    correct result.
    """
    labels = "dans en a au pendant".split()
    toks = []
    i = 0
    for tag in "dans en en a a a a a au au".split():
        toks.append(Token(LabeledText('to', tag), i))
        i += 1

    func1 = lambda w:(w.label() in ('dans', 'en'))
    fdlist = LabeledTextFunctionFDList(func1, (1,))

    trainer = trainer_class(fdlist)

    classifier = trainer.train(toks, labels=labels, iter=15)
    dist = classifier.distribution_dictionary(Token('to'))
    print dist
    error = (abs(3.0/20 - dist['dans']) +
              abs(3.0/20 - dist['en']) +
              abs(7.0/30 - dist['a']) +
              abs(7.0/30 - dist['au']) +
              abs(7.0/30 - dist['pendant']))
        
    if (error) > 1e-5:
        print 'WARNING: BROKEN MAXENT IMPLEMENTATION', trainer
        print '  Error: %10.5e' % error
        return 0
    else:
        print 'simple_test passed for', trainer
        return 1

def demo(labeled_tokens, trainer_class,
         n_features=10000, n_words=7, debug=5):
    t = time.time()
    def _timestamp(t):
        return '%8.2fs ' % (time.time()-t)

    if debug: print _timestamp(t), 'Getting a list of labels...'
    labelmap = {}
    for ltok in labeled_tokens:
        labelmap[ltok.type().label()] = 1
    labels = labelmap.keys()
    
    if debug: print _timestamp(t), 'Constructing feature list...'
    f_range = [chr(i) for i in (range(ord('a'), ord('z'))+[ord("'")])]
    fdlist = TextFunctionFDList(lambda w:w[0:1], f_range, labels)
    fdlist += TextFunctionFDList(lambda w:w[-1:], f_range, labels)
    fdlist += TextFunctionFDList(lambda w:w[-2:-1], f_range, labels)
    fdlist += TextFunctionFDList(lambda w:w, ["atlanta's"], labels)
    n_lens = (n_features - len(fdlist))/len(labels)
    fdlist += TextFunctionFDList(lambda w:len(w), range(n_lens), labels)

    # Only use the features that are attested.
    fdselector = AttestedFeatureSelector(labeled_tokens,
                                         min_count=2)
    fdlist = fdselector.select(fdlist)

    trainer = trainer_class(fdlist)
    if debug:
        print _timestamp(t), 'Training', trainer
        print _timestamp(t), '  %d samples' % len(labeled_tokens)
        print _timestamp(t), '  %d features' % len(fdlist)
        print _timestamp(t), '  %d labels' % len(labels)

    # If it's GIS, specify C.
    if trainer_class == GISMaxentClassifierTrainer:
        classifier = trainer.train(labeled_tokens, iter=5,
                                   debug=debug, C=5)
    else:
        classifier = trainer.train(labeled_tokens, iter=5,
                                   debug=debug)
    if debug: print _timestamp(t), '  done training'

    return

    # A few test words...
    toks = WSTokenizer().tokenize("jury the reports aweerdr "+
                                  "atlanta's atlanta_s moowerp's")

    toks = toks * (1+((n_words-1)/len(toks)))
    if debug:print _timestamp(t), 'Testing on %d tokens' % len(toks)
    t = time.time()
    for word in toks:
        if debug: print _timestamp(t), word
        if 1:
            items = classifier.distribution_dictionary(word).items()
            items.sort(lambda x,y:cmp(y[1], x[1]))
            for (label,p) in items[:2]:
                if p > 0.01:
                    print _timestamp(t), '    %3.5f %s' % (p, label)

    return classifier

def get_toks(debug=0):
    from nltk.tagger import TaggedTokenizer
    file = '/mnt/cdrom2/data/brown/ca01'
    text = open(file).read()

    if debug: print 'tokenizing %d chars' % len(text)
    ttoks = TaggedTokenizer().tokenize(text)
    labeled_tokens = [Token(LabeledText(tok.type().base().lower(),
                                           tok.type().tag()),
                               tok.loc())
                         for tok in ttoks]
    if debug: print '  done tokenizing'
    return labeled_tokens

def main():
    toks = get_toks(1)[:100]
    
    # Do some simple tests.
    if simple_test(GISMaxentClassifierTrainer):
        demo(toks, GISMaxentClassifierTrainer)
        print
    if simple_test(IISMaxentClassifierTrainer):
        demo(toks, IISMaxentClassifierTrainer)
        print

if __name__ == '__main__':
    main()
