import sys
import optparse

from itertools import *

try:
    import cPickle as pickle
except:
    import pickle

from nltk.data import *
from nltk.corpus import *
from nltk.tag.hmm import *
from nltk.utilities import * 
from nltk.chunk.util import *

def lidstone_estimator(fd, bins):
    return LidstoneProbDist(fd, 0.1, bins)

def train_hmm(labeled_sequence, test_sequence):
    symbols = set()
    tag_set = set()
    for sentence in labeled_sequence:
        for token in sentence:
            word, tag = token
            symbols.add(word)
            tag_set.add(tag)
    trainer = HiddenMarkovModelTrainer(list(tag_set), list(symbols))
    hmm_tagger = trainer.train_supervised(labeled_sequence, 
                                    estimator=lidstone_estimator)
    if test_sequence:
        test_pos(hmm_tagger, test_sequence, False)

    return hmm_tagger

class TreebankTagger(HiddenMarkovModelTagger):
    def __init__(self, labeled_sequence, test_sequence=None):
        self._hmm_tagger = train_hmm(labeled_sequence, test_sequence)

    def __getattr__(self, name):
        if name != '_hmm_tagger':
            return getattr(self._hmm_tagger, name)

class TreebankChunker(HiddenMarkovModelTagger):
    _CLOSED_CATS = set(['CC', 'DT', 'MD', 'POS', 'PP$', 'RP', 'TO', 'WDT',
                        'WP$', 'EX', 'IN', 'PDT', 'PRP', 'WP', 'WRB'])

    def __init__(self, labeled_sequence, test_sequence=None):
        labeled_sequence = [[(self._word(token), self._tag(token))
                             for token in sentence] 
                            for sentence in labeled_sequence]
        if test_sequence:
            test_sequence = [[(self._word(token), self._tag(token))
                              for token in sentence] 
                             for sentence in test_sequence]
        self._hmm_tagger = train_hmm(labeled_sequence, test_sequence)

    def __getattr__(self, name):
        if name != '_hmm_tagger':
            return getattr(self._hmm_tagger, name)

    def _word(self, token):
        word, tag = token[:2]
        if tag in self._CLOSED_CATS:
            return (word, tag)
        else:
            return tag

    def _tag(self, token):
        word, tag, chunk_typ = token
        if tag in self._CLOSED_CATS:
            return token
        else:
            return (tag, chunk_typ)

    def tag(self, tokens):
        tags = HiddenMarkovModelTagger.tag(self, 
                    [self._word(token) for token in tokens])
        for i in range(len(tokens)):
            # is this really the best way to do this?
            tokens[i] += tags[i][-1:][0][-1:]
        return tokens

    def parse(self, tokens):
        return conllstr2tree('\n'.join([' '.join(token) 
                                        for token in self.tag(tokens)]))

class TreebankTaggerCorpusReader(CorpusReader):
    """A decorator.
    """
    def __init__(self, reader):
        self._reader = reader
        self._treebank_tagger = \
            nltk.data.load('nltk:taggers/treebank.tagger.pickle')

    def __getattr__(self, name):
        if name not in ['_reader', '_treebank_tagger', 'tagged_sents']:
            return getattr(self._reader, name)

    def tagged_sents(self):
        return LazyMappedList(self.sents(),
                              self._treebank_tagger.tag)

class TreebankChunkerCorpusReader(CorpusReader):
    """A decorator.
    """
    def __init__(self, reader):
        self._reader = TreebankTaggerCorpusReader(reader)
        self._treebank_chunker = \
            nltk.data.load('nltk:chunkers/treebank.chunker.pickle')

    def __getattr__(self, name):
        if name not in ['_reader', '_treebank_chunker',
                        'chunked_sents', 'parsed_sents']:
            return getattr(self._reader, name)

    def chunked_sents(self):
        return LazyMappedList(self._reader.tagged_sents(), 
                              self._treebank_chunker.tag)

    def parsed_sents(self):
        return LazyMappedList(self._reader.tagged_sents(),
                              self._treebank_chunker.parse)

