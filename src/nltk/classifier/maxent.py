# Natural Language Toolkit: Maxent Classifiers
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$


# NOTE TO SELF:
#   Normalize terminology fo variables (fdlist, features
#   featuredetectors, etc)
#
# NOTE TO SELF:
#   Factor out common training code for GIS/IIS

from nltk.classifier import *
from nltk.classifier.feature import *
from nltk.chktype import chktype as _chktype
from nltk.token import Token, WSTokenizer

# Two different exp's!!!
from math import log, exp
import Numeric
import time

##//////////////////////////////////////////////////////
##  Maxent Classifier
##//////////////////////////////////////////////////////

class MaxentClassifier(ClassifierI):
    """
    Model parameters:
      - FeatureDetectorList
      - Set of labels?
      - weights, one for each feature detector
      - normalization constant.  Is this redundant?

    What do do if there are features we haven't seen before??
    """
    def __init__(self, fdlist, labels, weights):
        """
        """
        self._fdlist = fdlist
        self._labels = labels
        self._weights = weights

        # Create a default to return, if we get nothing..
        self._default = {}
        for label in labels:
            self._default[label] = 1.0/len(labels)

    def _zero_distribution(self, text):
        """
        Try to find the distribution, even though there are features
        whose weights are zero.  Assume that zeros cancel each other
        out (one-for-one).
        """
        #dist = {}
        #for l in self._labels: dist[l]=0
        #return dist
        return self._default
        dist = {}
        min_zeros = 10000

        # Find the non-normalized probability estimates
        for label in self._labels:
            labeled_text = LabeledText(text, label)
            featurevalues = self._fdlist.detect(labeled_text)
            zeros = 0
            p = 1.0
            for (id,val) in featurevalues.assignments():
                if self._weights[id] == 0:
                    zeros += 1
                elif val == 1:
                    p *= self._weights[id]
                else: p *= (self._weights[id] ** val)
                    
            dist[label] = (p, zeros)
            min_zeros = min(zeros, min_zeros)

        # Handle the zeros.
        total_p = 0.0
        for (label, (p, zeros)) in dist.items():
            if zeros > min_zeros:
                dist[label] = 0
            else:
                dist[label] = p
                total_p += p

        # Normalize our probability estimates
        for (label, p) in dist.items():
            dist[label] = p / total_p

        return dist

    def _zero_classify(self, text):
        dist = self._zero_distribution(text)
        max = (None, 0.0)
        for (label, p) in dist.items():
            if p > max[1]: max = (label, p)
        return max[0]

    def distribution(self, text):
        # Inherit docs.
        total_p = 0.0
        dist = {}

        # Find the non-normalized probability estimates
        for label in self._labels:
            labeled_text = LabeledText(text, label)
            featurevalues = self._fdlist.detect(labeled_text)
            p = 1.0
            for (id,val) in featurevalues.assignments():
                if val == 1: p *= self._weights[id]
                else: p *= (self._weights[id] ** val)
                    
            dist[label] = p
            total_p += p

        # What should we do if nothing is possible?
        if total_p == 0:
            return self._zero_distribution(text)

        # Normalize our probability estimates
        for (label, p) in dist.items():
            dist[label] = p / total_p

        return dist

    def classify(self, text):
        # Inherit docs
        max_p = 0
        max_label = None

        # Find the label that maximizes the non-normalized probability
        # estimates.
        for label in self._labels:
            labeled_text = LabeledText(text, label)
            featurevalues = self._fdlist.detect(labeled_text)
            p = 1.0
            for (id,val) in featurevalues.assignments():
                if val == 1: p *= self._weights[id]
                else: p *= (self._weights[id] ** val)
            if p > max_p:
                max_p = p
                max_label = label

        if max_label is None:
            return self._zero_classify(text)

        return max_label

    def weights(self):
        return self._weights

    def features(self):
        return self._fdlist

    def labels(self):
        return self._labels

    def accuracy(self, labeled_tokens):
        """
        Test this model's accuracy on the given list of labeled
        tokens. 
        """
        #for i in range(len(self._weights)):
        #     if self._weights[i] == 0: print 'ouch 0:', i
        #     if self._weights[i] == 1e1000: print 'ouch inf:', i
        #
        total = 0
        correct = 0
        for tok in labeled_tokens:
            text = tok.type().text()
            label = tok.type().label()
            if self.classify(text) == label:
                correct += 1
            total += 1
        return float(correct)/total            
    
    def log_likelihood(self, labeled_tokens):
        """
        Test this model's accuracy on the given list of labeled
        tokens. 
        """
        likelihood = 0.0
        for tok in labeled_tokens:
            text = tok.type().text()
            label = tok.type().label()
            dist = self.distribution(text)
            if dist[label] == 0:
                # Um.. What should we do here??
                likelihood -= 1e1000
            else:
                likelihood += log(dist[label])
        return likelihood
    
    def __repr__(self):
        """
        @rtype: C{string}
        @return: A string representation of this Naive Bayes
            classifier.  
        """
        return ('<MaxentClassifier: %d labels, %d features>' %
                (len(self._labels), len(self._fdlist)))

