# Natural Language Toolkit (NLTK) Coreference Chunking Utilities
#
# Copyright (C) 2001-2009 NLTK Project 
# Author: Joseph Frazee <jfrazee@mail.utexas.edu>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

import re
import time
import optparse

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
    CorpusReaderDecorator
from nltk_contrib.coref.tag import TaggerCorpusReader
from nltk_contrib.coref.train import train_model

TREEBANK_CLOSED_CATS = set(['CC', 'DT', 'MD', 'POS', 'PP$', 'RP', 'TO', 'WDT',
                            'WP$', 'EX', 'IN', 'PDT', 'PRP', 'WP', 'WRB'])


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
    @classmethod
    def _tokens2conllstr(cls, tokens):
        return '\n'.join([' '.join(token) for token in tokens])

    def parse(self, tokens):
        tokens = ChunkTagger._flatten(self.tag(tokens))
        return conllstr2tree(self._tokens2conllstr(tokens))

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
            correct = conllstr2tree(ChunkTagger._tokens2conllstr(test_sent))
            guess = self.parse(correct.leaves())
            chunkscore.score(correct, guess)
            if kwargs.get('verbose'):
                correct_tags = \
                    [iob for word, pos, iob in tree2conlltags(correct)]
                guessed_tags = tree2conlltags(guess)
                for (word, pos, guess), correct \
                in zip(guessed_tags, correct_tags):
                    if guess == correct:
                        result = ''
                    else:
                        result = '*' 
                    print '%-25s %-6s %-6s %-6s %s' % \
                        (word, pos, guess, correct, result)
                
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

    def chunked_sents(self):
        return LazyMap(self._chunk, self._reader.tagged_sents())

    def chunker(self):
        """
        Return the underlying C{ChunkTagger} object.
        
        @return: the underlying C{ChunkTagger} object.
        @type: C{ChunkTagger}
        """
        return self._chunker
           
 
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
        model.show_most_informative_features(25)
    return chunker
                                       
_NUM_DEMO_SENTS = 10
def demo(verbose=False):
    from nltk_contrib.coref.chunk import train
    from nltk_contrib.coref import CorpusReaderDecorator
    from nltk.corpus.util import LazyCorpusLoader    
    from nltk.corpus.reader import BracketParseCorpusReader
    model = train(_NUM_DEMO_SENTS, _NUM_DEMO_SENTS, verbose=verbose)
    treebank = LazyCorpusLoader(
        'treebank/combined', BracketParseCorpusReader, r'wsj_.*\.mrg')
    treebank = ChunkTaggerCorpusReader(treebank, chunker=model)
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
    parser.add_option('-p', '--psyco', action='store_true',
                      default=False, dest='psyco',
                      help='use Psyco JIT, if available')
    parser.add_option('-v', '--verbose', action='store_true',
                      default=False, dest='verbose',
                      help='verbose')
    (options, args) = parser.parse_args()
        
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