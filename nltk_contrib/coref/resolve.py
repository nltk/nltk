# Natural Language Toolkit (NLTK) Coreference Resolver
#
# Copyright (C) 2001-2009 NLTK Project 
# Author: Joseph Frazee <jfrazee@mail.utexas.edu>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

import gzip
import time
import optparse

try:
    import cPickle as pickle
except:
    import pickle
    
try:
    from cStringIO import StringIO
except:
    from StringIO import StringIO

from nltk.util import LazyMap, LazyZip, LazyConcatenation, LazyEnumerate

from nltk.corpus import BracketParseCorpusReader, ConllChunkCorpusReader
from nltk.corpus.util import LazyCorpusLoader

from nltk.tag.hmm import HiddenMarkovModelTagger

from nltk_contrib.coref.api import *

from nltk_contrib.coref import MUC6CorpusReader

from nltk_contrib.coref.features import *

from nltk_contrib.coref.chunk import HiddenMarkovModelChunkTagger, \
     ClosedCategoryChunkTransform
    
from nltk_contrib.coref.ne import BaselineNamedEntityChunkTagger, \
     NamedEntityChunkTransform, NamedEntityFeatureDetector, \
     NamedEntityClassifier, NamedEntityFeatureDetector2
     
from nltk_contrib.coref.util import LidstoneProbDistFactory, \
    TreebankTaggerCorpusReader, TreebankChunkTaggerCorpusReader, \
    zipzip, load_treebank

TREEBANK_CLOSED_CATS = set(['CC', 'DT', 'MD', 'POS', 'PP$', 'RP', 'TO', 'WDT',
                            'WP$', 'EX', 'IN', 'PDT', 'PRP', 'WP', 'WRB'])

class BaselineCorefResolver(CorefResolverI):
    def __init__(self):
        self._chunk_tagger = BaselineNamedEntityChunkTagger()

    def resolve_mention(self, mentions, index, history):
        mention, mention_id, sent_index, chunk_index = mentions[index]
        
        # If the mention is a pronoun and there is an antecedent available,
        # link it to the most recent mention.
        if history and isinstance(mention, str) and is_pronoun(mention):
            prev_mention, prev_mention_id = history[-1][:2]
            return (mention, prev_mention_id, sent_index, chunk_index)
        
        for previous_mention, previous_mention_id, previous_sent_index, \
            previous_chunk_index in history:
            
            M = set([word.lower() for word in mention if len(word.lower()) > 2])
            P = set([word.lower() for word in previous_mention if len(word.lower()) > 2])
            
            # If the current mention and a previous mention have some
            # non-trivial overlap of words, then link the current mention to
            # that previous mention.
            if M.intersection(P):
                return (mention, previous_mention_id, sent_index, chunk_index)
        
        # Otherwise, the current mention does not co-refer with any previous
        # mentions.
        return (mention, mention_id, sent_index, chunk_index)
            
    def mentions(self, discourse):
        mentions = []
        
        chunked_discourse = LazyMap(self._chunk_tagger.chunk, discourse)
        
        mention_id = 0       
        for sent_index, chunked_sent in LazyEnumerate(chunked_discourse):
            for chunk_index, chunk in LazyEnumerate(chunked_sent):
                if isinstance(chunk, list) or is_pronoun(chunk):
                    mentions.append((chunk, mention_id, sent_index, chunk_index))
                    mention_id += 1

        return mentions

    def resolve_mentions(self, mentions, **kwargs):
        history = []
        for index, (mention, i, j, k) in LazyEnumerate(mentions):
            mentions[index] = self.resolve_mention(mentions, index, history)
            history.append(mentions[index])
        return mentions
    
    def resolve(self, discourse, **kwargs):
        resolved_discourse = []
                
        mentions = {}
        for mention, mention_id, sent_index, chunk_index \
        in self.resolve_mentions(self.mentions(discourse)):
            mentions[(sent_index, chunk_index)] = (mention, mention_id)
        
        chunked_discourse = LazyMap(self._chunk_tagger.chunk, discourse)        
        for sent_index, sent in LazyEnumerate(chunked_discourse):
            resolved_discourse.append([])
            for chunk_index, chunk in LazyEnumerate(sent):
                mention, mention_id = \
                    mentions.get((sent_index, chunk_index), (None, None))
                resolved_discourse[sent_index].append((chunk, mention_id))                    

        return resolved_discourse
    
