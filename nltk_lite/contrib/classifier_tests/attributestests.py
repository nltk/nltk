# Natural Language Toolkit
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk_lite.contrib.classifier import attributes as a, attribute as attr
from nltk_lite.contrib.classifier_tests import *

class AttributesTestCase(unittest.TestCase):
    def setUp(self):
        #make sure you run all tests from the tests directory
        self.attrs = a.Attributes(datasetsDir(self) + 'test_phones' + SEP + 'phoney')    
    
    def test_counts_correct_number_of_attributes(self):
        self.assertEqual(5, len(self.attrs), 'there should be 5 attributes')
        
    def test_attributes_are_valid(self):
        self.assertTrue(self.attrs.has_values(['dual', 'big', 'symbian', 'y', 'y']))

    def test_attributes_are_in_order(self):
        self.assertEqual('band', self.attrs[0].name)
        self.assertEqual('size', self.attrs[1].name)
        self.assertEqual('os', self.attrs[2].name)
        self.assertEqual('pda', self.attrs[3].name)
        self.assertEqual('mp3', self.attrs[4].name)
        
    def test_attributes_contain_an_attribute(self):
        self.assertTrue(self.attrs.__contains__(attr.Attribute('band:dual,tri,quad', 0)))

    def test_attributes_are_equal(self):
        same = a.Attributes(datasetsDir(self) + 'test_phones' + SEP + 'phoney')
        self.assertEqual(self.attrs, same, 'they should be the same')
        other = a.Attributes(datasetsDir(self) + 'test_faulty' + SEP + 'invalid_attributes')
        self.assertNotEqual(self.attrs, other, 'shouldnt be the same')

    def test_index_stored_in_attributes(self):
        for i in range(len(self.attrs)):
            self.assertEqual(i, self.attrs[i].index)

    def test_has_continuous_attibutes_returns_true_if_even_1_attr_is_cont(self):
        has_cont = a.Attributes(datasetsDir(self) + 'numerical' + SEP + 'weather')
        self.assertTrue(has_cont.has_continuous_attributes())
        
        all_disc = a.Attributes(datasetsDir(self) + 'test_phones' + SEP + 'phoney')
        self.assertFalse(all_disc.has_continuous_attributes())
        
    def test_does_not_check_continuous_attribute_for_validity(self):
        has_cont = a.Attributes(datasetsDir(self) + 'numerical' + SEP + 'weather')
        self.assertTrue(has_cont.has_values(['sunny','21','normal','true']))
        
if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(unittest.TestSuite(unittest.makeSuite(AttributesTestCase)))
