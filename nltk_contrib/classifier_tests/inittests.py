# Natural Language Toolkit - Format tests
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://www.nltk.org/>
# This software is distributed under GPL, for license information see LICENSE.TXT
from nltk_contrib.classifier_tests import *
from nltk_contrib.classifier import *
from nltk.probability import FreqDist

class InitTestCase(unittest.TestCase):
    def test_split_file_names(self):
        returnvalue = split_ignore_space('foo , bar, foobar')
        self.assertEqual(3, len(returnvalue))
        self.assertEqual(['foo', 'bar', 'foobar'], returnvalue)

    def test_entropy_of_elements(self):
        e = entropy(['yes', 'no', 'yes', 'yes', 'yes', 'no'])
        self.assertEqual(-1 * (4.0/6 * math.log( 4.0/6, 2) + 2.0/6 * math.log(2.0/6, 2)), e)
    
    def test_min_entropy_breakpoint(self):
        position, min_ent = min_entropy_breakpoint(['yes', 'no', 'yes', 'yes', 'yes', 'no'])
        self.assertEqual(4, position)
        self.assertEqual(-1 * (4.0/5 * math.log(4.0/5, 2) + 1.0/5 * math.log(1.0/5, 2)), min_ent)
        
    def test_entropy_function(self):
        dictionary_of_klass_counts = {}
        dictionary_of_klass_counts['yes'] = 2
        dictionary_of_klass_counts['no'] = 0
        self.assertEqual(0, entropy_of_key_counts(dictionary_of_klass_counts))
        
        dictionary_of_klass_counts['yes'] = 3
        dictionary_of_klass_counts['no'] = 3
        self.assertAlmostEqual(1, entropy_of_key_counts(dictionary_of_klass_counts))
        
        dictionary_of_klass_counts['yes'] = 9
        dictionary_of_klass_counts['no'] = 5
        self.assertAlmostEqual(0.94, entropy_of_key_counts(dictionary_of_klass_counts), 2)
        
        dictionary_of_klass_counts['yes'] = 1
        dictionary_of_klass_counts['no'] = 3
        expected = -(1.0/4 * math.log(1.0/4, 2)) + -(3.0/4 * math.log(3.0/4, 2))
        self.assertAlmostEqual(expected, entropy_of_key_counts(dictionary_of_klass_counts), 6)

        dictionary_of_klass_counts['yes'] = 2
        dictionary_of_klass_counts['no'] = 1
        expected = -(2.0/3 * math.log(2.0/3, 2))  + -(1.0/3 * math.log(1.0/3, 2))
        self.assertAlmostEqual(expected, entropy_of_key_counts(dictionary_of_klass_counts), 6)

    def test_entropy_of_freq_dist(self):
        fd = FreqDist()
        fd.inc('yes', 2)
        fd.inc('no', 1)
        expected = -(2.0/3 * math.log(2.0/3, 2))  + -(1.0/3 * math.log(1.0/3, 2))
        self.assertAlmostEqual(expected, entropy_of_freq_dist(fd), 6)
