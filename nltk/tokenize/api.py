# Natural Language Toolkit: Tokenizer Interface
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Tokenizer Interface
"""

class TokenizerI(object):
    """
    A procesing interface for I{tokenizing} a string, or dividing it
    into a list of substrings.
    """
    def tokenize(self, s):
        """
        Divide the given string into a list of substrings.
        
        @return: C{list} of C{str}
        """
        raise NotImplementedError()
