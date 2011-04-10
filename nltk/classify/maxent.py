# Natural Language Toolkit: Maximum Entropy Classifiers
#
# Copyright (C) 2001-2011 NLTK Project
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Dmitry Chichkov <dchichkov@gmail.com> (TypedMaxentFeatureEncoding)
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
A classifier model based on maximum entropy modeling framework.  This
framework considers all of the probability distributions that are
empirically consistant with the training data; and chooses the
distribution with the highest entropy.  A probability distribution is
X{empirically consistant} with a set of training data if its estimated
frequency with which a class and a feature vector value co-occur is
equal to the actual frequency in the data.

Terminology: 'feature'
======================
The term I{feature} is usually used to refer to some property of an
unlabeled token.  For example, when performing word sense
disambiguation, we might define a C{'prevword'} feature whose value is
the word preceeding the target word.  However, in the context of
maxent modeling, the term I{feature} is typically used to refer to a
property of a X{labeled} token.  In order to prevent confusion, we
will introduce two distinct terms to disambiguate these two different
concepts:

  - An X{input-feature} is a property of an unlabeled token.
  - A X{joint-feature} is a property of a labeled token.

In the rest of the C{nltk.classify} module, the term X{features} is
used to refer to what we will call X{input-features} in this module.

In literature that describes and discusses maximum entropy models,
input-features are typically called X{contexts}, and joint-features
are simply referred to as X{features}.

