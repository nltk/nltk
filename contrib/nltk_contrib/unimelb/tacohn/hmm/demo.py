#
# Natural Language Toolkit: Hidden Markov Model extensions
#
# Copyright (C) 2004 University of Melbourne
# Author: Trevor Cohn <tacohn@cs.mu.oz.au>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$
#

"""
Demonstration of the optimised Viterbi implementations.

Running on an PowerPC G4 @ 1GHz (times in seconds):
   unoptimized     500
   numeric         14.5
   standard c      17.8
   altivec         1.5
"""

from nltk.hmm import *
from nltk.token import Token
from nltk.probability import LidstoneProbDist
import nltk_contrib.unimelb.tacohn.hmm.numeric as numeric
import nltk_contrib.unimelb.tacohn.hmm.standard_c as standard_c
import nltk_contrib.unimelb.tacohn.hmm.veclib as veclib

def demo(best_path, cache_factory):
    # demonstrates POS tagging using supervised training

    print 'Training HMM...'
    labelled_sequences, tag_set, symbols = load_pos()
    trainer = HiddenMarkovModelTrainer(tag_set, symbols)
    hmm = trainer.train_supervised(Token(SUBTOKENS=labelled_sequences[100:]),
                    estimator=lambda fd, bins: LidstoneProbDist(fd, 0.1, bins))

    print 'Creating cache', cache_factory
    cache = cache_factory(hmm)

    print 'Overriding best_path with', best_path
    hmm.__class__.best_path = lambda self, seq: best_path(self, seq, cache)

    print 'Testing...'
    import time
    start = time.clock()
    test_pos(hmm, labelled_sequences[:100], True)
    print 'elapsed time', (time.clock() - start)

if __name__ == '__main__':
    demo(numeric.best_path, numeric.create_cache)
    demo(standard_c.best_path, standard_c.Cache)
    demo(veclib.best_path, veclib.Cache)
