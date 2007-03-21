# Natural Language Toolkit
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT
from nltk_lite_contrib import classify as c
from nltk_lite_contrib.classifier_tests import *

class ClassifyTestCase(unittest.TestCase):
    def setUp(self):
        self.classify = c.Classify()
        
    def test_reads_classifier_name(self):
        self.classify.parse(['-a', '0R']) #Zero R classifier
        self.assertEqual('0R', self.classify.values.ensure_value('algorithm', None))
        
        self.classify.parse(['-a', '1R']) #One R classifier
        self.assertEqual('1R', self.classify.values.ensure_value('algorithm', None))
        
        #self.classify.parse(['-a', 'DT']) #Decision Tree classifier
        #self.assertEqual('DT', self.classify.values.ensure_value('algorithm', None))

    def test_accuracy_and_fscore_are_true_by_default(self):
        self.classify.parse(None)
        self.assertEqual(True, self.classify.values.ensure_value('accuracy', None))
        self.assertEqual(True, self.classify.values.ensure_value('fscore', None))
        
        self.classify.parse(["-A"])
        self.assertEqual(False, self.classify.values.ensure_value('accuracy', None))
        
        self.classify.parse(["-AF"])
        self.assertEqual(False, self.classify.values.ensure_value('accuracy', None))
        self.assertEqual(False, self.classify.values.ensure_value('fscore', None))

    def testClassifyDoesNotThrowErrorIfRequiredComponentsArePresent(self):
        path = datasetsDir(self) + 'minigolf' + SEP + 'weather'
        classify = StubClassify()
        self.assertFalse(classify.classifyCalled)
        classify.parse(['-a', '1R', '-t', path, '-T', path])
        classify.execute()
        self.assertTrue(classify.classifyCalled)
        self.assertFalse(classify.errorCalled)
        
        classify = StubClassify()
        self.assertFalse(classify.classifyCalled)
        classify.parse(['-a', '1R', '-t', path, '-g', path])
        classify.execute()
        self.assertTrue(classify.classifyCalled)
        self.assertFalse(classify.errorCalled)
        
    def testClassifyThrowsErrorIfNeitherTestNorGoldIsPresent(self):
        path = datasetsDir(self) + 'minigolf' + SEP + 'weather'
        classify = StubClassify()
        self.assertFalse(classify.classifyCalled)
        classify.parse(['-a', '1R', '-t', path])
        classify.execute()
        self.assertTrue(classify.errorCalled)
        self.assertTrue(classify.classifyCalled)#in reality it will never be called as it exits in the error method
        self.assertEqual('Invalid attributes', classify.message)
        
    def testOnlyFilesImpliesTrainingAndTest(self):
        path = datasetsDir(self) + 'minigolf' + SEP + 'weather'
        classify = StubClassify()
        self.assertFalse(classify.classifyCalled)
        classify.parse(['-a', '1R', '-f', path])
        classify.execute()
        self.assertTrue(classify.classifyCalled)
        self.assertEqual(path, classify.testSet)
        self.assertEqual(None, classify.goldSet)

    def testFilesWithVerifyImpliesTrainingAndGold(self):
        path = datasetsDir(self) + 'minigolf' + SEP + 'weather'
        classify = StubClassify()
        self.assertFalse(classify.classifyCalled)
        classify.parse(['-a', '1R', '-v', '-f', path])
        classify.execute()
        self.assertTrue(classify.classifyCalled)
        self.assertEqual(None, classify.testSet)
        self.assertEqual(path, classify.goldSet)


class StubClassify(c.Classify):
    def __init__(self):
        c.Classify.__init__(self)
        self.errorCalled = False
        self.classifyCalled = False
        
    def error(self, message):
        #in reality error will display usage and quit
        self.message = message
        self.errorCalled = True
            
    def classify(self, classifier, test, gold):
        self.classifyCalled = True
        self.testSet = test
        self.goldSet = gold