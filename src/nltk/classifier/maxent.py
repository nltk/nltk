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

from nltk.classifier import *
from nltk.chktype import chktype as _chktype
from nltk.token import Token, WSTokenizer

from Numeric import zeros, ones, array, take, product
import time
from math import log

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
    """
    def __init__(self, features, labels, weights):
        """
        """
        self._features = features
        self._labels = labels
        self._weights = weights

    def distribution(self, text):
        # Inherit docs.
        total_p = 0.0
        dist = {}

        # Find the non-normalized probability estimates
        for label in self._labels:
            labeled_text = LabeledText(text, label)
            featurevalues = self._features.detect(labeled_text)
            p = 1.0
            for (id,val) in featurevalues.assignments():
                if val == 1: p *= self._weights[id]
                else: p *= (self._weights[id] ** val)
                    
            dist[label] = p
            total_p += p

        # What should we do if nothing is possible?
        if total_p == 0: return {}

        # Normalize our probability estimates
        for (label, p) in dist.items():
            dist[label] = p / total_p

        return dist

    def classify(self, text):
        # Inherit docs
        max_p = -1
        max_label = None

        # Find the label that maximizes the non-normalized probability
        # estimates.
        for label in self._labels:
            labeled_text = LabeledText(text, label)
            featurevalues = self._features.detect(labeled_text)
            p = 1.0
            for (id,val) in featurevalues.assignments():
                if val == 1: p *= self._weights[id]
                else: p *= (self._weights[id] ** val)
                if p <= max_p: break
            if p > max_p:
                max_p = p
                max_label = label
                
        return max_label

    def weights(self):
        return self._weights

    def features(self):
        return self._features

    def labels(self):
        return self._labels

    def accuracy(self, labeled_tokens):
        """
        Test this model's accuracy on the given list of labeled
        tokens. 
        """
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
        total = 0
        correct = 0.0
        for tok in labeled_tokens:
            text = tok.type().text()
            label = tok.type().label()
            dist = self.distribution(text)
            if dist.has_key(label): correct += log(dist[label])
            total += 1
        return correct
    
##//////////////////////////////////////////////////////
##  GIS
##//////////////////////////////////////////////////////

class GIS_FDList(AbstractFeatureDetectorList):
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

class MemoizedFDList(AbstractFeatureDetectorList):
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
        self._labels = None

    def _find_labels(self, labeled_tokens):
        labelmap = {}
        for token in labeled_tokens:
            labelmap[token.type().label()] = 1
        return labelmap.keys()

    def _fcount_emperical(self, fdlist, labeled_tokens):
        """
        Find the frequency of each feature..
        """
        fcount = zeros(len(fdlist), 'd')
        
        for labeled_token in labeled_tokens:
            labeled_text = labeled_token.type()
            values = fdlist.detect(labeled_text)
            for (feature_id, val) in values.assignments():
                fcount[feature_id] += val

        return fcount

    def _fcount_estimated(self, classifier, fdlist,
                          labeled_tokens, labels):
        fcount = zeros(len(fdlist), 'd')
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
        @param kwargs:
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
        labels = self._labels
        for (key, val) in kwargs.items():
            if key in ('iterations', 'iter'):
                iter = val
            elif key == 'debug':
                debug = val
            elif key == 'labels':
                labels = val
            elif key in ('c', 'C'):
                C = val
            else:
                raise TypeError('Unknown keyword arg %s' % key)
        
        # Find the labels, if necessary.
        if labels is None:
            labels = self._find_labels(labeled_tokens)

        # Build the corrected feature detector list
        corrected_fdlist = GIS_FDList(self._fdlist, C)
        Cinv = 1.0 / corrected_fdlist.C()

        # Memoize the results..
        if debug > 0: print '  ==> Memoizing training results'
        memoized_fdlist = MemoizedFDList(corrected_fdlist,
                                         labeled_tokens,
                                         labels)

        # Count how many times each feature occurs in the training
        # data.  This represents an emperical estimate for the
        # frequency of each feature.
        fcount_emperical = self._fcount_emperical(memoized_fdlist,
                                                  labeled_tokens)

        # Build the classifier.  Start with weight=1 for each feature.
        weights = ones(len(corrected_fdlist), 'd')
        classifier = MaxentClassifier(memoized_fdlist, 
                                      labels, weights)

        # Train for a fixed number of iterations.
        if debug > 0:
            print timestamp(),'  ==> Training (%d iterations)' % iter
        for i in range(iter):
            if debug > 3:
                accuracy = classifier.accuracy(labeled_tokens)
                print ('    --> Accuracy = %.3f' % accuracy)

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
            #print '%5.3f %5.3f %5.3f' % tuple(weights)
            #print '%5.3f %5.3f %5.3f' % tuple(fcount_emperical)
            #print '%5.3f %5.3f %5.3f' % tuple(fcount_estimated)
            #print
            for fid in range(len(weights)):
                if fcount_emperical[fid]==0:
                    weights[fid] = 0
                    continue
                weights[fid] *= ( fcount_emperical[fid] /
                                  fcount_estimated[fid] )**Cinv

                
        if debug > 3: 
            accuracy = classifier.accuracy(labeled_tokens)
            print ('    --> Accuracy = %.3f' % accuracy)
                   

        # Make sure to use the un-memoized features for the classifier
        # we return.
        return MaxentClassifier(corrected_fdlist, labels,
                                classifier.weights())


class GISMaxentClassifierTrainer(ClassifierTrainerI):
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
    features = FunctionFeatureDetectorList(func1, (1,))

    trainer = GISMaxentClassifierTrainer(features)
    classifier = trainer.train(toks, labels=labels,
                               C=1, iter=10)
    dist = classifier.distribution('to')
    error1 = (abs(3.0/20 - dist['dans']) +
              abs(3.0/20 - dist['en']) +
              abs(7.0/30 - dist['a']) +
              abs(7.0/30 - dist['au']) +
              abs(7.0/30 - dist['pendant']))
    
    classifier = trainer.train(toks, labels=labels,
                               C=5, iter=100)
    dist = classifier.distribution('to')
    error2 = (abs(3.0/20 - dist['dans']) +
              abs(3.0/20 - dist['en']) +
              abs(7.0/30 - dist['a']) +
              abs(7.0/30 - dist['au']) +
              abs(7.0/30 - dist['pendant']))

    if (error1 + error2) > 1e-5:
        print 'WARNING: BROKEN MAXENT IMPLEMENTATION'
        print '  Error: %10.5e %10.5e' % (error1, error2)
    else:
        print 'Test passed'

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
    f_range = [(chr(i),l)
             for i in (range(ord('a'), ord('z'))+[ord("'")])
             for l in labels]
    func = lambda w:(w.text()[0:1], w.label())
    features = FunctionFeatureDetectorList(func, f_range)
    func = lambda w:(w.text()[-1:], w.label())
    features += FunctionFeatureDetectorList(func, f_range)
    func = lambda w:(w.text()[-2:-1], w.label())
    features += FunctionFeatureDetectorList(func, f_range)
    f_vals = [LabeledText("Atlanta's", l) for l in labels]
    features += ValueFeatureDetectorList(f_vals)
    f_range = [(n, l) for n in range(n_lens) for l in labels]
    func = lambda w:(len(w.text()), w.label())
    features += FunctionFeatureDetectorList(func, f_range)

    if debug: print timestamp(), '  got %d features' % len(features)

    if debug: print timestamp(), 'training on %d samples...' % len(labeled_tokens)
    t=time.time()
    trainer = GISMaxentClassifierTrainer(features)
    classifier = trainer.train(labeled_tokens, iter=50,
                               debug=2, C=5)
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
            for (label,p) in items:
                if p > 0.01:
                    print timestamp(), '    %3.5f %s' % (p, label)
        #label = classifier.classify(word.type())
        #if debug: print timestamp(), '  =>', label

    print tuple(classifier.weights())
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
     features = AlwaysFeatureDetectorList()
     f_range = [(chr(i),l)
              for i in (range(ord('a'), ord('z'))+[ord("'")])
              for l in labels]
     func = lambda w:(w.text()[0:1], 'x')
     features += FunctionFeatureDetectorList(func, f_range)
     func = lambda w:(w.text()[-1:], 'x')
     features += FunctionFeatureDetectorList(func, f_range)
     func = lambda w:(w.text()[-2:-1], 'x')
     features += FunctionFeatureDetectorList(func, f_range)
     f_vals = [LabeledText("Atlanta's", l) for l in labels]
     features += ValueFeatureDetectorList(f_vals)
     f_range = [(n, l) for n in range(n_lens) for l in labels]
     func = lambda w:(len(w.text()), 'x')
     features += ValueFeatureDetectorList(f_vals)

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
#    simple_test()
#else:
    #toks = get_toks(1)
    print
    #demo(toks, 5)
    #foo(toks, 5, 10)

            
        

"""
OUTPUT FROM RUNNING GIS ON '/mnt/cdrom2/data/brown/ca01'
    0.00s  tokenizing 20187 chars
    2.80s    done tokenizing

    0.00s  getting a list of labels...
    0.13s    got 84 labels.
    0.13s  constructing feature list...
    0.36s    got 6721 features
    0.36s  training on 2242 samples...
    0.47s    ==> Memoizing training results
  346.70s    ==> Training iteration 0
  705.85s    ==> Training iteration 1
 1066.19s    ==> Training iteration 2
 1425.89s    ==> Training iteration 3
 1784.96s    ==> Training iteration 4
 2144.38s    ==> Training iteration 5
 2503.86s    ==> Training iteration 6
 2863.26s    ==> Training iteration 7
 3222.63s    ==> Training iteration 8
 3582.02s    ==> Training iteration 9
 3951.48s    done training
 3951.48s  2242 tokens, 84 labels
 3951.49s  Testing on 7 tokens
 3951.49s  'jury'@[0w]
 3951.71s      0.25140 NN
 3951.71s      0.25014 NN-TL
 3951.71s      0.24959 NP
 3951.71s      0.24887 RB
 3951.94s    => NN
 3951.94s  'the'@[1w]
 3952.09s      0.12710 AT
 3952.09s      0.12562 NN
 3952.09s      0.12472 RB
 3952.09s      0.12467 JJ
 3952.09s      0.12460 VBD
 3952.09s      0.12451 NP
 3952.09s      0.12447 VBN
 3952.09s      0.12431 AT-TL
 3952.29s    => AT
 3952.29s  'reports'@[2w]
 3952.47s      0.16816 NNS
 3952.48s      0.16701 VBZ
 3952.48s      0.16657 JJ
 3952.48s      0.16631 NP
 3952.48s      0.16599 IN
 3952.48s      0.16597 VB
 3952.67s    => NNS
 3952.67s  'aweerdr'@[3w]
 3952.85s      0.14357 NN
 3952.85s      0.14310 NP-TL
 3952.85s      0.14270 NN-TL
 3952.85s      0.14269 RB
 3952.85s      0.14268 VB
 3952.85s      0.14263 NP
 3952.85s      0.14262 JJ
 3953.02s    => NN
 3953.03s  "atlanta's"@[4w]
 3953.22s      1.00000 NP$
 3953.36s    => NP$
 3953.36s  'atlanta_s'@[5w]
 3953.57s      0.12563 NNS
 3953.57s      0.12556 CS
 3953.57s      0.12531 NP$
 3953.57s      0.12491 JJ
 3953.57s      0.12482 NP
 3953.57s      0.12470 IN
 3953.57s      0.12468 RB
 3953.57s      0.12440 VB
 3953.74s    => NNS
 3953.74s  "moowerp's"@[6w]
 3953.96s      1.00000 NN$
 3954.10s    => NN$
