# Natural Language Toolkit (NLTK) Coreference Chunking Utilities
#
# Copyright (C) 2001-2009 NLTK Project 
# Author: Joseph Frazee <jfrazee@mail.utexas.edu>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

import os
import re
import time
import optparse

import nltk

from nltk.data import load
from nltk.util import LazyMap

from nltk.corpus import ConllChunkCorpusReader
from nltk.corpus.util import LazyCorpusLoader

from nltk.tree import Tree

from nltk.chunk import ChunkParserI
from nltk.chunk.util import conllstr2tree, tree2conlltags, ChunkScore

from nltk.tag import ClassifierBasedTagger

from nltk.classify import ClassifierI
from nltk.classify.maxent import MaxentClassifier

from nltk_contrib.coref import TrainableI, AbstractClassifierBasedTagger, \
    CorpusReaderDecorator, NLTK_COREF_DATA
from nltk_contrib.coref.tag import TaggerCorpusReader
from nltk_contrib.coref.train import train_model

TREEBANK_CLOSED_CATS = set(['CC', 'DT', 'MD', 'POS', 'PP$', 'RP', 'TO', 'WDT',
                            'WP$', 'EX', 'IN', 'PDT', 'PRP', 'WP', 'WRB'])

CONLL2K_CHUNK_TAGGER = \
    'nltk:taggers/maxent_conll2k_chunk_tagger/conll2k.chunker.pickle'

class ChunkTaggerFeatureDetector(dict):
    """
    A simple feature detector for training a C{ChunkTagger}.
    """
    def __init__(self, tokens, index=0, history=None, **kwargs):
        """
        @param tokens: a list of tokens containing a token to featurize.
        @type tokens: C{list} of C{tuple}
        @param index: the list position of the token to featurize.
        @type index: C{int}
        @param history: the previous features and classifier predictions
        @type history: C{list} of C{dict}
        @kwparam window: the number of previous/next tokens to include in the
            features
        @type window: C{int}
        """
        dict.__init__(self)
        
        window = kwargs.get('window', 2)
        # TODO: This will tag (X, Y, Z) to ((X, Y, Z), W) as well as (X, Y)  to
        # ((X, Y), W). Do we want this?
        spelling, pos = tokens[index][:2]

        self['spelling'] = spelling
        self['word'] = spelling.lower()
        self['pos'] = pos
        self['isupper'] = spelling.isupper()
        self['islower'] = spelling.islower()
        self['istitle'] = spelling.istitle()
        self['isalnum'] = spelling.isalnum() 
        self['isnumeric'] = \
            bool(re.match(r'^(\d{1,3}(\,\d{3})*|\d+)(\.\d+)?$', spelling))
        for i in range(1, 4):
            self['prefix_%d' % i] = spelling[:i]
            self['suffix_%d' % i] = spelling[-i:]
        self['isclosedcat'] = pos in TREEBANK_CLOSED_CATS

        if window > 0 and index > 0:
            prev_feats = \
                self.__class__(tokens, index - 1, history, window=window - 1)
            for key, val in prev_feats.items():
                if not key.startswith('next_'):
                    self['prev_%s' % key] = val

        if window > 0 and index < len(tokens) - 1:
            next_feats = self.__class__(tokens, index + 1, window=window - 1)        
            for key, val in next_feats.items():
                if not key.startswith('prev_'):
                    self['next_%s' % key] = val        

        if 'prev_pos' in self:
            self['prev_pos_pair'] = '%s/%s' % \
                (self.get('prev_pos'), self.get('pos'))

        if history and index > 0:
            self['prev_tag'] = history[index - 1]
            
                
