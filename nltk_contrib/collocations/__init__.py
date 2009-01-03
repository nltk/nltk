# Natural Language Toolkit: Collocations and Association Measures 
#
# Copyright (C) 2001-2008 NLTK Project
# Author: Joel Nothman <jnothman@student.usyd.edu.au>
# URL: <http://nltk.org>
# For license information, see LICENSE.TXT
#
"""
Tools to identify X{collocation}s --- words that often appear consecutively
--- within corpora. They may also be used to find other X{association}s between
word occurrences.
See Manning and Schutze ch. 5 at http://nlp.stanford.edu/fsnlp/promo/colloc.pdf

Finding collocations requires first calculating the frequencies of words and
their appearance in the context of other words. Often the collection of words
will then requiring filtering to only retain useful content terms. Each ngram
of words may then be scored according to some X{association measure}, in order
to determine the relative likelihood of each ngram being a collocation.

The L{BigramCollocationFinder} and L{TrigramCollocationFinder} classes provide
these functionalities, dependent on being provided a function which scores a
ngram given appropriate frequency counts. A number of standard association
measures are provided in L{bigram_measures} and L{trigram_measures}.
"""

# Possible TODOs:
# - separate arguments for candidates and use ngram_freq, etc. functions;
# - consider the distinction between f(x,_) and f(x) and whether our
#   approximation is good enough for fragmented data, and mention the approximation;
# - add methods to compare different association measures' results
# - is it better to refer to things as bigrams/trigrams, or pairs/triples?

from finders import *
import bigram_measures
import trigram_measures

__all__ = ['BigramCollocationFinder', 'TrigramCollocationFinder',
           'bigram_measures', 'trigram_measures']

######################################################################
#{ Deprecated
######################################################################
