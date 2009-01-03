# Natural Language Toolkit: Trigram Association Measures
#
# Copyright (C) 2001-2008 NLTK Project
# Author: Joel Nothman <jnothman@student.usyd.edu.au>
# URL: <http://nltk.org>
# For license information, see LICENSE.TXT
#
"""
TODO: write comment
"""


def raw_freq(n_iii,
             n_ixx, n_xix, n_xxi,
             n_iix, n_ixi, n_xii,
             n_xxx):
    return float(n_iii) / n_xxx

