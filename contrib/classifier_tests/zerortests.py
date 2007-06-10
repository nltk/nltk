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
        path = datasetsDir(self) + 'test_phones' + SEP + 'phoney'
        classifier = z.ZeroR(format.C45_FORMAT.get_training_instances(path), format.C45_FORMAT.get_attributes(path), format.C45_FORMAT.get_klass(path))
        self.assertEqual(format.C45_FORMAT.get_training_instances(datasetsDir(self) + 'test_phones' + SEP + 'phoney'), classifier.training, 'should have created training instances')
    
    def test_zeroR_verifies_validity_of_training_data(self):
        try:
            path = datasetsDir(self) + 'test_faulty' + SEP + 'invalid_attributes'
            classifier = z.ZeroR(format.C45_FORMAT.get_training_instances(path), format.C45_FORMAT.get_attributes(path), format.C45_FORMAT.get_klass(path))
            self.fail('should throw invalid data error')
        except inv.InvalidDataError:
            pass
        
    def test_majority_class(self):
        path = datasetsDir(self) + 'test_phones' + SEP + 'phoney'
        classifier = z.ZeroR(format.C45_FORMAT.get_training_instances(path), format.C45_FORMAT.get_attributes(path), format.C45_FORMAT.get_klass(path))
        self.assertEqual('b', classifier.majority_class())
        
    def test_majority_class_is_set_on_test_instances(self):
        path = datasetsDir(self) + 'test_phones' + SEP + 'phoney'
        zeror = z.ZeroR(format.C45_FORMAT.get_training_instances(path), format.C45_FORMAT.get_attributes(path), format.C45_FORMAT.get_klass(path))

        zeror.test(format.C45_FORMAT.get_test_instances(path))
        i = 0
        for i in range(4):
            self.assertEqual('b', zeror.test_instances[i].classified_klass)
            self.assertEqual(None, zeror.test_instances[i].klass_value)
            
    def test_verify_returns_correct_confusion_matrix(self):
        path = datasetsDir(self) + 'minigolf' + SEP + 'weather'
        zeror = z.ZeroR(format.C45_FORMAT.get_training_instances(path), format.C45_FORMAT.get_attributes(path), format.C45_FORMAT.get_klass(path))
        confusion_matrix = zeror.verify(format.C45_FORMAT.get_gold_instances(path))
        self.assertEqual(0.75, confusion_matrix.accuracy())
        self.assertEqual(0.25, confusion_matrix.error())
        self.assertEqual(1, confusion_matrix.tpr())
        self.assertEqual(0, confusion_matrix.tnr())
        self.assertEqual(1, confusion_matrix.fpr())
        self.assertEqual(0.75, confusion_matrix.precision())
        self.assertEqual(1, confusion_matrix.recall())
        self.assertAlmostEqual(0.85714286, confusion_matrix.fscore(), 8)

    def test_can_classify_data_having_continuous_attributes(self):
        path = datasetsDir(self) + 'numerical' + SEP + 'weather'
        zeror = z.ZeroR(format.C45_FORMAT.get_training_instances(path), format.C45_FORMAT.get_attributes(path), format.C45_FORMAT.get_klass(path))
        zeror.verify(format.C45_FORMAT.get_gold_instances(path))
        
        
        

        