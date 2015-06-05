# Natural Language Toolkit: Splitta sentence tokenizer
#
# Copyright (C) 2001-2015 NLTK Project
# Algorithm: Gillick (2009)
# Author: Dan Gillick <dgillick@gmail.com> (original Python implementation)
#         Sam Raker <sam.raker@gmail.com> (NLTK-compatible version)
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Splitta sentence tokenizer. This algorithm uses a classifier to label pairs
of tokens based on whether those pairs span a sentence boundary. The algorithm
is both tokenizer- and classifier-agnostic.
"""
