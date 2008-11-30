# Natural Language Toolkit Discretized attribute tests
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://www.nltk.org/>
# This software is distributed under GPL, for license information see LICENSE.TXT
from nltk_contrib.classifier import discretisedattribute as da, numrange as nr, attribute as attr
from nltk_contrib.classifier.exceptions import invaliddataerror as inv
from nltk_contrib.classifier_tests import *

class DiscretisedAttributeTestCase(unittest.TestCase):
    def test_binary_search(self):
        ranges = [nr.Range(2, 4), nr.Range(4, 6), nr.Range(6, 8), nr.Range(8, 10, True)]
        self.assertEqual(0, da.binary_search(ranges, 2))
        self.assertEqual(1, da.binary_search(ranges, 4))
        self.assertEqual(3, da.binary_search(ranges, 10))
        self.assertEqual(-1, da.binary_search(ranges, 1))
        self.assertEqual(-1, da.binary_search(ranges, 11))
        
        ranges = [nr.Range(2, 4), nr.Range(4, 6), nr.Range(6, 8, True)]
        self.assertEqual(-1, da.binary_search(ranges, 9))
        self.assertEqual(2, da.binary_search(ranges, 8))
        
        ranges = nr.Range(6, 32, True).split(3)
        self.assertEqual(0, da.binary_search(ranges, 12))
        
        ranges = nr.Range(0, 2, True).split(2)
        self.assertEqual(0, da.binary_search(ranges, 0))
        
    def test_creates_class_values_for_ranges(self):
        ranges = nr.Range(-10, 40, True).split(5)
        disc_attr = da.DiscretisedAttribute('temperature', ranges, 1)
        self.assertEqual('temperature', disc_attr.name)
        self.assertEqual(['a', 'b', 'c', 'd', 'e'], disc_attr.values)
        self.assertEqual(ranges, disc_attr.ranges)
        self.assertEqual(1, disc_attr.index)
        self.assertEqual(attr.DISCRETE, disc_attr.type)
        
    def test_maps_continuous_value_to_correct_discretised_equivalent(self):
        ranges = nr.Range(-10, 40, True).split(5)
        disc_attr = da.DiscretisedAttribute('temperature', ranges, 1)
        self.assertEqual('a', disc_attr.mapping(-10))
        self.assertEqual('b', disc_attr.mapping(0))
        self.assertEqual('b', disc_attr.mapping(1))
        self.assertEqual('c', disc_attr.mapping(10))
        self.assertEqual('e', disc_attr.mapping(40))
        
    def test_finding_mapping_for_value_out_of_range_returns_nearest_match(self):
        ranges = nr.Range(-10, 40, True).split(5)
        disc_attr = da.DiscretisedAttribute('temperature', ranges, 1)
        self.assertEqual('e', disc_attr.mapping(50))
        self.assertEqual('a', disc_attr.mapping(-20))
        

