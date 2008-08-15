# Natural Language Toolkit (NLTK) Coreference Utilities
#
# Copyright (C) 2008 NLTK Project 
# Author: Joseph Frazee <jfrazee@mail.utexas.edu>
# URL: http://nltk.org/
# For license information, see LICENSE.TXT

from nltk.data import load
from nltk.corpus import CorpusReader
from nltk.util import LazyMap, LazyConcatenation, LazyZip

#from nltk.tag.sequential import ClassifierBasedTagger

#from nltk.classify import ClassifierI
#from nltk.classify.maxent import MaxentClassifier, BinaryMaxentFeatureEncoding
#from nltk.classify.naivebayes import NaiveBayesClassifier

from nltk.probability import LidstoneProbDist

from nltk_contrib.coref import *
from nltk_contrib.coref.chunk import *
from nltk_contrib.coref.features import *

TREEBANK_TAGGER = 'nltk:taggers/treebank.tagger.pickle.gz'

TREEBANK_CHUNKER = 'nltk:chunkers/treebank.chunker.pickle.gz'

MUC6_NE_CHUNKER = 'nltk:chunkers/muc6.nechunker.pickle.gz'

class LidstoneProbDistFactory(LidstoneProbDist):
    def __init__(self, fd, bins, *factory_args):
        LidstoneProbDist.__init__(self, fd, 0.1, bins)


class CorpusReaderDecorator(CorpusReaderDecoratorI):
    def __init__(self, reader, **kwargs):
        self._reader = reader

    def __getattr__(self, name):
        if name != '_reader':
            return getattr(self._reader, name)

    def reader(self):
        wrapped_reader = self._reader
        while isinstance(wrapped_reader, CorpusReaderDecoratorI):
            wrapped_reader = wrapped_reader.reader()
        return wrapped_reader


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


class ChunkTaggerCorpusReader(CorpusReaderDecorator):
    """A decorator.
    """
    
    def __init__(self, reader, **kwargs):
        reader = TaggerCorpusReader(reader, tagger=kwargs.get('tagger'))
        self._chunker = kwargs.get('chunker')
        CorpusReaderDecorator.__init__(self, reader, **kwargs)

    def chunked_sents(self):
        return LazyMap(self._chunker.chunk, self.tagged_sents())

    def chunker(self):
        return self._chunker

    def tagger(self):
        return self._tagger

        
class TreebankTaggerCorpusReader(TaggerCorpusReader):
    """A decorator.
    """

    def __init__(self, reader):
        tagger = load(TREEBANK_TAGGER)
        TaggerCorpusReader.__init__(self, reader, tagger=tagger)
            
       
class TreebankChunkTaggerCorpusReader(ChunkTaggerCorpusReader):
    """A decorator.
    """
            
    def __init__(self, reader):
        chunker = load(TREEBANK_CHUNKER)
        tagger = load(TREEBANK_TAGGER)
        ChunkTaggerCorpusReader.__init__(self, reader, 
                                               chunker=chunker, tagger=tagger)
    
    def parsed_sents(self):
        return LazyMap(self._chunker.parse, self.tagged_sents())
        

def zipzip(*lists):
    return LazyMap(lambda lst: zip(*lst), LazyZip(*lists))

def treebank_tagger_demo():
    from nltk.corpus.util import LazyCorpusLoader    
    from nltk.corpus.reader import PlaintextCorpusReader
    from nltk_contrib.coref.util import TreebankTaggerCorpusReader
    
    state_union = LazyCorpusLoader(
        'state_union', PlaintextCorpusReader, r'(?!\.svn).*\.txt')
    state_union = TreebankTaggerCorpusReader(state_union)
    
    print 'Treebank tagger demo...'
    print 'Tagged sentences:'
    for sent in state_union.tagged_sents()[500:505]:
        print sent
        print
    print
    print 'Tagged words:'
    for word in state_union.tagged_words()[500:505]:
        print word
    print

def treebank_chunk_tagger_demo():
    from nltk.corpus.util import LazyCorpusLoader    
    from nltk.corpus.reader import PlaintextCorpusReader
    from nltk_contrib.coref.util import TreebankChunkTaggerCorpusReader
    
    state_union = LazyCorpusLoader(
        'state_union', PlaintextCorpusReader, r'(?!\.svn).*\.txt')
    state_union = TreebankChunkTaggerCorpusReader(state_union)

    print 'Treebank chunker demo...'
    print 'Chunked sentences:'
    for sent in state_union.chunked_sents()[500:505]:
        print sent
        print
    print
    print 'Parsed sentences:'
    for tree in state_union.parsed_sents()[500:505]:
        print tree
        print
    print    

def demo():
    from nltk_contrib.coref.util import treebank_tagger_demo, \
         treebank_chunk_tagger_demo
    treebank_tagger_demo()
    treebank_chunk_tagger_demo()
    
if __name__ == '__main__':
    demo()