##//////////////////////////////////////////////////////
##  GIS
##//////////////////////////////////////////////////////

class GIS_FDList(AbstractFDList):
    """
    Adds 2 features to a feature list:
      - one feature that's always on
      - one correction feature.
    """
    def __init__(self, sub_fdlist, C):
        self._sub_fdlist = sub_fdlist
        if C == None: C = len(self._sub_fdlist)
        self._C = C
        
    def __len__(self):
        return len(self._sub_fdlist) + 2

    def detect(self, labeled_text):
        values = self._sub_fdlist.detect(labeled_text)
        assignments = values.assignments()

        # Add the correction feature
        correction = self._C - len(assignments)
        assignments.append( (len(self._sub_fdlist)+1, correction) ) 
        
        # Add the always-on feature
        assignments.append( (len(self._sub_fdlist), 1) )

        return SimpleFeatureValueList(assignments, len(self._sub_fdlist)+2)

    def C(self):
        return self._C

class MemoizedFDList(AbstractFDList):
    """
    Remember the feature detector lists for the training data, so we
    don't need to re-compute them.
    """
    def __init__(self, fdlist, labeled_text_toks, labels):
        self._cache = {}
        self._fdlist = fdlist
        for tok in labeled_text_toks:
            text = tok.type().text()
            for label in labels:
                ltext = LabeledText(text, label)
                self._cache[ltext] = fdlist.detect(ltext)

    def detect(self, labeled_text):
        return self._cache[labeled_text]

    def __len__(self):
        return len(self._fdlist)

class FilteredFDList(AbstractFDList):
    """
    Only include features that mean something.
    """
    def __init__(self, fdlist, labeled_toks, labels):
        self._fdlist = fdlist
        
        useful = Numeric.zeros(len(fdlist))
        for tok in labeled_toks:
            text = tok.type().text()
            for label in labels:
                #fvlist = fdlist.detect(LabeledText(text, label))
                fvlist = fdlist.detect(tok.type())
                for (id, val) in fvlist.assignments():
                    useful[id] = 1
        self._len = Numeric.sum(useful)
        self._idmap = Numeric.zeros(len(fdlist))
        src = 0
        for dest in range(len(useful)):
            if useful[dest]:
                self._idmap[dest] = src
                src += 1
            else:
                self._idmap[dest] = -1
                
    def __len__(self):
        return self._len

    def detect(self, ltext):
        assignments = [(self._idmap[id], val) for (id, val)
                       in self._fdlist.detect(ltext).assignments()
                       if self._idmap[id] >= 0]
        #if len(assignments) > 0:
        #    print ltext, assignments
        #    if randint(0, 10) == 0: raise ValueError()
        return SimpleFeatureValueList(assignments, self._len)

