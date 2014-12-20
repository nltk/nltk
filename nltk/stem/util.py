# Natural Language Toolkit: Stemmer Utilities
#
# Copyright (C) 2001-2014 NLTK Project
# Author: Helder <he7d3r@gmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

def suffix_replace(original, old, new):
    """
    Replaces the old suffix of the original string by a new suffix
    """
    return original[:-len(old)] + new
