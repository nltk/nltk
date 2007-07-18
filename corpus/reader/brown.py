# Natural Language Toolkit: Brown Corpus Reader
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
A reader for corpora formatted using the Brown Corpus format.
"""       

from api import *
from util import *
from nltk.tag import string2tags, string2words
import os

class BrownCorpusReader(CorpusReader):
    def __init__(self, root, items, extension=''):
        if isinstance(items, basestring):
            items = find_corpus_items(root, items, extension)
        self._root = root
        self.items = tuple(items)
        self._extension = extension

    def raw(self, items=None):
        return concat([open(filename).read()
                       for filename in self._item_filenames(items)])

    def words(self, items=None):
        return concat([BrownCorpusView(filename, False, False, False)
                       for filename in self._item_filenames(items)])

    def sents(self, items=None):
        return concat([BrownCorpusView(filename, False, True, False)
                       for filename in self._item_filenames(items)])

    def paras(self, items=None):
        return concat([BrownCorpusView(filename, False, True, True)
                       for filename in self._item_filenames(items)])

    def tagged_words(self, items=None):
        return concat([BrownCorpusView(filename, True, False, False)
                       for filename in self._item_filenames(items)])

    def tagged_sents(self, items=None):
        return concat([BrownCorpusView(filename, True, True, False)
                       for filename in self._item_filenames(items)])

    def tagged_paras(self, items=None):
        return concat([BrownCorpusView(filename, True, True, True)
                       for filename in self._item_filenames(items)])

    def _item_filenames(self, items):
        if items is None: items = self.items
        if isinstance(items, basestring): items = [items]
        return [os.path.join(self._root, '%s%s' % (item, self._extension))
                for item in items]
    
class BrownCorpusView(StreamBackedCorpusView):
    """
    A specialized corpus view for brown documents.  It can be customized
    via flags to divide brown corpus documents up by sentence or paragraph,
    and to include or omit part of speech tags.  C{BrownCorpusView}
    objects are typically created by L{read_document()} (not directly by
    the brown corpus modules' users).
    """
    def __init__(self, corpus_file, tagged, group_by_sent, group_by_para):
        self.tagged = tagged
        self.group_by_sent = group_by_sent
        self.group_by_para = group_by_para
        StreamBackedCorpusView.__init__(self, corpus_file)
        
    def read_block(self, stream):
        """Reads one paragraph at a time."""
        para = []
        while True:
            line = stream.readline().strip()
            if line:
                if self.tagged:
                    words = string2tags(line)
                else:
                    words = string2words(line)
                if self.group_by_sent:
                    para.append(words)
                else:
                    para.extend(words)
            elif para:
                if self.group_by_para:
                    return [para]
                else:
                    return para
            else:
                return []

######################################################################
#{ Demo
######################################################################

def demo():
    from nltk.corpus import brown
    import textwrap
    def show(hdr, info):
        print hdr, textwrap.fill(info, initial_indent=' '*len(hdr),
                                 subsequent_indent=' '*4)[len(hdr):]
    
    d1 = brown.sents('a')
    for sent in d1[3:5]:
        show('Sentence from a:', ' '.join(sent))

    d2 = brown.tagged_words('b')
    show('Tagged words from b:', ' '.join('%s/%s' % w for w in d2[220:240]))
                       
    d3 = brown.words('c')
    show('Untagged words from c:', ' '.join(d3[220:250]))

if __name__ == '__main__':
    demo()

