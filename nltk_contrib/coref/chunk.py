# Natural Language Toolkit (NLTK) Coreference Chunker
#
# Copyright (C) 2001-2009 NLTK Project 
# Author: Joseph Frazee <jfrazee@mail.utexas.edu>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

import re
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

from nltk_contrib.coref import TrainableI, CorpusReaderDecorator
from nltk_contrib.coref.tag import TaggerCorpusReader
from nltk_contrib.coref.train import train_model

TREEBANK_CLOSED_CATS = set(['CC', 'DT', 'MD', 'POS', 'PP$', 'RP', 'TO', 'WDT',
                            'WP$', 'EX', 'IN', 'PDT', 'PRP', 'WP', 'WRB'])


class ChunkTaggerFeatureDetector(dict):
    def __init__(self, tokens, index=0, history=None):
        dict.__init__(self, features(tokens, index, history, depth=2))
        

class ChunkTagger(ClassifierBasedTagger, ChunkParserI, ClassifierI, TrainableI):    
    def __getattr__(self, name):
        if name != '_classifier':
            return getattr(self._classifier, name)

    @classmethod
    def _tokens2conllstr(cls, tokens):
        return '\n'.join([' '.join(token) for token in tokens])
    
    @classmethod
    def _flatten(cls, tokens):
        return [(token, tag, iob) for (token, tag), iob in tokens]
    
    @classmethod
    def _unflatten(cls, tokens):
        return [((token, tag), iob) for token, tag, iob in tokens]        

    def batch_classify(self, featuresets):
        return self._classifier.batch_classify(featuresets)

    def batch_prob_classify(self, featuresets):
        return self._classifier.batch_prob_classify(featuresets)    

    def labels(self):
        return self._classifier.labels()       
                           
    def parse(self, tokens):
        tokens = ChunkTagger._flatten(self.tag(tokens))
        return conllstr2tree(self._tokens2conllstr(tokens))

    def test(self, test_sequence, **kwargs):
        """
        Tests the C{ChunkTagger} instance.

    	@param test_sequence: a sequence of labeled test instances
        @type test_sequence: C{list} of C{list}
        @kwparam verbose: boolean flag indicating whether training should be
            verbose or include printed output
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

    @classmethod
    def train(cls, labeled_sequence, test_sequence=None,
                   unlabeled_sequence=None, **kwargs):
        classifier = \
            cls(kwargs.get('feature_detector'), 
                LazyMap(ChunkTagger._unflatten, labeled_sequence), 
                kwargs.get('classifier_builder'))
        if test_sequence:
            classifier.test(test_sequence)
        return classifier


class ChunkTaggerCorpusReader(CorpusReaderDecorator):
    """A decorator.
    """

    def __init__(self, reader, **kwargs):
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
        return self._chunker

    def tagger(self):
        return self._tagger


def features(tokens, index, history=None, **kwargs):
    spelling, pos = tokens[index][:2]

    feats = {}
    feats['spelling'] = spelling
    feats['word'] = spelling.lower()
    feats['pos'] = pos
    feats['isupper'] = spelling.isupper()
    feats['islower'] = spelling.islower()
    feats['istitle'] = spelling.istitle()
    feats['isalnum'] = spelling.isalnum() 
    feats['isnumeric'] = \
        bool(re.match(r'^(\d{1,3}(\,\d{3})*|\d+)(\.\d+)?$', spelling))
    for i in range(1, 4):
        feats['prefix_%d' % i] = spelling[:i]
        feats['suffix_%d' % i] = spelling[-i:]
    feats['isclosedcat'] = pos in TREEBANK_CLOSED_CATS
    if kwargs.get('depth', 1) > 0 and index > 0:
        prev_feats = features(tokens, index - 1, history, 
                              depth=kwargs.get('depth', 1) - 1)
        for key, val in prev_feats.items():
            feats['prev_%s' % key] = val
    if history and index > 0:
        feats['prev_tag'] = history[index - 1]
    feats['prev_pos/pos'] = '%s/%s' % (feats.get('prev_pos'), feats.get('pos'))

    return feats
            
def maxent_classifier_builder(labeled_featuresets):
    return MaxentClassifier.train(
        labeled_featuresets,
        algorithm='megam',
        gaussian_prior_sigma=0.1,
        count_cutoff=1,
        min_lldelta=1e-7)

def train(num_train_sents, num_test_sents, model_file=None, **kwargs):
    conll2k_train = LazyCorpusLoader(
        'conll2000', ConllChunkCorpusReader, 
        ['train.txt'], ('NP','VP','PP'))
    conll2k_train_sequence = conll2k_train.iob_sents()
    conll2k_test = LazyCorpusLoader(
        'conll2000', ConllChunkCorpusReader,
        ['test.txt'], ('NP','VP','PP'))
    conll2k_test_sequence = conll2k_test.iob_sents()
    model = train_model(ChunkTagger, 
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
    return model
                                       
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
        train(options.num_train_sents, options.num_test_sents,
              options.model_file, verbose=options.verbose)
    elif options.demo:
        demo(options.verbose)