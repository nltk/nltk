# Natural Language Toolkit: Decision list classifier
#
# Copyright (C) 2003 University of Melbourne
# Author: Trevor Cohn <tacohn@cs.mu.oz.au>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
A word sense disambiguation (WSD) classifier model using a decision list [1].
This hypothesis space includes the set of arbitary length condition, label
pairs ordered such that the label assigned to a given instance is that
corresponding to the first condition which is met by the instance. This can be
thought of as a big if-then-else chain of statements, as shown below::

    if condition/1 then label/1
    elsif condition/2 then label/2
    elsif condition/3 then label/3
    ...
    else default label

Note that the labels listed may be the same or different between separate
conditions, and the default label is simply the label which occured most
commonly in training.

Finding the hypothesis which maximises the probability of the training data
simply involves ranking each C{(feature, value)} pair in order of
I{log-likelihood}::

    abs(log(Pr(fv | l1) / Pr(fv | l2)))

where C{fv} is the feature value and C{l1} and C{l2} are the two possible
labels, assuming a binary classification task. Extending this to deal with
more that two labels simply involves summing the probability of the C{fv} over
all the labels other than C{l1} and using this as the denominator.

Once the ranking has been performed, this list is transformed into a decision
list by sorting into decreasing I{log-likelihood} and using the C{(feature,
value)} pair as the condition (is the instance's value for C{feature} equal to
C{value}?), and the C{l1} as the label.

