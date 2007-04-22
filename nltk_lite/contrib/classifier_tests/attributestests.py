# Natural Language Toolkit
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk_lite.contrib.classifier import attribute as a, discretisedattribute as da, numrange as nr, format
from nltk_lite.contrib.classifier_tests import *

class AttributesTestCase(unittest.TestCase):
    def setUp(self):
        self.attrs = format.C45_FORMAT.get_attributes(datasetsDir(self) + 'test_phones' + SEP + 'phoney')    
    
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
        self.assertTrue(self.attrs.__contains__(a.Attribute('band', ['dual','tri','quad'], 0)))

    def test_attributes_are_equal(self):
        attrs = a.Attributes([a.Attribute('band', ['dual','tri','quad'], 0), a.Attribute('size', ['big','small','medium'], 1)])
        same = a.Attributes([a.Attribute('band', ['dual','tri','quad'], 0), a.Attribute('size', ['big','small','medium'], 1)])
        self.assertEqual(attrs, same, 'they should be the same')
        other = a.Attributes([a.Attribute('band', ['dual','tri','quad'], 0), a.Attribute('pda', ['y','n'], 1)])
        self.assertNotEqual(self.attrs, other, 'shouldnt be the same')

    def test_index_stored_in_attributes(self):
        for i in range(len(self.attrs)):
            self.assertEqual(i, self.attrs[i].index)

    def test_has_continuous_attibutes_returns_true_if_even_1_attr_is_cont(self):
        has_cont = format.C45_FORMAT.get_attributes(datasetsDir(self) + 'numerical' + SEP + 'weather')
        self.assertTrue(has_cont.has_continuous_attributes())
        
        all_disc = format.C45_FORMAT.get_attributes(datasetsDir(self) + 'test_phones' + SEP + 'phoney')
        self.assertFalse(all_disc.has_continuous_attributes())
        
    def test_does_not_check_continuous_attribute_for_validity(self):
        has_cont = format.C45_FORMAT.get_attributes(datasetsDir(self) + 'numerical' + SEP + 'weather')
        self.assertTrue(has_cont.has_values(['sunny','21','normal','true']))
        
    def test_return_subset_as_requested_by_index_array(self):
        attrs = format.C45_FORMAT.get_attributes(datasetsDir(self) + 'numerical' + SEP + 'person')
        subset = attrs.subset([2, 4, 5])
        self.assertEqual(3, len(subset))
        self.assertEqual(2, subset[0].index)
        self.assertEqual(4, subset[1].index)
        self.assertEqual(5, subset[2].index)

    def test_discretise_replaces_cont_attrs_in_args_with_disc_ones(self):
        attrs = format.C45_FORMAT.get_attributes(datasetsDir(self) + 'numerical' + SEP + 'person')
        self.assertTrue(attrs[0].is_continuous())
        self.assertTrue(attrs[4].is_continuous())
        self.assertTrue(attrs[6].is_continuous())
        self.assertTrue(attrs[7].is_continuous())
        
        attrs.discretise([da.DiscretisedAttribute('dependents', nr.Range(0, 2, True).split(2), 4), \
                          da.DiscretisedAttribute('annualincome', nr.Range(0, 120000, True).split(5), 6)])
        
        self.assertFalse(attrs[4].is_continuous())
        self.assertFalse(attrs[6].is_continuous())
        
        self.assertTrue(attrs[0].is_continuous())
        self.assertTrue(attrs[7].is_continuous())
        
        self.assertEqual(['a', 'b'], attrs[4].values)
        self.assertEqual(['a', 'b', 'c', 'd', 'e'], attrs[6].values)
        
if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(unittest.TestSuite(unittest.makeSuite(AttributesTestCase)))
