# Natural Language Toolkit (NLTK) Coreference Tagging Utilities
#
# Copyright (C) 2001-2009 NLTK Project 
# Author: Joseph Frazee <jfrazee@mail.utexas.edu>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

import os
import re
import optparse

import numpy

import nltk

from nltk.util import LazyMap, LazyConcatenation
from nltk.corpus.util import LazyCorpusLoader
from nltk.corpus.reader import BracketParseCorpusReader

from nltk.data import load, find, ZipFilePathPointer
from nltk.tag import HiddenMarkovModelTagger

from nltk_contrib.coref import CorpusReaderDecorator, NLTK_COREF_DATA
from nltk_contrib.coref.train import train_model, LidstoneProbDistFactory

TREEBANK_TAGGER = \
    'nltk:taggers/hmm_treebank_pos_tagger/treebank.tagger.pickle'           


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


class TreebankTaggerCorpusReader(TaggerCorpusReader):
    def __init__(self, reader, **kwargs):
        kwargs['tagger'] = load_treebank_tagger()
        TaggerCorpusReader.__init__(self, reader, **kwargs)


def load_treebank_tagger():
    nltk.data.path.insert(0, NLTK_COREF_DATA)
    return load(TREEBANK_TAGGER)

def train_treebank_tagger(num_train_sents, num_test_sents, **kwargs):
    model_file = kwargs.get('model_file')
    treebank = LazyCorpusLoader(
        'treebank/combined', BracketParseCorpusReader, r'wsj_.*\.mrg')
    treebank_tagged_sents = treebank.tagged_sents()
    max_train_sents = int(len(treebank_tagged_sents)*0.9)
    max_test_sents = len(treebank_tagged_sents) - max_train_sents
    num_train_sents = min((num_train_sents or max_train_sents, max_train_sents))
    num_test_sents = min((num_test_sents or max_test_sents, max_test_sents))
    treebank_train_sequence = \
        treebank_tagged_sents[:num_train_sents]
    treebank_test_sequence = \
        treebank_tagged_sents[num_train_sents:num_train_sents + num_test_sents]
    # Import HiddenMarkovModelTagger and WittenBellProbDist because we want 
    # train_model() and the pickled object to use the full class names.
    from nltk.tag import HiddenMarkovModelTagger
    from nltk_contrib.coref.train import LidstoneProbDistFactory
    tagger = train_model(HiddenMarkovModelTagger, 
                         treebank_train_sequence, 
                         treebank_test_sequence,
                         model_file,
                         num_train_sents,
                         num_test_sents,
                         estimator=LidstoneProbDistFactory,
                         verbose=kwargs.get('verbose'))
    if kwargs.get('verbose'):
        tagger.show_most_informative_features(25)
    return tagger


def demo(verbose=False):
    import nltk
    from nltk.corpus.util import LazyCorpusLoader    
    from nltk.corpus.reader import PlaintextCorpusReader
    from nltk_contrib.coref import NLTK_COREF_DATA
    from nltk_contrib.coref.tag import TreebankTaggerCorpusReader
    if nltk.data.path[0] != NLTK_COREF_DATA:
        nltk.data.path.insert(0, NLTK_COREF_DATA)
    state_union = LazyCorpusLoader(    
        'state_union', PlaintextCorpusReader, r'(?!\.svn).*\.txt')
    state_union = TreebankTaggerCorpusReader(state_union)
    for sent in state_union.tagged_sents()[:5]:
        for word in sent:
           print word
        print

if __name__ == '__main__':
    parser = optparse.OptionParser()
    parser.add_option('-d', '--demo', action='store_true', dest='demo',
                      default=True, help='run demo')
    parser.add_option('-t', '--train-chunker', action='store_true',
                      default=False, dest='train', 
                      help='train Penn Treebank tagger')
    parser.add_option('-f', '--model-file', metavar='FILE',
                      dest='model_file', help='save model to FILE')
    parser.add_option('-e', '--num-test-sents', metavar='NUM_TEST',
                      dest='num_test_sents', type=int, 
                      help='number of test sentences')
    parser.add_option('-r', '--num-train-sents', metavar='NUM_TRAIN',
                      dest='num_train_sents', type=int, 
                      help='number of training sentences')
    parser.add_option('-l', '--local-models', action='store_true',
                    dest='local_models', default=False,
                    help='use models from nltk_contrib.coref')                      
    parser.add_option('-p', '--psyco', action='store_true',
                      default=False, dest='psyco',
                      help='use Psyco JIT, if available')
    parser.add_option('-v', '--verbose', action='store_true',
                      default=False, dest='verbose',
                      help='verbose')
    (options, args) = parser.parse_args()

    if options.local_models and nltk.data.path[0] != NLTK_COREF_DATA:
            nltk.data.path.insert(0, NLTK_COREF_DATA)
        
    if options.psyco:
        try:
            import psyco
            psyco.profile(memory=256)
        except:
            pass

    if options.train:
        chunker = train_treebank_tagger(options.num_train_sents, 
                                        options.num_test_sents,
                                        model_file=options.model_file, 
                                        verbose=options.verbose)    
                     
    elif options.demo:
        demo(options.verbose)

    else:
        demo(options.verbose)
