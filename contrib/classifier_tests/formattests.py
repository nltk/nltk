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
        
    def test_classified_klass_in_gold_is_not_written_if_asked_not_to(self):
        gold = format.C45_FORMAT.get_gold_instances(datasetsDir(self) + 'numerical' + SEP + 'weather')
        fmt = C45FormatStub()
        self.assertTrue(fmt.dummy_file is None)
        fmt.write_gold_to_file(gold, '/dummy/path')
        self.assertFalse(fmt.dummy_file is None)
        self.assertEqual(len(gold), len(fmt.dummy_file.lines_written))
        self.assertEqual(['sunny,21,normal,true,yes,None', 'overcast,18,high,true,yes,None', 'overcast,28.3,notmal,false,yes,None', 'rainy,17.9,high,true,no,None'], fmt.dummy_file.lines_written)
        
        fmt = C45FormatStub()
        fmt.write_gold_to_file(gold, '/dummy/path', False)
        self.assertEqual(['sunny,21,normal,true,yes', 'overcast,18,high,true,yes', 'overcast,28.3,notmal,false,yes', 'rainy,17.9,high,true,no'], fmt.dummy_file.lines_written)

    def test_classified_klass_in_test_is_not_written_if_asked_not_to(self):
        test = format.C45_FORMAT.get_test_instances(datasetsDir(self) + 'numerical' + SEP + 'weather')
        fmt = C45FormatStub()
        self.assertTrue(fmt.dummy_file is None)
        fmt.write_test_to_file(test, '/dummy/path')
        self.assertFalse(fmt.dummy_file is None)
        self.assertEqual(len(test), len(fmt.dummy_file.lines_written))
        self.assertEqual(['overcast,25.4,high,true,None'], fmt.dummy_file.lines_written)
        
        fmt = C45FormatStub()
        fmt.write_test_to_file(test, '/dummy/path', False)
        self.assertEqual(['overcast,25.4,high,true'], fmt.dummy_file.lines_written)

if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(unittest.TestSuite(unittest.makeSuite(FormatTestCase)))

class C45FormatStub(format.C45Format):
    def __init__(self):
        self.dummy_file = None
        
    def create_file(self, path, extension):
        self.dummy_file = LinesFile()
        return self.dummy_file
        
class LinesFile:
    def __init__(self):
        self.lines_written = None
    
    def write(self, lines):
        self.lines_written = lines