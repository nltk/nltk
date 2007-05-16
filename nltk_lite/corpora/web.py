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

from urllib import urlopen
from HTMLParser import HTMLParser
from nltk_lite import tokenize
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

def raw(urls):
    if type(urls) is str: urls = (urls,)
    cleaner = MarkupCleaner()

    for url in urls:
        html = urlopen(url).read()
        cleaner.feed(html)
        text = cleaner.clean_text()
        for token in tokenize.wordpunct(text):
            yield token

def demo():
    from nltk_lite.corpora import web
    from textwrap import wrap

    constitution = "http://www.archives.gov/national-archives-experience/charters/constitution_transcript.html"

    text = string.join(web.raw(constitution))
    print "\n".join(wrap(text))

if __name__ == '__main__':
    demo()