def train_model(train_class, labeled_sequence, test_sequence, pickle_file,
                num_train_sents, num_test_sents, **kwargs):
    print 'Training ', train_class
    print 'Loading training data (supervised)...'

    labeled_sequence = labeled_sequence[:num_train_sents]
    sent_count = len(labeled_sequence)
    word_count = sum([len(sent) for sent in labeled_sequence])

    print '%s sentences' % (sent_count)
    print '%s words' % (word_count)
    
    print 'Training...'
    
    start = time.time()
    model = train_class.train(labeled_sequence, **kwargs)
    end = time.time()
    
    print 'Training time: %.3fs' % (end - start)
    print 'Training time per sentence: %.3fs' % (float(end - start) / sent_count)    
    print 'Training time per word: %.3fs' % (float(end - start) / word_count)
    
    print 'Loading test data...'

    test_sequence = test_sequence[:num_test_sents]
    sent_count = len(test_sequence)
    word_count = sum([len(sent) for sent in test_sequence])

    print '%s sentences' % (sent_count)
    print '%s words' % (word_count)
    
    try:
        print 'Saving model...'        
        if isinstance(pickle_file, str):
            if pickle_file.endswith('.gz'):
                _open = gzip.open
            else:
                _open = open
            stream = _open(pickle_file, 'wb')
            pickle.dump(model, stream)
            stream.close()
            model = pickle.load(_open(pickle_file, 'rb'))
            print 'Model saved as %s' % pickle_file
        else:
            stream = StringIO()
            pickle.dump(model, stream)
            stream = StringIO(stream.getvalue())
            model = pickle.load(stream)
    except Exception, e:
        print 'Error saving model, %s' % str(e)
    
    print 'Testing...'
    
    start = time.time()
    model.test(test_sequence, **kwargs)
    end = time.time()    
    
    print 'Test time: %.3fs' % (end - start)
    print 'Test time per sentence: %.3fs' % (float(end - start) / sent_count)    
    print 'Test time per word: %.3fs' % (float(end - start) / word_count)

    return model

def baseline_coref_resolver_demo():
    from nltk.corpus.util import LazyCorpusLoader
    from nltk.corpus import BracketParseCorpusReader
    from nltk_contrib.coref.resolve import BaselineCorefResolver
    
    resolver = BaselineCorefResolver()
    treebank = load_treebank('0[12]')
    
    sents = LazyMap(lambda sent: \
            [word for word in sent if not word.startswith('*')],
        treebank.sents()[:10])
    mentions = resolver.mentions(sents)
    resolved_mentions = resolver.resolve_mentions(mentions)
    resolved_discourse = resolver.resolve(sents)
        
    print 'Baseline coref resolver demo...'
    print 'Mentions:'
    for mention in mentions:
        print mention
    print
    print 'Resolved mentions:'
    for mention in resolved_mentions:
        print mention
    print
    print 'Resolved discourse:'
    for sent in resolved_discourse:
        print sent
        print
    print
    