# Implementation node: this class is *not* thread-safe.
class GISMaxentClassifierTrainer(ClassifierTrainerI):
    """
    @ivar _fdlist: The feature detector list
    @ivar _labels: The set of labels
    @ivar _debug: The default debug level
    @ivar _iter: The default number of iterations
    """
    def __init__(self, fdlist, labels=None):
        """
        Construct a new classifier trainer, using the given feature
        detector list.

        """
        self._fdlist = fdlist

    def _fcount_emperical(self, fdlist, labeled_tokens):
        """
        Find the frequency of each feature..
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
        fcount = Numeric.zeros(len(fdlist), 'd')
        for tok in labeled_tokens:
            text = tok.type().text()
            dist = classifier.distribution(text)
            for lnum in range(len(labels)):
                label = labels[lnum]
                p = dist[label]
                ltext = LabeledText(text, label)
                fvlist = fdlist.detect(ltext)
                for (fid, val) in fvlist.assignments():
                    fcount[fid] += p * val
        return fcount

    def train(self, labeled_tokens, **kwargs):
        """
        @param kwargs: Keyword arguments.
          - C{iterations}: The maximum number of times GIS should
            iterate.  If GIS converges before this number of
            iterations, it may terminate.  Default=C{5}.
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
        iter = 5
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
        corrected_fdlist = GIS_FDList(self._fdlist, C)
        Cinv = 1.0 / corrected_fdlist.C()

        if debug > 0: print '  ==> Filtering training results'
        filtered_fdlist = FilteredFDList(corrected_fdlist,
                                         labeled_tokens,
                                         labels)
        
        # Memoize the results..
        if debug > 0: print '  ==> Memoizing training results'
        memoized_fdlist = MemoizedFDList(filtered_fdlist,
                                         labeled_tokens,
                                         labels)

        # Count how many times each feature occurs in the training
        # data.  This represents an emperical estimate for the
        # frequency of each feature.
        fcount_emperical = self._fcount_emperical(memoized_fdlist,
                                                  labeled_tokens)

        # Build the classifier.  Start with weight=1 for each feature.
        weights = Numeric.ones(len(memoized_fdlist), 'd')
        classifier = MaxentClassifier(memoized_fdlist, 
                                      labels, weights)

        # Train for a fixed number of iterations.
        if debug > 0:
            print '  ==> Training (%d iterations)' % iter
        for i in range(iter):
            if debug > 3:
                accuracy = classifier.accuracy(labeled_tokens)
                print ('    --> Accuracy = %.3f' % accuracy)
                ll = classifier.log_likelihood(labeled_tokens)
                print ('    --> Log Likelihood = %.3f' % ll)

            if debug > 1:
                print '    ==> Training iteration %d' % (i+1)
            
            # Use the model to estimate the number of times each
            # feature should occur in the training data.  This
            # represents our model's estimate for the frequency of
            # each feature.
            if debug > 2: print '    --> Finding fcount_estimated'
            fcount_estimated = self._fcount_estimated(classifier,
                                                      memoized_fdlist,
                                                      labeled_tokens,
                                                      labels)
                    
            if debug > 2: print '    --> Updating weights'
            # Use fcount_estimated to update the classifier weights
            weights = classifier.weights()
            
            for fid in range(len(weights)):
                if fcount_emperical[fid]==0:
                    weights[fid] = 0.0
                    continue
                weights[fid] *= ( fcount_emperical[fid] /
                                  fcount_estimated[fid] )**Cinv

        if debug > 3: 
            accuracy = classifier.accuracy(labeled_tokens)
            print ('    --> Accuracy = %.3f' % accuracy)
            ll = classifier.log_likelihood(labeled_tokens)
            print ('    --> Log Likelihood = %.3f' % ll)
                   

        global gis_classifier
        gis_classifier = MaxentClassifier(filtered_fdlist, labels,
                                classifier.weights())
        global gis_fdlist
        gis_fdlist = filtered_fdlist
                
        # Make sure to use the un-memoized features for the classifier
        # we return.
        return MaxentClassifier(filtered_fdlist, labels,
                                classifier.weights())

   def __repr__(self):
        return '<GISMaxentClassifierTrainer: %d features>' % len(self._fdlist)

##//////////////////////////////////////////////////////
##  IIS
##//////////////////////////////////////////////////////