class ChunkTagger(AbstractClassifierBasedTagger, ChunkParserI):
    """
    A classifier-based chunk tagger object that can be trained on arbitrary
    sequences of tokens, e.g. (word, pos, iob). L{parse()} and L{test()}
    methods are provided.
    """
    # _tokens2tree() is almost entirely based on nltk.chunk.util.conllstr2tree().
    @classmethod    
    def _tokens2tree(cls, tokens, chunk_types=('NP', 'PP', 'VP'), top_node="S"):
        stack = [Tree(top_node, [])]

        for token in tokens:
            word, tag = token[:2]
            state, chunk_type = re.match(r'([IOB])-?(\S+)?', token[-1]).groups()

            # If it's a chunk type we don't care about, treat it as O.
            if (chunk_types is not None and
                chunk_type not in chunk_types):
                state = 'O'

            # For "Begin"/"Outside", finish any completed chunks -
            # also do so for "Inside" which don't match the previous token.
            mismatch_I = state == 'I' and chunk_type != stack[-1].node
            if state in 'BO' or mismatch_I:
                if len(stack) == 2: stack.pop()

            # For "Begin", start a new chunk.
            if state == 'B' or mismatch_I:
                chunk = Tree(chunk_type, [])
                stack[-1].append(chunk)
                stack.append(chunk)

            # Add the new word token.
            stack[-1].append((word, tag))

        return stack[0]        

    def parse(self, tokens):
        tagged_tokens = self.__class__._flatten(self.tag(tokens))
        return self.__class__._tokens2tree(tagged_tokens, None)

    def test(self, test_sequence, **kwargs):
        """
        Tests the C{ChunkTagger} instance.

    	@param test_sequence: a sequence of labeled test instances.
        @type test_sequence: C{list} of C{list} of C{tuple}
        @kwparam verbose: boolean flag indicating whether training should be
            verbose or include printed output.
        @type verbose: C{bool}
        """
        count = sum([len(sent) for sent in test_sequence])
        chunkscore = ChunkScore()
        for test_sent in test_sequence:
            untagged_sent = [token[:-1] for token in test_sent]
            correct = self.__class__._tokens2tree(test_sent, None)
            guess = self.parse(untagged_sent)
            chunkscore.score(correct, guess)
            if kwargs.get('verbose'):
                correct_tags = [token[-1] for token in test_sent]
                guessed_tags = [token[-1] for token in self.tag(untagged_sent)]
                for (token, guessed_tag, correct_tag) \
                in zip(untagged_sent, guessed_tags, correct_tags):
                    if guessed_tag == correct_tag:
                        result = ''
                    else:
                        result = '*' 
                    template = '%-25s' + ' %-6s'*(len(token) + 1) + ' %s'
                    args = token + (guessed_tag,) + (correct_tag,) + (result,)
                    print template % args
                
        print 'f-score over %d tokens:   %.2f' % (count, chunkscore.f_measure())
        print 'precision over %d tokens: %.2f' % (count, chunkscore.precision())
        print 'recall over %d tokens:    %.2f' % (count, chunkscore.recall())


class ChunkTaggerCorpusReader(CorpusReaderDecorator):
    """
    A C{CorpusReaderDecorator} that adds chunking functionality to an
    arbitrary C{CorpusReader}.
    """
    def __init__(self, reader, **kwargs):
        """
        @return: a corpus reader.
        @rtype: C{ChunkTaggerCorpusReader}
        @param reader: the corpus reader to decorate.
        @type reader: C{CorpusReader}
        @kwparam chunker: the chunker object to defer chunking to.
        @type chunker: C{ChunkTagger}
        @kwparam tagger: an tagger object to defer tagging to.
        @type tagger: C{TaggerI}
        """        
        if kwargs.get('tagger'):
            reader = TaggerCorpusReader(reader, tagger=kwargs.get('tagger'))
        self._chunker = kwargs.get('chunker')
        CorpusReaderDecorator.__init__(self, reader, **kwargs)

    def _chunk(self, tagged_sent):
        chunks = []
        for chunk in self._chunker.parse(tagged_sent):
            if isinstance(chunk, Tree):
                chunks.append(chunk.leaves())
            elif isinstance(chunk, tuple):
                chunks.append(chunk)
            else:
                raise
        return chunks
        
    def _tag(self, sent):
        return self._chunker.__class__._flatten(self._chunker.tag(sent))

    def iob_sents(self):
        return LazyMap(self._tag, self._reader.tagged_sents())
        
    def chunked_sents(self):
        return LazyMap(self._chunk, self._reader.tagged_sents())

    def chunker(self):
        """
        Return the underlying C{ChunkTagger} object.
        
        @return: the underlying C{ChunkTagger} object.
        @type: C{ChunkTagger}
        """
        return self._chunker
        

