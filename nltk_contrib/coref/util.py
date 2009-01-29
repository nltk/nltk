# Natural Language Toolkit (NLTK) Coreference Utilities
#
# Copyright (C) 2001-2009 NLTK Project 
# Author: Joseph Frazee <jfrazee@mail.utexas.edu>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

from nltk.data import load, find
from nltk.corpus import CorpusReader, BracketParseCorpusReader
from nltk.util import LazyMap, LazyConcatenation, LazyZip

#from nltk.tag.sequential import ClassifierBasedTagger

#from nltk.classify import ClassifierI
#from nltk.classify.maxent import MaxentClassifier, BinaryMaxentFeatureEncoding
#from nltk.classify.naivebayes import NaiveBayesClassifier

from nltk.probability import LidstoneProbDist

from nltk_contrib.coref import *
from nltk_contrib.coref.ne import *
from nltk_contrib.coref.chunk import *
from nltk_contrib.coref.features import *

TREEBANK_TAGGER = 'nltk:taggers/treebank.tagger.pickle.gz'

TREEBANK_CHUNKER = 'nltk:chunkers/treebank.chunker.pickle.gz'

MUC6_CHUNK_TAGGER = 'nltk:chunkers/muc6.chunk.tagger.pickle.gz'

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


class MUC6NamedEntityChunkTaggerCorpusReader(ChunkTaggerCorpusReader):
    def __init__(self, reader):
        chunker = load(MUC6_CHUNK_TAGGER)
        tagger = load(TREEBANK_TAGGER)
        ChunkTaggerCorpusReader.__init__(self, reader, 
                                               chunker=chunker, tagger=tagger)
        
        

def zipzip(*lists):
    return LazyMap(lambda lst: zip(*lst), LazyZip(*lists))

def load_treebank(sections):
    treebank_path = os.environ.get('NLTK_TREEBANK', 'treebank/combined')
    treebank = LazyCorpusLoader(
        treebank_path,
        BracketParseCorpusReader, 
        r'(%s\/)?wsj_%s.*\.mrg' % (sections, sections))
    return treebank

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
    
def muc6_chunk_tagger_demo():
    from nltk.corpus.util import LazyCorpusLoader
    from nltk.corpus import BracketParseCorpusReader
    from nltk_contrib.coref.util import MUC6NamedEntityChunkTaggerCorpusReader
     
    treebank = MUC6NamedEntityChunkTaggerCorpusReader(load_treebank('0[12]'))
    
    print 'MUC6 named entity chunker demo...'
    print 'Chunked sentences:'
    for sent in treebank.chunked_sents()[:10]:
        print sent
        print      
    print

def baseline_chunk_tagger_demo():
    from nltk.corpus.util import LazyCorpusLoader
    from nltk.corpus import BracketParseCorpusReader
    
    chunker = BaselineNamedEntityChunkTagger()
    treebank = load_treebank('0[12]')
    
    print 'Baseline named entity chunker demo...'
    print 'Chunked sentences:'
    for sent in treebank.sents()[:10]:
        print chunker.chunk(sent)
        print
    print 'IOB-tagged sentences:'
    for sent in treebank.sents()[:10]:
        print chunker.tag(sent)
        print
    print

def demo():
    from nltk_contrib.coref.util import treebank_tagger_demo, \
         treebank_chunk_tagger_demo, muc6_chunk_tagger_demo
    treebank_tagger_demo()
    treebank_chunk_tagger_demo()
    muc6_chunk_tagger_demo()
    
if __name__ == '__main__':
    try:
        import psyco
        psyco.profile()
    except:
        pass
    demo()