def train_treebank_tagger(pickle_file, num_train_sents, num_test_sents):
    treebank_train = LazyCorpusLoader(
        'penn-treebank-rel3/parsed/mrg/wsj/',
        BracketParseCorpusReader, r'(0[2-9]|1[0-9]|2[01])\/wsj_.*\.mrg')

    treebank_test = LazyCorpusLoader(
        'penn-treebank-rel3/parsed/mrg/wsj/',
        BracketParseCorpusReader, r'24\/wsj_.*\.mrg')

    print 'Training treebank tagger...'
    print 'Loading training data (supervised)...'

    labeled_sequence = treebank_train.tagged_sents()[:num_train_sents]

    print '%s sentences' % (len(labeled_sequence))
    print '%s words' % (sum([len(sent) for sent in labeled_sequence]))

    print 'Loading test data...'

    test_sequence = treebank_test.tagged_sents()[:num_test_sents]

    print '%s sentences' % (len(test_sequence))
    print '%s words' % (sum([len(sent) for sents in test_sequence]))

    print 'Training (supervised)...'

    treebank_tagger = TreebankTagger(labeled_sequence, test_sequence)

    if isinstance(pickle_file, str):
        print 'Saving model...'

        pickle.dump(treebank_tagger, open(pickle_file, 'wb'))

def train_treebank_chunker(pickle_file, num_train_sents, num_test_sents):
    conll2000_train = LazyCorpusLoader(
         'conll2000', ConllChunkCorpusReader, ['train.txt'], ('NP','VP','PP'))
    conll2000_test = LazyCorpusLoader(
         'conll2000', ConllChunkCorpusReader, ['test.txt'], ('NP','VP','PP')) 

    print 'Training treebank chunker...'
    print 'Loading training data (supervised)...'

    labeled_sequence = conll2000_train.bio_sents()[:num_train_sents]

    print '%s sentences' % (len(labeled_sequence))
    print '%s words' % (sum([len(sent) for sent in labeled_sequence]))

    print 'Loading test data...'

    test_sequence = conll2000_test.bio_sents()[:num_test_sents]

    print '%s sentences' % (len(test_sequence))
    print '%s words' % (sum([len(sent) for sent in test_sequence]))

    print 'Training (supervised)...'

    treebank_chunker = TreebankChunker(labeled_sequence, test_sequence)

    if isinstance(pickle_file, str):
        print 'Saving model...'

        pickle.dump(treebank_chunker, open(pickle_file, 'wb'))

def demo():
    print 'Demo...'
    conll2000_test = LazyCorpusLoader(
         'conll2000', ConllChunkCorpusReader, ['test.txt'], ('NP','VP','PP')) 
    tagger_reader = TreebankTaggerCorpusReader(conll2000_test)
    chunker_reader = TreebankChunkerCorpusReader(conll2000_test)
    for sent in tagger_reader.tagged_sents()[:1]:
        print sent
        print
    for sent in chunker_reader.parsed_sents()[:1]:
        print sent
        print

if __name__ == '__main__':
    parser = optparse.OptionParser()
    parser.add_option('-d', '--demo', action='store_true', dest='demo',
                      default=True, help='run demo')
    parser.add_option('-t', '--train-tagger', action='store_true',
                      default=False, dest='train_tagger', 
                      help='train Treebank POS tagger')
    parser.add_option('-c', '--train-chunker', action='store_true',
                      default=False, dest='train_chunker', 
                      help='train Treebank chunker')
    parser.add_option('-f', '--model-file', metavar='FILE',
                      dest='model_file', help='save model to FILE')
    parser.add_option('-e', '--num-test-sents', metavar='NUM_TEST',
                      dest='num_test_sents', type=int, 
                      help='number of test sentences')
    parser.add_option('-r', '--num-train-sents', metavar='NUM_TRAIN',
                      dest='num_train_sents', type=int, 
                      help='number of training sentences')
    (options, args) = parser.parse_args()
    if options.train_tagger:
        train_treebank_tagger(options.model_file, options.num_train_sents,
                              options.num_test_sents)
    elif options.train_chunker:
        train_treebank_chunker(options.model_file, options.num_train_sents,
                               options.num_test_sents)
    elif options.demo:
        demo()