class IISMaxentClassifierTrainer(ClassifierTrainerI):
    """
    """
    def __init__(self, fdlist):
        """
        Construct a new classifier trainer, using the given feature
        detector list.

        """
        self._fdlist = fdlist

    def _ffreq_emperical(self, fdlist, labeled_tokens):
        """
        Find the frequency of each feature..
        """
        fcount = Numeric.zeros(len(fdlist), 'd')
        
        for labeled_token in labeled_tokens:
            labeled_text = labeled_token.type()
            values = fdlist.detect(labeled_text)
            for (feature_id, val) in values.assignments():
                fcount[feature_id] += val

        return fcount / len(labeled_tokens)

    def _nf_init(self, labeled_tokens, labels, num_features):
        """
        Initialize some useful variables having to do with nf.  These
        are all constant for any given training session.
        """
        # Map from nf to indices.  This allows us to use smaller arrays. 
        nfmap = {}
        nfnum = 0
        for i in xrange(len(labeled_tokens)):
            for j in xrange(len(labels)):
                nf = num_features[i, j]
                if not nfmap.has_key(nf):
                    nfmap[nf] = nfnum
                    nfnum += 1
        nfs = nfmap.items()
        nfs.sort(lambda x,y:cmp(x[1],y[1]))
        nfs = [nf for (nf, i) in nfs]
                    
        self._nfarray = Numeric.array(nfs, 'd')
        self._nfident = Numeric.identity(len(self._nfarray)) * self._nfarray
        self._nfmap = nfmap

    def _deltas1(self, memoized_fdlist, labeled_tokens, labels,
                 classifier, num_features, useless, useful,
                 ffreq_emperical):
        """
        Find the deltas, using Newton's method.  This particular
        version uses Numeric to do its computations.  But it might
        take too much memory if fn can take on too many different
        values

        Size requirement: sizeof(double)*
        """
        NEWTON_CONVERGE = 1e-12
        MAX_NEWTON = 30
        
        deltas = Numeric.ones(len(memoized_fdlist), 'd')

        # Precompute the A matrix.
        # A[nf][id] = sum ( p(text) * p(label|text) * f(text,label) )
        # over all label,text s.t. num_features[label,text]=nf
        A = Numeric.zeros((len(self._nfmap),
                           len(memoized_fdlist)), 'd')
        for i in xrange(len(labeled_tokens)):
            text = labeled_tokens[i].type().text()
            dist = classifier.distribution(text)
            for j in xrange(len(labels)):
                label = labels[j]
                nf = num_features[i, j]
                ltext = LabeledText(text, labels[j])
                fvlist = memoized_fdlist.detect(ltext)
                for (id, val) in fvlist.assignments():
                    if dist[label]==0: continue
                    A[self._nfmap[nf], id] += dist[label] * val
        A /= len(labeled_tokens)
        
        # Now solve for delta.
        for rangenum in range(MAX_NEWTON):
            # nf_delta[x][y] = nf[x] * delta[y]
            nf_delta = Numeric.outerproduct(self._nfarray, deltas)

            # exp_nf_delta[x][y] = exp(nf[x] * delta[y])
            exp_nf_delta = Numeric.exp(nf_delta)

            # nf_exp_nf_delta[x][y] = nf[x] * exp(nf[x] * delta[y])
            nf_exp_nf_delta = Numeric.matrixmultiply(self._nfident, exp_nf_delta)

            # sum1[i][nf] = sum p(text)p(label|text)f[i](label,text)exp(delta[i]nf)
            # sum2[i][nf] = sum p(text)p(label|text)f[i](label,text)nf exp(delta[i]nf)
            sum1 = Numeric.sum(exp_nf_delta * A) 
            sum2 = Numeric.sum(nf_exp_nf_delta * A)

            # Avoid division by zero.
            sum2 += useless
            
            # Update the deltas.
            deltas -= (ffreq_emperical - sum1) / -sum2
            deltas *= useful

            # We can stop once we converge.
            n_error = (Numeric.sum(abs((ffreq_emperical-sum1)*useful))/
                       Numeric.sum(abs(deltas)))
            if n_error < NEWTON_CONVERGE:
                return deltas

        return deltas

    def _deltas2(self, memoized_fdlist, labeled_tokens, labels,
                 classifier, num_features, useless, useful,
                 ffreq_emperical):
        """
        Find the deltas, using Newton's method.
        """
        NEWTON_CONVERGE = 1e-12
        MAX_NEWTON = 30
        
        deltas = Numeric.ones(len(memoized_fdlist), 'd')

        for rangenum in range(MAX_NEWTON):
            sum1 = Numeric.zeros(len(memoized_fdlist), 'd')
            sum2 = useless.copy()
            for i in xrange(len(labeled_tokens)):
                text = labeled_tokens[i].type().text()
                dist = classifier.distribution(text)
                for j in xrange(len(labels)):
                    label = labels[j]
                    nf = num_features[i, j]
                    ltext = LabeledText(text, labels[j])
                    fvlist = memoized_fdlist.detect(ltext)
                    for (id, val) in fvlist.assignments():
                        if dist[label]==0: continue
                        x = (dist[label] * val *
                             exp(deltas[id] * nf))
                        sum1[id] += x
                        sum2[id] += x * nf

            # Normalize the sums
            sum1 /= len(labeled_tokens)
            sum2 /= len(labeled_tokens)

            # Update the deltas.
            deltas -= (ffreq_emperical - sum1) / -sum2
            deltas *= useful

            # We can stop once we converge.
            n_error = (Numeric.sum(abs((ffreq_emperical-sum1)*useful))/
                       Numeric.sum(abs(deltas)))
            if n_error < NEWTON_CONVERGE:
                break

        return deltas
                
    def train(self, labeled_tokens, **kwargs):
        """
        @param kwargs: Keyword arguments.
          - C{iterations}: The maximum number of times GIS should
            iterate.  If GIS converges before this number of
            iterations, it may terminate.  Default=C{5}.
            (type=C{int})
          - C{debug}: The debugging level.  Higher values will cause
            more verbose output.  Default=C{0}.  (type=C{int})
          - C{labels}: The set of possible labels.  If none is given,
            then the set of all labels attested in the training data
            will be used instead.  (type=C{list} of (immutable)).
        """
        # Process the keyword arguments.
        iter = 5
        debug = 0
        labels = None
        for (key, val) in kwargs.items():
            if key in ('iterations', 'iter'):
                iter = val
            elif key == 'debug':
                debug = val
            elif key == 'labels':
                labels = val
            elif key == 'C':
                pass #Ignore for now.. Fix me later.
            else:
                raise TypeError('Unknown keyword arg %s' % key)
            
        # Find the labels, if necessary.
        if labels is None:
            labels = find_labels(labeled_tokens)

        # Select out the features that actually mean anything.
        if debug > 0: print '  ==> Filtering training results'
        filtered_fdlist = self._fdlist
        #filtered_fdlist = (
        #     AlwaysFDList() +
        #     FilteredFDList(self._fdlist, labeled_tokens, labels))
        
        #filtered_fdlist = self._fdlist
        if debug > 2:
            print '    --> Got %d useful features' % len(filtered_fdlist)

        # Memoize the results..
        if debug > 0: print '  ==> Memoizing training results'
        memoized_fdlist = MemoizedFDList(filtered_fdlist,
                                         labeled_tokens,
                                         labels)

        # Whee.
        ffreq_emperical = self._ffreq_emperical(memoized_fdlist,
                                                labeled_tokens)

        # Which features are useless?  We need this to prevent
        # divide-by-zero errors.
        useless = Numeric.ones(len(memoized_fdlist), 'd')
        for i in xrange(len(memoized_fdlist)):
            if ffreq_emperical[i] > 0:
                useless[i] = 0
        useful = 1-useless
            
        # The number of features that fire for a given labeled instance.
        num_features = Numeric.zeros( (len(labeled_tokens), len(labels)) )
        for i in xrange(len(labeled_tokens)):
            for j in xrange(len(labels)):
                ltext = LabeledText(labeled_tokens[i].type().text(),
                                    labels[j])
                fvlist = memoized_fdlist.detect(ltext)
                for (id, val) in fvlist.assignments():
                    num_features[i, j] += val

        # Where to do what?
        self._nf_init(labeled_tokens, labels, num_features)
        
        # Build the classifier.  Start with weight=0 for each feature,
        # except for the always-on feature.  This feature prevents
        # some divide by zero errors; set its weight to 1.
        # Technically speaking, we don't know which index corresponds
        # to the always-on feature.  But we'll rely on the fact that
        # it's the first feature, which is true in the current
        # implementation. 
        weights = Numeric.zeros(len(memoized_fdlist), 'd')
        weights[0] = 1
        classifier = MaxentClassifier(memoized_fdlist, 
                                      labels, weights)

        # Train for a fixed number of iterations.
        if debug > 0:
            print '  ==> Training (%d iterations)' % iter
        for iternum in range(iter):
            if debug>20:
                print;print
                print 'Weights:', tuple(weights)
                print 'Distribution:'
                for (k,v) in classifier.distribution('to').items(): print ' ',k,v

            if debug > 3:
                accuracy = classifier.accuracy(labeled_tokens)
                print ('    --> Accuracy = %.8f' % accuracy)
                ll = classifier.log_likelihood(labeled_tokens)
                print ('    --> Log Likelihood = %.3f' % ll)

            if debug > 1:
                print '    ==> Training iteration %d' % (iternum+1)

            deltas = self._deltas1(memoized_fdlist, labeled_tokens,
                                   labels, classifier, num_features,
                                   useless, useful, ffreq_emperical)

            # Use the deltas to update our weights.
            weights += deltas

            for i in range(len(weights)):
                if weights[i] < 0:
                    print 'ACK NEGATIVE WEIGHT', i, weights[i]
            
            if debug>30:
                asdf = 0
                print 'WEIGHTS:'
                for w in classifier.weights()[:18]:
                    #if w == 1: continue
                    print ('%8.4f' % w),
                    asdf += 1
                    if (asdf % 6) == 0: print
                print
                        
        if debug > 3: 
            accuracy = classifier.accuracy(labeled_tokens)
            print ('    --> Accuracy = %.8f' % accuracy)
            ll = classifier.log_likelihood(labeled_tokens)
            print ('    --> Log Likelihood = %.3f' % ll)
                   
        # Make sure to use the un-memoized features for the classifier
        # we return.
        return MaxentClassifier(filtered_fdlist, labels,
                                classifier.weights())

   def __repr__(self):
        return '<IISMaxentClassifierTrainer: %d features>' % len(self._fdlist)
        

