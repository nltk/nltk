# Natural Language Toolkit: Webpage reader
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Read tokens from a webpage
"""

# to do: check html comments are being ignored properly
# to do: add support for a cache directory

from util import *
from urllib import urlopen
from nltk import tokenize, clean_html
import string

def read_document(url, format='tokenized'):
    """
    Read the document at the given URL, and return its contents.
    C{format} determines the format that the result will be returned
    in:
      - C{'raw'}: a single C{string}
      - C{'tokenized'}: a list of words and punctuation symbols.
        HTML markup will be removed, and various other 'clean-up'
        steps may be applied to the raw HTML, in an attempt to
        extract the text of the webpage.
    """
    if isinstance(item, list):
        return concat([read(doc, format) for doc in item])
    if format == 'tokenized':
        html = urlopen(url).read()
        text = clean_html()
        return tokenize.wordpunct(text)
    elif format == 'raw':
        return urlopen(url).read()
    else:
        raise ValueError('Expected format to be one of: "words", "raw"')
read = read_document

######################################################################
#{ Convenience Functions
######################################################################
read = read_document

def tokenized(item):
    """@return: the given document as a list of words and punctuation
    symbols.  HTML markup will be removed, and various other
    'clean-up' steps may be applied to the raw HTML, in an attempt to
    extract the text of the webpage."""
    return read_document(item, format='tokenized')

def raw(item):
    """@return: the given document as a single string."""
    return read_document(item, format='raw')

######################################################################
#{ Demo
######################################################################

def demo():
    from nltk.corpus import web
    from textwrap import wrap

    constitution = "http://www.archives.gov/national-archives-experience/charters/constitution_transcript.html"

    text = string.join(web.read(constitution, 'tokenized'))
    print "\n".join(wrap(text))

if __name__ == '__main__':
    demo()
