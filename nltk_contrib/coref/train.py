# Natural Language Toolkit (NLTK) Coreference Training Utilities
#
# Copyright (C) 2001-2009 NLTK Project 
# Author: Joseph Frazee <jfrazee@mail.utexas.edu>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

import gzip
import time

try:
    import cPickle as pickle
except:
    import pickle
    
try:
    from cStringIO import StringIO
except:
    from StringIO import StringIO


def train_model(train_class, labeled_sequence, test_sequence, pickle_file,
                num_train_sents, num_test_sents, **kwargs):
    """
    Train a C{TrainableI} object.
    
    @param train_class: the C{TrainableI} type to be trained.
    @type train_class: C{type}
    @labeled_sequence: a sequence of labeled training instances.
    @type labeled_sequence: C{list} of C{list}
    @param pickle_file: the path to save the pickled model to.
    @type pickle_file: C{str}
    @param num_train_sents: the number of sentences to train on. 
    @type num_train_sents: C{int}
    @param num_test_sents: the number of sentences to test on.
    @type num_test_sents: C{int}
    @kwparam verbose: boolean flag indicating whether training should be
        verbose or include printed output.
    @type verbose: C{bool}
    """
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
