# Natural Language Toolkit: RTE Corpus Reader
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author:  Ewan Klein <ewan@inf.ed.ac.uk>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Initial code for interfacing RTE tagger with the RTECorpusReader.
"""

from nltk.corpus import rte
from nltk import evaluate


def accuracy(rtetagger, gold):
	"""
    Score the accuracy of the RTETagger against the Gold standard.

    @type rtetagger: ???
    @param tagger: The rtetagger being evaluated.
    @type gold: C{list} of L{RTEPair}
    @param gold: The list of tagged text-hypothesis pairs to score the tagger on.
    @rtype: C{float}
    """
	gold_values = [(rtepair.gid, rtepair.value) for rtepair in gold]
	predictions = []
	for rtepair in gold:
		predictions.append((rtepair.gid, tagger.tag(rtepair)))
	return evaluate.accuracy(gold_values, predictions)



class RTEGuesser(object):
	"""
	Random baseline tagger
	"""
	def tag(self, rtepair):
		from random import choice
		return choice([0, 1])

def demo():
	"""
	Demo of the random guesser for RTE
	"""
	gold = rte.pairs(('rte1_test_gold', 'rte2_test_gold', 'rte3_test_gold'))

	tagger = RTEGuesser()
	print accuracy(tagger, gold)