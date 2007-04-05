# Natural Language Toolkit - RangeTest
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
from nltk_lite.contrib.classifier import range
from nltk_lite.contrib.classifier_tests import *

class RangeTestCase(unittest.TestCase):
    def test_within_range(self):
        _range = range.Range(0, 4)
        self.assertTrue(_range.includes(0))
        self.assertTrue(_range.includes(1))
        self.assertTrue(_range.includes(3))
        self.assertTrue(_range.includes(3.9999))
        self.assertFalse(_range.includes(4))
        self.assertFalse(_range.includes(4.1))
        
        _new_range = range.Range(0, 4, True)
        self.assertTrue(_new_range.includes(4))
        self.assertFalse(_range.includes(4.1))
                
    def test_range_equality(self):
        _range = range.Range(0, 4)
        _same = range.Range(0, 4)
        self.assertEqual(_range, _same)
        self.assertEqual(hash(_range), hash(_same))
        _other = range.Range(0, 4.1)
        self.assertNotEqual(_range, _other)
        
    def test_include_expands_range(self):
        _range = range.Range()
        _range.include(4)
        self.assertTrue(_range.includes(0))
        self.assertTrue(_range.includes(1))
        self.assertTrue(_range.includes(4))
        
        _other = range.Range(0, 4)
        self.assertTrue(_range, _other)
        _same = range.Range(0, 4, True)
        self.assertTrue(_range, _same)
        
        _other.include(4)
        self.assertEqual(0, _other.lower)
        self.assertEqual(4.000001, _other.upper)
        
        _range.include(5)
        self.assertTrue(_range.includes(4.1))
        self.assertTrue(_range.includes(5))
        
    def test_split_returns_none_when_lower_eq_upper(self):
        _range = range.Range()
        self.assertEquals(None, _range.split(2))
        
    def test_split_returns_none_if_size_of_each_split_is_less_than_delta(self):
        _range = range.Range(0, 0.000005)
        self.assertEquals(None, _range.split(7))
        
    def test_split_includes_the_highest_and_lowest(self):
        _range = range.Range()
        _range.include(4)
        splits = _range.split(4)
        self.assertEqual(0, splits[0].lower)
        self.assertEqual(1, splits[0].upper)
        self.assertEqual(1, splits[1].lower)
        self.assertEqual(2, splits[1].upper)
        self.assertEqual(2, splits[2].lower)
        self.assertEqual(3, splits[2].upper)
        self.assertEqual(3, splits[3].lower)
        self.assertEqual(4.000001, splits[3].upper)
        


        