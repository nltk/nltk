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
X{emperically consistant} with a set of training data if its estimated
frequency for each pair M{(c, f[i])} is equal to the pair's actual
frequency in the data, where M{c} is a class and M{f[i]} is the M{i}th
feature vector element.

                 SUM[t|c[t]=c0] f[i][t]
freq(c0, f[i]) = -----------------------
                    SUM[t] f[i][t]


                 SUM[t] SUM[c] P(c[t]=c0) f[i][t]
prob(c0, f[i]) = ---------------------------------
                 
c[t]
f[i][t]


the frequency of each (class, 

(v,c) pair is equal to the actual
frequency of the (v,c) pair in the training data.

In other
words::

  SUM[t] P(c[t]|f[t]) * f[t][i,c] = SUM[t] freq(c[t]) * 
  
  t[fv][i],c) * P(

  S(t[FEATURE_VECOTR][i] *
                 P(t[FEATURE_VECOTR][i], c)) = 

  SUM[lt] (fd[i](lt) * P(lt)) = SUM[lt] (fd[i](lt) * freq(lt))
  
For all i, where:
  - M{lt} is a labeled text.
  - M{fd[i]} is the feature detector for the M{i}th feature.
  - M{freq(lt)} is the frequency of M{lt} in the training corpus.
  - M{P(lt)} is the estimated probability of M{lt}.

It can be shown that the emperically consistant distribution that
maximizes entropy must have the form::


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

@warning: We plan to significantly refactor the nltk.classifier
    package for the next release of nltk.

@group Classifiers: ConditionalExponentialClassifier
@group Classifier Trainers: GISMaxentClassifierTrainer,
       IISMaxentClassifierTrainer
@group Feature Detector Lists: GIS_FDList
"""

# NOTES TO SELF:
#   - Figure out what to do with FilteredFDList
#   - Add keyword arguments to stop iteration at:
#       - A specified value of classifier_log_likelihood
#       - A specified delta value of classifier_log_likelihood
#       - A specified value of accuracy
#       - A specified delta value of accuracy
#   - Add keyword arguments for IIS, for when to stop Newton's
#      method. 

from nltk.classifier import *
from nltk.feature import *
from nltk.probability import DictionaryProbDist
from nltk.chktype import chktype as _chktype
from nltk.token import Token
from nltk.tokenizer import WhitespaceTokenizer
from nltk.chktype import chktype as _chktype
from nltk import TaskI, PropertyIndirectionMixIn
import time, types

# Don't use from .. imports, because math and Numeric provide
# different definitions for useful functions (exp, log, etc.)
import math, Numeric

##//////////////////////////////////////////////////////
##  Maxent Classifier
##//////////////////////////////////////////////////////

# encoder needs to be kept separate!!
# -> user might want to do different encoding!
# -> or feature selection!
# -> so... classifier works off FEATURE_VECTOR

class ConditionalExponentialClassifier(ClassifierI, PropertyIndirectionMixIn):
    """

    A conditional exponential model for document classification.  This
    model associates a real-valued weight M{w[i,j]} with each feature
    vector index M{i} and class M{j}, which indicates the importance
    of feature vector index M{i} for classifying a text with class
    M{j}.  It predicts the probability of a class for a given text
    using the following formula::

      P(t[CLASS]=c[j]) = 1/Z(t) * (w[0,j] ** t[FEATURE_VECTOR][0]) *
                                  (w[1,j] ** t[FEATURE_VECTOR][1]) *
                                  ...
                                  (w[n,j] ** t[FEATURE_VECTOR][n])

    Where:
      - M{t} is a token
        - M{t[CLASS]} is token M{t}'s class
        - M{t[FEATURE_VECTOR]} is token M{t}'s feature vector
      - M{c} is a list of the possible classes
      - M{w} is the classifier's weight vector
      - M{Z(t)} is a normalization factor, computed by summing
        M{P(c|t)} over all classes::

            Z(t) = SUM[j] P(t[class]=c[j])

    Tokens are classified by assigning them the most likely class:

        classify(t) = ARGMAX[cls] P(t[CLASS]=cls)

    This model is theoretically significant because it is the only
    model that is emperically consistant and maximizes entropy.

    The feature weights can be informally thought of as the
    "importance" of a feature for a given class.  If a weight is one,
    then the corresponding feature has no effect on the decision to
    assign the token to that class.  If the weight is greater that
    one, then the feature will increase the probability estimates for
    the corresponding class.  If the weight is less than one, then the
    feature will decrease the probability estimates for the
    corresponding class.

    This model is sometimes written using the following equivalant
    formulation::

      P(t[CLASS]=c[j]) = 1/Z(t) * (e ** (lambda[0,j] * t[FEATURE_VECTOR][0] +
                                         lambda[1,j] * t[FEATURE_VECTOR][n] +
                                         ...
                                         lambda[n,j] * t[FEATURE_VECTOR][n]))

    where M{lambda[i] = log(w[i])}.  We use the formulation with
    weights M{w[i]} instead of the M{lambda[i]} formulation because
    there is no obvious value of M{lambda[i]} corresponding to
    M{w[i]=0}.

    C{ConditionalExponentialClassifier} requires that input tokens
    define the FEATURE_VECTOR property, which should contain a
    C{SparseList}.
    """
    def __init__(self, classes, weights, **property_names):
        """
        Construct a new conditional exponential classifier model.
        Typically, new classifier models are created by
        C{ClassifierTrainer}s.

        @type classes: C{list}
        @param classes: A list of the classes that can be generated by
            this classifier.  The order of these classes must
            correspond to the order of the weights.
        @type weights: C{list} of C{float}
        @param weights:  The feature weight vector for this classifier.
            Weight M{w[i,j]} is encoded by C{weights[i+j*N]}, where
            C{N} is the length of the feature vector.
        """
        PropertyIndirectionMixIn.__init__(self, **property_names)
        self._classes = classes # <- order matters here!
        self._weights = weights

    def classes(self):
        # Inherit docstring from ClassifierI
        return self._classes

    def set_weights(self, new_weights):
        """
        Set the feature weight vector for this classifier.  Weight
        M{w[i,j]} is encoded by C{weights[i+j*N]}, where C{N} is the
        length of the feature vector.
        @param new_weights: The new feature weight vector.
        @type new_weights: C{list} of C{float}
        """
        self._weights = new_weights

    def weights(self):
        """
        @return: The feature weight vector for this classifier.
        Weight M{w[i,j]} is encoded by C{weights[i+j*N]}, where C{N}
        is the length of the feature vector.
        @rtype new_weights: C{list} of C{float}
        """
        return self._weights

    def get_class_list(self, token):
        pdist = self.get_class_probs(token)
        temp = [(-pdist.prob(c), c) for c in pdist.samples()]
        temp.sort()
        return [c for (_,c) in temp]

    def classify(self, token):
        CLASS = self.property('CLASS')
        token[CLASS] = self.get_class(token)

    def get_class(self, token):
        return self.get_class_probs(token).max()

    def get_class_probs(self, token):
        feature_vector = token[self.property('FEATURE_VECTOR')]
        
        if len(feature_vector)*len(self._classes) != len(self._weights):
            raise ValueError, 'Bad feature vector length'
            
        prob_dict = {}
        for i, cls in enumerate(self._classes):
            # Find the offset into the weights vector.
            offset = i * len(feature_vector)

            # Multiply the weights of all active features for this class.
            prod = 1.0
            for (id, val) in feature_vector.assignments():
                prod *= (self._weights[id+offset] ** val)
            prob_dict[cls] = prod

        # Normalize the dictionary to give a probability distribution
        return DictionaryProbDist(prob_dict, normalize=True)
        
    def __repr__(self):
        return ('<ConditionalExponentialClassifier: %d classes, %d weights>' %
                (len(self._classes), len(self._weights)))

##//////////////////////////////////////////////////////
##  Generalized Iterative Scaling
##//////////////////////////////////////////////////////

class GISFeatureEncoder(FeatureEncoderI, PropertyIndirectionMixIn):
    """
    A feature encoder for use with the generalized iterative scaling
    trainer (C{GISMaxentClassifierTrainer}).  This encoder takes a
    base encoder, and adds two new feature vector values:

      - A feature whose value is always 1.
      - A X{correction feature}, whose value is chosen to ensure that
        the feature vector always sums to a constant non-negative
        number.

    This encoder is used to ensure two preconditions for the GIS
    algorithm:

      - At least one feature vector index must be nonzero for every
        token.
      - The feature vector must sum to a constant non-negative number
        for every token.
    """
    def __init__(self, base_encoder, C=None, **property_names):
        """
        @param C: The correction constant for this encoder.  This
            value must be at least as great as the highest sum of
            feature vectors that could be returned by C{base_encoder}.
            If no value is given, a default of C{len(base_encoder)} is
            used.  While this value is safe (for boolean feature
            vectors), it is highly conservative, and usually leads to
            poor performance.
        @type C: C{int}
        """
        PropertyIndirectionMixIn.__init__(self, **property_names)
        self._encoder = base_encoder
        if C is None:
            self._C = encoder.num_features()
        else:
            self._C = C
        
    def encode_features(self, token):
        # Inherit docs from FeatureEncoderI
        FEATURES = self.property('FEATURES')
        FEATURE_VECTOR = self.property('FEATURE_VECTOR')
        token[FEATURE_VECTOR] = self.raw_encode_features(token[FEATURES])

    def raw_encode_features(self, features):
        # Inherit docs from FeatureEncoderI
        fvlist = self._encoder.raw_encode_features(features)
        correction = self._C - sum([v for (i,v) in fvlist.assignments()])
        fvlist.extend(SparseList({0:correction, 1:1}, 2, 0))
        return fvlist

    def description(self, index):
        # Inherit docs from FeatureEncoderI
        if index == 0: return 'correction'
        if index == 1: return 'constant'
        else: raise IndexError, 'bad feature index'

    def num_features(self):
        # Inherit docs from FeatureEncoderI
        return 2

    def C(self):
        # Inherit docs from FeatureEncoderI
        return self._C

# [XX] requires: features must be encoded with a GISFeatureEncoder!
class GISMaxentClassifierTrainer(ClassifierTrainerI):
    def _fcount_emperical(self, train_toks):
        fcount = Numeric.zeros(self._weight_vector_len, 'd')

        for tok in train_toks:
            feature_vector = tok['FEATURE_VECTOR']
            cls = tok['CLASS']
            offset = self._offsets[cls]
            for (index, val) in feature_vector.assignments():
                fcount[index+offset] += val

        return fcount

    def _fcount_estimated(self, classifier, train_toks):
        fcount = Numeric.zeros(self._weight_vector_len, 'd')

        for tok in train_toks:
            dist = classifier.get_class_probs(tok)
            for cls, offset in self._offsets.items():
                prob = dist.prob(cls)
                for (index, val) in feature_vector.assignments():
                    fcount[index+offset] += prob * val

        return fcount

    def _vector_info(self, feature_vector):
        return sum([v for (i,v) in feature_vector.assignments()])

    def train(self, train_toks, ll_cutoff=None, lldelta_cutoff=None,
              acc_cutoff=None, accdelta_cutoff=None, debug=1,
              iterations=3):

        # Find the set of classes.
        classes = attested_classes(train_toks)
        self._classes = classes

        # Find the length & sum of the first token's feature vector.
        if len(train_toks) == 0:
            raise ValueError('Expected at least one training token')
        vector0 = train_toks[0]['FEATURE_VECTOR']
        self._feature_vector_len = len(vector0)
        self._weight_vector_len = self._feature_vector_len*len(self._classes)
        C = sum([v for (i,v) in vector0.assignments()])

        # Check that all other tokens' feature vectors have the same
        # length and sum.
        for tok in train_toks:
            vector = tok['FEATURE_VECTOR']
            if self._feature_vector_len != len(vector):
                raise ValueError('Feature vectors must be same length')
            if C != sum([v for (i,v) in vector.assignments()]):
                raise ValueError('Feature vectors must have const sum '+
                                 '(try using GISFeatureEncoder)')

        ## Playing with smoothing... (this isn't the best way to do it!)
        #smooth = True # add one to each feature.
        #if smooth:
        #    train_toks = train_toks[:]
        #    assigns = dict([(i,1) for i in range(self._feature_vector_len)])
        #    fvec = SparseList(assigns, self._feature_vector_len, 0)
        #    for cls in classes:
        #        train_toks.append(Token(FEATURE_VECTOR=fvec, CLASS=cls))

        # Cinv is the inverse of the sum of each vector.  This controls
        # the learning rate: higher Cinv (or lower C) gives faster
        # learning.
        Cinv = 1.0/C
        
        # Build the offsets dictionary.  This maps from a class to the
        # index in the weight vector where that class's weights begin.
        self._offsets = dict([(cls, i*self._feature_vector_len)
                              for i, cls in enumerate(classes)])

        # Count how many times each feature occurs in the training data.
        fcount_emperical = self._fcount_emperical(train_toks)
        
        # An array that is 1 whenever fcount_emperical is zero.  In
        # other words, it is one for any feature that's not attested
        # in the training data.  This is used to avoid division by zero.
        unattested = Numeric.zeros(len(fcount_emperical))
        for i in range(len(fcount_emperical)):
            if fcount_emperical[i] == 0: unattested[i] = 1

        # Build the classifier.  Start with weight=1 for each feature,
        # except for the unattested features.  Start those out at
        # zero, since we know that's the correct value.
        weights = Numeric.ones(len(fcount_emperical), 'd')
        weights -= unattested
        classifier = ConditionalExponentialClassifier(classes, weights)

        # Old log-likelihood and accuracy; used to check if the change
        # in log-likelihood or accuracy is sufficient to indicate convergence.
        ll_old = None
        acc_old = None
            
        if debug > 0: print '  ==> Training (%d iterations)' % iterations
        if debug > 2: self._trace_header()

        # Train for a fixed number of iterations.
        for iternum in range(iterations):
            print time.ctime(), ' iterating..'
            if debug > 2: self._trace(iternum, classifier, train_toks)
            
            # Use the model to estimate the number of times each
            # feature should occur in the training data.
            print time.ctime(), '    enter fcount-estimated'
            fcount_estimated = self._fcount_estimated(classifier, train_toks)
            print time.ctime(), '    exit fcount-estimated'

            # Avoid division by zero.
            fcount_estimated += unattested
            
            # Update the classifier weights
            weights = classifier.weights()
            weights *= (fcount_emperical / fcount_estimated) ** Cinv
            classifier.set_weights(weights)

            # Check log-likelihood cutoffs.
            if ll_cutoff is not None or lldelta_cutoff is not None:
                ll = classifier_log_likelihood(classifier, train_toks)
                if ll_cutoff is not None and ll >= -abs(ll_cutoff): break
                if lldelta_cutoff is not None:
                    if ll_old and (ll - ll_old) <= lldelta_cutoff: break
                    ll_old = ll

            # Check accuracy cutoffs.
            if acc_cutoff is not None or accdelta_cutoff is not None:
                acc = accuracy(classifier, train_toks)
                if acc_cutoff is not None and acc >= acc_cutoff: break
                if accdelta_cutoff is not None:
                    if acc_old and (acc_old - acc) <= accdelta_cutoff: break
                    acc_old = acc

        if debug > 2: self._trace(iternum, classifier, train_toks)

        # Return the classifier.
        #print weights
        return classifier

    def _trace_header(self):
        print
        print '      Iteration    Log Likelihood    Accuracy'
        print '      ---------------------------------------'
        
    def _trace(self, iternum, classifier, train_toks):
        print ('     %9d    %14.5f    %9.3f' %
               (iternum+1, classifier_log_likelihood(classifier, train_toks),
                accuracy(classifier, train_toks)))
        print

    def __repr__(self):
        return '<GISMaxentClassifierTrainer: %d features>' % len(self._fd_list)

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

      w[i] := w[i] * (e ** delta[i])

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
    def _ffreq_emperical(self, train_toks):
        """
        Calculate the emperical frequency for each feature.
        The emperical frequency for the M{i}th feature represents the
        average value of the feature values for the M{i}th feature
        over the labeled texts in C{labeled_tokens}.  It is defined
        as::

            SUM[lt] fd_list.detect(lt)[i]/len(labeled_tokens)

        Where M{lt} are the labeled texts from C{labeled_tokens}.

        @return: an array containing the emperical frequency for
            each feature.  The M{i}th element of this array is the
            emperical frequency for feature M{i}.
        @rtype: C{array} of C{float}
        """
        fcount = Numeric.zeros(self._weight_vector_len, 'd')

        for tok in train_toks:
            feature_vector = tok['FEATURE_VECTOR']
            cls = tok['CLASS']
            offset = self._offsets[cls]
            for (index, val) in feature_vector.assignments():
                fcount[index+offset] += val

        return fcount / len(train_toks)

    def _nfmap(self, train_toks):
        """
        Construct a map that can be used to compress C{nf} (which is
        typically sparse).

        M{nf(t)} is the sum of the feature values for M{t}::

            nf(t) = sum(fv(t))

        This represents the number of features that are active for a
        given labeled text.  This method finds all values of M{nf(t)}
        that are attested for at least one token in the given list of
        training tokens; and constructs a dictionary mapping these
        attested values to a continuous range M{0...N}.  For example,
        if the only values of M{nf()} that were attested were 3, 5,
        and 7, then C{_nfmap} might return the dictionary {3:0, 5:1,
        7:2}.

        @return: A map that can be used to compress C{nf} to a dense
            vector.
        @rtype: C{dictionary} from C{int} to C{int}
        """
        # Map from nf to indices.  This allows us to use smaller arrays.
        nfset = Set()
        for i, tok in enumerate(train_toks):
            fvec = tok['FEATURE_VECTOR']
            nfset.add(sum([val for (id,val) in fvec.assignments()]))
        return dict([(nf, i) for (i, nf) in enumerate(nfset)])
    
    def _deltas(self, train_toks, #fd_list, labeled_tokens, labels,
                classifier, unattested, ffreq_emperical, nfmap,
                nfarray, nftranspose):
        """
        Calculate the update values for the classifier weights for
        this iteration of IIS.  These update weights are the value of
        C{delta} that solves the equation::
        
          ffreq_emperical[i]
                 =
          SUM[t,l] (classifier.prob(LabeledText(t,l)) *
                    fd_list.detect(LabeledText(t,l))[i] *
                    exp(delta[i] * nf(LabeledText(t,l))))

        Where:
            - M{t} is a text C{labeled_tokens}
            - M{l} is an element of C{labels}
            - M{nf(ltext)} = SUM[M{j}] C{fd_list.detect}(M{ltext})[M{j}] 

        This method uses Newton's method to solve this equation for
        M{delta[i]}.  In particular, it starts with a guess of
        C{delta[i]}=1; and iteratively updates C{delta} with::

            delta[i] -= (ffreq_emperical[i] - sum1[i])/(-sum2[i])

        until convergence, where M{sum1} and M{sum2} are defined as::
        
          sum1 = SUM[t,l] (classifier.prob(LabeledText(t,l)) *
                           fd_list.detect(LabeledText(t,l))[i] *
                           exp(delta[i] * nf(LabeledText(t,l))))
          sum2 = SUM[t,l] (classifier.prob(LabeledText(t,l)) *
                           fd_list.detect(LabeledText(t,l))[i] *
                           nf(LabeledText(t,l)) *
                           exp(delta[i] * nf(LabeledText(t,l))))

        Note that M{sum1} and M{sum2} depend on C{delta}; so they need
        to be re-computed each iteration.
        
        The variables C{nfmap}, C{nfarray}, and C{nftranspose} are
        used to generate a dense encoding for M{nf(ltext)}.  This
        allows C{_deltas} to calculate M{sum1} and M{sum2} using
        matrices, which yields a signifigant performance improvement. 

        @param fd_list: The feature detector list for the classifier
            that this C{IISMaxentClassifierTrainer} is training.
        @type fd_list: C{FeatureDetectorListI}
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
        
        deltas = Numeric.ones(self._weight_vector_len, 'd')

        # Precompute the A matrix:
        # A[nf][id] = sum ( p(text) * p(label|text) * f(text,label) )
        # over all label,text s.t. num_features[label,text]=nf
        A = Numeric.zeros((len(nfmap), self._weight_vector_len), 'd')

        for i, tok in enumerate(train_toks):
            dist = classifier.get_class_probs(tok)

            # Find the number of active features.
            feature_vector = tok['FEATURE_VECTOR']
            assignments = feature_vector.assignments()
            nf = sum([val for (id, val) in assignments])

            # Update the A matrix
            for cls, offset in self._offsets.items():
                for (id, val) in assignments:
                    A[nfmap[nf], id+offset] += dist.prob(cls) * val
        A /= len(train_toks)

        # Iteratively solve for delta.  Use the following variables:
        #   - nf_delta[x][y] = nf[x] * delta[y]
        #   - exp_nf_delta[x][y] = exp(nf[x] * delta[y])
        #   - nf_exp_nf_delta[x][y] = nf[x] * exp(nf[x] * delta[y])
        #   - sum1[i][nf] = sum p(text)p(label|text)f[i](label,text)
        #                       exp(delta[i]nf)
        #   - sum2[i][nf] = sum p(text)p(label|text)f[i](label,text)
        #                       nf exp(delta[i]nf)
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

    def train(self, train_toks, **kwargs):
        """
        Train a new C{ConditionalExponentialClassifier}, using the
        given training samples.  This
        C{ConditionalExponentialClassifier} should encode the model
        that maximizes entropy from all the models that are
        emperically consistant with C{train_toks}.
        
        @param kwargs: Keyword arguments.
          - C{iterations}: The maximum number of times IIS should
            iterate.  If IIS converges before this number of
            iterations, it may terminate.  Default=C{20}.
            (type=C{int})
            
          - C{debug}: The debugging level.  Higher values will cause
            more verbose output.  Default=C{0}.  (type=C{int})
            
          - C{classes}: The set of possible classes.  If none is given,
            then the set of all classes attested in the training data
            will be used instead.  (type=C{list} of (immutable)).
            
          - C{accuracy_cutoff}: The accuracy value that indicates
            convergence.  If the accuracy becomes closer to one
            than the specified value, then IIS will terminate.  The
            default value is None, which indicates that no accuracy
            cutoff should be used. (type=C{float})

          - C{delta_accuracy_cutoff}: The change in accuracy should be
            taken to indicate convergence.  If the accuracy changes by
            less than this value in a single iteration, then IIS will
            terminate.  The default value is C{None}, which indicates
            that no accuracy-change cutoff should be
            used. (type=C{float})

          - C{log_likelihood_cutoff}: specifies what log-likelihood
            value should be taken to indicate convergence.  If the
            log-likelihod becomes closer to zero than the specified
            value, then IIS will terminate.  The default value is
            C{None}, which indicates that no log-likelihood cutoff
            should be used. (type=C{float})

          - C{delta_log_likelihood_cutoff}: specifies what change in
            log-likelihood should be taken to indicate convergence.
            If the log-likelihood changes by less than this value in a
            single iteration, then IIS will terminate.  The default
            value is C{None}, which indicates that no
            log-likelihood-change cutoff should be used.  (type=C{float})
        """
        assert _chktype(1, train_toks, [Token], (Token,))
        # Process the keyword arguments.
        iter = 20
        debug = 0
        classes = None
        ll_cutoff = lldelta_cutoff = None
        acc_cutoff = accdelta_cutoff = None
        for (key, val) in kwargs.items():
            if key in ('iterations', 'iter'): iter = val
            elif key == 'debug': debug = val
            elif key == 'classes': classes = val
            elif key == 'log_likelihood_cutoff':
                ll_cutoff = abs(val)
            elif key == 'delta_log_likelihood_cutoff':
                lldelta_cutoff = abs(val)
            elif key == 'accuracy_cutoff': 
                acc_cutoff = abs(val)
            elif key == 'delta_accuracy_cutoff':
                accdelta_cutoff = abs(val)
            else: raise TypeError('Unknown keyword arg %s' % key)
        if classes is None:
            classes = attested_classes(train_toks)
            self._classes = classes
            
        # Find the classes, if necessary.
        if classes is None:
            classes = find_classes(train_toks)

        # Find the length of the first token's feature vector.
        if len(train_toks) == 0:
            raise ValueError('Expected at least one training token')
        vector0 = train_toks[0]['FEATURE_VECTOR']
        self._feature_vector_len = len(vector0)
        self._weight_vector_len = self._feature_vector_len*len(self._classes)

        # Build the offsets dictionary.  This maps from a class to the
        # index in the weight vector where that class's weights begin.
        self._offsets = dict([(cls, i*self._feature_vector_len)
                              for i, cls in enumerate(classes)])

        # Find the frequency with which each feature occurs in the
        # training data.
        ffreq_emperical = self._ffreq_emperical(train_toks)

        # Find the nf map, and related variables nfarray and nfident.
        # nf is the sum of the features for a given labeled text.
        # nfmap compresses this sparse set of values to a dense list.
        # nfarray performs the reverse operation.  nfident is 
        # nfarray multiplied by an identity matrix.
        nfmap = self._nfmap(train_toks)
        nfs = nfmap.items()
        nfs.sort(lambda x,y:cmp(x[1],y[1]))
        nfarray = Numeric.array([nf for (nf, i) in nfs], 'd')
        nftranspose = Numeric.reshape(nfarray, (len(nfarray), 1))

        # An array that is 1 whenever ffreq_emperical is zero.  In
        # other words, it is one for any feature that's not attested
        # in the data.  This is used to avoid division by zero.
        unattested = Numeric.zeros(self._weight_vector_len, 'd')
        for i in range(len(unattested)):
            if ffreq_emperical[i] == 0: unattested[i] = 1

        # Build the classifier.  Start with weight=1 for each feature,
        # except for the unattested features.  Start those out at
        # zero, since we know that's the correct value.
        weights = Numeric.ones(self._weight_vector_len, 'd')
        weights -= unattested
        classifier = ConditionalExponentialClassifier(classes, weights)
                
        if debug > 0: print '  ==> Training (%d iterations)' % iter
        if debug > 2:
            print
            print '      Iteration    Log Likelihood    Accuracy'
            print '      ---------------------------------------'

        # Train for a fixed number of iterations.
        for iternum in range(iter):
            if debug > 2:
                print ('     %9d    %14.5f    %9.3f' %
                       (iternum, classifier_log_likelihood(classifier, train_toks),
                        classifier_accuracy(classifier, train_toks)))

            # Calculate the deltas for this iteration, using Newton's method.
            deltas = self._deltas(train_toks, classifier, unattested,
                                  ffreq_emperical, nfmap, nfarray,
                                  nftranspose)

            # Use the deltas to update our weights.
            weights = classifier.weights()
            weights *= Numeric.exp(deltas)
            classifier.set_weights(weights)
                        
            # Check log-likelihood cutoffs.
            if ll_cutoff is not None or lldelta_cutoff is not None:
                ll = classifier_log_likelihood(classifier, train_toks)
                if ll_cutoff is not None and ll > -ll_cutoff: break
                if lldelta_cutoff is not None:
                    if (ll - ll_old) < lldelta_cutoff: break
                    ll_old = ll

            # Check accuracy cutoffs.
            if acc_cutoff is not None or accdelta_cutoff is not None:
                acc = classifier_accuracy(classifier, train_toks)
                if acc_cutoff is not None and acc < acc_cutoff: break
                if accdelta_cutoff is not None:
                    if (acc_old - acc) < accdelta_cutoff: break
                    acc_old = acc

        if debug > 2:
            print ('     %9d    %14.5f    %9.3f' %
                   (iternum+1, classifier_log_likelihood(classifier, train_toks),
                    classifier_accuracy(classifier, train_toks)))
            print
                   
        # Return the classifier.
        return classifier

    def __repr__(self):
        return '<IISMaxentClassifierTrainer: %d features>' % len(self._fd_list)
        

##//////////////////////////////////////////////////////
##  Demonstration
##//////////////////////////////////////////////////////

from nltk.feature import *
from nltk.feature.word import *

def demo(items=30):
    import nltk.corpus
    
    # Load the training data, and split it into test & train.
    print 'reading data...'
    toks = []
    for item in nltk.corpus.brown.items()[:items]:
        text = nltk.corpus.brown.read(item, add_contexts=True)
        toks += text['WORDS']
    
    toks = toks
    split = len(toks)-30
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
        #ContextWordFeatureDetector(offset=-1), # previous word's text
        #ContextWordFeatureDetector(offset=1),  # next word's text
        )

    # Run feature detection on the training data.
    print 'feature detection...'
    for tok in train: detector.detect_features(tok)

    # Create a feature encoder, and run it.
    #encoder = GISFeatureEncoder(learn_encoder(train), C=10)
    encoder = learn_encoder(train)
    for tok in train: encoder.encode_features(tok)

    # Train a new classifier
    print 'training...'
    global classifier
    classifier = IISMaxentClassifierTrainer().train(train, debug=3)

    # Use it to classify the test words.
    print 'classifying...'
    print
    print 'correct? |     token     | cls | class distribution'
    print '---------+---------------+-----+-------------------------------------'
    for tok in test:
        s = '%22s' % tok.exclude('CONTEXT', 'CLASS')
        c = tok['CLASS']
        detector.detect_features(tok)
        encoder.encode_features(tok)
        classifier.classify(tok)
        tok['CLASS_PROBS'] = classifier.get_class_probs(tok)
        if c == tok['CLASS']: s = '   '+s
        else: s = '[X]' + s
        s += ' %-4s  ' % tok['CLASS']
        pdist = tok['CLASS_PROBS']
        probs = [(pdist.prob(val),val) for val in pdist.samples()]
        
        probs.sort(); probs.reverse()
        for prob,val in probs[:3]:
            s += '%5s=%.3f' % (val,prob)
        print s + ' ...'
    
if __name__ == '__main__': demo(30)
