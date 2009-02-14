# Natural Language Toolkit (NLTK) Coreference Chunker
#
# Copyright (C) 2001-2009 NLTK Project 
# Author: Joseph Frazee <jfrazee@mail.utexas.edu>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

import re
import optparse

from nltk.util import LazyMap, LazyConcatenation, LazyZip
from nltk.metrics import precision, recall, accuracy, f_measure

from nltk.corpus import BracketParseCorpusReader, ConllChunkCorpusReader
from nltk.corpus.util import LazyCorpusLoader

from nltk.metrics import accuracy

from nltk.chunk.util import conllstr2tree

from nltk.tag import ClassifierBasedTagger

from nltk.classify import ClassifierI
from nltk.classify.maxent import MaxentClassifier

from nltk_contrib.coref.features import *
from nltk_contrib.coref.train import train_model

TREEBANK_CLOSED_CATS = set(['CC', 'DT', 'MD', 'POS', 'PP$', 'RP', 'TO', 'WDT',
                            'WP$', 'EX', 'IN', 'PDT', 'PRP', 'WP', 'WRB'])

class ChunkFeatureDetector(dict):
    def __init__(self, tokens, index=0, history=None):
        dict.__init__(self, features(tokens, index, history))
        

class ChunkTagger(ClassifierBasedTagger, ClassifierI):    
    def __getattr__(self, name):
        if name != '_classifier':
            return getattr(self._classifier, name)

    def labels(self):
        return self._classifier.labels()

    def batch_classify(self, featuresets):
        return self._classifier.batch_classify(featuresets)

    def batch_prob_classify(self, featuresets):
        return self._classifier.batch_prob_classify(featuresets)
            
    @classmethod
    def train(cls, labeled_sequence, test_sequence=None,
                   unlabeled_sequence=None, **kwargs):

        classifier = \
            cls(kwargs.get('feature_detector'), labeled_sequence, 
                kwargs.get('classifier_builder'))
        
        if test_sequence:
            classifier.test(test_sequence)
        
        return classifier  

    def test(self, test_sequence, **kwargs):
        """
        Tests the C{ChunkTagger} instance.

    	@param test_sequence: a sequence of labeled test instances
        @type test_sequence: C{list} of C{list}
        @kwparam verbose: boolean flag indicating whether training should be
            verbose or include printed output
        @type verbose: C{bool}
        """

        def words(sent):
            return [word for (word, tag) in sent]

        def tags(sent):
            return [tag for (word, tag) in sent]

        predicted_sequence = LazyMap(self.tag, LazyMap(words, test_sequence))

        test_tags = LazyConcatenation(LazyMap(tags, test_sequence))
        predicted_tags = LazyConcatenation(LazyMap(tags, predicted_sequence))
        
        if kwargs.get('verbose'):
            for (word, pos), gold, pred \
            in LazyZip(LazyConcatenation(LazyMap(words, test_sequence)), 
                       test_tags, predicted_tags):
                print '%-25s %-6s %-6s %s' % (word, gold, pred, gold == pred)

        acc = accuracy(test_tags, predicted_tags)

        count = sum([len(sent) for sent in test_sequence])

        print 'accuracy over %d tokens: %.2f' % (count, acc * 100)   


def maxent_classifier_builder(labeled_featuresets):
    return MaxentClassifier.train(
        labeled_featuresets,
        algorithm='megam',
        gaussian_prior_sigma=0.1,
        count_cutoff=1,
        min_lldelta=1e-5)

def features(tokens, index, history=None, **kwargs):
    spelling, pos = tokens[index][:2]
    
    feats = {}
    feats['spelling'] = spelling
    feats['word'] = spelling.lower()
    feats['pos'] = pos
    feats['is_upper_case'] = is_upper_case(spelling)
    feats['is_lower_case'] = is_lower_case(spelling)
    feats['is_title_case'] = is_title_case(spelling)
    feats['is_alnum_case'] = is_alpha_numeric(spelling)  
    
    for i in range(1, 4):
        feats['prefix_%d' % i] = spelling[:i]
        feats['suffix_%d' % i] = spelling[-i:]
        
    feats['is_closed_cat'] = pos in TREEBANK_CLOSED_CATS    

    # You can do ok without this block of features, but they *do* help.
    feats['is_digit'] = is_digit(spelling)
    feats['is_numeric'] = is_numeric(spelling)
    feats['is_punct'] = is_punct(spelling)
    feats['isroman'] = is_roman_numeral(spelling)
    feats['is_initial'] = is_initial(spelling)
    feats['is_tla'] = is_tla(spelling)
    feats['is_name'] = is_name(spelling)
    feats['is_city'] = is_city(spelling)
    feats['is_state'] = is_state(spelling)
    feats['is_country'] = is_country(spelling)
    feats['is_location'] = is_location(spelling)
    feats['contains_city'] = contains_city(spelling)
    feats['contains_state'] = contains_state(spelling)
    feats['contains_country'] = contains_country(spelling)
    feats['contains_location'] = contains_location(spelling)        
    feats['is_person_prefix'] = is_person_prefix(spelling)
    feats['is_person_suffix'] = is_person_suffix(spelling)
    feats['is_org_suffix'] = is_org_suffix(spelling)
    feats['is_day'] = is_day(spelling)
    feats['is_month'] = is_month(spelling)
    feats['is_date'] = is_date(spelling)
    feats['is_time'] = is_time(spelling)    
    feats['is_ordinal'] = is_ordinal(spelling)
    feats['is_year'] = is_year(spelling)
    feats['is_pronoun'] = is_pronoun(spelling)
    
    if kwargs.get('depth', 1) > 0 and index > 0:
        prev_feats = features(tokens, index - 1, 
                              depth=kwargs.get('depth', 1) - 1)
        for key, val in prev_feats.items():
            feats['prev_%s_%d' % (key, 1)] = val
    if history and index > 0:
        feats['prev_tag_%d' % 1] = history[index - 1]
    feats['prev_pos_%d/pos' % 1] = '%s/%s' % (feats.get('prev_pos_%d' % 1), 
                                         feats.get('pos'))
                                         
    return feats
    
def wordtag(sent):
    return [((word, tag), iob) for word, tag, iob in sent]

def train(num_train_sents, num_test_sents, model_file=None, **kwargs):
    conll2k_train = LazyCorpusLoader(
        'conll2000', ConllChunkCorpusReader, 
        ['train.txt'], ('NP','VP','PP'))
    conll2k_train_sequence = LazyMap(wordtag, conll2k_train.iob_sents())
    conll2k_test = LazyCorpusLoader(
        'conll2000', ConllChunkCorpusReader,
        ['test.txt'], ('NP','VP','PP'))
    conll2k_test_sequence = LazyMap(wordtag, conll2k_test.iob_sents())
    model = train_model(ChunkTagger, 
                        conll2k_train_sequence, 
                        conll2k_test_sequence,
                        model_file,
                        num_train_sents,
                        num_test_sents,
                        feature_detector=ChunkFeatureDetector,
                        classifier_builder=maxent_classifier_builder,
                        verbose=kwargs.get('verbose'))
    if kwargs.get('verbose'):
        model.show_most_informative_features(25)
    return model
                        
def demo(verbose=False):
    from nltk_contrib.coref.chunk2 import train
    model = train(10, 10, verbose=verbose)
    
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