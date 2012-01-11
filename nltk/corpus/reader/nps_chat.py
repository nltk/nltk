# Natural Language Toolkit: NPS Chat Corpus Reader
#
# Copyright (C) 2001-2012 NLTK Project
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

import re
import textwrap

from nltk.util import LazyConcatenation
from nltk.internals import ElementWrapper

from util import *
from api import *
from xmldocs import *

class NPSChatCorpusReader(XMLCorpusReader):

    def __init__(self, root, fileids, wrap_etree=False, tag_mapping_function=None):
        XMLCorpusReader.__init__(self, root, fileids, wrap_etree)
        self._tag_mapping_function = tag_mapping_function

    def xml_posts(self, fileids=None):
        if self._wrap_etree:
            return concat([XMLCorpusView(fileid, 'Session/Posts/Post',
                                         self._wrap_elt)
                           for fileid in self.abspaths(fileids)])
        else:
            return concat([XMLCorpusView(fileid, 'Session/Posts/Post')
                           for fileid in self.abspaths(fileids)])

    def posts(self, fileids=None):
        return concat([XMLCorpusView(fileid, 'Session/Posts/Post/terminals',
                                     self._elt_to_words)
                       for fileid in self.abspaths(fileids)])

    def tagged_posts(self, fileids=None, simplify_tags=False):
        def reader(elt, handler):
            return self._elt_to_tagged_words(elt, handler, simplify_tags)
        return concat([XMLCorpusView(fileid, 'Session/Posts/Post/terminals',
                                     reader)
                       for fileid in self.abspaths(fileids)])

    def words(self, fileids=None):
        return LazyConcatenation(self.posts(fileids))

    def tagged_words(self, fileids=None, simplify_tags=False):
        return LazyConcatenation(self.tagged_posts(fileids, simplify_tags))

    def _wrap_elt(self, elt, handler):
        return ElementWrapper(elt)

    def _elt_to_words(self, elt, handler):
        return [self._simplify_username(t.attrib['word'])
                for t in elt.findall('t')]

    def _elt_to_tagged_words(self, elt, handler, simplify_tags=False):
        tagged_post = [(self._simplify_username(t.attrib['word']),
                        t.attrib['pos']) for t in elt.findall('t')]
        if simplify_tags:
            tagged_post = [(w, self._tag_mapping_function(t))
                           for (w,t) in tagged_post]
        return tagged_post

    @staticmethod
    def _simplify_username(word):
        if 'User' in word:
            word = 'U' + word.split('User', 1)[1]
        return word