##//////////////////////////////////////////////////////
##  Test code
##//////////////////////////////////////////////////////

def simple_test():
    """
    This test is to make sure that I'm getting something close to the
    correct maxent solution.
    """
    labels = "dans en a au pendant".split()
    toks = []
    for tag in "dans en en a a a a au au au".split():
        toks.append(Token(LabeledText('to', tag)))

    func1 = lambda w:(w.label() in ('dans', 'en'))
    features = FunctionFDList(func1, (1,))
    features += AlwaysFDList()

    if 0:
        trainer = IISMaxentClassifierTrainer(features)
    else:
        trainer = GISMaxentClassifierTrainer(features)
        
    classifier = trainer.train(toks, labels=labels, iter=15)
    dist = classifier.distribution('to')
    error = (abs(3.0/20 - dist['dans']) +
              abs(3.0/20 - dist['en']) +
              abs(7.0/30 - dist['a']) +
              abs(7.0/30 - dist['au']) +
              abs(7.0/30 - dist['pendant']))

    if (error) > 1e-5:
        print 'WARNING: BROKEN MAXENT IMPLEMENTATION'
        print '  Error: %10.5e' % error
    else:
        print 'Test passed'

t0=0
def resettime():
    global t0
    t0 = time.time()
def timestamp():
    return '%8.2fs ' % (time.time()-t0)

