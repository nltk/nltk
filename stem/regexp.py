# Natural Language Toolkit: Stemmers
#
# Copyright (C) 2001-2006 University of Melbourne
# Author: Trevor Cohn <tacohn@cs.mu.oz.au>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

from nltk_lite.stem import *

class Regexp(StemI):
    """
    A stemmer that uses regular expressions to identify morphological
    affixes.  Any substrings that matches the regular expressions will
    be removed.
    """
    def __init__(self, regexp):
        """
        Create a new regexp stemmer.

        @type regexp: C{string} or C{regexp}
        @param regexp: The regular expression that should be used to
            identify morphological affixes.
        """

        if not hasattr(regexp, 'pattern'):
            regexp = re.compile(regexp)
        self._regexp = regexp

    def stem(self, word):
        return self._regexp.sub('', word)

    def __repr__(self):
        return '<Regexp Stemmer: %r>' % self._regexp.pattern

def demo():
    from nltk_lite import tokenize, stem

    # Create a simple regular expression based stemmer
    stemmer = stem.Regexp('ing$|s$|e$')
    text = "John was eating icecream"
    tokens = tokenize.whitespace(text)

    # Print the results.
    print stemmer
    for word in tokens:
        print '%20s => %s' % (word, stemmer.stem(word))
    print
        

if __name__ == '__main__': demo()

    
