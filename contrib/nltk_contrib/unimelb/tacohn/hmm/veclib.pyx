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
Optimisations of the nltk.hmm.best_path function. Extension of the standard_c
version to use the PowerPC velocity engine (in the G4 and later).
"""

cdef extern from "Accelerate.h":
    void vadd(float *v1, int s1, float *v2, int s2, float *r, int rs, int sz)
    void vsub(float *v1, int s1, float *v2, int s2, float *r, int rs, int sz)
    void vmul(float *v1, int s1, float *v2, int s2, float *r, int rs, int sz)
    void vsmul(float *v1, int s1, float *v2, float *r, int rs, int sz)
    int dotpr(float *v1, int s1, float *v2, int s2, float *r, int sz)
    int vIsamax(int count, float *v)
    int vIsamin(int count, float *v)

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

cdef show(float *vec, int count):
    cdef int i
    for i from 0 <= i < count:
        print '%f' % vec[i],
    print

def best_path(model, sequence, Cache cache):
    cdef int T, i, j, k, best_index
    cdef float *V, *temp, best_score

    symbols = []
    for token in sequence['SUBTOKENS']:
        symbols.append(token['TEXT'])
    T = len(symbols)
    V = malloc(T * cache.N * sizeof(float))
    temp = malloc(cache.N * sizeof(float))
    B = {}

    vadd(cache.P, 1,
         &cache.O[cache.S[symbols[0]]], cache.N,
         V, 1,
         cache.N)
    for t from 1 <= t < T:
        for j from 0 <= j < cache.N:
            vadd(&V[(t-1)*cache.N], 1, &cache.X[j], cache.N, temp, 1, cache.N)
            best_index = 0
            best_score = temp[0]
            for k from 1 <= k < cache.N:
                if temp[k] > best_score:
                    best_score = temp[k]
                    best_index = k
            #best_index = vIsamax(cache.N, temp)
            #best_score = temp[best_index]
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
