# Natural Language Toolkit (NLTK) Coreference Resolver
#
# Copyright (C) 2008 NLTK Project 
# Author: Joseph Frazee <jfrazee@mail.utexas.edu>
# URL: http://nltk.org/
# For license information, see LICENSE.TXT

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

from nltk.utilities import LazyMap, LazyZip, LazyConcatenation

from nltk.corpus import BracketParseCorpusReader, ConllChunkCorpusReader
from nltk.corpus.util import LazyCorpusLoader

from nltk_contrib.coref import MUC6CorpusReader

from nltk_contrib.coref.chunk import HiddenMarkovModelTagger, \
     HiddenMarkovModelChunkTagger, ClosedCategoryChunkTransform, \
     NamedEntityChunkTransform
     
from nltk_contrib.coref.util import HiddenMarkovModelChunkTagger, \
    ChunkTaggerCorpusReader, TreebankTaggerCorpusReader, \
    TreebankChunkTaggerCorpusReader
from nltk_contrib.coref.util import zipzip

TREEBANK_CLOSED_CATS = set(['CC', 'DT', 'MD', 'POS', 'PP$', 'RP', 'TO', 'WDT',
                            'WP$', 'EX', 'IN', 'PDT', 'PRP', 'WP', 'WRB'])
    
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
    
    print 'Testing...'
    
    start = time.time()
    model.test(test_sequence, **kwargs)
    end = time.time()    
    
    print 'Test time: %.3fs' % (end - start)
    print 'Test time per sentence: %.3fs' % (float(end - start) / sent_count)    
    print 'Test time per word: %.3fs' % (float(end - start) / word_count)    
    
    try:
        print 'Saving model...'        
        if isinstance(pickle_file, str):
            pickle.dump(model, open(pickle_file, 'wb'))
            model = pickle.load(open(pickle_file))
        else:
            stream = StringIO()
            pickle.dump(model, stream)
            stream = StringIO(stream.getvalue())
            model = pickle.load(stream)
        print 'Model saved'
    except Error, (errno, error):
        print "Error saving model, error(%s): %s" % (errno, error)

    return model

def demo():
    print 'Demo...'
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
    parser.add_option('-n', '--train-ne-chunker', action='store_true',
                      default=False, dest='train_ne_chunker', 
                      help='train MUC6 named entity chunker')
    parser.add_option('-f', '--model-file', metavar='FILE',
                      dest='model_file', help='save model to FILE')
    parser.add_option('-e', '--num-test-sents', metavar='NUM_TEST',
                      dest='num_test_sents', type=int, 
                      help='number of test sentences')
    parser.add_option('-r', '--num-train-sents', metavar='NUM_TRAIN',
                      dest='num_train_sents', type=int, 
                      help='number of training sentences')
    parser.add_option('-v', '--verbose', action='store_true',
                      default=False, dest='verbose',
                      help='verbose')
    (options, args) = parser.parse_args()

    if options.train_tagger:
        treebank_train = LazyCorpusLoader(
            'penn-treebank-rel3/parsed/mrg/wsj/',
            BracketParseCorpusReader, r'(0[2-9]|1[0-9]|2[01])\/wsj_.*\.mrg')
        treebank_train_sequence = treebank_train.tagged_sents()
        treebank_test = LazyCorpusLoader(
            'penn-treebank-rel3/parsed/mrg/wsj/',
            BracketParseCorpusReader, r'24\/wsj_.*\.mrg')
        treebank_test_sequence = treebank_test.tagged_sents()
        model = train_model(HiddenMarkovModelTagger, 
                            treebank_train_sequence, 
                            treebank_test_sequence,
                            options.model_file, 
                            options.num_train_sents, 
                            options.num_test_sents,
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
        conll2k_transform = ClosedCategoryChunkTransform(TREEBANK_CLOSED_CATS)
        model = train_model(HiddenMarkovModelChunkTagger, 
                            conll2k_train_sequence, 
                            conll2k_test_sequence,
                            options.model_file, 
                            options.num_train_sents, 
                            options.num_test_sents,
                            transform=conll2k_transform,
                            verbose=options.verbose)
        
    elif options.train_ne_chunker:
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

        muc6_test_sequence = list(muc6_test_sequence[:options.num_test_sents])
        muc6_transform = NamedEntityChunkTransform(TREEBANK_CLOSED_CATS)
        model = train_model(HiddenMarkovModelChunkTagger, 
                            muc6_train_sequence, 
                            muc6_test_sequence,
                            options.model_file, 
                            options.num_train_sents, 
                            options.num_test_sents,
                            transform=muc6_transform,
                            verbose=options.verbose)

    elif options.demo:
        demo()

    print time.ctime(time.time())
