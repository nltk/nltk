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
        self.assertTrue(_range.includes(4))
        self.assertFalse(_range.includes(4.1))
        
        _new_range = range.Range(0, 4, False)
        self.assertFalse(_new_range.includes(4))
        self.assertTrue(_new_range.includes(3.9999))
                
    def test_range_equality(self):
        _range = range.Range(0, 4)
        _same = range.Range(0, 4)
        self.assertEqual(_range, _same)
        self.assertEqual(hash(_range), hash(_same))
        _other = range.Range(0, 4.1)
        self.assertNotEqual(_range, _other)
        
    def test_include_expands_range(self):
        _range = range.Range(0, 4)
        self.assertTrue(_range.includes(0))
        self.assertTrue(_range.includes(1))
        self.assertTrue(_range.includes(4))
        self.assertFalse(_range.includes(4.1))
        _range.include(5)
        self.assertTrue(_range.includes(4.1))
        self.assertTrue(_range.includes(5))


        