def demo():
    print 'Demo...'
    baseline_coref_resolver_demo()
    # muc6_test = LazyCorpusLoader(
    #         'muc6', MUC6CorpusReader, 
    #         r'.*\-(01[8-9][0-9])\..*\.sgm')
    # 
    # test_iob_sents = muc6_test.iob_sents()
    # gold_iob_tags = LazyMap(lambda sent: \
    #         [iob_tag for (word, iob_tag) in sent],
    #     test_iob_sents)
    # 
    # muc6_test = ChunkTaggerCorpusReader(muc6_test, load(MUC6_NE_CHUNKER))
    # predicted_chunked_sents = muc6_test.chunked_sents()
    # predicted_iob_tags = LazyMap(lambda sent: \
    #         [iob_tag for (word, tag, iob_tag) in sent],
    #     predicted_chunked_sents)
    # 
    # for token in LazyZip(LazyConcatenation(predicted_iob_tags),
    #                      LazyConcatenation(gold_iob_tags),
    #                      LazyConcatenation(test_iob_sents)):
    #     print token
    # print
    # 
    # evaluate(gold_iob_tags, predicted_iob_tags)
    # 
    # return
    # 
    # conll2000_test = LazyCorpusLoader(
    #      'conll2000', ConllChunkCorpusReader, ['test.txt'], ('NP','VP','PP')) 
    # tagger_reader = TreebankTaggerCorpusReader(conll2000_test)
    # chunker_reader = TreebankChunkerCorpusReader(conll2000_test)
    # for sent in tagger_reader.tagged_sents()[:1]:
    #     print sent
    #     print
    # for sent in chunker_reader.parsed_sents()[:5]:
    #     print sent
    #     print

