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
from HTMLParser import HTMLParser
from nltk import tokenize
import string

skip = ['script']   # non-nesting tags to skip

class MarkupCleaner(HTMLParser):
    def __init__(self):
        self.reset()
        self.fed = []
        self._flag = True
    def handle_data(self, d):
        if self._flag:
            self.fed.append(d)
    def handle_starttag(self, tag, attrs):
        if tag in skip:
            self._flag = False
    def handle_endtag(self, tag):
        if tag in skip:
            self._flag = True
    def clean_text(self):
        return ''.join(self.fed)

def read_document(url, format='words'):
    if format == 'words':
        html = urlopen(url).read()
        cleaner = MarkupCleaner()
        cleaner.feed(html)
        text = cleaner.clean_text()
        return tokenize.wordpunct(text)
    elif format == 'raw':
        return urlopen(url).read()
    else:
        raise ValueError('Expected format to be one of: "words", "raw"')
read = read_document

def demo():
    from nltk.corpus import web
    from textwrap import wrap

    constitution = "http://www.archives.gov/national-archives-experience/charters/constitution_transcript.html"

    text = string.join(web.read(constitution, 'words'))
    print "\n".join(wrap(text))

if __name__ == '__main__':
    demo()
