# Natural Language Toolkit
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT
from nltk_lite.contrib.classifier import classify as c
from nltk_lite.contrib.classifier_tests import *

class ClassifyTestCase(unittest.TestCase):
    def setUp(self):
        self.classify = c.Classify()
        
    def test_reads_classifier_name(self):
        self.classify.parse(['-a', '0R']) #Zero R classifier
        self.assertEqual('0R', self.classify.values.ensure_value('algorithm', None))
        
        self.classify.parse(['-a', '1R']) #One R classifier
        self.assertEqual('1R', self.classify.values.ensure_value('algorithm', None))
        
        self.classify.parse(['-a', 'DT']) #Decision Tree classifier
        self.assertEqual('DT', self.classify.values.ensure_value('algorithm', None))

    def test_accuracy_and_fscore_are_true_by_default(self):
        self.classify.parse(None)
        self.assertEqual(True, self.classify.values.ensure_value('accuracy', None))
        self.assertEqual(True, self.classify.values.ensure_value('fscore', None))
        
        self.classify.parse(["-A"])
        self.assertEqual(False, self.classify.values.ensure_value('accuracy', None))
        
        self.classify.parse(["-AF"])
        self.assertEqual(False, self.classify.values.ensure_value('accuracy', None))
        self.assertEqual(False, self.classify.values.ensure_value('fscore', None))

    def test_classifyDoesNotThrowErrorIfRequiredComponentsArePresent(self):
        path = datasetsDir(self) + 'minigolf' + SEP + 'weather'
        dns = DoNothingStrategy()
        
        classify = StubClassify(dns)
        self.assertFalse(dns.called)
        classify.run(['-a', '1R', '-t', path, '-T', path])
        self.assertTrue(dns.called)
        self.assertFalse(classify.errorCalled)
        
        dns = DoNothingStrategy()
        classify = StubClassify(dns)
        self.assertFalse(dns.called)
        classify.run(['-a', '1R', '-t', path, '-g', path])
        self.assertTrue(dns.called)
        self.assertFalse(classify.errorCalled)
        
    def test_classify_throws_error_if_neither_test_nor_gold_is_present(self):
        path = datasetsDir(self) + 'minigolf' + SEP + 'weather'
        dns = DoNothingStrategy()
        classify = StubClassify(dns)
        self.assertFalse(dns.called)
        classify.parse(['-a', '1R', '-t', path])
        try:
            classify.execute()
        except TypeError:
            pass
        self.assertTrue(classify.errorCalled)
        self.assertTrue(dns.called)#in reality it will never be called as it exits in the error method
        self.assertEqual('Invalid arguments. One or more required arguments are not present.', classify.message)
        
    def test_throws_error_if_both_files_and_other_options_are_present(self):
        path = datasetsDir(self) + 'minigolf' + SEP + 'weather'
        dns = DoNothingStrategy()
        classify = StubClassify(dns)
        self.assertFalse(dns.called)
        classify.parse(['-a', '1R', '-f', path, '-t', path])
        classify.execute()
        self.assertTrue(classify.errorCalled)
        self.assertEqual('Invalid arguments. The files argument cannot exist with training, test or gold arguments.', classify.message)

    def test_throws_error_if_both_test_and_gold_files_are_present(self):
        path = datasetsDir(self) + 'minigolf' + SEP + 'weather'
        dns = DoNothingStrategy()
        classify = StubClassify(dns)
        self.assertFalse(dns.called)
        classify.parse(['-a', '1R', '-t', path, '-T', path, '-g', path])
        classify.execute()
        self.assertTrue(classify.errorCalled)
        self.assertEqual('Invalid arguments. Test and gold files are mutually exclusive.', classify.message)

    def test_throws_error_if_verify_options_are_present_for_a_test_file(self):
        path = datasetsDir(self) + 'minigolf' + SEP + 'weather'
        dns = DoNothingStrategy()
        classify = StubClassify(dns)
        self.assertFalse(dns.called)
        classify.parse(['-a', '1R', '-v', '-t', path, '-T', path])
        classify.execute()
        self.assertTrue(classify.errorCalled)
        self.assertEqual('Invalid arguments. Cannot verify classification for test data.', classify.message)
        
    def test_get_file_strategy(self):
        strategy = c.get_file_strategy('files', None, None, None, True)
        self.assertEqual(c.CommonBaseNameStrategy, strategy.__class__)
        values = strategy.values()
        self.assertEqual(values[0], 'files')
        self.assertEqual(values[1], None)
        self.assertEqual(values[2], 'files')
        
        strategy = c.get_file_strategy('files', None, None, None, False)
        self.assertEqual(c.CommonBaseNameStrategy, strategy.__class__)
        values = strategy.values()
        self.assertEqual(values[0], 'files')
        self.assertEqual(values[1], 'files')
        self.assertEqual(values[2], None)
        
        strategy = c.get_file_strategy(None, 'train', 'test', None, False)
        self.assertEqual(c.ExplicitNamesStrategy, strategy.__class__)
        values = strategy.values()
        self.assertEqual(values[0], 'train')
        self.assertEqual(values[1], 'test')
        self.assertEqual(values[2], None)

        strategy = c.get_file_strategy(None, 'train', None, 'gold', False)
        self.assertEqual(c.ExplicitNamesStrategy, strategy.__class__)
        values = strategy.values()
        self.assertEqual(values[0], 'train')
        self.assertEqual(values[1], None)
        self.assertEqual(values[2], 'gold')
        
        
class StubClassify(c.Classify):
    def __init__(self, strategy):
        c.Classify.__init__(self)
        self.errorCalled = False
        self.strategy = strategy
        
    def error(self, message):
        #in reality error will display usage and quit
        self.message = message
        self.errorCalled = True
        
    def get_classification_strategy(self, classifier, test, gold):
        return self.strategy
                    
class DoNothingStrategy:
    def __init__(self):
        self.called = False
        
    def classify(self):
        #do nothing
        self.called = True
    
    def print_results(self, log, accuracy, error, fscore, precision, recall):
        #do nothing
        pass
    
    def write(self, log, should_write, data_format, suffix):
        #do nothing
        pass
        