# Natural Language Toolkit
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk_lite_contrib.classifier import zeror as z, instances as ins
from nltk_lite_contrib.classifier.exceptions import invaliddataerror as inv
from nltk_lite_contrib.classifier_tests import *

class ZeroRTestCase(unittest.TestCase):
    def testZeroRInstanceIsCreatedWithTrainingData(self):
        classifier = z.ZeroR(datasetsDir(self) + 'test_phones' + SEP + 'phoney')
        self.assertEqual(z.ZeroRTrainingInstances(datasetsDir(self) + 'test_phones' + SEP + 'phoney'), classifier.training, 'should have created training instances')
    
    def testZeroRVerifiesValidityOfTrainingData(self):
        try:
            classifier = z.ZeroR(datasetsDir(self) + 'test_faulty' + SEP + 'invalid_attributes')
            self.fail('should throw invalid data error')
        except inv.InvalidDataError:
            pass
        
    def testMajorityClass(self):
        tinstances = z.ZeroRTrainingInstances(datasetsDir(self) + 'test_phones' + SEP + 'phoney')
        self.assertEqual('b', tinstances.majorityClass())
        
    def testMajorityClassIsSetOnTestInstances(self):
        zeror = z.ZeroR(datasetsDir(self) + 'test_phones' + SEP + 'phoney')
        zeror.test(datasetsDir(self) + 'test_phones' + SEP + 'phoney', False)
        i = 0
        for i in range(4):
            self.assertEqual('b', zeror.testInstances.instances[i].classifiedKlass)
            self.assertEqual(None, zeror.testInstances.instances[i].klassValue)
            
    def testVerifyReturnsCorrectConfusionMatrix(self):
        zeror = z.ZeroR(datasetsDir(self) + 'minigolf' + SEP + 'weather')
        confusionMatrix = zeror.verify(datasetsDir(self) + 'minigolf' + SEP + 'weather')
        self.assertEqual(0.75, confusionMatrix.accuracy())
        self.assertEqual(0.25, confusionMatrix.errorRate())
        self.assertEqual(1, confusionMatrix.tpr())
        self.assertEqual(0, confusionMatrix.tnr())
        self.assertEqual(1, confusionMatrix.fpr())
        self.assertEqual(0.75, confusionMatrix.precision())
        self.assertEqual(1, confusionMatrix.recall())
        self.assertAlmostEqual(0.85714286, confusionMatrix.fscore(), 8)
        
        

        