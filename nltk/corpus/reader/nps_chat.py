# Natural Language Toolkit: NPS Chat Corpus Reader
#
# Copyright (C) 2001-2008 University of Pennsylvania
# Author: Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

from nltk.compat import *
from nltk.corpus.reader.util import *
from nltk.corpus.reader.api import *
from nltk.corpus.reader.xmldocs import *
from nltk.utilities import LazyConcatenation
from nltk.internals import ElementWrapper
import re, textwrap

class NPSChatCorpusReader(XMLCorpusReader):

    def __init__(self, root, files, wrap_etree=False):
        XMLCorpusReader.__init__(self, root, files, wrap_etree)

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

    def tagged_posts(self, files=None):
        return concat([XMLCorpusView(filename, 'Session/Posts/Post/terminals',
                                     self._elt_to_tagged_words)
                       for filename in self.abspaths(files)])

    def words(self, files=None):
        return LazyConcatenation(self.posts(files))

    def tagged_words(self, files=None):
        return LazyConcatenation(self.tagged_posts(files))

    def _wrap_elt(self, elt, handler):
        return ElementWrapper(elt)

    def _elt_to_words(self, elt, handler):
        return [t.attrib['word'] for t in elt.findall('t')]
        
    def _elt_to_tagged_words(self, elt, handler):
        return [(t.attrib['word'], t.attrib['pos']) for t in elt.findall('t')]
        
# Example post:
# <Post class="Greet" user="10-19-20sUser59">hey everyone
#   <terminals>
#     <t pos="UH" word="hey"/>
#     <t pos="NN" word="everyone"/>
#   </terminals>
# </Post>
# to [hey/UH everyone/NN] -> tagged_sents(), tagged_words(), sents(), words()
