# Natural Language Toolkit
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk_lite.contrib.classifier import zeror as z, instances as ins, format
from nltk_lite.contrib.classifier.exceptions import invaliddataerror as inv
from nltk_lite.contrib.classifier_tests import *

class ZeroRTestCase(unittest.TestCase):
    def test_zeroR_instance_is_created_with_training_data(self):
        classifier = z.ZeroR(datasetsDir(self) + 'test_phones' + SEP + 'phoney')
        self.assertEqual(format.C45_FORMAT.get_training_instances(datasetsDir(self) + 'test_phones' + SEP + 'phoney'), classifier.training, 'should have created training instances')
    
    def test_zeroR_verifies_validity_of_training_data(self):
        try:
            z.ZeroR(datasetsDir(self) + 'test_faulty' + SEP + 'invalid_attributes')
            self.fail('should throw invalid data error')
        except inv.InvalidDataError:
            pass
        
    def test_majority_class(self):
        classifier = z.ZeroR(datasetsDir(self) + 'test_phones' + SEP + 'phoney')
        self.assertEqual('b', classifier.majority_class())
        
    def test_majority_class_is_set_on_test_instances(self):
        zeror = z.ZeroR(datasetsDir(self) + 'test_phones' + SEP + 'phoney')
        zeror.test(datasetsDir(self) + 'test_phones' + SEP + 'phoney', False)
        i = 0
        for i in range(4):
            self.assertEqual('b', zeror.test_instances[i].classifiedKlass)
            self.assertEqual(None, zeror.test_instances[i].klass_value)
            
    def test_verify_returns_correct_confusion_matrix(self):
        zeror = z.ZeroR(datasetsDir(self) + 'minigolf' + SEP + 'weather')
        confusion_matrix = zeror.verify(datasetsDir(self) + 'minigolf' + SEP + 'weather')
        self.assertEqual(0.75, confusion_matrix.accuracy())
        self.assertEqual(0.25, confusion_matrix.error())
        self.assertEqual(1, confusion_matrix.tpr())
        self.assertEqual(0, confusion_matrix.tnr())
        self.assertEqual(1, confusion_matrix.fpr())
        self.assertEqual(0.75, confusion_matrix.precision())
        self.assertEqual(1, confusion_matrix.recall())
        self.assertAlmostEqual(0.85714286, confusion_matrix.fscore(), 8)

    def test_can_classify_data_having_continuous_attributes(self):
        zeror = z.ZeroR(datasetsDir(self) + 'numerical' + SEP + 'weather')
        zeror.verify(datasetsDir(self) + 'numerical' + SEP + 'weather')
        
        
        

        