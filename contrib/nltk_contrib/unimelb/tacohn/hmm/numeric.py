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
Optimisation of the nltk.hmm.best_path function. This involves reducing the
probability distributions to Numeric arrays of floats (previously python
dictionaries), then using Numeric vector operations to find the Viterbi path.
These Numeric operations are (mostly) highly optimised C code. This runs about
20 times faster than the naive python implementation. But of course, it's not
so clear to read! 
"""

from Numeric import *

def create_cache(model):
    N = len(model._states)
    M = len(model._symbols)
    P = zeros(N, Float32) 
    X = zeros((N, N), Float32)
    O = zeros((N, M), Float32)
    for i in range(N):
        si = model._states[i]
        P[i] = model._priors.logprob(si)
        for j in range(N):
            X[i, j] = model._transitions[si].logprob(model._states[j])
        for k in range(M):
            O[i, k] = model._outputs[si].logprob(model._symbols[k])

    S = {}
    for k in range(M):
        S[model._symbols[k]] = k

    return P, O, X, S

def best_path(model, sequence, cache):
    symbols = map(lambda tk: tk['TEXT'], sequence['SUBTOKENS'])
    T = len(symbols)
    N = len(model._states)
    P, O, X, S = cache

    V = zeros((T, N), Float32)
    B = ones((T, N), Int) * -1

    V[0] = P + O[:, S[symbols[0]]]
    for t in range(1, T):
        for j in range(N):
            vs = V[t-1, :] + X[:, j]
            best = argmax(vs)
            V[t, j] = vs[best] + O[j, S[symbols[t]]]
            B[t, j] = best

    current = argmax(V[T-1,:])
    sequence = [current]
    for t in range(T-1, 0, -1):
        last = B[t, current]
        sequence.append(last)
        current = last

    sequence.reverse()
    return map(model._states.__getitem__, sequence)

if __name__ == '__main__':
    from nltk_contrib.unimelb.tacohn.hmm.demo import demo
    demo(best_path, create_cache)
