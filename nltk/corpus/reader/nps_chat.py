# Natural Language Toolkit: NPS Chat Corpus Reader
#
# Copyright (C) 2001-2008 NLTK Project
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.org>
# For license information, see LICENSE.TXT

from nltk.compat import *
from nltk.corpus.reader.util import *
from nltk.corpus.reader.api import *
from nltk.corpus.reader.xmldocs import *
from nltk.utilities import LazyConcatenation
from nltk.internals import ElementWrapper
import re, textwrap

class NPSChatCorpusReader(XMLCorpusReader):

    def __init__(self, root, files, wrap_etree=False, tag_mapping_function=None):
        XMLCorpusReader.__init__(self, root, files, wrap_etree)
        self._tag_mapping_function = tag_mapping_function

    def xml_posts(self, files=None):
        if self._wrap_etree:
            return concat([XMLCorpusView(filename, 'Session/Posts/Post',
                                         self._wrap_elt)
                           for filename in self.abspaths(files)])
        else:
            return concat([XMLCorpusView(filename, 'Session/Posts/Post')
                           for filename in self.abspaths(files)])

    def posts(self, files=None):
        return concat([XMLCorpusView(filename, 'Session/Posts/Post/terminals',
                                     self._elt_to_words)
                       for filename in self.abspaths(files)])

    def tagged_posts(self, files=None, simplify_tags=False):
        def reader(elt, handler):
            return self._elt_to_tagged_words(elt, handler, simplify_tags)
        return concat([XMLCorpusView(filename, 'Session/Posts/Post/terminals',
                                     reader)
                       for filename in self.abspaths(files)])

    def words(self, files=None):
        return LazyConcatenation(self.posts(files))

    def tagged_words(self, files=None, simplify_tags=False):
        return LazyConcatenation(self.tagged_posts(files, simplify_tags))

    def _wrap_elt(self, elt, handler):
        return ElementWrapper(elt)

    def _elt_to_words(self, elt, handler):
        return [t.attrib['word'] for t in elt.findall('t')]
        
    def _elt_to_tagged_words(self, elt, handler, simplify_tags=False):
        tagged_post = [(t.attrib['word'], t.attrib['pos']) for t in elt.findall('t')]
        if simplify_tags:
            tagged_post = [(w, self._tag_mapping_function(t))
                           for (w,t) in tagged_post]
        return tagged_post
