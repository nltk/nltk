import time
import optparse

from nltk.util import LazyMap
from nltk.corpus.util import LazyCorpusLoader
from nltk.corpus.reader import BracketParseCorpusReader

from nltk_contrib.coref import CorpusReaderDecorator
from nltk_contrib.coref.train import train_model


class TaggerCorpusReader(CorpusReaderDecorator):
    """A decorator.
    """

    def __init__(self, reader, **kwargs):
        self._tagger = kwargs.get('tagger') 
        CorpusReaderDecorator.__init__(self, reader, **kwargs)
    
    def tagged_sents(self):
        return LazyMap(self._tagger.tag, self.sents())
    
    def tagged_words(self):
        return LazyConcatenation(LazyMap(self._tagger.tag, self.sents()))

    def tagger(self):
        return self._tagger

