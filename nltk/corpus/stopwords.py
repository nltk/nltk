# Natural Language Toolkit: Stopwords Corpus Reader
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Read tokens from the Stopwords Corpus.
"""       

from util import *
import os

#: A dictionary specifying the list of lexicons defined by this
#: corpus.  The keys of this dictionary are the lexicon names;
#: and the values are plaintext descriptions.
lexicons = {
    'danish':     'Danish stopwords',
    'dutch':      'Dutch stopwords',
    'english':    'English stopwords',
    'french':     'French stopwords',
    'german':     'German stopwords',
    'italian':    'Italian stopwords',
    'norwegian':  'Norwegian stopwords',
    'portuguese': 'Portuguese stopwords',
    'russian':    'Russian stopwords',
    'spanish':    'Spanish stopwords',
    'swedish':    'Swedish stopwords',
    }

#: A list of all lexicons in this corpus.
items = sorted(lexicons)

def read_lexicon(item='english', format='listed'):
    """
    Read the given lexicon from the corpus, and return its contents.
    C{format} determines the format that the result will be returned
    in:
      - C{'raw'}: a single C{string}
      - C{'listed'}: a list of names
    """
    filename = find_corpus_file('stopwords', item)
    if format == 'listed':
        return open(filename).read().split()
    elif format == 'raw':
        return open(filename).read()
    else:
        raise ValueError('Expected format to be listed or raw')

######################################################################
#{ Convenience Functions
######################################################################
read = read_lexicon

def raw(item):
    """@return: the given document as a single string."""
    return read_lexicon(item, 'raw')

def listed(item):
    """@return: the given document as a list"""
    return read_lexicon(item, 'listed')

######################################################################
#{ Demo
######################################################################

def demo():
    from nltk.corpus import stopwords
    from itertools import islice
    from pprint import pprint

    print "20 English stopwords"
    pprint(stopwords.read()[300:320])

    print "20 Danish stopwords"
    pprint(stopwords.read('danish')[10:30])

if __name__ == '__main__':
    demo()

