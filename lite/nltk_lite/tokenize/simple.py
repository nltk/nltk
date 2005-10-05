# Natural Language Toolkit: Simple Tokenizers
#
# Copyright (C) 2001-2005 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@ldc.upenn.edu>
#         Trevor Cohn <tacohn@cs.mu.oz.au>
# URL: <http://nltk.sourceforge.net>
# For license information, see LICENSE.TXT

"""
Functions for tokenizing a text, based on a regular expression
which matches tokens or gaps.
"""

SPACE      = ' '
NEWLINE    = '\n'
BLANKLINE  = '\n\n'
SHOEBOXSEP = r'^\\'

def space(s):
    """
    Tokenize the text at a single space character.

    @param s: the string or string iterator to be tokenized
    @type s: C{string} or C{iter(string)}
    @return: An iterator over tokens
    """
    return s.split(SPACE)

def line(s):
    """
    Tokenize the text into lines.

    @param s: the string or string iterator to be tokenized
    @type s: C{string} or C{iter(string)}
    @return: An iterator over tokens
    """
    return s.split(NEWLINE)

def blankline(s):
    """
    Tokenize the text into paragraphs (separated by blank lines).

    @param s: the string or string iterator to be tokenized
    @type s: C{string} or C{iter(string)}
    @return: An iterator over tokens
    """
    return s.split(BLANKLINE)

def shoebox(s):
    """
    Tokenize a Shoebox entry into its fields (separated by backslash markers).

    @param s: the string or string iterator to be tokenized
    @type s: C{string} or C{iter(string)}
    @return: An iterator over tokens
    """
    return s.split(SHOEBOXSEP)

##//////////////////////////////////////////////////////
##  Demonstration
##//////////////////////////////////////////////////////

def demo():
    """
    A demonstration that shows the output of several different
    tokenizers on the same string.
    """
    # Define the test string.
    s = "Good muffins cost $3.88\nin New York.  Please buy me\ntwo of them.\n\nThanks."
    print 'Input text:'
    print `s`
    print
    print 'Tokenize using individual space characters:'
    print list(space(s))
    print
    print 'Tokenize by lines:'
    print list(line(s))
    print
    
if __name__ == '__main__':
    demo()