Converting Input-Features to Joint-Features
-------------------------------------------
In maximum entropy models, joint-features are required to have numeric
values.  Typically, each input-feature C{input_feat} is mapped to a
set of joint-features of the form::

    joint_feat(token, label) = { 1 if input_feat(token) == feat_val
                               {      and label == some_label
                               {
                               { 0 otherwise

For all values of C{feat_val} and C{some_label}.  This mapping is
performed by classes that implement the L{MaxentFeatureEncodingI}
interface.
"""
__docformat__ = 'epytext en'

import numpy
import time
import tempfile
import os
import gzip

from nltk.compat import defaultdict
from nltk.util import OrderedDict
from nltk.probability import *

import nltk.classify.util # for accuracy & log_likelihood
from api import *
from util import attested_labels, CutoffChecker
from megam import call_megam, write_megam_file, parse_megam_weights
from tadm import call_tadm, write_tadm_file, parse_tadm_weights

######################################################################
#{ Classifier Model
######################################################################

class MaxentClassifier(ClassifierI):
    """
    A maximum entropy classifier (also known as a X{conditional
    exponential classifier}).  This classifier is parameterized by a
    set of X{weights}, which are used to combine the joint-features
    that are generated from a featureset by an X{encoding}.  In
    particular, the encoding maps each C{(featureset, label)} pair to
    a vector.  The probability of each label is then computed using
    the following equation::

                                dotprod(weights, encode(fs,label))
      prob(fs|label) = ---------------------------------------------------
                       sum(dotprod(weights, encode(fs,l)) for l in labels)
    
    Where C{dotprod} is the dot product::

      dotprod(a,b) = sum(x*y for (x,y) in zip(a,b))
    """
    def __init__(self, encoding, weights, logarithmic=True):
        """
        Construct a new maxent classifier model.  Typically, new
        classifier models are created using the L{train()} method.

        @type encoding: L{MaxentFeatureEncodingI}
        @param encoding: An encoding that is used to convert the
            featuresets that are given to the C{classify} method into
            joint-feature vectors, which are used by the maxent
            classifier model.

        @type weights: C{list} of C{float}
        @param weights:  The feature weight vector for this classifier.

        @type logarithmic: C{bool}
        @param logarithmic: If false, then use non-logarithmic weights.
        """
        self._encoding = encoding
        self._weights = weights
        self._logarithmic = logarithmic
        #self._logarithmic = False
        assert encoding.length() == len(weights)

    def labels(self):
        return self._encoding.labels()

    def set_weights(self, new_weights):
        """
        Set the feature weight vector for this classifier.  
        @param new_weights: The new feature weight vector.
        @type new_weights: C{list} of C{float}
        """
        self._weights = new_weights
        assert (self._encoding.length() == len(new_weights))

    def weights(self):
        """
        @return: The feature weight vector for this classifier.
        @rtype: C{list} of C{float}
        """
        return self._weights

    def classify(self, featureset):
        return self.prob_classify(featureset).max()
        
    def prob_classify(self, featureset):
        prob_dict = {}
        for label in self._encoding.labels():
            feature_vector = self._encoding.encode(featureset, label)

            if self._logarithmic:
                total = 0.0
                for (f_id, f_val) in feature_vector:
                    total += self._weights[f_id] * f_val
                prob_dict[label] = total

            else:
                prod = 1.0
                for (f_id, f_val) in feature_vector:
                    prod *= self._weights[f_id] ** f_val
                prob_dict[label] = prod

        # Normalize the dictionary to give a probability distribution
        return DictionaryProbDist(prob_dict, log=self._logarithmic,
                                  normalize=True)
        
    def explain(self, featureset, columns=4):
        """
        Print a table showing the effect of each of the features in
        the given feature set, and how they combine to determine the
        probabilities of each label for that featureset.
        """
        descr_width = 50
        TEMPLATE = '  %-'+str(descr_width-2)+'s%s%8.3f'

        pdist = self.prob_classify(featureset)
        labels = sorted(pdist.samples(), key=pdist.prob, reverse=True)
        labels = labels[:columns]
        print '  Feature'.ljust(descr_width)+''.join(
            '%8s' % str(l)[:7] for l in labels)
        print '  '+'-'*(descr_width-2+8*len(labels))
        sums = defaultdict(int)
        for i, label in enumerate(labels):
            feature_vector = self._encoding.encode(featureset, label)
            feature_vector.sort(key=lambda (fid,_): abs(self._weights[fid]),
                                reverse=True)
            for (f_id, f_val) in feature_vector:
                if self._logarithmic: score = self._weights[f_id] * f_val
                else: score = self._weights[fid] ** f_val
                descr = self._encoding.describe(f_id)
                descr = descr.split(' and label is ')[0] # hack
                descr += ' (%s)' % f_val                 # hack
                if len(descr) > 47: descr = descr[:44]+'...'
                print TEMPLATE % (descr, i*8*' ', score)
                sums[label] += score
        print '  '+'-'*(descr_width-1+8*len(labels))
        print '  TOTAL:'.ljust(descr_width)+''.join(
            '%8.3f' % sums[l] for l in labels)
        print '  PROBS:'.ljust(descr_width)+''.join(
            '%8.3f' % pdist.prob(l) for l in labels)

    def show_most_informative_features(self, n=10, show='all'):
        """
        @param show: all, neg, or pos (for negative-only or positive-only)
        """
        fids = sorted(range(len(self._weights)),
                      key=lambda fid: abs(self._weights[fid]),
                      reverse=True)
        if show == 'pos':
            fids = [fid for fid in fids if self._weights[fid]>0]
        elif show == 'neg':
            fids = [fid for fid in fids if self._weights[fid]<0]
        for fid in fids[:n]:
            print '%8.3f %s' % (self._weights[fid],
                                self._encoding.describe(fid))
                    
    def __repr__(self):
        return ('<ConditionalExponentialClassifier: %d labels, %d features>' %
                (len(self._encoding.labels()), self._encoding.length()))

    #: A list of the algorithm names that are accepted for the
    #: L{train()} method's C{algorithm} parameter.
    ALGORITHMS = ['GIS', 'IIS', 'CG', 'BFGS', 'Powell', 'LBFGSB',
                  'Nelder-Mead', 'MEGAM', 'TADM']

    @classmethod
    def train(cls, train_toks, algorithm=None, trace=3, encoding=None, 
              labels=None, sparse=True, gaussian_prior_sigma=0, **cutoffs):
        """
        Train a new maxent classifier based on the given corpus of
        training samples.  This classifier will have its weights
        chosen to maximize entropy while remaining empirically
        consistent with the training corpus.

        @rtype: L{MaxentClassifier}
        @return: The new maxent classifier

        @type train_toks: C{list}
        @param train_toks: Training data, represented as a list of
            pairs, the first member of which is a featureset,
            and the second of which is a classification label.

        @type algorithm: C{str}
        @param algorithm: A case-insensitive string, specifying which
            algorithm should be used to train the classifier.  The
            following algorithms are currently available.
            
              - Iterative Scaling Methods
                - C{'GIS'}: Generalized Iterative Scaling
                - C{'IIS'}: Improved Iterative Scaling
                
              - Optimization Methods (require C{scipy})
                - C{'CG'}: Conjugate gradient
                - C{'BFGS'}: Broyden-Fletcher-Goldfarb-Shanno algorithm
                - C{'Powell'}: Powell agorithm
                - C{'LBFGSB'}: A limited-memory variant of the BFGS algorithm
                - C{'Nelder-Mead'}: The Nelder-Mead algorithm

              - External Libraries
                - C{'megam'}: LM-BFGS algorithm, with training performed
                  by an U{megam <http://www.cs.utah.edu/~hal/megam/>}.
                  (requires that C{megam} be installed.)

            The default algorithm is C{'CG'} if C{'scipy'} is
            installed; and C{'iis'} otherwise.

        @type trace: C{int}
        @param trace: The level of diagnostic tracing output to produce.
            Higher values produce more verbose output.

        @type encoding: L{MaxentFeatureEncodingI}
        @param encoding: A feature encoding, used to convert featuresets
            into feature vectors.  If none is specified, then a
            L{BinaryMaxentFeatureEncoding} will be built based on the
            features that are attested in the training corpus.

        @type labels: C{list} of C{str}
        @param labels: The set of possible labels.  If none is given, then
            the set of all labels attested in the training data will be
            used instead.

        @param sparse: If true, then use sparse matrices instead of
            dense matrices.  Currently, this is only supported by
            the scipy (optimization method) algorithms.  For other
            algorithms, its value is ignored.
        
        @param gaussian_prior_sigma: The sigma value for a gaussian
            prior on model weights.  Currently, this is supported by
            the scipy (optimization method) algorithms and C{megam}.
            For other algorithms, its value is ignored.
            
        @param cutoffs: Arguments specifying various conditions under
            which the training should be halted.  (Some of the cutoff
            conditions are not supported by some algorithms.)
            
              - C{max_iter=v}: Terminate after C{v} iterations.
              - C{min_ll=v}: Terminate after the negative average
                log-likelihood drops under C{v}.
              - C{min_lldelta=v}: Terminate if a single iteration improves
                log likelihood by less than C{v}.
              - C{tolerance=v}: Terminate a scipy optimization method when
                improvement drops below a tolerance level C{v}.  The
                exact meaning of this tolerance depends on the scipy
                algorithm used.  See C{scipy} documentation for more
                info.  Default values: 1e-3 for CG, 1e-5 for LBFGSB,
                and 1e-4 for other algorithms.  I{(C{scipy} only)}
        """
        if algorithm is None:
            try:
                import scipy
                algorithm = 'cg'
            except ImportError:
                algorithm = 'iis'
        for key in cutoffs:
            if key not in ('max_iter', 'min_ll', 'min_lldelta', 'tolerance', 
                           'max_acc', 'min_accdelta', 'count_cutoff', 
                           'norm', 'explicit', 'bernoulli'):
                raise TypeError('Unexpected keyword arg %r' % key)
        algorithm = algorithm.lower()
        if algorithm == 'iis':
            return train_maxent_classifier_with_iis(
                train_toks, trace, encoding, labels, **cutoffs)
        elif algorithm == 'gis':
            return train_maxent_classifier_with_gis(
                train_toks, trace, encoding, labels, **cutoffs)
        elif algorithm in cls._SCIPY_ALGS:
            return train_maxent_classifier_with_scipy(
                train_toks, trace, encoding, labels, 
                cls._SCIPY_ALGS[algorithm], sparse, 
                gaussian_prior_sigma, **cutoffs)
        elif algorithm == 'megam':
            return train_maxent_classifier_with_megam(
                train_toks, trace, encoding, labels, 
                gaussian_prior_sigma, **cutoffs)
        elif algorithm == 'tadm':
            kwargs = cutoffs
            kwargs['trace'] = trace
            kwargs['encoding'] = encoding
            kwargs['labels'] = labels
            kwargs['gaussian_prior_sigma'] = gaussian_prior_sigma
            return TadmMaxentClassifier.train(train_toks, **kwargs)
        else:
            raise ValueError('Unknown algorithm %s' % algorithm)

    _SCIPY_ALGS = {'cg':'CG', 'bfgs':'BFGS', 'powell':'Powell',
                   'lbfgsb':'LBFGSB', 'nelder-mead':'Nelder-Mead'}


#: Alias for MaxentClassifier.
ConditionalExponentialClassifier = MaxentClassifier


######################################################################
#{ Feature Encodings
######################################################################

class MaxentFeatureEncodingI(object):
    """
    A mapping that converts a set of input-feature values to a vector
    of joint-feature values, given a label.  This conversion is
    necessary to translate featuresets into a format that can be used
    by maximum entropy models.

    The set of joint-features used by a given encoding is fixed, and
    each index in the generated joint-feature vectors corresponds to a
    single joint-feature.  The length of the generated joint-feature
    vectors is therefore constant (for a given encoding).

    Because the joint-feature vectors generated by
    C{MaxentFeatureEncodingI} are typically very sparse, they are
    represented as a list of C{(index, value)} tuples, specifying the
    value of each non-zero joint-feature.

    Feature encodings are generally created using the L{train()}
    method, which generates an appropriate encoding based on the
    input-feature values and labels that are present in a given
    corpus.
    """
    def encode(self, featureset, label):
        """
        Given a (featureset, label) pair, return the corresponding
        vector of joint-feature values.  This vector is represented as
        a list of C{(index, value)} tuples, specifying the value of
        each non-zero joint-feature.
        
        @type featureset: C{dict}
        @rtype: C{list} of C{(int, number)}
        """
        raise AssertionError('Not implemented')

    def length(self):
        """
        @return: The size of the fixed-length joint-feature vectors
            that are generated by this encoding.
        @rtype: C{int}
        """
        raise AssertionError('Not implemented')

    def labels(self):
        """
        @return: A list of the \"known labels\" -- i.e., all labels
            C{l} such that C{self.encode(fs,l)} can be a nonzero
            joint-feature vector for some value of C{fs}.
        @rtype: C{list}
        """
        raise AssertionError('Not implemented')

    def describe(self, fid):
        """
        @return: A string describing the value of the joint-feature
            whose index in the generated feature vectors is C{fid}.
        @rtype: C{str}
        """
        raise AssertionError('Not implemented')

    def train(cls, train_toks):
        """
        Construct and return new feature encoding, based on a given
        training corpus C{train_toks}.

        @type train_toks: C{list} of C{tuples} of (C{dict}, C{str})
        @param train_toks: Training data, represented as a list of
            pairs, the first member of which is a feature dictionary,
            and the second of which is a classification label.
        """
        raise AssertionError('Not implemented')
    
class FunctionBackedMaxentFeatureEncoding(MaxentFeatureEncodingI):
    """
    A feature encoding that calls a user-supplied function to map a
    given featureset/label pair to a sparse joint-feature vector.
    """
    def __init__(self, func, length, labels):
        """
        Construct a new feature encoding based on the given function.

        @type func: (callable)
        @param func: A function that takes two arguments, a featureset
             and a label, and returns the sparse joint feature vector
             that encodes them:

             >>> func(featureset, label) -> feature_vector
        
             This sparse joint feature vector (C{feature_vector}) is a
             list of C{(index,value)} tuples.

        @type length: C{int}
        @param length: The size of the fixed-length joint-feature
            vectors that are generated by this encoding.

        @type labels: C{list}
        @param labels: A list of the \"known labels\" for this
            encoding -- i.e., all labels C{l} such that
            C{self.encode(fs,l)} can be a nonzero joint-feature vector
            for some value of C{fs}.
        """
        self._length = length
        self._func = func
        self._labels = labels
        
    def encode(self, featureset, label):
        return self._func(featureset, label)
        
    def length(self):
        return self._length
    
    def labels(self):
        return self._labels

    def describe(self, fid):
        return 'no description available'
        
class BinaryMaxentFeatureEncoding(MaxentFeatureEncodingI):
    """
    A feature encoding that generates vectors containing a binary
    joint-features of the form::

      joint_feat(fs, l) = { 1 if (fs[fname] == fval) and (l == label)
                          {
                          { 0 otherwise

    Where C{fname} is the name of an input-feature, C{fval} is a value
    for that input-feature, and C{label} is a label.

    Typically, these features are constructed based on a training
    corpus, using the L{train()} method.  This method will create one
    feature for each combination of C{fname}, C{fval}, and C{label}
    that occurs at least once in the training corpus.  

    The C{unseen_features} parameter can be used to add X{unseen-value
    features}, which are used whenever an input feature has a value
    that was not encountered in the training corpus.  These features
    have the form::

      joint_feat(fs, l) = { 1 if is_unseen(fname, fs[fname])
                          {      and l == label
                          {
                          { 0 otherwise

    Where C{is_unseen(fname, fval)} is true if the encoding does not
    contain any joint features that are true when C{fs[fname]==fval}.

    The C{alwayson_features} parameter can be used to add X{always-on
    features}, which have the form::

      joint_feat(fs, l) = { 1 if (l == label)
                          {
                          { 0 otherwise

    These always-on features allow the maxent model to directly model
    the prior probabilities of each label.
    """
    def __init__(self, labels, mapping, unseen_features=False,
                 alwayson_features=False):
        """
        @param labels: A list of the \"known labels\" for this encoding.
        
        @param mapping: A dictionary mapping from C{(fname,fval,label)}
            tuples to corresponding joint-feature indexes.  These
            indexes must be the set of integers from 0...len(mapping).
            If C{mapping[fname,fval,label]=id}, then
            C{self.encode({..., fname:fval, ...}, label)[id]} is 1;
            otherwise, it is 0.
            
        @param unseen_features: If true, then include unseen value
           features in the generated joint-feature vectors.
           
        @param alwayson_features: If true, then include always-on
           features in the generated joint-feature vectors.
        """
        if set(mapping.values()) != set(range(len(mapping))):
            raise ValueError('Mapping values must be exactly the '
                             'set of integers from 0...len(mapping)')
        
        self._labels = list(labels)
        """A list of attested labels."""

        self._mapping = mapping
        """dict mapping from (fname,fval,label) -> fid"""

        self._length = len(mapping)
        """The length of generated joint feature vectors."""

        self._alwayson = None
        """dict mapping from label -> fid"""

        self._unseen = None
        """dict mapping from fname -> fid"""
        
        if alwayson_features:
            self._alwayson = dict([(label,i+self._length)
                                   for (i,label) in enumerate(labels)])
            self._length += len(self._alwayson)

        if unseen_features:
            fnames = set(fname for (fname, fval, label) in mapping)
            self._unseen = dict([(fname, i+self._length)
                                 for (i, fname) in enumerate(fnames)])
            self._length += len(fnames)

    def encode(self, featureset, label):
        # Inherit docs.
        encoding = []

        # Convert input-features to joint-features:
        for fname, fval in featureset.items():
            # Known feature name & value:
            if (fname, fval, label) in self._mapping:
                encoding.append((self._mapping[fname, fval, label], 1))
                
            # Otherwise, we might want to fire an "unseen-value feature".
            elif self._unseen:
                # Have we seen this fname/fval combination with any label?
                for label2 in self._labels:
                    if (fname, fval, label2) in self._mapping:
                        break # we've seen this fname/fval combo
                # We haven't -- fire the unseen-value feature
                else:
                    if fname in self._unseen:
                        encoding.append((self._unseen[fname], 1))

        # Add always-on features:
        if self._alwayson and label in self._alwayson:
            encoding.append((self._alwayson[label], 1))
            
        return encoding

    def describe(self, f_id):
        # Inherit docs.
        if not isinstance(f_id, (int, long)):
            raise TypeError('describe() expected an int')
        try:
            self._inv_mapping
        except AttributeError:
            self._inv_mapping = [-1]*len(self._mapping)
            for (info, i) in self._mapping.items():
                self._inv_mapping[i] = info

        if f_id < len(self._mapping):
            (fname, fval, label) = self._inv_mapping[f_id]
            return '%s==%r and label is %r' % (fname, fval, label)
        elif self._alwayson and f_id in self._alwayson.values():
            for (label, f_id2) in self._alwayson.items():
                if f_id==f_id2: return 'label is %r' % label
        elif self._unseen and f_id in self._unseen.values():
            for (fname, f_id2) in self._unseen.items():
                if f_id==f_id2: return '%s is unseen' % fname
        else:
            raise ValueError('Bad feature id')
        
    def labels(self):
        # Inherit docs.
        return self._labels

    def length(self):
        # Inherit docs.
        return self._length

    @classmethod
    def train(cls, train_toks, count_cutoff=0, labels=None, **options):
        """
        Construct and return new feature encoding, based on a given
        training corpus C{train_toks}.  See the L{class description
        <BinaryMaxentFeatureEncoding>} for a description of the
        joint-features that will be included in this encoding.

        @type train_toks: C{list} of C{tuples} of (C{dict}, C{str})
        @param train_toks: Training data, represented as a list of
            pairs, the first member of which is a feature dictionary,
            and the second of which is a classification label.

        @type count_cutoff: C{int}
        @param count_cutoff: A cutoff value that is used to discard
            rare joint-features.  If a joint-feature's value is 1
            fewer than C{count_cutoff} times in the training corpus,
            then that joint-feature is not included in the generated
            encoding.

        @type labels: C{list}
        @param labels: A list of labels that should be used by the
            classifier.  If not specified, then the set of labels
            attested in C{train_toks} will be used.

        @param options: Extra parameters for the constructor, such as
            C{unseen_features} and C{alwayson_features}.
        """
        mapping = {}              # maps (fname, fval, label) -> fid
        seen_labels = set()       # The set of labels we've encountered
        count = defaultdict(int)  # maps (fname, fval) -> count
        
        for (tok, label) in train_toks:
            if labels and label not in labels:
                raise ValueError('Unexpected label %s' % label)
            seen_labels.add(label)

            # Record each of the features.  
            for (fname, fval) in tok.items():

                # If a count cutoff is given, then only add a joint
                # feature once the corresponding (fname, fval, label)
                # tuple exceeds that cutoff.
                count[fname,fval] += 1
                if count[fname,fval] >= count_cutoff:
                    if (fname, fval, label) not in mapping:
                        mapping[fname, fval, label] = len(mapping)

        if labels is None: labels = seen_labels
        return cls(labels, mapping, **options)

class GISEncoding(BinaryMaxentFeatureEncoding):
    """
    A binary feature encoding which adds one new joint-feature to the
    joint-features defined by L{BinaryMaxentFeatureEncoding}: a
    correction feature, whose value is chosen to ensure that the
    sparse vector always sums to a constant non-negative number.  This
    new feature is used to ensure two preconditions for the GIS
    training algorithm:
      - At least one feature vector index must be nonzero for every
        token.
      - The feature vector must sum to a constant non-negative number
        for every token.
    """
    def __init__(self, labels, mapping, unseen_features=False,
                 alwayson_features=False, C=None):
        """
        @param C: The correction constant.  The value of the correction
            feature is based on this value.  In particular, its value is
            C{C - sum([v for (f,v) in encoding])}.
        @seealso: L{BinaryMaxentFeatureEncoding.__init__}
        """
        BinaryMaxentFeatureEncoding.__init__(
            self, labels, mapping, unseen_features, alwayson_features)
        if C is None:
            C = len(set([fname for (fname,fval,label) in mapping]))+1
            
        self._C = C
        """The non-negative constant that all encoded feature vectors
           will sum to."""
        
    C = property(lambda self: self._C, doc="""
        The non-negative constant that all encoded feature vectors
        will sum to.""")

    def encode(self, featureset, label):
        # Get the basic encoding.
        encoding = BinaryMaxentFeatureEncoding.encode(self, featureset, label)
        base_length = BinaryMaxentFeatureEncoding.length(self)
        
        # Add a correction feature.
        total = sum([v for (f,v) in encoding])
        if total >= self._C:
            raise ValueError('Correction feature is not high enough!')
        encoding.append( (base_length, self._C-total) )
        
        # Return the result
        return encoding

    def length(self):
        return BinaryMaxentFeatureEncoding.length(self) + 1

    def describe(self, f_id):
        if f_id == BinaryMaxentFeatureEncoding.length(self):
            return 'Correction feature (%s)' % self._C
        else:
            return BinaryMaxentFeatureEncoding.describe(self, f_id)


class TadmEventMaxentFeatureEncoding(BinaryMaxentFeatureEncoding):
    def __init__(self, labels, mapping, unseen_features=False, 
                       alwayson_features=False):
        self._mapping = OrderedDict(mapping)
        self._label_mapping = OrderedDict()
        BinaryMaxentFeatureEncoding.__init__(self, labels, self._mapping,
                                                   unseen_features, 
                                                   alwayson_features)
 
    def encode(self, featureset, label):
        encoding = []
        for feature, value in featureset.items():
            if (feature, label) not in self._mapping:
                self._mapping[(feature, label)] = len(self._mapping)
            if value not in self._label_mapping:
                if not isinstance(value, int):
                    self._label_mapping[value] = len(self._label_mapping)
                else:
                    self._label_mapping[value] = value
            encoding.append((self._mapping[(feature, label)], 
                             self._label_mapping[value]))
        return encoding

    def labels(self):
        return self._labels

    def describe(self, fid):
        for (feature, label) in self._mapping:
            if self._mapping[(feature, label)] == fid:
                return (feature, label)

    def length(self):
        return len(self._mapping)

    @classmethod
    def train(cls, train_toks, count_cutoff=0, labels=None, **options):
        mapping = OrderedDict()
        if not labels:
            labels = []
            
        # This gets read twice, so compute the values in case it's lazy.
        train_toks = list(train_toks)        
        
        for (featureset, label) in train_toks:
            if label not in labels:
                labels.append(label)

        for (featureset, label) in train_toks:
            for label in labels:
                for feature in featureset:
                    if (feature, label) not in mapping:
                        mapping[(feature, label)] = len(mapping)
                        
        return cls(labels, mapping, **options)


class TypedMaxentFeatureEncoding(MaxentFeatureEncodingI):
    """
    A feature encoding that generates vectors containing integer, 
    float and binary joint-features of the form::

    Binary (for string and boolean features):
      joint_feat(fs, l) = { 1 if (fs[fname] == fval) and (l == label)
                          {
                          { 0 otherwise
    Value (for integer and float features):
      joint_feat(fs, l) = { fval if     (fs[fname] == type(fval)) 
                          {         and (l == label)
                          {
                          { not encoded otherwise

    Where C{fname} is the name of an input-feature, C{fval} is a value
    for that input-feature, and C{label} is a label.

    Typically, these features are constructed based on a training
    corpus, using the L{train()} method.  

    For string and boolean features [type(fval) not in (int, float)] 
    this method will create one feature for each combination of 
    C{fname}, C{fval}, and C{label} that occurs at least once in the
    training corpus. 

    For integer and float features [type(fval) in (int, float)] this 
    method will create one feature for each combination of C{fname} 
    and C{label} that occurs at least once in the training corpus.

    For binary features the C{unseen_features} parameter can be used 
    to add X{unseen-value features}, which are used whenever an input 
    feature has a value that was not encountered in the training 
    corpus.  These features have the form::

      joint_feat(fs, l) = { 1 if is_unseen(fname, fs[fname])
                          {      and l == label
                          {
                          { 0 otherwise

    Where C{is_unseen(fname, fval)} is true if the encoding does not
    contain any joint features that are true when C{fs[fname]==fval}.

    The C{alwayson_features} parameter can be used to add X{always-on
    features}, which have the form::

      joint_feat(fs, l) = { 1 if (l == label)
                          {
                          { 0 otherwise

    These always-on features allow the maxent model to directly model
    the prior probabilities of each label.
    """
    def __init__(self, labels, mapping, unseen_features=False,
                 alwayson_features=False):
        """
        @param labels: A list of the \"known labels\" for this encoding.

        @param mapping: A dictionary mapping from C{(fname,fval,label)}
            tuples to corresponding joint-feature indexes.  These
            indexes must be the set of integers from 0...len(mapping).
            If C{mapping[fname,fval,label]=id}, then
            C{self.encode({..., fname:fval, ...}, label)[id]} is 1;
            otherwise, it is 0.

        @param unseen_features: If true, then include unseen value
           features in the generated joint-feature vectors.

        @param alwayson_features: If true, then include always-on
           features in the generated joint-feature vectors.
        """
        if set(mapping.values()) != set(range(len(mapping))):
            raise ValueError('Mapping values must be exactly the '
                             'set of integers from 0...len(mapping)')

        self._labels = list(labels)
        """A list of attested labels."""

        self._mapping = mapping
        """dict mapping from (fname,fval,label) -> fid"""

        self._length = len(mapping)
        """The length of generated joint feature vectors."""

        self._alwayson = None
        """dict mapping from label -> fid"""

        self._unseen = None
        """dict mapping from fname -> fid"""

        if alwayson_features:
            self._alwayson = dict([(label,i+self._length)
                                   for (i,label) in enumerate(labels)])
            self._length += len(self._alwayson)

        if unseen_features:
            fnames = set(fname for (fname, fval, label) in mapping)
            self._unseen = dict([(fname, i+self._length)
                                 for (i, fname) in enumerate(fnames)])
            self._length += len(fnames)

    def encode(self, featureset, label):
        # Inherit docs.
        encoding = []

        # Convert input-features to joint-features:
        for fname, fval in featureset.items():
            if(type(fval) in (int, float)):
                # Known feature name & value:
                if (fname, type(fval), label) in self._mapping:
                    encoding.append((self._mapping[fname, type(fval), label], fval))
            else:
                # Known feature name & value:
                if (fname, fval, label) in self._mapping:
                    encoding.append((self._mapping[fname, fval, label], 1))

                # Otherwise, we might want to fire an "unseen-value feature".
                elif self._unseen:
                    # Have we seen this fname/fval combination with any label?
                    for label2 in self._labels:
                        if (fname, fval, label2) in self._mapping:
                            break # we've seen this fname/fval combo
                    # We haven't -- fire the unseen-value feature
                    else:
                        if fname in self._unseen:
                            encoding.append((self._unseen[fname], 1))


        # Add always-on features:
        if self._alwayson and label in self._alwayson:
            encoding.append((self._alwayson[label], 1))

        return encoding

    def describe(self, f_id):
        # Inherit docs.
        if not isinstance(f_id, (int, long)):
            raise TypeError('describe() expected an int')
        try:
            self._inv_mapping
        except AttributeError:
            self._inv_mapping = [-1]*len(self._mapping)
            for (info, i) in self._mapping.items():
                self._inv_mapping[i] = info

        if f_id < len(self._mapping):
            (fname, fval, label) = self._inv_mapping[f_id]
            return '%s==%r and label is %r' % (fname, fval, label)
        elif self._alwayson and f_id in self._alwayson.values():
            for (label, f_id2) in self._alwayson.items():
                if f_id==f_id2: return 'label is %r' % label
        elif self._unseen and f_id in self._unseen.values():
            for (fname, f_id2) in self._unseen.items():
                if f_id==f_id2: return '%s is unseen' % fname
        else:
            raise ValueError('Bad feature id')

    def labels(self):
        # Inherit docs.
        return self._labels

    def length(self):
        # Inherit docs.
        return self._length

    @classmethod
    def train(cls, train_toks, count_cutoff=0, labels=None, **options):
        """
        Construct and return new feature encoding, based on a given
        training corpus C{train_toks}.  See the L{class description
        <TypedMaxentFeatureEncoding>} for a description of the
        joint-features that will be included in this encoding.

        Note: recognized feature values types are (int, float), over
        types are interpreted as regular binary features.

        @type train_toks: C{list} of C{tuples} of (C{dict}, C{str})
        @param train_toks: Training data, represented as a list of
            pairs, the first member of which is a feature dictionary,
            and the second of which is a classification label.

        @type count_cutoff: C{int}
        @param count_cutoff: A cutoff value that is used to discard
            rare joint-features.  If a joint-feature's value is 1
            fewer than C{count_cutoff} times in the training corpus,
            then that joint-feature is not included in the generated
            encoding.

        @type labels: C{list}
        @param labels: A list of labels that should be used by the
            classifier.  If not specified, then the set of labels
            attested in C{train_toks} will be used.

        @param options: Extra parameters for the constructor, such as
            C{unseen_features} and C{alwayson_features}.
        """
        mapping = {}              # maps (fname, fval, label) -> fid
        seen_labels = set()       # The set of labels we've encountered
        count = defaultdict(int)  # maps (fname, fval) -> count

        for (tok, label) in train_toks:
            if labels and label not in labels:
                raise ValueError('Unexpected label %s' % label)
            seen_labels.add(label)

            # Record each of the features.
            for (fname, fval) in tok.items():
                if(type(fval) in (int, float)): fval = type(fval)
                # If a count cutoff is given, then only add a joint
                # feature once the corresponding (fname, fval, label)
                # tuple exceeds that cutoff.
                count[fname,fval] += 1
                if count[fname,fval] >= count_cutoff:
                    if (fname, fval, label) not in mapping:
                        mapping[fname, fval, label] = len(mapping)

        if labels is None: labels = seen_labels
        return cls(labels, mapping, **options)




######################################################################
#{ Classifier Trainer: Generalized Iterative Scaling
######################################################################

def train_maxent_classifier_with_gis(train_toks, trace=3, encoding=None,
                                     labels=None, **cutoffs):
    """
    Train a new C{ConditionalExponentialClassifier}, using the given
    training samples, using the Generalized Iterative Scaling
    algorithm.  This C{ConditionalExponentialClassifier} will encode
    the model that maximizes entropy from all the models that are
    empirically consistent with C{train_toks}.

    @see: L{train_maxent_classifier()} for parameter descriptions.
    """
    cutoffs.setdefault('max_iter', 100)
    cutoffchecker = CutoffChecker(cutoffs)
    
    # Construct an encoding from the training data.
    if encoding is None:
        encoding = GISEncoding.train(train_toks, labels=labels)

    if not hasattr(encoding, 'C'):
        raise TypeError('The GIS algorithm requires an encoding that '
                        'defines C (e.g., GISEncoding).')

    # Cinv is the inverse of the sum of each joint feature vector.
    # This controls the learning rate: higher Cinv (or lower C) gives
    # faster learning.
    Cinv = 1.0/encoding.C
    
    # Count how many times each feature occurs in the training data.
    empirical_fcount = calculate_empirical_fcount(train_toks, encoding)

    # Check for any features that are not attested in train_toks.
    unattested = set(numpy.nonzero(empirical_fcount==0)[0])
    
    # Build the classifier.  Start with weight=0 for each attested
    # feature, and weight=-infinity for each unattested feature.
    weights = numpy.zeros(len(empirical_fcount), 'd')
    for fid in unattested: weights[fid] = numpy.NINF
    classifier = ConditionalExponentialClassifier(encoding, weights)
    
    # Take the log of the empirical fcount.
    log_empirical_fcount = numpy.log2(empirical_fcount)
    del empirical_fcount

    # Old log-likelihood and accuracy; used to check if the change
    # in log-likelihood or accuracy is sufficient to indicate convergence.
    ll_old = None
    acc_old = None

    if trace > 0: print '  ==> Training (%d iterations)' % cutoffs['max_iter']
    if trace > 2:
        print
        print '      Iteration    Log Likelihood    Accuracy'
        print '      ---------------------------------------'

    # Train the classifier.
    try:
        while True:
            if trace > 2:
                ll = cutoffchecker.ll or nltk.classify.util.log_likelihood(
                                                classifier, train_toks)
                acc = cutoffchecker.acc or nltk.classify.util.accuracy(
                                                classifier, train_toks)
                iternum = cutoffchecker.iter
                print '     %9d    %14.5f    %9.3f' % (iternum, ll, acc)
            
            # Use the model to estimate the number of times each
            # feature should occur in the training data.
            estimated_fcount = calculate_estimated_fcount(
                classifier, train_toks, encoding)
    
            # Take the log of estimated fcount (avoid taking log(0).)
            for fid in unattested: estimated_fcount[fid] += 1
            log_estimated_fcount = numpy.log2(estimated_fcount)
            del estimated_fcount
    
            # Update the classifier weights
            weights = classifier.weights()
            weights += (log_empirical_fcount - log_estimated_fcount) * Cinv
            classifier.set_weights(weights)
    
            # Check the log-likelihood & accuracy cutoffs.
            if cutoffchecker.check(classifier, train_toks):
                break
            
    except KeyboardInterrupt:
        print '      Training stopped: keyboard interrupt'
    except:
        raise

    if trace > 2:
        ll = nltk.classify.util.log_likelihood(classifier, train_toks)
        acc = nltk.classify.util.accuracy(classifier, train_toks)
        print '         Final    %14.5f    %9.3f' % (ll, acc)

# Return the classifier.
    return classifier

def calculate_empirical_fcount(train_toks, encoding):
    fcount = numpy.zeros(encoding.length(), 'd')

    for tok, label in train_toks:
        for (index, val) in encoding.encode(tok, label):
            fcount[index] += val

    return fcount

def calculate_estimated_fcount(classifier, train_toks, encoding):
    fcount = numpy.zeros(encoding.length(), 'd')

    for tok, label in train_toks:
        pdist = classifier.prob_classify(tok)
        for label in pdist.samples():
            prob = pdist.prob(label)
            for (fid, fval) in encoding.encode(tok, label):
                fcount[fid] += prob*fval

    return fcount


######################################################################
#{ Classifier Trainer: Improved Iterative Scaling
######################################################################

def train_maxent_classifier_with_iis(train_toks, trace=3, encoding=None,
                                     labels=None, **cutoffs):
    """
    Train a new C{ConditionalExponentialClassifier}, using the given
    training samples, using the Improved Iterative Scaling algorithm.
    This C{ConditionalExponentialClassifier} will encode the model
    that maximizes entropy from all the models that are empirically
    consistent with C{train_toks}.

    @see: L{train_maxent_classifier()} for parameter descriptions.
    """
    cutoffs.setdefault('max_iter', 100)
    cutoffchecker = CutoffChecker(cutoffs)
    
    # Construct an encoding from the training data.
    if encoding is None:
        encoding = BinaryMaxentFeatureEncoding.train(train_toks, labels=labels)
    
    # Count how many times each feature occurs in the training data.
    empirical_ffreq = (calculate_empirical_fcount(train_toks, encoding) /
                       len(train_toks))

    # Find the nf map, and related variables nfarray and nfident.
    # nf is the sum of the features for a given labeled text.
    # nfmap compresses this sparse set of values to a dense list.
    # nfarray performs the reverse operation.  nfident is 
    # nfarray multiplied by an identity matrix.
    nfmap = calculate_nfmap(train_toks, encoding)
    nfarray = numpy.array(sorted(nfmap, key=nfmap.__getitem__), 'd')
    nftranspose = numpy.reshape(nfarray, (len(nfarray), 1))

    # Check for any features that are not attested in train_toks.
    unattested = set(numpy.nonzero(empirical_ffreq==0)[0])

    # Build the classifier.  Start with weight=0 for each attested
    # feature, and weight=-infinity for each unattested feature.
    weights = numpy.zeros(len(empirical_ffreq), 'd')
    for fid in unattested: weights[fid] = numpy.NINF
    classifier = ConditionalExponentialClassifier(encoding, weights)
            
    if trace > 0: print '  ==> Training (%d iterations)' % cutoffs['max_iter']
    if trace > 2:
        print
        print '      Iteration    Log Likelihood    Accuracy'
        print '      ---------------------------------------'

    # Old log-likelihood and accuracy; used to check if the change
    # in log-likelihood or accuracy is sufficient to indicate convergence.
    ll_old = None
    acc_old = None
    
    # Train the classifier.
    try:
        while True:
            if trace > 2:
                ll = cutoffchecker.ll or nltk.classify.util.log_likelihood(
                                                classifier, train_toks)
                acc = cutoffchecker.acc or nltk.classify.util.accuracy(
                                                classifier, train_toks)
                iternum = cutoffchecker.iter
                print '     %9d    %14.5f    %9.3f' % (iternum, ll, acc)
    
            # Calculate the deltas for this iteration, using Newton's method.
            deltas = calculate_deltas(
                train_toks, classifier, unattested, empirical_ffreq, 
                nfmap, nfarray, nftranspose, encoding)
    
            # Use the deltas to update our weights.
            weights = classifier.weights()
            weights += deltas
            classifier.set_weights(weights)
                        
            # Check the log-likelihood & accuracy cutoffs.
            if cutoffchecker.check(classifier, train_toks):
                break
            
    except KeyboardInterrupt:
        print '      Training stopped: keyboard interrupt'
    except:
        raise
            

    if trace > 2:
        ll = nltk.classify.util.log_likelihood(classifier, train_toks)
        acc = nltk.classify.util.accuracy(classifier, train_toks)
        print '         Final    %14.5f    %9.3f' % (ll, acc)
               
    # Return the classifier.
    return classifier

def calculate_nfmap(train_toks, encoding):
    """
    Construct a map that can be used to compress C{nf} (which is
    typically sparse).

    M{nf(feature_vector)} is the sum of the feature values for
    M{feature_vector}.

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
    nfset = set()
    for tok, _ in train_toks:
        for label in encoding.labels():
            nfset.add(sum([val for (id,val) in encoding.encode(tok,label)]))
    return dict([(nf, i) for (i, nf) in enumerate(nfset)])

def calculate_deltas(train_toks, classifier, unattested, ffreq_empirical,
                     nfmap, nfarray, nftranspose, encoding):
    """
    Calculate the update values for the classifier weights for
    this iteration of IIS.  These update weights are the value of
    C{delta} that solves the equation::
    
      ffreq_empirical[i]
             =
      SUM[fs,l] (classifier.prob_classify(fs).prob(l) *
                 feature_vector(fs,l)[i] *
                 exp(delta[i] * nf(feature_vector(fs,l))))

    Where:
        - M{(fs,l)} is a (featureset, label) tuple from C{train_toks}
        - M{feature_vector(fs,l)} = C{encoding.encode(fs,l)}
        - M{nf(vector)} = C{sum([val for (id,val) in vector])}

    This method uses Newton's method to solve this equation for
    M{delta[i]}.  In particular, it starts with a guess of
    C{delta[i]}=1; and iteratively updates C{delta} with::

        delta[i] -= (ffreq_empirical[i] - sum1[i])/(-sum2[i])

    until convergence, where M{sum1} and M{sum2} are defined as::

        sum1[i](delta) = SUM[fs,l] f[i](fs,l,delta)
        
        sum2[i](delta) = SUM[fs,l] (f[i](fs,l,delta) *
                                    nf(feature_vector(fs,l)))
        
      f[i](fs,l,delta) = (classifier.prob_classify(fs).prob(l) *
                          feature_vector(fs,l)[i] *
                          exp(delta[i] * nf(feature_vector(fs,l))))

    Note that M{sum1} and M{sum2} depend on C{delta}; so they need
    to be re-computed each iteration.
    
    The variables C{nfmap}, C{nfarray}, and C{nftranspose} are
    used to generate a dense encoding for M{nf(ltext)}.  This
    allows C{_deltas} to calculate M{sum1} and M{sum2} using
    matrices, which yields a signifigant performance improvement. 

    @param train_toks: The set of training tokens.
    @type train_toks: C{list} of C{tuples} of (C{dict}, C{str})
    @param classifier: The current classifier.
    @type classifier: C{ClassifierI}
    @param ffreq_empirical: An array containing the empirical
        frequency for each feature.  The M{i}th element of this
        array is the empirical frequency for feature M{i}.
    @type ffreq_empirical: C{sequence} of C{float}
    @param unattested: An array that is 1 for features that are
        not attested in the training data; and 0 for features that
        are attested.  In other words, C{unattested[i]==0} iff
        C{ffreq_empirical[i]==0}. 
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
    MAX_NEWTON = 300
    
    deltas = numpy.ones(encoding.length(), 'd')

    # Precompute the A matrix:
    # A[nf][id] = sum ( p(fs) * p(label|fs) * f(fs,label) )
    # over all label,fs s.t. num_features[label,fs]=nf
    A = numpy.zeros((len(nfmap), encoding.length()), 'd')

    for tok, label in train_toks:
        dist = classifier.prob_classify(tok)

        for label in encoding.labels():
            # Generate the feature vector
            feature_vector = encoding.encode(tok,label)
            # Find the number of active features
            nf = sum([val for (id, val) in feature_vector])
            # Update the A matrix
            for (id, val) in feature_vector:
                A[nfmap[nf], id] += dist.prob(label) * val
    A /= len(train_toks)
    
    # Iteratively solve for delta.  Use the following variables:
    #   - nf_delta[x][y] = nfarray[x] * delta[y]
    #   - exp_nf_delta[x][y] = exp(nf[x] * delta[y])
    #   - nf_exp_nf_delta[x][y] = nf[x] * exp(nf[x] * delta[y])
    #   - sum1[i][nf] = sum p(fs)p(label|fs)f[i](label,fs)
    #                       exp(delta[i]nf)
    #   - sum2[i][nf] = sum p(fs)p(label|fs)f[i](label,fs)
    #                       nf exp(delta[i]nf)
    for rangenum in range(MAX_NEWTON):
        nf_delta = numpy.outer(nfarray, deltas)
        exp_nf_delta = 2 ** nf_delta
        nf_exp_nf_delta = nftranspose * exp_nf_delta
        sum1 = numpy.sum(exp_nf_delta * A, axis=0)
        sum2 = numpy.sum(nf_exp_nf_delta * A, axis=0)

        # Avoid division by zero.
        for fid in unattested: sum2[fid] += 1

        # Update the deltas.
        deltas -= (ffreq_empirical - sum1) / -sum2

        # We can stop once we converge.
        n_error = (numpy.sum(abs((ffreq_empirical-sum1)))/
                   numpy.sum(abs(deltas)))
        if n_error < NEWTON_CONVERGE:
            return deltas

    return deltas

######################################################################
#{ Classifier Trainer: scipy algorithms (GC, LBFGSB, etc.)
######################################################################

# [xx] n.b.: it's possible to supply custom trace functions, which
# could be used to make trace output consistent with iis/gis.
def train_maxent_classifier_with_scipy(train_toks, trace=3, encoding=None,
                                       labels=None,  algorithm='CG',
                                       sparse=True, gaussian_prior_sigma=0,
                                       **cutoffs):
    """
    Train a new C{ConditionalExponentialClassifier}, using the given
    training samples, using the specified C{scipy} optimization
    algorithm.  This C{ConditionalExponentialClassifier} will encode
    the model that maximizes entropy from all the models that are
    empirically consistent with C{train_toks}.

    @see: L{train_maxent_classifier()} for parameter descriptions.
    @require: The C{scipy} package must be installed.
    """
    try:
        import scipy
    except ImportError, e:
        raise ValueError('The maxent training algorithm %r requires '
                         'that the scipy package be installed.  See '
                         'http://www.scipy.org/' % algorithm)
    try:
        # E.g., if libgfortran.2.dylib is not found.
        import scipy.sparse, scipy.maxentropy
    except ImportError, e:
        raise ValueError('Import of scipy package failed: %s' % e)
    
    # Construct an encoding from the training data.
    if encoding is None:
        encoding = BinaryMaxentFeatureEncoding.train(train_toks, labels=labels)
    elif labels is not None:
        raise ValueError('Specify encoding or labels, not both')

    labels = encoding.labels()
    labelnum = dict([(label, i) for (i, label) in enumerate(labels)])
    num_features = encoding.length()
    num_toks = len(train_toks)
    num_labels = len(labels)

    # Decide whether to use a sparse matrix or a dense one.  Very
    # limited testing has shown that the lil matrix format
    # (list-of-lists) performs better than csr and csc formats.
    # Limited testing also suggests that the sparse matrix format
    # doesn't save much memory over the dense format in practice
    # (in terms of max memory usage).
    if sparse: zeros = scipy.sparse.lil_matrix
    else: zeros = numpy.zeros

    # Construct the 'F' matrix, which lists the feature values for
    # each training instance.  F[i, j*len(labels)+k] is equal to the
    # value of the i'th feature for the feature vector corresponding
    # to (tok[j], label[k]).
    F = zeros((num_features, num_toks*num_labels))

    # Construct the 'N' matrix, which specifies the correct label for
    # each training instance.  N[0, j*len(labels)+k] is equal to one
    # iff label[k] is the correct label for tok[j].
    N = zeros((1, num_toks*num_labels))

    # Fill in the 'F' and 'N' matrices (just make one pass through the
    # training tokens.)
    for toknum, (featureset, label) in enumerate(train_toks):
        N[0, toknum*len(labels) + labelnum[label]] += 1
        for label2 in labels:
            for (fid, fval) in encoding.encode(featureset, label2):
                F[fid, toknum*len(labels) + labelnum[label2]] = fval

    # Set up the scipy model, based on the matrices F and N.
    model = scipy.maxentropy.conditionalmodel(F, N, num_toks)
    # note -- model.setsmooth() is buggy.
    if gaussian_prior_sigma:
        model.sigma2 = gaussian_prior_sigma**2
    if algorithm == 'LBFGSB':
        model.log = None
    if trace >= 3:
        model.verbose = True
    if 'max_iter' in cutoffs:
        model.maxiter = cutoffs['max_iter']
    if 'tolerance' in cutoffs:
        if algorithm == 'CG': model.avegtol = cutoffs['tolerance']
        elif algorithm == 'LBFGSB': model.maxgtol = cutoffs['tolerance']
        else: model.tol = cutoffs['tolerance']

    # Train the model.
    model.fit(algorithm=algorithm)

    # Convert the model's weights from base-e to base-2 weights.
    weights = model.params * numpy.log2(numpy.e)

    # Build the classifier
    return MaxentClassifier(encoding, weights)

######################################################################
#{ Classifier Trainer: megam
######################################################################

# [xx] possible extension: add support for using implicit file format;
# this would need to put requirements on what encoding is used.  But
# we may need this for other maxent classifier trainers that require
# implicit formats anyway.
def train_maxent_classifier_with_megam(train_toks, trace=3, encoding=None,
                                       labels=None, gaussian_prior_sigma=0,
                                       **kwargs):
    """
    Train a new C{ConditionalExponentialClassifier}, using the given
    training samples, using the external C{megam} library.  This
    C{ConditionalExponentialClassifier} will encode the model that
    maximizes entropy from all the models that are empirically
    consistent with C{train_toks}.

    @see: L{train_maxent_classifier()} for parameter descriptions.
    @see: L{nltk.classify.megam}
    """
    
    explicit = True
    bernoulli = True
    if 'explicit' in kwargs: explicit = kwargs['explicit']
    if 'bernoulli' in kwargs: bernoulli = kwargs['bernoulli']
    
    # Construct an encoding from the training data.
    if encoding is None:
        # Count cutoff can also be controlled by megam with the -minfc
        # option. Not sure where the best place for it is.
        count_cutoff = kwargs.get('count_cutoff', 0)
        encoding = BinaryMaxentFeatureEncoding.train(train_toks, count_cutoff,
                                                     labels=labels, 
                                                     alwayson_features=True)
    elif labels is not None:
        raise ValueError('Specify encoding or labels, not both')

    # Write a training file for megam.
    try:
        fd, trainfile_name = tempfile.mkstemp(prefix='nltk-', suffix='.gz')
        trainfile = gzip.open(trainfile_name, 'wb')
        write_megam_file(train_toks, encoding, trainfile, \
                            explicit=explicit, bernoulli=bernoulli)
        trainfile.close()
    except (OSError, IOError, ValueError), e:
        raise ValueError('Error while creating megam training file: %s' % e)

    # Run megam on the training file.
    options = []
    options += ['-nobias', '-repeat', '10']
    if explicit:
        options += ['-explicit']
    if not bernoulli:
        options += ['-fvals']
    if gaussian_prior_sigma:
        # Lambda is just the precision of the Gaussian prior, i.e. it's the
        # inverse variance, so the parameter conversion is 1.0/sigma**2.
        # See http://www.cs.utah.edu/~hal/docs/daume04cg-bfgs.pdf.
        inv_variance = 1.0 / gaussian_prior_sigma**2
    else:
        inv_variance = 0
    options += ['-lambda', '%.2f' % inv_variance, '-tune']
    if trace < 3:
        options += ['-quiet']
    if 'max_iter' in kwargs:
        options += ['-maxi', '%s' % kwargs['max_iter']]
    if 'll_delta' in kwargs:
        # [xx] this is actually a perplexity delta, not a log
        # likelihood delta
        options += ['-dpp', '%s' % abs(kwargs['ll_delta'])]
    options += ['multiclass', trainfile_name]
    stdout = call_megam(options)
    # print './megam_i686.opt ', ' '.join(options)
    # Delete the training file
    try: os.remove(trainfile_name)
    except (OSError, IOError), e:
        print 'Warning: unable to delete %s: %s' % (trainfile_name, e)

    # Parse the generated weight vector.
    weights = parse_megam_weights(stdout, encoding.length(), explicit)

    # Convert from base-e to base-2 weights.
    weights *= numpy.log2(numpy.e)

    # Build the classifier
    return MaxentClassifier(encoding, weights)

######################################################################
#{ Classifier Trainer: tadm
######################################################################
                            
class TadmMaxentClassifier(MaxentClassifier):
    @classmethod
    def train(cls, train_toks, **kwargs):
        algorithm = kwargs.get('algorithm', 'tao_lmvm')
        trace = kwargs.get('trace', 3)
        encoding = kwargs.get('encoding', None)
        labels = kwargs.get('labels', None)
        sigma = kwargs.get('gaussian_prior_sigma', 0)
        count_cutoff = kwargs.get('count_cutoff', 0)
        max_iter = kwargs.get('max_iter')
        ll_delta = kwargs.get('min_lldelta')
        
        # Construct an encoding from the training data.
        if not encoding:
            encoding = TadmEventMaxentFeatureEncoding.train(train_toks, 
                                                            count_cutoff,
                                                            labels=labels)

        trainfile_fd, trainfile_name = \
            tempfile.mkstemp(prefix='nltk-tadm-events-', suffix='.gz')
        weightfile_fd, weightfile_name = \
            tempfile.mkstemp(prefix='nltk-tadm-weights-')
                    
        trainfile = gzip.open(trainfile_name, 'wb')                    
        write_tadm_file(train_toks, encoding, trainfile)
        trainfile.close()
        
        options = []
        options.extend(['-monitor'])
        options.extend(['-method', algorithm])
        if sigma:
            options.extend(['-l2', '%.6f' % sigma**2])
        if max_iter:
            options.extend(['-max_it', '%d' % max_iter])
        if ll_delta:
            options.extend(['-fatol', '%.6f' % abs(ll_delta)])
        options.extend(['-events_in', trainfile_name])
        options.extend(['-params_out', weightfile_name])
        if trace < 3:
            options.extend(['2>&1'])
        else:
            options.extend(['-summary'])
        
        call_tadm(options)
        
        weightfile = open(weightfile_name, 'rb')
        weights = parse_tadm_weights(weightfile)
        weightfile.close()
        
        os.remove(trainfile_name)
        os.remove(weightfile_name)
    
        # Convert from base-e to base-2 weights.
        weights *= numpy.log2(numpy.e)

        # Build the classifier
        return cls(encoding, weights)
        
######################################################################
#{ Demo
######################################################################
def demo():
    from nltk.classify.util import names_demo
    classifier = names_demo(MaxentClassifier.train)

if __name__ == '__main__':
    demo()