def demo(labeled_tokens, n_words=5, n_lens=20, debug=5):
    resettime()

    if debug: print timestamp(), 'getting a list of labels...'
    labelmap = {}
    for ltok in labeled_tokens:
        labelmap[ltok.type().label()] = 1
    labels = labelmap.keys()
    if debug: print timestamp(), '  got %d labels.' % len(labels)
    
    if debug: print timestamp(), 'constructing feature list...'
    fdlist = AlwaysOnFDList()
    f_range = [chr(i) for i in (range(ord('a'), ord('z'))+[ord("'")])]
    fdlist += TextFunctionFDList(lambda w:w[0:1], f_range, labels)
    fdlist += TextFunctionFDList(lambda w:w[-1:], f_range, labels)
    fdlist += TextFunctionFDList(lambda w:w[-2:-1], f_range, labels)
    fdlist += TextFunctionFDList(lambda w:w, ["atlanta's"], labels)
    fdlist += TextFunctionFDList(lambda w:len(w), range(n_lens), labels)
    if debug: print timestamp(), '  got %d features' % len(fdlist)

    if debug: print timestamp(), 'training on %d samples...' % len(labeled_tokens)
    t=time.time()
    # ======================
    if 1:
        trainer = IISMaxentClassifierTrainer(fdlist)
        classifier = trainer.train(labeled_tokens, iter=10,
                                   debug=debug)
    else:
        trainer = GISMaxentClassifierTrainer(fdlist)
        classifier = trainer.train(labeled_tokens, iter=20,
                                   debug=debug, C=4)
    if debug: print timestamp(), '  done training'

    # !!!TESTING!!!
    #asdf = 0
    #print 'FEATURES:'
    #for w in classifier.weights():
    #    if w == 0: continue
    #    print ('%8.4f' % w),
    #    asdf += 1
    #    if (asdf % 6) == 0: print
    #print
    
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
            items = classifier.distribution(word.type()).items()
            items.sort(lambda x,y:cmp(y[1], x[1]))
            for (label,p) in items[:2]:
                if p > 0.01:
                    print timestamp(), '    %3.5f %s' % (p, label)
        #label = classifier.classify(word.type())
        #if debug: print timestamp(), '  =>', label

    #print tuple(classifier.weights())
    return classifier

