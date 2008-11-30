# Natural Language Toolkit CommandLine
#     understands the command line interaction
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://www.nltk.org/>
# This software is distributed under GPL, for license information see LICENSE.TXT
from nltk_contrib.classifier_tests import *
from nltk_contrib.classifier import commandline as cl

class CommandLineTestCase(unittest.TestCase):
    def test_converts_an_array_into_integer_array(self):
        returned = cl.as_integers('Foo', None)
        self.assertEqual([], returned)
        
        returned = cl.as_integers('Foo', '3,5, 7, 9')
        self.assertEqual([3, 5, 7, 9], returned)
        
