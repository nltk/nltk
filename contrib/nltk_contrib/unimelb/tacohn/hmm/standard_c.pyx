#
# Natural Language Toolkit: Optimised HMM Viterbi implemenation
#
# Copyright (C) 2004 University of Melbourne
# Author: Trevor Cohn <tacohn@cs.mu.oz.au>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$
#

"""
Optimisations of the nltk.hmm.best_path function. This involves reducing the
prob dists to arrays of floats, then using a primarily C-based inner loop.
Hence the use of Pyrex, which allows C and python-like code to be
interspersed.
"""

cdef extern from *:
    float *malloc(int)
    void free(float *)

cdef class Cache:
    cdef int N, M
    cdef float *P, *X, *O
    cdef object S

    def __init__(self, model):
        self.N = len(model._states)
        self.M = len(model._symbols)
        self.P = malloc(self.N * sizeof(float))
        self.X = malloc(self.N * self.N * sizeof(float))
        self.O = malloc(self.N * self.M * sizeof(float))
        for i from 0 <= i < self.N:
            si = model._states[i]
            self.P[i] = model._priors.logprob(si)
            for j from 0 <= j < self.N:
                self.X[i*self.N + j] = \
                    model._transitions[si].logprob(model._states[j])
            for k from 0 <= k < self.M:
                self.O[i*self.M + k] = \
                    model._outputs[si].logprob(model._symbols[k])

        self.S = {}
        for k from 0 <= k < self.M:
            self.S[model._symbols[k]] = k

    def __del__(self):
        free(self.P)
        free(self.X)
        free(self.O)

def best_path(model, sequence, Cache cache):
    cdef int T, i, j, k, best_index
    cdef float *V, *temp, best_score, score

    symbols = []
    for token in sequence['SUBTOKENS']:
        symbols.append(token['TEXT'])
    T = len(symbols)
    V = malloc(T * cache.N * sizeof(float))
    temp = malloc(cache.N * sizeof(float))
    B = {}

    for i from 0 <= i < cache.N:
        V[i] = cache.P[i] + cache.O[i*cache.M + cache.S[symbols[0]]]

    for t from 1 <= t < T:
        for j from 0 <= j < cache.N:
            best_index = best_score = -1
            for k from 0 <= k < cache.N:
                score = V[(t-1)*cache.N + k] + cache.X[k * cache.N + j]
                if score > best_score or best_index == -1:
                    best_score = score
                    best_index = k
            V[t*cache.N + j] = best_score + \
                cache.O[j*cache.M + cache.S[symbols[t]]]
            B[t, j] = best_index

    best_index = 0
    best_score = V[(T-1)*cache.N]
    for k from 1 <= k < cache.N:
        if V[(T-1)*cache.N + k] > best_score:
            best_score = V[(T-1)*cache.N + k]
            best_index = k

    free(V)
    free(temp)

    current = best_index
    sequence = [current]
    for t in range(T-1, 0, -1):
        last = B[t, current]
        sequence.append(last)
        current = last

    sequence.reverse()
    return map(model._states.__getitem__, sequence)