class Conll2kChunkTaggerCorpusReader(ChunkTaggerCorpusReader):
    """
    A C{CorpusReaderDecorator} that adds chunking functionality to an
    arbitrary C{CorpusReader}.
    """
    def __init__(self, reader, **kwargs):     
        if kwargs.get('tagger'):
            reader = TaggerCorpusReader(reader, tagger=kwargs.get('tagger'))
        kwargs['chunker'] = load(CONLL2K_CHUNK_TAGGER)
        ChunkTaggerCorpusReader.__init__(self, reader, **kwargs)
           
 
def maxent_classifier_builder(labeled_featuresets):
    return MaxentClassifier.train(
        labeled_featuresets,
        algorithm='megam',
        gaussian_prior_sigma=0.1,
        count_cutoff=1,
        min_lldelta=1e-7)

def train_conll2k_chunker(num_train_sents, num_test_sents, **kwargs):
    model_file = kwargs.get('model_file')
    phrase_types = kwargs.get('phrase_types', ('NP', 'VP', 'PP'))
    conll2k_train = LazyCorpusLoader(
        'conll2000', ConllChunkCorpusReader, 
        ['train.txt'], phrase_types)
    conll2k_train_sequence = conll2k_train.iob_sents()
    conll2k_test = LazyCorpusLoader(
        'conll2000', ConllChunkCorpusReader,
        ['test.txt'], phrase_types)
    conll2k_test_sequence = conll2k_test.iob_sents()
    # Import ChunkTagger and ChunkTaggerFeatureDetector because we want 
    # train_model() and the pickled object to use the full class names.
    from nltk_contrib.coref.chunk import ChunkTagger, \
        ChunkTaggerFeatureDetector    
    chunker = train_model(ChunkTagger, 
                          conll2k_train_sequence, 
                          conll2k_test_sequence,
                          model_file,
                          num_train_sents,
                          num_test_sents,
                          feature_detector=ChunkTaggerFeatureDetector,
                          classifier_builder=maxent_classifier_builder,
                          verbose=kwargs.get('verbose'))
    if kwargs.get('verbose'):
        chunker.show_most_informative_features(25)
    return chunker
                                       
def demo(verbose=False):
    import nltk
    from nltk.corpus.util import LazyCorpusLoader    
    from nltk.corpus.reader import BracketParseCorpusReader
    from nltk_contrib.coref import NLTK_COREF_DATA
    from nltk_contrib.coref.chunk import Conll2kChunkTaggerCorpusReader
    if nltk.data.path[0] != NLTK_COREF_DATA:
        nltk.data.path.insert(0, NLTK_COREF_DATA)
    treebank = LazyCorpusLoader(
        'treebank/combined', BracketParseCorpusReader, r'wsj_.*\.mrg')
    treebank = Conll2kChunkTaggerCorpusReader(treebank)
    for sent in treebank.chunked_sents()[:10]:
        for chunk in sent:
           print chunk
        print
    
if __name__ == '__main__':
    parser = optparse.OptionParser()
    parser.add_option('-d', '--demo', action='store_true', dest='demo',
                      default=True, help='run demo')
    parser.add_option('-t', '--train-chunker', action='store_true',
                      default=False, dest='train', 
                      help='train CoNLL 2000 chunker')
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
    
    if options.local_models:
        if nltk.data.path[0] != NLTK_COREF_DATA:
            nltk.data.path.insert(0, NLTK_COREF_DATA)
        
    if options.psyco:
        try:
            import psyco
            psyco.profile(memory=256)
        except:
            pass
    
    if options.train:
        chunker = train_conll2k_chunker(options.num_train_sents, 
                                        options.num_test_sents,
                                        model_file=options.model_file, 
                                        verbose=options.verbose)  
                       
    elif options.demo:
        demo(options.verbose)

    else:
        demo(options.verbose)