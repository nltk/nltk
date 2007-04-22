# Natural Language Toolkit - Format tests
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT
from nltk_lite.contrib.classifier_tests import *
from nltk_lite.contrib.classifier import format, instance as ins, attribute as a

class FormatTestCase(unittest.TestCase):
    def test_get_c45_name(self):
        self.assertEqual('foo', format.C45_FORMAT.get_name('foo:a,b,c'))

    def test_get_c45_values(self):
        self.assertEqual(['a', 'b', 'c'], format.C45_FORMAT.get_values('foo:a,b,c'))
    
    def test_attribute_creation(self):
        attributes = format.C45_FORMAT.get_attributes(datasetsDir(self) + 'numerical' + SEP + 'person')
        self.assertEqual(8, len(attributes), '8 attributes should be present')
        self.assertEqual(a.Attribute('id', ['continuous'], 0), attributes[0])
        self.assertEqual(a.Attribute('creditrating', ['continuous'], 7), attributes[7])

    def test_training_intances_creation(self):
        instances = format.C45_FORMAT.get_training_instances(datasetsDir(self) + 'numerical' + SEP + 'person')
        self.assertEqual(6, len(instances), '6 instances should be present')
        self.assertEqual(ins.TrainingInstance(['0','25','salaried','single','0','0','65000','3'],'yes'), instances[0])
        self.assertEqual(ins.TrainingInstance(['5','42','salaried','married','2','6','65000','6'],'no'), instances[5])

    def test_test_intances_creation(self):
        instances = format.C45_FORMAT.get_test_instances(datasetsDir(self) + 'numerical' + SEP + 'weather')
        self.assertEqual(1, len(instances), '1 instance should be present')
        self.assertEqual(ins.TestInstance(['overcast','25.4','high','true']), instances[0])

    def test_gold_intances_creation(self):
        instances = format.C45_FORMAT.get_gold_instances(datasetsDir(self) + 'numerical' + SEP + 'weather')
        self.assertEqual(4, len(instances), '4 instances should be present')
        self.assertEqual(ins.GoldInstance(['sunny','21','normal','true'],'yes'), instances[0])
        self.assertEqual(ins.GoldInstance(['rainy','17.9','high','true'],'no'), instances[3])
        
    def test_klass_creation(self):
        klass = format.C45_FORMAT.get_klass(datasetsDir(self) + 'numerical' + SEP + 'weather')
        self.assertEqual(2, len(klass))
        self.assertEqual(['yes', 'no'], klass)

if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(unittest.TestSuite(unittest.makeSuite(FormatTestCase)))
