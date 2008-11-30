# Natural Language Toolkit - Attribute
#  can extract the name and values from a line and operate on them
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://www.nltk.org/>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk_contrib.classifier import autoclass
from nltk_contrib.classifier_tests import *

class AutoClassTestCase(unittest.TestCase):
    def test_base26(self):
        self.assertEqual(0, autoclass.FIRST.base26())
        self.assertEqual(25, autoclass.AutoClass('z').base26())
        self.assertEqual(26, autoclass.AutoClass('ba').base26())
        self.assertEqual(0, autoclass.AutoClass('aaa').base26())
        self.assertEqual(26 * 3, autoclass.AutoClass('baaa').base26())
        
    def test_string(self):
        self.assertEqual('a', autoclass.string(0))
        self.assertEqual('z', autoclass.string(25))
        self.assertEqual('ba', autoclass.string(26))
        self.assertEqual('bb', autoclass.string(27))
    
    def test_next(self):
        a = autoclass.FIRST
        b = a.next()
        self.assertEqual('b', str(b))    
        self.assertEqual('c', str(b.next()))    
        self.assertEqual('z', self.next('y'))    
        self.assertEqual('ba', self.next('z'))    
        self.assertEqual('bb', self.next('ba'))
        self.assertEqual('bc', self.next('bb'))    
        self.assertEqual('ca', self.next('bz'))
        self.assertEqual('baa', self.next('zz'))
        
    def next(self, current):
        return str(autoclass.AutoClass(current).next())
