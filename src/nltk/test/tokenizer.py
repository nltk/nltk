# Natural Language Toolkit: Test Code for Tokens and Tokenizers
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
Unit testing for L{nltk.tokenizer}.
"""

from nltk.token import *
from nltk.tokenizer import *

def test_WhitespaceTokenizer(): r"""
Unit test cases for L{nltk.tokenizer.WhitespaceTokenizer}.

    >>> tokenizer = WhitespaceTokenizer(SUBTOKENS='WORDS')

The whitespace tokenizer breaks a text wherever sequences of
whitespace occur:
    
    >>> tok = Token(TEXT='this is a test')
    >>> tokenizer.tokenize(tok)
    >>> print tok
    <[<this>, <is>, <a>, <test>]>

Words can be broken by multiple whitespace characters:

    >>> tok = Token(TEXT='this  is a \n\t\t test')
    >>> tokenizer.tokenize(tok)
    >>> print tok
    <[<this>, <is>, <a>, <test>]>

Leading and trailing whitespace are ignored:

    >>> tok = Token(TEXT='   this  is a \n\t\t test  ')
    >>> tokenizer.tokenize(tok)
    >>> print tok
    <[<this>, <is>, <a>, <test>]>

The addlocs flag can be used to add locations:

    >>> tok = Token(TEXT='this is a test')
    >>> tokenizer.tokenize(tok, addlocs=1)
    >>> print tok
    <[<this>@[0:4c], <is>@[5:7c], <a>@[8:9c], <test>@[10:14c]]>

The addcontexts flag can be used to add context pointers:

    >>> tok = Token(TEXT='this is a test')
    >>> tokenizer.tokenize(tok, addcontexts=1)
    >>> print tok
    <[<this>, <is>, <a>, <test>]>
    >>> print tok['WORDS'][1]['CONTEXT'].getrange(-1, 2)
    [<this>, <is>, <a>]

The C{raw_tokenize} method simply breaks up a string (not using
C{Token}s at all):

    >>> tokenizer.raw_tokenize('this is a test')
    ['this', 'is', 'a', 'test']

As with the normal C{tokenize} method, multiple whitespace may appear
between words, and leading and trailing whitespace are ignored:

    >>> tokenizer.raw_tokenize('\n\t this\tis\na test   ')
    ['this', 'is', 'a', 'test']

The C{xtokenize} method generates an iterator instead of a list:

    >>> tokenizer.xtokenize(tok, addcontexts=1)
    >>> print [w for w in tok['WORDS']]
    [<this>, <is>, <a>, <test>]
    >>> print [w for w in tok['WORDS']] # generator is exhausted!
    []
"""

def test_RegexpTokenizer(): r"""
Unit test cases for L{nltk.tokenizer.RegexpTokenizer}.

This tokenizer only keeps strings of word characters; everything else
is treated as a separator:

    >>> tokenizer1 = RegexpTokenizer('\w+')

    >>> tok = Token(TEXT='\n this\t is\\a.:?test  ,')
    >>> tokenizer1.tokenize(tok)
    >>> print tok
    <[<this>, <is>, <a>, <test>]>

This tokenizer treats any sequence of whitepsace as a separator:

    >>> tokenizer2 = RegexpTokenizer('\s+', negative=1)
    >>> tok = Token(TEXT='this\t is\\a.:?test  ,')
    >>> tokenizer2.tokenize(tok)
    >>> print tok
    <[<this>, <is\\a.:?test>, <,>]>

Leading and trailing whitespace are ignored:

    >>> tok = Token(TEXT='    test:this  \n')
    >>> tokenizer2.tokenize(tok)
    >>> print tok
    <[<test:this>]>

C{raw_tokenize} directly breaks up the string (with no tokens):

    >>> tokenizer2.raw_tokenize('this\t is\\a.:?test  ,')
    ['this', 'is\\a.:?test', ',']
"""
    
#######################################################################
# Test Runner
#######################################################################

import sys, os, os.path
if __name__ == '__main__': sys.path[0] = None
import unittest, doctest, trace

def testsuite(reload_module=False):
    import doctest, nltk.test.tokenizer
    if reload_module: reload(nltk.test.tokenizer)
    return doctest.DocTestSuite(nltk.test.tokenizer)

def test(verbosity=2, reload_module=False):
    runner = unittest.TextTestRunner(verbosity=verbosity)
    runner.run(testsuite(reload_module))

if __name__ == '__main__':
    test(reload_module=True)
