"""Test suite that runs the NLTK 'simple' doctest."""
import doctest, unittest

def additional_tests():
    return unittest.TestSuite(
        [ doctest.DocFileSuite('simple.doctest') ]
        )