[1] Yarowsky, D. ``Decision Lists for Lexical Ambiguity Resolution: Application
to Accent Restoration in Spanish and French.'' In Proceedings of the 32nd
Annual Meeting of the Association for Computational Linguistics.  Las Cruces,
NM, pp. 88-95, 1994.
"""

import bisect, operator
from nltk.set import Set
from nltk_contrib.unimelb.tacohn.classifier import ClassifierTrainerI
from nltk_contrib.unimelb.tacohn.classifier.feature import *
from nltk.probability import *
from nltk.token import *

class DecisionListClassifier(AbstractFeatureClassifier):
    """
    A classifier using an ordered list of C{(condition, label)} pairs to
    classify instances. The label from the first matching condition is
    assigned to each instance to be classified.
    """

    def __init__(self, fd_list, ranked_fvs, labels, default):
        """
        Creates the decision list classifier.

        @param fd_list: The feature detector list.
        @type fd_list: C{FDList}
        @param labels: The set of possible labels.
        @type fd_list: C{sequence} of any
        @param default: The default label to use. Must be a member of
            C{labels}.
        @type fd_list: any
        """
        AbstractFeatureClassifier.__init__(self, fd_list, labels)
        self._default = default
        self._default_likelihood = 1e-20 # just a little more than one
        self._ranked_fvs = ranked_fvs
        # ranked_fvs is a (likelihood, sense, list of non-zero indices)

    def fv_list_likelihood(self, fv_list, label):
        # inherit docs from AFC
        # find an entry matching entry in the list 
        for likelihood, sense, (fnum, fval) in self._ranked_fvs:
            if fv_list[fnum] == fval and sense == label:
                return likelihood # should this be e^lh? FIXME
            # otherwise, keep going

        if label == self._default:
            return self._default_likelihood
        else:
            return 0.0

    def likelihood(self, labeled_token):
        """
        @return: The likelihood of the given labeled token. This is a scaled
        probability and can be used as such after normalisation.
        @param labeled_token: The labeled token to test.
        @type labeled_token: C{Token} of C{LabeledText}
        """
        fv_list = self._fd_list.detect(labeled_token.type())
        return self.fv_list_likelihood(fv_list, labeled_token.type().label())

    def classify(self, unlabeled_token):
        # inheriy docs from AFC
        label = self._default
        fv_list = self._fd_list.detect(unlabeled_token.type())

        # find an entry matching entry in the list 
        for likelihood, sense, (fnum, fval) in self._ranked_fvs:
            if fv_list[fnum] == fval:
                label = sense
                break

        return Token(LabeledText(unlabeled_token.type(), label), 
                     unlabeled_token.loc())

    def __repr__(self):
        # inheriy docs from AFC
        return '<DecisionListClassifier with %d options>' % len(self._fd_list)

class DecisionListClassifierTrainer(ClassifierTrainerI):
    """
    Trainer for the decision list classifier. This classifier induces a
    hypothesis of the form of a decision list, a series of conditions and
    labels, where the label from the first match condition is used for
    classification.

    Finding the hypothesis which maximises the probability of the training data
    simply involves ranking each C{(feature, value)} pair in order of
    I{log-likelihood}::

        abs(log(Pr(fv | l1) / Pr(fv | l2)))

    where C{fv} is the feature value and C{l1} and C{l2} are the two possible
    labels, assuming a binary classification task. Extending this to deal with
    more that two labels simply involves summing the probability of the C{fv} over
    all the labels other than C{l1} and using this as the denominator.

    Smoothing is performed in order to avoid zero numerators and denominators.
    This is done by simply adding a small constant C{alpha} to the count of
    each C{(feature value, label)} pair. This means that the new MLE estimate
    of C{Pr(fv | l)} for all C{fv} and C{l} can never be zero.

    Once the ranking has been performed, this list is transformed into a decision
    list by sorting into decreasing I{log-likelihood} and using the C{(feature,
    value)} pair as the condition (is the instance's value for C{feature} equal to
    C{value}?), and the C{l1} as the label.

    [1] Yarowsky, D. ``Decision Lists for Lexical Ambiguity Resolution: Application
    to Accent Restoration in Spanish and French.'' In Proceedings of the 32nd
    Annual Meeting of the Association for Computational Linguistics.  Las Cruces,
    NM, pp. 88-95, 1994.
    """
    
    def __init__(self, fd_list, alpha = 0.1, llt = 0, trace = False):
        """
        Create the trainer.
        @param fd_list: The feature detector list.
        @type fd_list: C{FDList}
        @param alpha: The smoothing parameter. (default 0.1)
        @type alpha: float
        @param llt: The log-likelihood threshold, below which to exclude all
            rules from consideration. This pruning will reduce the size of the
            decision list, but may also decrease accuracy. It cannot be below
            zero, as this condition would then predict a different label.
            (default 0)
        @type llt: float
        @param trace: Show debug output. (default False)
        @type trace: boolean
        """
        self._fd_list = fd_list
        self._alpha = alpha
        self._llt = llt
        self._trace = trace
    
        assert self._alpha > 0.0, 'alpha must be positive' 
        assert self._llt >= 0.0, 'llt cannot be negative'

    def train(self, training_tokens):
        # inherit docs from CTI
        if self._trace:
            print 'DLT.train - getting frequency stats'

        # count the occurances of the senses for each combination of features
        # required and their detection output on the training data.
        coocurance_fd = ConditionalFreqDist()
        sense_fd = FreqDist()
        for token in training_tokens:
            lt = token.type()
            sense_fd.inc(lt.label())
            fv_list = self._fd_list.detect(lt.text())
            assignments = fv_list.assignments()
            for id, value in assignments:
                coocurance_fd[id, value].inc(lt.label())

        if self._trace:
            print 'DLT.train - smoothing into a ProbDist'

        # this means the pr(a) = (count(a) + alpha) / (N + B * alpha)
        # effectively the counts are all incremented by alpha
        # when considering pr(a) / pr(b), the denominators cancel
        # leaving (count(a) + alpha) / (count(b) + alpha), which effectively
        # damps low count values (with high enough alpha) and eliminates
        # possibility of infinity (divide by zero), given alpha > 0
        coocurance_pd = ConditionalProbDist(coocurance_fd,
            LidstoneProbDist, self._alpha)

        # FIXME - shouldn't I supply the number of buckets??? Although this
        # means I need to know the range of possible feature values - well
        # the size of the cartesian product of (feature, value) pairs. Can't
        # think of an easy way to do this!

        if self._trace:
            print 'DLT.train - ranking by loglikelihood'

        # rank the conditions - tuple of detector combination tuple and
        # detector output tuple - in order of loglikelihood. Defined as
        # abs(log(Pr(S_i | condition) / sum k != i Pr(S_i | condition))).
        # higher is better, indicating that S_i is more common that the other
        # senses given the evidence.
        ranks = []
        for condition in coocurance_pd.conditions():
            max = None
            sum = 0
            for sense in sense_fd.samples():
                p = coocurance_pd[condition].logprob(sense)
                sum += p
                if not max or p > max[0]:
                    max = (p, sense)

            loglikelihood = abs(max[0] - (sum - max[0]))
            bisect.insort(ranks, (loglikelihood, max[1], condition))

        # remove those below the loglikelihood threshold
        ranked_fvs = filter(lambda item: item[0] >= self._llt, ranks)
        ranked_fvs.reverse()

        # show the decision list structure
        if self._trace:
            print 'DLT.train - done, conditions are:'
            for lp, sense, (fnum, val) in ranked_fvs:
                try:
                    verbose = self._fd_list.describe(fnum)
                except AttributeError:
                    verbose = str(fnum)
                print '%.2f => (%s) %s = %s' % (lp, sense, verbose, val)

        return DecisionListClassifier(self._fd_list, ranked_fvs,
            sense_fd.samples(), sense_fd.max())

def demo():
    instances = [['bank', 'river'], ['bank', 'swim'],
                 ['banks', 'swim'], ['bank', 'visit'],
                 ['banks', 'charge'], ['bank', 'interest'], 
                 ['bank', 'visit'], ['banking', 'internet'], 
                 ['bank', 'with'], ['bank', 'on'], ['bank', 'with']]
    labels = ['river', 'river', 'river', 'river',
              'finance', 'finance', 'finance', 'finance', 'finance',
              'depend', 'depend']
    lts = map(LabeledText, instances, labels)
    tts = map(Token, lts)

    ws = reduce(operator.add, instances)
    words = Set(*reduce(operator.add, instances)).elements()

    first_word = FilteredFDList(lambda seq: seq[0:1], BagOfWordsFDList(words), 'first word is')
    second_word = FilteredFDList(lambda seq: seq[1:2], BagOfWordsFDList(words), 'second word is')
    fd_list = first_word + second_word

    print words

    print first_word.detect(['bank', 'river']).assignments()
    print second_word.detect(['bank', 'river']).assignments()
    print fd_list.detect(['bank', 'river']).assignments()

    print 'training...'
    trainer = DecisionListClassifierTrainer(fd_list, alpha=0.2, trace=True)
    classifier = trainer.train(tts)
    print 'classifier ', classifier

    tests = map(Token,
                [['banks', 'visit'],
                 ['bank', 'with'],
                 ['bank', 'swim'],
                 ['banks', 'swim'],
                 ['banks', 'swim'],
                 ['banks', 'charge'],
                 ['banks', 'on'],
                 ['banking', 'with'],
                 ['banking', 'internet'],
                 ['bank', 'charge']])

    print 'testing...'
    for test in tests:
        print 'classify(%s) = %s' % (test, classifier.classify(test))
        print 'dist_dict(%s) = %s' % (test, classifier.distribution_dictionary(test))

if __name__ == '__main__':
    demo()
