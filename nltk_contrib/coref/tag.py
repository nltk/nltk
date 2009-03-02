# Natural Language Toolkit (NLTK) Coreference Tagging Utilities
#
# Copyright (C) 2001-2009 NLTK Project 
# Author: Joseph Frazee <jfrazee@mail.utexas.edu>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

from nltk.util import LazyMap
from nltk.corpus.util import LazyCorpusLoader
from nltk.corpus.reader import BracketParseCorpusReader

from nltk_contrib.coref import CorpusReaderDecorator


class TaggerCorpusReader(CorpusReaderDecorator):
    """
    A C{CorpusReaderDecorator} that adds tagger functionality to an arbitrary
    C{CorpusReader}.
    """
    
    def __init__(self, reader, **kwargs):
        """
        @return: a corpus reader
        @rtype: C{TaggerCorpusReader}
        @param reader: the corpus reader to decorate
        @type reader: C{CorpusReader}
        @kwparam tagger: a tagger object to defer tagging to
        @type tagger: C{TaggerI}
        """
        self._tagger = kwargs.get('tagger') 
        CorpusReaderDecorator.__init__(self, reader, **kwargs)
    
    def tagged_sents(self):
        return LazyMap(self._tagger.tag, self.sents())
    
    def tagged_words(self):
        return LazyConcatenation(LazyMap(self._tagger.tag, self.sents()))

    def tagger(self):
        return self._tagger