"""

    

"""
>>> ## working on region in file /usr/tmp/python-iTE1rC...
    0.00s  tokenizing 20187 chars
    3.00s    done tokenizing

    0.00s  getting a list of labels...
    0.16s    got 84 labels.
    0.16s  constructing feature list...
    0.49s    got 7476 features
    0.49s  training on 2242 samples...
  ==> Memoizing training results
  ==> Training (10 iterations)
    ==> Training iteration 1
    ==> Training iteration 2
    ==> Training iteration 3
    ==> Training iteration 4
    ==> Training iteration 5
    ==> Training iteration 6
    ==> Training iteration 7
    ==> Training iteration 8
    ==> Training iteration 9
    ==> Training iteration 10
 1353.32s    done training
 1353.32s  2242 tokens, 84 labels
 1353.32s  Testing on 7 tokens
 1353.32s  'jury'@[0w]
 1353.46s      0.72589 NN
 1353.46s      0.11196 NN-TL
 1353.47s      0.10240 NP
 1353.47s      0.05975 RB
 1353.47s  'the'@[1w]
 1353.61s      0.97864 AT
 1353.61s  'reports'@[2w]
 1353.75s      0.80890 NNS
 1353.75s      0.11392 VBZ
 1353.75s      0.05297 JJ
 1353.75s      0.01628 VB
 1353.75s  'aweerdr'@[3w]
 1353.90s      0.51810 NP-TL
 1353.90s      0.23421 NN
 1353.90s      0.09865 VB
 1353.90s      0.05158 JJ
 1353.90s      0.03838 NP
 1353.90s      0.03736 RB
 1353.90s      0.02172 NN-TL
 1353.90s  "atlanta's"@[4w]
 1354.04s      1.00000 NP$
 1354.04s  'atlanta_s'@[5w]
 1354.18s      0.82383 NNS
 1354.18s      0.11020 NP$
 1354.18s      0.03791 JJ
 1354.18s      0.01120 RB
 1354.18s  "moowerp's"@[6w]
