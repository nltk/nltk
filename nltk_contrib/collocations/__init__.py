# Natural Language Toolkit: Association Measures and Collocations
#
# Copyright (C) 2001-2008 NLTK Project
# Author: Joel Nothman <jnothman@student.usyd.edu.au>
# URL: <http://nltk.org>
# For license information, see LICENSE.TXT
#
"""
TODO: write comment
"""

# Possible TODOs:
# - separate arguments for candidates and use ngram_freq, etc. functions;
# - consider the distinction between f(x,_) and f(x) and whether our
#   approximation is good enough for fragmented data, and mention the approximation;
# - add methods to compare different association measures' results
# - is it better to refer to things as bigrams/trigrams, or pairs/triples?

from finder import *
import bigram_measures
import trigram_measures

__all__ = ['BigramCollocationFinder', 'TrigramCollocationFinder',
           'bigram_measures', 'trigram_measures']

######################################################################
#{ Deprecated
######################################################################