if __name__ == '__main__':
    print time.ctime(time.time())
        
    parser = optparse.OptionParser()
    parser.add_option('-d', '--demo', action='store_true', dest='demo',
                      default=True, help='run demo')
    parser.add_option('-t', '--train-tagger', action='store_true',
                      default=False, dest='train_tagger', 
                      help='train Treebank POS tagger')
    parser.add_option('-c', '--train-chunker', action='store_true',
                      default=False, dest='train_chunker', 
                      help='train Treebank chunker')
    parser.add_option('-n', '--train-ner', metavar='NER_COMPONENT',
                      dest='train_ner', type='choice',
                      choices=('chunker', 'classifier', 'classifier2', 'recognizer'),
                      help='train NER components (chunker, classifier, classifier2, recognizer)')
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
            psyco.profile()
        except:
            pass

    if options.train_tagger:
        treebank_train = load_treebank('0[2-9]|1[0-9]|2[01]')
        treebank_train_sequence = treebank_train.tagged_sents()
        treebank_test = load_treebank('24')
        treebank_test_sequence = treebank_test.tagged_sents()
        treebank_estimator = LidstoneProbDistFactory
        model = train_model(HiddenMarkovModelTagger, 
                            treebank_train_sequence, 
                            treebank_test_sequence,
                            options.model_file, 
                            options.num_train_sents, 
                            options.num_test_sents,
                            estimator=treebank_estimator,
                            verbose=options.verbose)

    elif options.train_chunker:
        conll2k_train = LazyCorpusLoader(
            'conll2000', ConllChunkCorpusReader, 
            ['train.txt'], ('NP','VP','PP'))
        conll2k_train_sequence = conll2k_train.iob_sents()
        conll2k_test = LazyCorpusLoader(
            'conll2000', ConllChunkCorpusReader,
            ['test.txt'], ('NP','VP','PP'))
        conll2k_test_sequence = conll2k_test.iob_sents()
        conll2k_estimator = LidstoneProbDistFactory
        conll2k_transform = ClosedCategoryChunkTransform(TREEBANK_CLOSED_CATS)
        model = train_model(HiddenMarkovModelChunkTagger, 
                            conll2k_train_sequence, 
                            conll2k_test_sequence,
                            options.model_file, 
                            options.num_train_sents, 
                            options.num_test_sents,
                            estimator=conll2k_estimator,
                            transform=conll2k_transform,
                            verbose=options.verbose)
        
    elif options.train_ner == 'chunker':
        muc6_train = TreebankTaggerCorpusReader(
            LazyCorpusLoader(
                'muc6', MUC6CorpusReader, 
                r'.*\-(0[01][0-7][0-9])\..*\.sgm'))
        muc6_train_sequence = LazyMap(lambda token: \
                [(word, tag, iob_tag) 
                 for ((word, tag), (word, iob_tag)) in token],
            zipzip(muc6_train.tagged_sents()[:options.num_train_sents], 
                   muc6_train.iob_sents()[:options.num_train_sents]))
        muc6_test = TreebankTaggerCorpusReader(
            LazyCorpusLoader(
                'muc6', MUC6CorpusReader, 
                r'.*\-(01[8-9][0-9])\..*\.sgm'))
        muc6_test_sequence = LazyMap(lambda token: \
                [(word, tag, iob_tag) 
                 for ((word, tag), (word, iob_tag)) in token],
            zipzip(muc6_test.tagged_sents()[:options.num_test_sents], 
                   muc6_test.iob_sents()[:options.num_test_sents]))
        muc6_estimator = LidstoneProbDistFactory
        muc6_transform = NamedEntityChunkTransform(TREEBANK_CLOSED_CATS)
        model = train_model(HiddenMarkovModelChunkTagger, 
                            muc6_train_sequence, 
                            muc6_test_sequence,
                            options.model_file, 
                            options.num_train_sents, 
                            options.num_test_sents,
                            estimator=muc6_estimator,
                            transform=muc6_transform,
                            verbose=options.verbose)

    elif options.train_ner == 'classifier':
        def join(chunk):
            if isinstance(chunk, tuple):
                word, iob_tag, ne_tag = chunk
            else:
                word = ' '.join([word for (word, iob_tag, ne_tag) in chunk])
                ne_tag = chunk[0][-1]
            return [(word, ne_tag)]
        muc6_train = LazyCorpusLoader(
                        'muc6', MUC6CorpusReader, 
                        r'.*\-(0[01][0-7][0-9])\..*\.sgm')
        muc6_train_sequence = LazyMap(join, muc6_train.ne_chunks())
        muc6_test = LazyCorpusLoader(
                        'muc6', MUC6CorpusReader, 
                        r'.*\-(01[8-9][0-9])\..*\.sgm')
        muc6_test_sequence = LazyMap(join, muc6_test.ne_chunks())
        model = train_model(NamedEntityClassifier, 
                            muc6_train_sequence, 
                            muc6_test_sequence,
                            options.model_file, 
                            options.num_train_sents, 
                            options.num_test_sents,
                            feature_detector=NamedEntityFeatureDetector,
                            out_tag=None,                 
                            verbose=options.verbose)
                            
        from nltk.tag.util import *
        for sent in muc6_test_sequence[:options.num_test_sents]:
            words = untag(sent)
            gold_tags = tags(sent)
            pred_tags = model.tag(words)
            for x, y, z in zip(pred_tags, gold_tags, words):
                if x == y:
                    print '  ', (x, y, z)
                else:
                    print '* ', (x, y, z)

    elif options.train_ner == 'classifier2':
        muc6_train = LazyCorpusLoader(
                        'muc6', MUC6CorpusReader, 
                        r'.*\-(0[01][0-7][0-9])\..*\.sgm')
        muc6_train_sequence = muc6_train.iob_sents()
        muc6_test = LazyCorpusLoader(
                        'muc6', MUC6CorpusReader, 
                        r'.*\-(01[8-9][0-9])\..*\.sgm')
        muc6_test_sequence = muc6_test.iob_sents()
        model = train_model(NamedEntityClassifier, 
                            muc6_train_sequence, 
                            muc6_test_sequence,
                            options.model_file, 
                            options.num_train_sents, 
                            options.num_test_sents,
                            feature_detector=NamedEntityFeatureDetector2,
                            out_tag='O',                 
                            verbose=options.verbose)
                            
        from nltk.tag.util import *
        for sent in muc6_test_sequence[:options.num_test_sents]:
            words = untag(sent)
            gold_tags = tags(sent)
            pred_tags = model.tag(words)
            for x, y, z in zip(pred_tags, gold_tags, words):
                if x == y:
                    print '  ', (x, y, z)
                else:
                    print '* ', (x, y, z)

    elif options.demo:
        demo()

    print time.ctime(time.time())