(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0811299680847752, 0.0, 0.0, 1.2146980554354043, 0.90013192985628876, 0.47181703625646648, 0.0, 1.2389064344066227, 0.0, 1.7823468792430612, 1.9590892206329511, 0.0, 0.0, 0.0, 0.0, 2.6974179466279296, 0.0, 0.0, 0.0, 2.5282768188924689, 0.0, 0.0, 0.0, 0.0, 0.65466051019946259, 0.0, 0.0, 1.7452395600129458, 0.0, 0.0, 0.0, 0.8002366805990907, 1.0907830242548937, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.7104253766495299, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.91825327772269605, 0.0, 0.0, 0.0, 0.0, 0.0, 0.58231117064454141, 0.0, 2.6933782333646454, 0.0, 0.0, 0.94493271185350602, 0.0, 1.0103642439847254, 0.44071372872260717, 0.0, 4.488825949992683, 0.0, 0.0, 0.0, 0.0, 2.289926773280524, 0.0, 0.0, 0.0, 2.5588117570701518, 3.6258498563755865, 0.0, 0.0, 0.0, 4.6214216273909976, 0.0, 0.0, 0.0, 1.1307617086216428, 0.0, 1.0754254560942413, 0.0, 0.0, 0.0, 0.0, 0.0, 3.4638064722365827, 0.83902257548435255, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.93476777153260104, 0.0, 3.2889690131930318, 0.0, 0.0, 0.0, 0.0, 0.68393667305952521, 0.0, 0.0, 1.4424521355826725, 0.0, 0.0, 0.0, 2.0171977810785298, 0.81702080868346993, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0564464910885636, 0.0, 0.0, 0.0, 0.0, 1.543081422656301, 0.0, 0.3953593899986575, 0.0, 0.0, 0.0, 0.0, 0.0, 0.84846944002865243, 0.0, 0.0, 0.0, 0.0, 1.0245776248708742, 0.0, 0.8810539579025578, 0.0, 0.0, 0.0, 2.2622600321787623, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.5226144890435327, 0.0, 2.0413473100637827, 0.0, 0.0, 0.49005138651934377, 0.0, 1.070504619541387, 0.0, 0.45467596911502717, 0.0, 0.0, 0.0, 0.26752569374573626, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.47760244416231806, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.64060680611308241, 1.6612297456219192, 0.0, 2.3673046003114022, 0.0, 0.0, 0.0, 0.92663060379859519, 0.41058188594910938, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.2033617941029946, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.50003903708602215, 0.0, 0.0, 0.0, 0.0, 0.0, 2.0777564465345004, 0.0, 0.0, 0.0, 2.4628425425512326, 1.4931971822414642, 0.0, 1.2882391386332179, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.3103213840465309, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 4.5818059772285507, 0.0, 0.0, 2.7061672076229319, 1.7362843878582959, 0.0, 0.0, 0.0, 0.0, 0.0, 0.77715589932524376, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.2643321677774819, 0.0, 0.0, 0.0, 0.0, 0.0, 1.1566370904109342, 1.1006650808520966, 0.0, 1.8112820499864017, 0.0, 0.0, 0.0, 1.8158003302076724, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.6779843842143478, 0.0, 1.1612633490685491, 0.0, 0.0, 0.74274724866393238, 0.0, 0.29550177201807371, 0.0, 0.0, 0.0, 0.0, 0.0, 2.1709637120105105, 3.6814107115256434, 0.0, 0.0, 0.0, 0.0, 0.0, 0.77481985148180499, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.7195607722468291, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.2252148297724976, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 17.645609856075016, 0.0, 0.0, 0.0, 0.0, 0.0, 2.9348246022067488, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.6443748742973705, 0.0, 0.0, 0.72483021727868091, 0.0, 0.0, 0.0, 0.267879706540472, 0.97335949641941277, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.9601288688341985, 0.0, 0.0, 0.0, 2.8453239281319314, 1.4445841150100547, 0.0, 0.98997445073978108, 0.0, 0.0, 0.0, 2.0026187578806098, 0.0, 0.29819982161783659, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.4799275193638244, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.63721859063892616, 0.0, 0.0, 0.0, 0.0, 0.60544028453270848, 0.0, 2.8646194541658465, 0.0, 0.0, 0.0, 2.4159963277940406, 0.0, 0.0, 0.97612501203117619, 0.0, 1.1671623224170715, 0.0, 3.3549752731160019, 0.0, 0.0, 0.0, 0.0, 0.0, 2.3197844867881505, 0.0, 1.2413096904475323, 0.0, 0.0, 2.0065270242726068, 0.0, 2.7304603441291104, 0.0, 1.0012645215178853, 1.1358191325411497, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.33407079796918904, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.0603075115886091, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.1558388511298459, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.63106982632107245, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 3.7562954159897539, 0.0, 0.0, 0.0, 0.0, 0.0, 2.0096165328752624, 0.0, 1.588852128691064, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 3.0961749857560661, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.4642695907389256, 0.0, 0.0, 1.4692915740807631, 0.0, 0.0, 0.0, 2.6935199644536807, 0.98563411097804032, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.74335441487590626, 0.0, 0.0, 0.0, 0.0, 2.9469098084884053, 0.0, 2.2321817805415134, 0.0, 0.0, 0.0, 0.0, 0.0, 1.5091668103091216, 0.0, 0.0, 0.0, 0.0, 1.26846933189558, 0.0, 1.2652434448288032, 2.1752946936077273, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.1270911158459174, 0.0, 2.5724700131816864, 0.0, 0.0, 0.0, 2.8639224819404285, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.73276226933673239, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.2114551249882699, 0.0, 0.0, 3.9399480074906323, 0.50284046098596158, 0.0, 0.0, 1.07949453456637, 0.0, 0.76754567533628404, 0.0, 1.2109084099922953, 0.65618133826444325, 0.0, 0.0, 1.6348181380081446, 0.0, 0.0, 2.4543665403685813, 0.0, 0.0, 0.0, 0.0, 0.76527825317086795, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.29589574026288668, 0.0, 0.0, 0.0, 0.0, 0.0, 2.9503569575886051, 0.0, 0.0, 2.9353164235301055, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.9040487443433394, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.6063110389163691, 0.0, 0.0, 0.0, 0.0, 0.0, 1.7079483786378096, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.8514032124733157, 0.0, 0.0, 0.0, 1.240275943369082, 0.0, 0.0, 1.2806725345905836, 0.0, 0.0, 0.0, 0.34608207303924499, 0.0, 0.0, 0.0, 2.990396707861716, 0.0, 0.0, 1.6056934411447683, 0.0, 0.0, 0.0, 0.0, 1.3680029527923312, 0.0, 0.0, 1.1658506946484597, 0.0, 0.7529178771868108, 0.0, 0.44281093957689727, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.3797090357374486, 0.0, 2.3262095882653124, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.2176051522862954, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 8.3938366588207103, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.90828931243914723, 0.0, 0.0, 0.0, 3.1143051948864926, 0.44168534284736877, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.1137410459653623, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.98452773549040107, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.4258048343234657, 0.0, 0.0, 0.0, 0.0, 0.0, 0.96290987157157892, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.8313880205116442, 0.0, 0.0, 0.0, 0.74310088734577906, 0.0, 0.0, 2.753894170220879, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.6556764255132237, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.25885340354498393, 0.0, 0.0, 2.2246915188085814, 0.0, 0.0, 0.0, 0.99623412292493074, 1.0985503582195022, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.4972810493952473, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.69190067047989878, 0.0, 0.0, 0.0, 0.0, 0.0, 3.5888202828453495, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.2394295732556269, 2.3437473171241496, 0.0, 0.0, 0.0, 0.0, 0.0, 1.679374915815915, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.4565022152555764, 0.0, 0.0, 2.5413747946772745, 0.0, 2.6081929478621548, 0.0, 1.1181553321165512, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.0587805373250778, 0.0, 3.7942199061246842, 0.0, 0.0, 1.3195079107728944, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.79999428268868689, 0.0, 0.0, 1.4105335439166782, 0.0, 3.5605060578160859, 0.0, 1.3181127603675222, 0.57878366925863223, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.2736777042154146, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0644288798798993, 0.0, 0.0, 0.0, 0.0, 0.0, 1.056764525012809, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.2120198633425101, 0.7272956897363646, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.3256283805912545, 0.0, 0.55672832422282503, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.8099459038903269, 0.0, 0.0, 0.0, 0.44207630723537289, 2.0966939121603225, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 3.5750305929098287, 0.0, 0.0, 0.0, 1.3831655749135889, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.7285589216345791, 0.0, 0.0, 0.0, 4.7096716543250325, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.1091162617783805, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.1457187740803727, 0.0, 0.0, 0.0, 0.0, 0.0, 2.0900976638408522, 0.0, 0.0, 2.7744751773280325, 0.0, 1.1072358774000888, 0.0, 0.0, 0.92506344618436731, 0.0, 2.421641409485038, 4.054082127456776, 0.0, 0.0, 0.0, 1.5158688730723953, 0.0, 0.0, 1.5695215962668394, 0.0, 0.0, 0.0, 0.18830038954390171, 1.2465643090631975, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.84489839470234018, 3.1843970514256141, 0.0, 0.0, 0.0, 1.1419632708227514, 0.0, 2.1241838768730648, 0.0, 0.0, 0.0, 0.0, 0.0, 1.7149196423235158, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.46494272100345813, 0.83402483543602335, 0.0, 0.0, 0.0, 0.0, 2.4219506756760452, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.2293148030591943, 0.0, 0.0, 2.5258902602340534, 0.0, 0.0, 0.48232093991220998, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.4939876651292439, 0.0, 0.0, 2.3644709597400406, 0.0, 0.0, 0.0, 0.88782461225907872, 0.0, 1.8355709306333732, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.1423625722447923, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.2649751768647164, 0.0, 0.0, 0.0, 0.0, 0.0, 0.37672615974680485, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.0539408001232715, 2.3346309229303777, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.5442430118045538, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 3.1542932213335142, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.4579685553536756, 1.301547315825534, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.3849666702776255, 0.0, 0.0, 0.0, 0.0, 0.0, 0.27202662311264708, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.964303846461718, 0.0, 3.1501397011426451, 1.4252113605232246, 0.0, 0.0, 0.0, 0.38197408007254252, 0.40501420549071032, 2.0320901670336844, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.4027161414347669, 0.0, 0.0, 1.9796944966407137, 0.0, 0.0, 0.0, 0.0, 0.80209386827886031, 0.0, 1.5602329048307744, 0.0, 0.0, 0.0, 0.0, 0.0, 1.3078520817207853, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.8983106672423868, 1.3515210182841764, 0.0, 0.0, 0.0, 0.0, 0.0, 1.1798654470852168, 1.8246472571639527, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.64958941598109676, 1.9977368434765279, 0.0, 1.8173966148020315, 0.0, 0.0, 0.0, 0.0, 0.0, 0.20587530681593275, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.9326372100923116, 0.0, 0.0, 1.3815275365108375, 0.0, 1.8019465783950792, 0.0, 1.1092021923309112, 1.0402845376695584, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.6631086449211887, 0.0, 0.0, 0.0, 0.0, 1.8327733653344023, 0.0, 0.83408525760007168, 0.0, 0.0, 0.9206511776463826, 1.2290544595309545, 0.0, 1.0909211190033887, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.6042886788930071, 0.0, 0.0, 2.6390887590637866, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.68902356477869275, 0.0, 0.0, 0.0, 0.0, 0.0, 1.73840928237265, 0.0, 0.0, 0.0, 0.0, 1.9635342154844446, 0.0, 0.0, 0.52692850255898871, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0321096897863893, 2.3566664866714451, 1.1816881827117851, 0.0, 0.0, 0.86288169229774159, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.2591513975876558, 0.0, 0.0, 0.4609985219427018, 0.0, 0.0, 1.0428731745209776, 0.0, 1.430199001871403, 0.0, 0.38359981381556918, 1.4012130074163076, 0.0, 1.7759542654962595, 0.0, 0.0, 0.0, 2.6063699996823235, 0.0, 0.0, 0.0, 0.0, 0.72312604435813255, 0.0, 0.0, 2.8309791575845749, 1.8350811311727495, 3.2181149682556387, 2.5630341545827569, 0.26635279126252526, 0.0, 0.0, 0.0, 0.0, 0.0, 0.15295919646871703, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.75455851609351321, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.419064004053423, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.7844139763419631, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.54224624615645389, 1.9577897950556993, 0.0, 0.0, 0.0, 0.0, 0.0, 2.2997512252347074, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.4634224224865977, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 6.1549265748605739, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.2402128176723286, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.77902285661369697, 0.0, 0.0, 2.5219350096311954, 0.0, 0.0, 0.0, 2.0188172122019363, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.1294904666642869, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.5820141111857409, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.8352252188564717, 2.4236527155173255, 0.0, 0.0, 0.0, 0.0, 0.0, 1.035735489308647, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 4.6373155617767035, 2.8134496886646447, 1.2914359146008867, 1.3577219817779573, 0.0, 0.0, 0.0, 0.0, 0.0, 0.96407864782568253, 0.0, 1.325646662251204, 0.0, 3.8224206612531293, 0.0, 0.0, 0.0, 0.93270963894065362, 0.0, 0.0, 0.0, 0.0, 0.0, 1.7231173026984765, 0.87217091285136339, 0.0, 0.0, 0.14102778147983935, 0.0, 2.5498096279833273, 2.4401460335268288, 1.0776654680768931, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.80765049243298548, 0.0, 0.0, 1.218795684762205, 0.0, 0.0, 0.0, 0.24112000303917067, 0.0, 2.8291817942540072, 0.0, 0.0, 0.0, 0.64047785322049544, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.89566874559479237, 1.9789266732681918, 0.0, 0.0, 0.0, 0.93270963894065362, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.9832294288584651, 0.0, 0.0, 0.0, 0.0, 2.8537126489513991, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.7040038279630831, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.4258048343234653, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.1518196113481292, 1.4008121167311987, 0.0, 0.0, 0.0, 0.0, 2.34772057278933, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.5766743778836756, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.4258048343234657, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.4048793713488248, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.79439850065709416, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.7514839073113131, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.41826824933801693, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.3230051538942762, 0.0, 0.0, 0.0, 1.7755722017652462, 0.0, 0.0, 2.6646123827521571, 0.0, 2.3295375714474034, 0.0, 0.0, 2.1477215491963779, 0.0, 0.0, 0.17182296949160739, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.6860610898973665, 0.0, 0.0, 0.0, 0.0, 0.58281185369626154, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.64478229398915876, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.52627786468166127, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.72101362633858923, 0.0, 0.0, 0.0, 0.0, 0.0, 0.13442624988727525, 2.7464926221442343, 0.0, 0.0, 0.0, 0.0, 0.0, 2.4817681778699803, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.4489700217413914, 0.0, 0.65796540806833326, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.58025294640050107, 0.0, 0.0, 0.33405615619020751, 0.0, 0.0, 0.0, 0.0, 0.0, 0.31981112781050491, 2.228540143309957, 0.0, 1.1385711143434571, 2.9949312881485395, 3.7448371599931307, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.1573187728047261, 0.0, 0.77533700243873382, 1.4615238001085771, 0.0, 0.0, 0.0, 0.0, 0.99722403105553492, 0.0, 0.18285625312979001, 0.49512405705073359, 0.85042633475224927, 0.0, 1.4295757794090493, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.5111163219361476, 0.0, 0.0, 1.663875539743737, 0.0, 0.0, 2.4475038295022169, 1.0327333867786173, 0.0, 0.0, 0.0, 2.351320165226626, 0.0, 1.411273661138349, 0.0, 2.3927499146708318, 2.1189432893027118, 0.0, 0.0, 0.0, 0.24624825031420089, 0.0, 0.0, 2.345289499127837, 1.9118291124352946, 0.0, 0.0, 0.0, 0.0, 2.4304335156763361, 0.0, 0.0, 0.0, 0.0, 1.2365022491937492, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.3936599257777633, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.24277048418517588, 1.6348772887482645, 0.0, 0.0, 0.0, 0.0, 0.0, 2.9615781964533232, 0.0, 0.0, 0.0, 0.0, 0.0, 0.97587903055629299, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.8808154411022331, 0.0, 0.0, 0.0, 0.0, 0.0, 3.0061735558463782, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 4.1729515948641502, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.6188985226077452, 0.0, 0.0, 0.35589356446002263, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.88330226001717327, 0.0, 0.0, 0.0, 2.8235616189512895, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.7980971020911412, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 3.217170038330095, 2.4703956802043914, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 6.7466642617143462, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.4514657765797188, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.72602506005237555, 0.0, 0.0, 0.0, 3.0954076591479489, 0.0, 0.0, 2.4305206590023021, 0.0, 3.2242695291332422, 0.0, 0.0, 0.0, 0.2097901994168484, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.4258048343234657, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.4258048343234657, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.2226098357734405, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 3.4175701445429998, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.4529285142885058, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.57855446266366917, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.5462448368472801, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.3848306966384949, 2.0097982581569607, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.5123598643402696, 0.0, 0.0, 2.3604138595031006, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 3.4623679617810401, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.96587743253907798, 0.0, 0.0, 0.47844105376873242, 0.0, 0.0, 0.0, 0.64238450584988305, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0533735225150336, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 3.316741662855732, 0.0, 0.0, 0.0, 0.0, 0.0, 0.52431532268618553, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.1052498934452153, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.6719727557787811, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.8017863548718442, 0.0, 0.0, 0.0, 0.0, 1.7925055786318473, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 3.1239375903038717, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0500359147015506, 0.0, 0.0, 1.8778776497957903, 0.0, 0.73851649739371938, 0.0, 1.6738376241996533, 0.0, 0.0, 0.0, 1.5234276655299128, 3.4790982299304942, 0.0, 0.0, 0.0, 1.5390362710746397, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 3.8948656537297888, 0.79590338016235018, 0.0, 0.0, 0.2356200082002709, 0.0, 0.0, 0.0, 1.5833676039283446, 1.4453120332191651, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.2641198903068545, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.43741958451727747, 0.0, 0.0, 0.0, 0.0, 0.0, 0.87055328471688076, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.5677793627814787, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.7518357753177307, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.4259947245896722, 1.1064361856453595, 1.4486407212134449, 0.0, 0.0, 1.1098485449558839, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.26561037968507806, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 3.0882056607503876, 0.0, 2.3492885120711993, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.5171456660435512, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 3.993815765946076, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.4740665311955556, 2.3700675820707557, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 3.006553821163461, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 3.1155364944633788, 1.1947821494858137, 0.0, 2.2929929231546833, 0.0, 0.0, 0.0, 0.0, 0.79747587408527421, 0.0, 0.0, 0.0, 2.5504833301536323, 0.0, 0.0, 1.7367421258139029, 0.0, 0.32999630152463044, 0.0, 3.3586565919230047, 0.0, 0.0, 3.9069947243409313, 4.1754195840607915, 0.0, 0.0, 1.6991684275807777, 0.71239723585035497, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0855674478980131, 0.80253756239945573, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.7266007157005967, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.82636838018433123, 0.0, 0.0, 0.0, 0.0, 0.0, 0.8941991328741401, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.97976961513248162, 0.0, 0.0, 0.0, 2.0382227042682359, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 3.3389757041372099, 1.3757682451689299, 0.0, 1.4628391469390722, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.058499652413594221, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.1940230267211049, 0.0, 0.0, 2.1384414439951538, 0.0, 0.0, 0.0, 0.075283985338496451, 1.1798345210369354, 2.5386650269613487, 2.6643831782395373, 0.0, 0.0, 2.0984619847693882, 0.47559840156556743, 0.14020070291154724, 2.1945737997009491, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.9233625744994098, 1.7365109023499354, 0.0, 0.43235306140257929, 0.0, 0.0, 0.80210597777873704, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.1709482335717112, 2.0395620746700431, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.3512643933383461, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.7039230568789532, 0.0, 0.0, 0.0, 2.0095286588356469, 2.1927239139135506, 0.0, 0.581934008087583, 0.0, 15.365482482458713, 0.0, 0.0, 0.0, 0.96525200766801222, 0.0, 1.3045551029245397, 0.97251851071710138, 0.0, 0.0, 0.0, 0.0, 0.0, 0.99763590734970597, 0.86303390036123862, 0.0, 0.0, 2.0517073819217022, 0.0, 0.99093103295887885, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.14431643353642559, 0.80898718274624049, 0.0, 0.0, 2.5039222315049177, 0.0, 0.0, 2.18343008857335, 2.5598821613683693, 0.0, 0.0, 0.0, 1.8100846366415821, 3.5441562494931298, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0145893977399691, 0.0, 6.1884788383367155, 0.0, 0.0, 0.0, 1.209652842643248, 0.0, 0.0, 0.0, 2.2533682053182869, 0.0, 0.0, 0.71616258113582221, 0.0, 0.0, 0.0, 0.0, 0.86849250110772647, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 8.509594157545207, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.93198097199958974, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.9686626138576109, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.4988079028809072, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.9380402516891195, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.2237139646006525, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 4.8093085477860376, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.6603088859110771, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.6711743557523312, 0.0, 0.0, 0.0, 0.65628210199148496, 0.0, 0.0, 0.0, 1.2179617632855204, 3.7651056481699481, 0.0, 1.9197742391516934, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.42975591659856616, 0.0, 0.0, 0.0, 0.0, 2.7961090169903411, 0.0, 0.49820556012632583, 2.0936505782995098, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.1459225609204911, 0.0, 0.0, 3.3544595109777302, 0.0, 0.0, 0.0, 0.59338673179822066, 0.0, 0.0, 0.0, 0.0, 0.0, 1.7784276769399239, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 4.9482271237935862, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.4258048343234653, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 3.4807450832900906, 1.4088812884120638, 0.0, 0.0, 2.1538501930627518, 0.0, 0.0, 0.0, 2.3978744004929582, 0.0, 0.0, 0.0, 0.0, 0.0, 2.2926709935522775, 0.66947976588032576, 0.0, 0.27775601182067022, 0.0, 0.0, 0.0, 0.0, 0.0, 1.231254226510843, 3.5005757767544923, 1.2731863283609417, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.16009305772888738, 0.0, 0.0, 0.11818592750021654, 0.0, 2.6135930567369714, 2.2175068217842684, 1.3160662998164245, 0.18999709792360003, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.88955759309328175, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.3456994496233197, 0.0, 6.0396733205504667, 0.0, 0.0, 0.0, 1.2974569766450819, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.45579639243980818, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.6071854390206037, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.92978883341133722, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.7725048217416379, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.54349483288152045, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.682356324299074, 0.0, 0.0, 1.7117704947176229, 0.0, 0.0, 0.0, 0.44705957291245518, 0.63234173995760357, 1.2665582602613261, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.2058270313943722, 0.0, 0.0, 0.0, 2.932885936301886, 0.0, 0.0, 0.54760588089510776, 0.0, 3.0549820243853079, 0.0, 0.0, 0.0, 0.66351857520333613, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.8566748156183885, 1.4475106517550393, 0.0, 14.713129607883461, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.4713197989971909, 0.0, 0.0, 2.4243844004834774, 0.0, 0.0, 0.0, 0.60650504625913848, 1.1465994043319037, 3.2785250841405085, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.57447885838858403, 0.0, 1.264257692131705, 0.0, 0.0, 1.3736972624689312, 0.0, 0.65831736146569308, 0.0, 0.0, 0.0, 0.0, 0.0, 0.61485375225808314, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.139211309292937, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.9792067463889564, 0.0, 0.0, 0.0, 0.0, 2.6270894118199073, 0.80590816222419137, 3.34427990198142, 1.4169374647339115, 0.0, 1.41935605257796, 2.8655904210232417, 0.0, 0.86150329877606968, 2.1012597131079103, 0.0, 0.0, 0.67588154403179768, 0.0, 0.0, 0.99559276096985549, 0.0, 0.37393704446455805, 0.0, 2.8320936654923776, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.4646110222818876, 1.0498161854324704, 0.0, 0.0, 2.2267899653086252, 0.0, 0.0, 0.0, 1.1306981969905101, 1.0160086897792286, 0.0, 0.0, 0.0, 0.0, 0.0, 1.4647208232997229, 0.0, 0.0, 0.0, 0.0, 0.64089257702914726, 0.0, 0.0, 2.9718844757607519, 0.0, 1.8292559973745055, 0.0, 0.58058349754140692, 0.0, 0.0, 0.0, 0.0, 0.0, 0.23041777437480124, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.3887603979565162, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.3366819340930189, 2.7871327802905204, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.1328952963274164, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.9800315187018236, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0279944915783592, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.9569714964638318, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.204246685156535, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.5482565754107394, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.77391535708612103, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.8508888178613504, 0.0, 0.54680365226518368, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.6715360354315871, 1.2300294257179858, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.54460051141784516, 0.24128432390100657, 0.0, 0.0, 1.3881112038346597, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.41963825091207851, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.23619349418587365, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.49941844384684242, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.60886298415965001, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.1400101974674486, 0.0, 0.0, 0.0, 0.0, 0.22781402817050686, 0.0, 0.79465942037409265, 0.0, 0.0, 0.0, 1.5074042875172078, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.9251835047626393, 0.0, 0.0, 0.0, 1.1141512467743446, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.81114960098660727, 0.0, 0.0, 0.0, 2.8160123872581235, 0.0, 0.0, 2.4024394682831005, 0.0, 0.0, 0.0, 0.0, 1.341246350677898, 0.0, 0.0, 0.0, 2.1132644534722993, 0.0, 0.0, 1.0915055219698759, 0.0, 0.0, 0.0, 0.0, 0.0, 0.59174054261857911, 2.9477016392630713, 0.0, 0.0, 0.0, 0.0, 2.24093683125357, 2.1621717394319124, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.4258048343234657, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.63100976009093523, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 3.1143663749376369, 0.0, 0.0, 2.9709100244209359, 0.0, 0.0, 0.0, 0.72926056004987139, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.63613156276382776, 0.0, 2.3091580281812334, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.77834336571933149, 3.176118386576591, 0.0, 0.27401038905694397, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 3.2130140566238343, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.53936422573433573, 0.0, 0.0, 1.6297256213643645, 0.0, 0.0, 0.0, 1.6545467552122004, 3.7555572418748091, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.74169345278903165, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.5963321582173797, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.25662400661301293, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.66688769526248337, 0.0, 0.0, 0.87493762319307977, 0.0, 1.8994092644002591, 0.0, 2.2297261759263218, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.80501847568305895, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.8467137809745309, 0.0, 0.0, 4.78690712600583, 0.0, 0.0, 2.2019128150827036, 0.0, 0.98425514427121141, 0.0, 0.0, 0.0, 2.2977286161893966, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.1893565123584264, 0.0, 0.0, 0.0, 0.0, 0.10677982023355718, 0.0, 0.0, 0.0, 0.0, 0.0, 0.82388920922776798, 0.86315016066652173, 0.0, 2.0670379730104504, 0.0, 3.9009583475718266, 0.0, 0.0, 0.0, 0.0, 2.698487559006062, 0.0, 0.0, 0.0, 0.0, 0.80428516108714687, 0.0, 2.7788450387120118, 1.5548125902937644, 0.0, 0.0, 0.0, 0.62028297156301349, 0.32650282230960531, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.2373834687183454, 0.0, 0.0, 1.5200557226254021, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.87283987131926577, 0.0, 0.0, 0.0, 2.7284953603583713, 0.0, 1.59691519167212, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.16372869660205525, 2.1386881571916767, 0.0, 1.8767499912384999, 0.0, 0.0, 0.0, 0.0, 1.7176718186829776, 0.0, 0.0, 0.0, 0.0, 0.0, 0.97189458321345135, 0.0, 1.8413645573896673, 0.0, 0.0, 1.1560698470288133, 0.0, 0.0, 0.0, 0.0, 0.15264058055521065, 0.0, 1.6181016595009179, 0.0, 0.0, 0.0, 1.9767681762619862, 0.0, 0.0, 0.0, 0.0, 0.77199367876351921, 0.0, 0.0, 0.0, 0.0, 5.6395477506413796, 0.0, 0.0, 0.0, 0.0, 0.50698491522593814, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.80233861064596113, 0.5473611688914124, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.3892825425091697, 0.0, 0.0, 0.0, 2.3873617426896661, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.42837255106435507, 0.0, 0.0, 0.0, 0.0, 0.0, 0.75220443314246066, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.9341970875649279, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.83157272378311731, 0.0, 0.0, 0.0, 1.9733113873090282, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.2350953732248084, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 4.5115069341162419, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.2450689198454974, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.40286046184026902, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.90137377805211538, 0.36103136477948777, 0.0, 1.7002308630678757, 3.8354003171464708, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.7627281928449055, 0.0, 0.99292020381785273, 0.67509819082759104, 0.0, 0.0, 2.309326912437176, 0.0, 0.0, 0.0, 1.6712073967000285, 0.52882783366549235, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.9749256918047755, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.27676504647912575, 0.0, 0.0, 0.0, 0.0, 0.0, 1.5320572274061803, 0.0, 3.0642284909494495, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.3451379668200789, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 3.3190832558928758, 0.0, 0.0, 0.0, 0.30461867108847734, 2.4551370410718003, 0.0, 0.0, 0.0, 0.0, 0.0, 1.6055857836443015, 0.0, 0.38846205508871806, 0.0, 0.0, 1.2886497161606307, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.5184842445880977, 0.0, 1.013122013538589, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.6758828438921314, 1.5392064408791535, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.5060259401254033, 0.0, 0.0, 0.0, 0.0, 0.0, 3.5704127295761503, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.3212470302090005, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0078424809348063, 0.0, 0.0, 2.4238997444389976, 1.4914494982147593, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.6368570496157666, 0.0, 5.0831126688825679, 0.0, 0.796972229081503, 0.0, 0.0, 1.7660751994606116, 0.0, 0.0, 0.0, 0.49834175032431238, 0.0, 0.0, 2.0084108211064442, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.6794604868345535, 0.0, 0.0, 0.0, 0.0, 0.39708479777396538, 0.0, 0.791575782142388, 0.0, 0.0, 0.0, 0.0, 0.0, 2.2471280455504234, 0.0, 0.0, 0.0, 2.2454982753776744, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 6.6192068206418275, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.461939977440598, 0.0, 0.0, 0.0, 0.0, 4.3356065744373922, 0.0, 0.0, 0.0, 0.0, 1.7346922607667539, 5.2514725048869462, 0.0, 0.0, 0.0, 1.5961465728377278, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.80972477621911165, 3.1715422123205879, 0.0, 0.0, 0.0, 0.0, 0.0, 1.4783253131178697, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.2781023041693804, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0502826120141546, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.5347637296435517, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.8624883326876398, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.3476400554645596, 0.0, 0.0, 0.0, 0.0, 0.0, 1.2114399498826469, 0.0, 0.0, 3.9032792475195182, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.9472943612303364, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.0058158501978776, 0.0, 0.0, 0.0, 1.2611564218470896, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.7674461413587568, 0.0, 0.0, 2.0426398403898576, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.4258048343234657, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.048881248639614, 0.0, 0.0, 0.0, 0.9054285570686107, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 3.5859172649977471, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.6201837372111356, 1.2502282802421449, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.6009311887674538, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0883869336135439, 0.0, 2.1902117639373393, 0.0, 0.0, 0.0, 0.0, 0.0, 1.588873281915459, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0883869336135439, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.058585325713149256, 0.0, 0.0, 0.0, 0.0, 0.0, 0.91229577592974165, 0.0, 0.0, 0.0, 0.49522805205952453, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.14367822206042904, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 4.2109417536154838, 4.1682020016763426, 0.0, 0.0, 0.0, 0.20633578248185344, 0.20633578248185344, 0.0, 0.0, 0.0, 0.12864862651357045, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.28499772594166739, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.44611587841361694, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.84538065856122213, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.003012454496393, 1.2318616839899272, 0.0, 0.0, 0.0, 1.4645383608503213, 0.0, 0.0, 0.0, 0.0, 1.169809882358805, 0.0, 0.0, 0.0, 0.0, 0.083840134522589427, 0.0, 0.0, 0.29741767620651782, 0.0, 0.0, 0.0, 0.66565784961938435, 0.13695035100022848, 0.0, 1.5431707889510646, 1.7641978210473206, 0.0, 0.0, 0.74636462248601498, 0.0, 0.0, 0.0, 0.0, 0.035241589621445149, 0.45299538566553182, 0.27583249534486165, 0.42021976514775017, 0.0, 0.0, 0.0, 0.0, 16.481876654628017, 0.0, 0.0, 0.0, 1.3345477761198095, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.2840637520282936, 0.0, 0.0, 2.4399635087505467, 0.0, 1.39178334626503, 0.0, 0.0, 0.0, 0.0, 0.0, 0.58300353638590097, 1.7904150402965819, 0.0, 0.0, 0.0, 1.6675295969034245, 1.1027325560642216, 0.0, 0.0, 0.0, 0.0, 0.0, 2.6011550623507707, 0.0, 0.50870925256619381, 0.0, 0.0, 0.0, 0.81766668265912856, 0.0, 1.3606267538451535, 2.2799350143473833, 1.0210944933966599, 0.0, 0.0, 1.7550322989162648, 1.2916329093631955, 0.0, 0.0, 0.0, 2.3769045646692537, 2.108981121769995, 0.0, 0.0, 0.0, 0.66861520504183947, 0.0, 0.0, 0.90805102125871251, 0.0, 0.0, 1.8887308594529717, 0.59949604268279955, 0.41515597589191405, 0.0, 0.0, 0.0, 0.0, 0.0, 1.1619503221666607, 1.9629949035152012, 0.0, 0.0, 0.0, 0.56189241714185945, 2.1285317804883679, 0.0, 0.0, 0.0, 0.0, 0.0, 0.48453932430958191, 0.0, 0.0, 0.0, 0.0, 0.0, 0.58453943681218901, 1.6741818191657749, 2.5620999429716784, 0.0, 0.0, 0.0, 0.0, 0.68220051876851184, 0.0, 0.0, 1.6802391989215133, 0.0, 0.0, 0.0, 1.9564943233795273, 0.48587079417827767, 0.0, 0.0, 0.0, 0.0, 2.4156179965695563, 0.0, 0.0, 0.0, 0.57661977061097469, 0.0, 0.9262821087186599, 1.401754190438522, 2.3084316466939794, 2.1340035458035045, 0.0, 1.5733331889166775, 0.0, 0.0, 0.0, 0.0, 1.6595222240307899, 0.86502366249948526, 0.0, 0.97306218549607415, 2.4346378412149727, 1.8237538498205179, 11.766696692144574, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.7401028818233164, 2.1155629298821532, 1.2422814533277831, 0.0, 0.0, 0.87444351173282764, 0.0, 0.88994088445900232, 0.0, 0.65108853579061665, 2.0142659061166519, 0.0, 0.0, 0.0, 0.0, 0.0, 1.065832691135882, 0.0, 0.0, 0.0, 0.0, 1.3359127317266914, 0.0, 0.0, 1.9784235632243286, 1.8324418834848277, 1.3959557833741036, 0.0, 0.43331698393601792, 0.0, 1.8405305773133402, 0.0, 1.4074696183923374, 0.0, 0.68807983531648498, 0.0, 0.0, 1.9198907937996341, 0.0, 0.0, 0.0, 1.8754813573722864, 0.0, 0.0, 1.9199559292040167, 0.0, 0.0, 0.0, 0.0, 1.9159188241795748, 0.0, 0.0, 0.0, 2.023998445622849, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.98834645912297403, 1.9283192199466455, 1.1723473723611371, 0.97119683227912912, 0.0, 0.59821861137604981, 0.0, 0.0, 0.0, 0.66385582254802222, 0.7684679814650921, 0.0, 0.88008532800154149, 0.0, 2.6407254490454228, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.3129357343562416, 1.7536419927110329, 4.8161050998032353, 1.4535287324511634, 0.0, 0.0, 1.9899306855060284, 0.0, 0.0, 0.0, 1.478524262677118, 0.96533582695336329, 1.1058748830415039, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.1734955602452999, 0.0, 0.0, 0.0, 0.0, 0.6106552283610901, 2.5570873161420193, 1.0268184613807212, 0.0, 2.2407226370034938, 0.0, 0.0, 0.0, 1.6107777426386676, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.7509632466012033, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.7547396968149882, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.59578811279863009, 0.0, 0.83281740265809123, 1.929754797710123, 0.0, 1.5537415470829787, 0.0, 2.2282398039376057, 0.0, 0.0, 0.0, 0.34424928829041518, 0.0, 0.0, 0.4103486244777399, 0.0, 0.0, 0.0, 0.0, 0.96850658347430407, 0.9907391451890708, 0.0, 0.0, 0.0, 0.0, 0.0, 1.1996284356835756, 0.0, 0.0, 1.9298091000783182, 0.0, 3.4270023147854429, 0.0, 1.6821287468287369, 0.2461270192329271, 4.2822872277349529, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.5515019640369845, 0.0, 0.0, 0.0, 0.0, 2.3776932785844065, 0.0, 0.94137339133060738, 0.0, 0.0, 0.0, 0.0, 0.0, 1.5011800164478031, 0.0, 0.0, 0.0, 0.0, 0.90379077570109989, 0.0, 1.5136154969696241, 2.2811759618865315, 0.0, 0.0, 0.0, 0.86248852092386608, 0.0, 0.0, 0.0, 1.8540932869277944, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 3.4325152783488511, 2.8855570683262419, 0.0, 0.0, 0.91868895820143814, 0.0, 0.0, 2.0117307826664597, 0.0, 1.2136520346997606, 0.0, 0.0, 0.0, 0.90717522070137424, 0.0, 0.0, 0.0, 0.0, 5.0836452189925243, 0.0, 3.1107307797956754, 1.1643617361550964, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0638850390670467, 1.8644460239892768, 0.0, 0.0, 1.6280743592574243, 0.0, 0.57455430120297024, 0.0, 0.94465662373598625, 0.48265628563844648, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.7902725528080838, 0.0, 0.0, 0.0, 0.0, 2.7802257007890567, 0.0, 1.3390194477320418, 0.0, 0.0, 0.0, 0.0, 0.0, 0.87992224988725909, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0227462061073969, 1.5076201262423219, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.4471248602744962, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.5818144087445269, 2.0982187149746663, 0.0, 1.8918482894765496, 1.0938020654181622, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.18361795718474788, 0.0, 0.0, 1.3451369230081294, 0.0, 0.0, 0.0, 1.6523098879986933, 0.85048183350481621, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.0086687925818061, 0.0, 0.0, 0.0, 0.0, 2.1255064083116131, 0.0, 1.1776549837614927, 0.0, 0.0, 0.0, 0.0, 0.0, 1.1705100177295447, 0.0, 0.0, 0.0, 2.3230115831575411, 0.0, 0.0, 1.6061270618583119, 1.0690791827886084, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.2288345338893274, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.5940834796733516, 0.0, 0.0, 6.2209294471299028, 0.0, 0.0, 0.67570783509360266, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.71520079359123157, 0.0, 0.0, 2.5395362680349152, 0.0, 2.7273028342146439, 0.0, 0.35731332946621897, 1.0502122104241947, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.2398303565581186, 0.0, 0.0, 1.6244356389542267, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.3687289341236035, 0.0, 0.0, 0.0, 2.518851748174372, 0.0, 1.8303555890966785, 0.0, 0.0, 0.0, 0.0, 1.4275861376178163, 0.0, 1.1467710223308845, 1.3795411047217114, 0.0, 0.0, 0.0, 0.0, 0.99999999999964084, 1.0000000000001568)
>>> 
"""
