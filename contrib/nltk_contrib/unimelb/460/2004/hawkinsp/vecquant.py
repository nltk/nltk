#!/usr/bin/python

__doc__ = '''
433-460 Human Language Technology Project
Author: Peter Hawkins <hawkinsp@cs.mu.oz.au>
Student Number: 119004

Given a set of vectors, perform vector quantization to obtain a set of
NUM_CODEWORDS representative codewords. Ideally, the codewords should end up
such that if each vector is grouped with the codeword to which it is nearest
in a Euclidean distance sense, then each codeword should end up with an
equal number of vectors.

The algorithm implemented here is the LBG (Linde, Buzo, Gray, 1980) algorithm,
taken from the description available at:
http://www.data-compression.com/vq.html

This Python implementation is very slow, probably due to repeated object 
creation/destruction cycles, so it has also been implemented in C++ in the file
vecquant.cpp. The C++ implementation is substantially faster, but identical
in most other respects.
'''

import sys, string, re
from vector import *

# A small constant used for permuting the vectors
EPSILON = 0.01

# The desired number of codewords
NUM_CODEWORDS = 64

# Number of dimensions for each vector
DIMENSIONS = 12

def closest_codeword(codewords, vec):
    '''Given a list of codeword vectors and a test vector, return the codeword
    vector that is closest to the test vector.'''
    
    best_index = None
    best_value = 0.0
    for i in range(len(codewords)):
        delta = codewords[i] - vec
        dist = delta * delta

        if best_index is None or dist < best_value:
            best_index = i
            best_value = dist

    return best_index

def vector_quantize(vecs):
    zero = Vector(array([0.] * DIMENSIONS))

    # Compute an initial centroid as the first codeword
    cw = zero.copy()

    for v in vecs:
        cw = cw + v

    cw.scale(1.0 / float(len(vecs)))

    codewords = [cw]
    
    d_av = 0.0
    for v in vecs:
        t = v - cw
        d_av = d_av + (t * t)
    d_av = d_av / (float(len(vecs)) * float(DIMENSIONS))

    while len(codewords) < NUM_CODEWORDS:
        print len(codewords)
        # Split each codeword into two codewords
        curcodewords = []
        for c in codewords:
            c1 = c.copy()
            c1.scale(1.0 - EPSILON)
            curcodewords.append(c1)
            c2 = c.copy()
            c2.scale(1.0 + EPSILON)
            curcodewords.append(c2)

        cur_d_av = d_av
        while 1:
            # Iteratively improve the codeword vectors
            q = [0] * len(vecs)
            vec_count = [0] * len(curcodewords)
            vec_sum = [zero.copy() for dummy in range(len(curcodewords))]

            # Compute the new codewords
            for i in range(len(vecs)):
                c = closest_codeword(curcodewords, vecs[i])
                q[i] = c
                vec_sum[c] = vec_sum[c] + vecs[i]
                vec_count[c] = vec_count[c] + 1

            # Update the codewords
            oldcodewords = curcodewords
            curcodewords = [
                # The EPSILON here is a fudge factor to avoid a possible
                # division by zero
                vec_sum[i].scale(1.0 / (float(vec_count[i]) + EPSILON))
                for i in range(len(oldcodewords))
            ]

            old_d_av = cur_d_av
            cur_d_av = 0.0
            for i in range(len(vecs)):
                t = vecs[i] - oldcodewords[q[i]]
                cur_d_av = cur_d_av + (t * t)
            cur_d_av = cur_d_av / (float(len(vecs)) * float(DIMENSIONS))

            # Loop until convergence
            if (old_d_av - cur_d_av) / old_d_av <= EPSILON:
                break

        codewords = curcodewords
        # Loop until we have enough codewords

    return codewords

def main():
    '''Given a set of vectors, perform a vector quantization procedure to
    produce a list of 'representative' codewords. See the documentation at
    the top of the file for more details.
    
    The expected format for the input file consists of the concatenation of any
    number MFCC coefficient files.  Each coefficient file begins with a single
    number n, which is the number of vectors in that file, followed by n lines,
    each containing DIMENSIONS floating point numbers, each representing a
    single vector.
    '''

    def parse_vec(x):
        return Vector(array(
            map(float, string.split(string.strip(re.sub('[\[\]]', '', x))))
        ))

    # Read in a list of vectors, one per line
    vecs = []
    inpline = sys.stdin.readline()

    while inpline:
        vecs = vecs + map(parse_vec, string.split(inpline, ';')[:-1])
        inpline = sys.stdin.readline()

    # Perform vector quantization to obtain a list of codewords
    cwds = vector_quantize(vecs)

    # Output the codewords
    print len(cwds)
    for c in cwds:
        val = []
        for v in c.value:
            sys.stdout.write("%f " % v)
        sys.stdout.write("\n")

if __name__ == "__main__":
    main()


