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
import re, textwrap

class NPSChatCorpusReader(XMLCorpusReader):

    def __init__(self, root, files, wrap_etree=False):
        XMLCorpusReader.__init__(self, root, files, wrap_etree)

        self._??? = XMLCorpusView(filename, 'Session/Posts/Post', post_handler)

# Convert this:
# <Post class="Greet" user="10-19-20sUser59">hey everyone
#   <terminals>
#     <t pos="UH" word="hey"/>
#     <t pos="NN" word="everyone"/>
#   </terminals>
# </Post>
# to [hey/UH everyone/NN] -> tagged_sents(), tagged_words(), sents(), words()
        
def post_handler(elt, _):
    return [(t.attrib['pos'], t.attrib['word']) for t in elt.findall('t')]
