# Natural Language Toolkit: Taggers
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
...
"""

class ParserI:
    def __init__(self):
        """
        Construct a new C{Parser}.
        """

    def parse(tokens):
        """
        @param tokens: The list of tokens to be parsed.
        @type tokens: C{list} of C{Token}
        @rtype: C{TreeToken}
        @return: The resulting parse tree.
        """
        assert 0, "ParserI is an abstract interface"
