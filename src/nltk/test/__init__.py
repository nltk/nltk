# Natural Language Toolkit: Unit Tests
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
Unit tests for the NLP toolkit.
"""

import unittest

def testsuite():
    """
    Return a PyUnit testsuite for the NLP toolkit
    """

    import nltk.test.token, nltk.test.tree

    modules = nltk.test.token, nltk.test.tree

    return unittest.TestSuite([m.testsuite() for m in modules]) 

def test():
    """
    Run unit tests for the NLP toolkit; print results to stdout/stderr
    """
    import unittest
    runner = unittest.TextTestRunner()
    runner.run(testsuite())

if __name__ == '__main__':
    test()
