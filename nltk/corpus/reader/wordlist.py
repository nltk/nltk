# Natural Language Toolkit: Word List Corpus Reader
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

from util import *
from api import *

class WordListCorpusReader(CorpusReader):
    """
    List of words, one per line.  Blank lines are ignored.
    """
    def __init__(self, root, items, extension=''):
        """
        @param root: The root directory for this corpus.
        @param items: A list of items in this corpus.
        @param extension: File extension for items in this corpus.
        """
        if isinstance(items, basestring):
            items = find_corpus_items(root, items, extension)
        self._root = root
        self.items = tuple(items)
        self._extension = extension

    def words(self, items):
        return concat([[w for w in open(filename).read().split('\n') if w]
                       for filename in self._item_filenames(items)])

    def raw(self, items):
        return concat([open(filename).read()
                       for filename in self._item_filenames(items)])

    def _item_filenames(self, items):
        if items is None: items = self.items
        if isinstance(items, basestring): items = [items]
        return [os.path.join(self._root, '%s%s' % (item, self._extension))
                for item in items]
        
######################################################################
#{ Demo
######################################################################

def demo():
    from nltk.corpus import stopwords, words, names
    import random

    print "20 English stopwords"
    print ' '.join(stopwords.words('english')[300:320])

    print "20 Danish stopwords"
    print ' '.join(stopwords.words('danish')[10:30])

    print "20 stopwords from assorted languages"
    wordlist = stopwords.words(stopwords.items)
    random.shuffle(wordlist)
    print ' '.join(wordlist[10:30])

    print "20 English words"
    print ' '.join(words.words('en')[:20])

    print "20 female names"
    female = list(names.words('female'))
    random.shuffle(female)
    print ' '.join(female[:20])

    print "20 male names"
    male = list(names.words('male'))
    random.shuffle(male)
    print ' '.join(male[:20])
    
if __name__ == '__main__':
    demo()