def get_toks(debug=0):
    resettime()
    from nltk.tagger import TaggedTokenizer
    file = '/mnt/cdrom2/data/brown/ca01'
    text = open(file).read()

    if debug: print timestamp(), 'tokenizing %d chars' % len(text)
    ttoks = TaggedTokenizer().tokenize(text)
    labeled_tokens = [Token(LabeledText(tok.type().base().lower(),
                                           tok.type().tag()),
                               tok.loc())
                         for tok in ttoks]
    if debug: print timestamp(), '  done tokenizing'
    return labeled_tokens
    
def foo(labeled_tokens, n_words=5, n_lens=20, debug=1):
    """
    Create a file foo.test
    """
    resettime()
    
    if debug: print timestamp(), 'getting a list of labels...'
    labelmap = {}
    for ltok in labeled_tokens:
        labelmap[ltok.type().label()] = 1
    labels = labelmap.keys()
    if debug: print timestamp(), '  got %d labels.' % len(labels)
    
    labels = ['x']
    if debug: print timestamp(), 'constructing feature list...'
    #features = AlwaysFDList()
    fdlist = AlwaysOnFDList()
    f_range = [chr(i) for i in (range(ord('a'), ord('z'))+[ord("'")])]
    fdlist += TextFunctionFDList(lambda w:w[0:1], f_range, labels)
    fdlist += TextFunctionFDList(lambda w:w[-1:], f_range, labels)
    fdlist += TextFunctionFDList(lambda w:w[-2:-1], f_range, labels)
    fdlist += TextFunctionFDList(lambda w:w, ["atlanta's"], labels)
    fdlist += TextFunctionFDList(lambda w:len(w), range(n_lens), labels)

    if debug: print timestamp(), '  got %d features' % len(features)

    out = open('foo.test', 'w')
    for tok in labeled_tokens:
        fvlist = features.detect(tok.type())
        print >>out, tok.type().label(),
        for assignment in fvlist.assignments():
            print >>out, "%d=%d" % assignment,
        print >>out
    out.close()

def test(classifier, labeled_tokens):
    import sys
    total = 0
    correct = 0
    for tok in labeled_tokens:
        if (correct % 10) == 0:
            sys.stdout.flush()
        text = tok.type().text()
        label = tok.type().label()
        if classifier.classify(text) == label:
            sys.stdout.write('+')
            correct += 1
        else:
            sys.stdout.write('-')
        total += 1
    print 'Accuracy:', float(correct)/total
    
if __name__ == '__main__':
     #simple_test()
     toks = get_toks(1)[:100]
     demo(toks, 5)
     #foo(toks, 5, 10)
