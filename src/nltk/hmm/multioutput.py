# Natural Language Toolkit: Multi-Output Hidden Markov Model
#
# Copyright (C) 2004 University of Melbourne
# Author: Phil Blunsom <pcbl@cs.mu.oz.au>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
Two Hidden Markov Models that overcome the limitation of the standard model 
that only allows single dimensional observations to be emitted from a
state. Multi-Ouput Hidden Markov Models represent multi-dimensional observations
as tuples of features and the probability of observing an observation in a 
particular state as the joint probability of the observations features given 
the state.
The joint probability formulas used here are based on: 
"McCallum, Nigram. A Comparision of Event models for Naive Bayes 
Text Classification"
"""

# PYTHON
from sys import *

# NLTK
from nltk.chktype import chktype
from nltk.probability import *
from nltk.hmm import HiddenMarkovModel 
from nltk.hmm import HiddenMarkovModelTrainer 
from nltk.token import Token

# Python
from numarray import *
import re

class MultinomialHMM(HiddenMarkovModel):
    def _output_logprob(self, state, symbol):
        """
        Assume that the features are independent. Therefore the
        probability of an observation is simply the product of the
        individual probabilities of its features given the state.
        """
        output_probability = 0
        for output_index in range(len(self._outputs)):
            output_probability += log(self._outputs[output_index] \
                                [state].prob(symbol[output_index]))
        return output_probability 

    def __repr__(self):
        features = len(self._symbols)
        str = ''
        for feature in range(features):
            str += ' Feature %d licenses %d output symbols,' \
                    % (feature, len(self._symbols[feature]))
        str = str.rstrip(',') + '>'
        return '<HMM %d states and %d output symbol features.' \
                % (len(self._states), features) + str

class MultiVariateBernoulliHMM(HiddenMarkovModel):
    def __init__(self, symbols, states, transitions, outputs, priors, **properties):
        """
        @param  symbols:        sets of output symbols (alphabets) for
                                each observation feature. Therefore the 
                                dimension of the observations equals
                                len(symbols)
        @type   symbols:        (seq) of (seq) of any
        @param  states:         a set of states representing state space
        @type   states:         seq of any
        @param  transitions:    transition probabilities; Pr(s_i | s_j)
                                is the probability of transition from state i
                                given the model is in state_j
        @type   transitions:    C{ConditionalProbDistI}
        @param  outputs:        output probabilities; Pr(o_k | s_i) is the
                                probability of emitting symbol k when entering
                                state i
        @type   outputs:        C{ConditionalProbDistI}
        @param  priors:         initial state distribution; Pr(s_i) is the
                                probability of starting in state i
        @type   priors:         C{ProbDistI}
        @param  properties:     property names: TAG, TEXT, and SUBTOKENS are
                                used and may be overridden
        @type   properties:     C{dict}
        """
        HiddenMarkovModel.__init__(self, symbols, states, transitions, outputs, priors, properties)
        self._compile_logprobs()

    def _compile_logprobs(self):
        """
        We precompile probabilities for all the features not occuring. This
        enables fast calculations for _output_logprob
        """
        self._no_output_prob = {}
        for state in self._states:
            probability = 0
            for i in range(len(self._outputs)):
                probDist = self._outputs[i][state]
                for sample in probDist.samples():
                    probability += log(1 - probDist.prob(sample))
            self._no_output_prob[state] = probability

    def _output_logprob(self, state, symbol):
        """
        Calculate the observation probability as the product of the probability
        of each observed feature, and the probability of not observing the unseen
        features, given the state.
        """
        output_probability = self._no_output_prob[state]
        for conProbDist, feature in zip(self._outputs, symbol):
            prob = conProbDist[state].prob(feature)
            if prob < 1:
                output_probability += log(prob)
                output_probability -= log(1 - prob)
        return output_probability 

class MultiOutputHMMTrainer(HiddenMarkovModelTrainer):
    def __init__(self, states=None, symbols=None, **properties):
        """
        Creates an HMM trainer to induce an HMM with the given states and
        output symbol alphabet. Only a supervised training method may be used.
        """
        assert chktype(1,symbols,types.TupleType,types.ListType,types.NoneType)
        assert chktype(2,states,types.TupleType,types.ListType,types.NoneType)
        if states:
            self._states = states
        else:
            self._states = []
        if symbols:
            self._symbols = symbols
        else:
            self._symbols = []
        self._properties = properties

    def train(self, labelled_sequences=None, unlabelled_sequences=None,
              **kwargs):
        raise NotImplementedError()

    def train_unsupervised(self, unlabelled_sequences, **kwargs):
        raise NotImplementedError()

    def train_supervised(self, labelled_sequences, **kwargs):
        """
        Supervised training maximising the joint probability of the symbol and
        state sequences. This is done via collecting frequencies of
        transitions between states, symbol observations while within each
        state and which states start a sentence. These frequency distributions
        are then normalised into probability estimates, which can be
        smoothed if desired.
        """
        assert chktype(1, labelled_sequences, Token)

        # grab the property names used
        TEXT = self._properties.get('TEXT', 'TEXT')
        TAG = self._properties.get('TAG', 'TAG')
        SUBTOKENS = self._properties.get('SUBTOKENS', 'SUBTOKENS')

        # default to the MLE estimate
        estimator = kwargs.get('estimator')
        if estimator == None:
            estimator = lambda fdist, bins: MLEProbDist(fdist)

        # default to the Multinomial model
        model = kwargs.get('model')
        if model == None:
            model = MultinomialHMM

        # count occurences of starting states, transitions out of each state
        # and output symbols observed in each state
        starting = FreqDist()
        transitions = ConditionalFreqDist()
        # for the multi-output hidden markov model we need a conditional freq
        # dist for each feature
        outputs = [ConditionalFreqDist() for i in range(len(self._symbols))]
        for super_token in labelled_sequences[SUBTOKENS]:
            lasts = None
            for token in super_token[SUBTOKENS]:
                state = token[TAG]
                symbol = token[TEXT]
                if lasts == None:
                    starting.inc(state)
                else:
                    transitions[lasts].inc(state)
                # updates counts for each observation feature independently
                for output, feature in zip(outputs, symbol):
                    output[state].inc(feature)
                lasts = state

                # update the state and symbol lists
                if state not in self._states:
                    self._states.append(state)
                # individual feature sets are kept for each observation feature
                for feature, feature_set in zip(symbol, self._symbols):
                    if feature not in feature_set:
                        feature_set.append(feature)

        # create probability distributions (with smoothing)
        N = len(self._states)
        pi = estimator(starting, N)
        A = ConditionalProbDist(transitions, estimator, False, N)
        # the output probabilities are stored in a conditional prob dist for
        # each feature of observations
        B = [ConditionalProbDist(output, estimator, False, len(feature)) \
            for output, feature in zip(outputs, self._symbols)]
                               
        return model(self._symbols, self._states, A, B, pi)

def load_pos():
    from nltk.corpus import brown

    tagged_tokens = []
    for item in brown.items()[:5]:
        tagged_tokens.append(brown.read(item))

    tag_set = ["'", "''", '(', ')', '*', ',', '.', ':', '--', '``', 'abl',
        'abn', 'abx', 'ap', 'ap$', 'at', 'be', 'bed', 'bedz', 'beg', 'bem',
        'ben', 'ber', 'bez', 'cc', 'cd', 'cd$', 'cs', 'do', 'dod', 'doz',
        'dt', 'dt$', 'dti', 'dts', 'dtx', 'ex', 'fw', 'hv', 'hvd', 'hvg',
        'hvn', 'hvz', 'in', 'jj', 'jjr', 'jjs', 'jjt', 'md', 'nn', 'nn$',
        'nns', 'nns$', 'np', 'np$', 'nps', 'nps$', 'nr', 'nr$', 'od', 'pn',
        'pn$', 'pp$', 'ppl', 'ppls', 'ppo', 'pps', 'ppss', 'ql', 'qlp', 'rb',
        'rb$', 'rbr', 'rbt', 'rp', 'to', 'uh', 'vb', 'vbd', 'vbg', 'vbn',
        'vbz', 'wdt', 'wp$', 'wpo', 'wps', 'wql', 'wrb']
        
    sequences = []
    sequence = []
    start_re = re.compile(r'[^-*+]*')
    for token in tagged_tokens:
        # the multi-output allows us to treat each word as a
        # tuple of features
        for sub_token in token['WORDS']:
            sequence.append(sub_token)
            # a feature for words as lower case
            features = [sub_token['TEXT'].lower()]
            #a feature for word suffixes of length 3
            features.append(sub_token['TEXT'][-3:])
            # a feature for the length of words
            features.append(len(sub_token['TEXT']))
            # store the observation as a tuple of features
            sub_token['TEXT'] = tuple(features)
            m = start_re.match(sub_token['TAG'])
            # cleanup the tag
            tag = m.group(0)
            if tag in tag_set:
                sub_token['TAG'] = tag
            else:
                sub_token['TAG'] = '*'
            # split on the period tag
            if sub_token['TAG'] == '.': 
                sequences.append(Token(SUBTOKENS=sequence))
                sequence = []

    return sequences, tag_set, 3

def demo_pos():
    from sys import stdout

    print 'Training HMM...'
    labelled_sequences, tag_set, num_features = load_pos()
    trainer = MultiOutputHMMTrainer(tag_set, [[] for x in range(num_features)])
    hmm = trainer.train_supervised(Token(SUBTOKENS=labelled_sequences[100:]),
                    estimator=lambda fd, bins: LidstoneProbDist(fd, 0.1, bins))
    
    print 'Testing...'
    
    for super_token in labelled_sequences[:3]:
        print super_token
        print 'HMM >>>'
        print hmm.best_path(super_token.exclude('TAG'))
        print '-' * 60

    count = correct = 0
    for super_token in labelled_sequences[:100]:
        print '.',
        stdout.flush()
        pts = hmm.best_path(super_token.exclude('TAG'))
        for token, tag in zip(super_token['SUBTOKENS'], pts):
            count += 1
            if tag == token['TAG']:
                correct += 1

    print 'accuracy over first', count, 'tokens %.1f' % (100.0 * correct / count)

def _untag(labelled_sequences):
    unlabelled = []
    for token in labelled_sequences:
        unlabelled.append(token.exclude('TAG'))
    return unlabelled


if __name__ == '__main__':
    demo_pos()
