#!/usr/bin/env python

from nltk import FreqDist, ConditionalFreqDist, ConditionalProbDist, \
    DictionaryProbDist, DictionaryConditionalProbDist, LidstoneProbDist, \
    MutableProbDist, MLEProbDist, UniformProbDist, HiddenMarkovModelTagger

from nltk.tag.hmm import _log_add
from hadooplib.mapper import MapperBase
from hadooplib.util import *

from numpy import *

# _NINF = float('-inf')  # won't work on Windows
_NINF = float('-1e300')

_TEXT = 0  # index of text in a tuple
_TAG = 1   # index of tag in a tuple

class EM_Mapper(MapperBase):
    """
    compute the local hmm parameters from one the input sequences
    """

    def pd(self, values, samples):
        """
        helper methods to get DictionaryProbDist from 
        a list of values
        """
        d = {}
        for value, item in zip(values, samples):
            d[item] = value
        return DictionaryProbDist(d)
    
    def cpd(self, array, conditions, samples):
        """
        helper methods to get DictionaryConditionalProbDist from 
        a two dimension array
        """
        d = {}
        for values, condition in zip(array, conditions):
            d[condition] = self.pd(values, samples)
        return DictionaryConditionalProbDist(d)

    def read_params(self):
        """
        read parameter file, initialize the hmm model
        """
        params = open("hmm_parameter", 'r')
        d = {}
        A = {}
        B = {}
        for line in params:
            words = line.strip().split()
            # ignore blank lines and comment lines
            if len(words) == 0 or line.strip()[0] == "#":
                continue
            if words[0] == "Pi":
                d[words[1]] = float(words[2])
            elif words[0] == "A":
                A[(words[1], words[2])] = float(words[3]) 
            elif words[0] == "B":
                B[(words[1], words[2])] = float(words[3]) 
        params.close()

        # get initial state probability p (state)
        Pi = DictionaryProbDist(d)

        A_keys = A.keys()
        B_keys = B.keys()
        states = set()
        symbols = set()
        for e in A_keys:
            states.add(e[0])
            states.add(e[1])
        for e in B_keys:
            states.add(e[0])
            symbols.add(e[1])

        states = list(states)
        states.sort()
        symbols = list(symbols)
        symbols.sort()

        # get transition probability p(state | state)
        prob_matrix = []
        for condition in states:
            li = []
            for state in states:
                li.append(A.get((condition, state), 0))
            prob_matrix.append(li)
        A = self.cpd(array(prob_matrix, float64), states, states)

        # get emit probability p(symbol | state)
        prob_matrix = []
        for state in states:
            li = []
            for symbol in symbols:
                li.append(B.get((state, symbol), 0))
            prob_matrix.append(li)
        B = self.cpd(array(prob_matrix, float64), states, symbols)
        
        return symbols, states, A, B, Pi

    def map(self, key, value):
        """
        establish the hmm model and estimate the local
        hmm parameters from the input sequences

        @param key: None
        @param value: input sequence
        """

        symbols, states, A, B, pi = self.read_params()
        N = len(states)
        M = len(symbols)
        symbol_dict = dict((symbols[i], i) for i in range(M))

        model = HiddenMarkovModelTagger(symbols=symbols, states=states, \
                transitions=A, outputs=B, priors=pi)

        logprob = 0
        sequence = list(value)
        if not sequence:
            return

        # compute forward and backward probabilities
        alpha = model._forward_probability(sequence)
        beta = model._backward_probability(sequence)

        # find the log probability of the sequence
        T = len(sequence)
        lpk = _log_add(*alpha[T-1, :])
        logprob += lpk

        # now update A and B (transition and output probabilities)
        # using the alpha and beta values. Please refer to Rabiner's
        # paper for details, it's too hard to explain in comments
        local_A_numer = ones((N, N), float64) * _NINF
        local_B_numer = ones((N, M), float64) * _NINF
        local_A_denom = ones(N, float64) * _NINF
        local_B_denom = ones(N, float64) * _NINF

        # for each position, accumulate sums for A and B
        for t in range(T):
            x = sequence[t][_TEXT] #not found? FIXME
            if t < T - 1:
                xnext = sequence[t+1][_TEXT] #not found? FIXME
            xi = symbol_dict[x]
            for i in range(N):
                si = states[i]
                if t < T - 1:
                    for j in range(N):
                        sj = states[j]
                        local_A_numer[i, j] =  \
                            _log_add(local_A_numer[i, j],
                                    alpha[t, i] + 
                                    model._transitions[si].logprob(sj) + 
                                    model._outputs[sj].logprob(xnext) +
                                    beta[t+1, j])
                    local_A_denom[i] = _log_add(local_A_denom[i],
                                alpha[t, i] + beta[t, i])
                else:
                    local_B_denom[i] = _log_add(local_A_denom[i],
                            alpha[t, i] + beta[t, i])

                local_B_numer[i, xi] = _log_add(local_B_numer[i, xi],
                        alpha[t, i] + beta[t, i])

        for i in range(N):
            self.outputcollector.collect("parameters", \
                    tuple2str(("Pi", states[i], pi.prob(states[i]))))

        self.collect_matrix('A', local_A_numer, lpk, N, N)
        self.collect_matrix('B', local_B_numer, lpk, N, M)
        self.collect_matrix('A_denom', [local_A_denom], lpk, 1, N)
        self.collect_matrix('B_denom', [local_B_denom], lpk, 1, N)

        self.outputcollector.collect("parameters", "states " + \
                tuple2str(tuple(states)))
        self.outputcollector.collect("parameters", "symbols " + \
                tuple2str(tuple(symbols)))


    def collect_matrix(self, name, matrix, lpk, row, col):
        """
        a utility function to collect the content in matrix
        """
        for i in range(row):
            for j in range(col):
                self.outputcollector.collect("parameters", \
                        tuple2str((name, i, j, matrix[i][j], lpk, row, col)))
                        



if __name__ == "__main__":
    EM_Mapper().call_map()
