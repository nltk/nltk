# Natural Language Toolkit - Discretise
#  The command line entry point to discretisers
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT
from nltk_lite.contrib.classifier_tests import *
from nltk_lite.contrib.classifier import discretise

class DiscretiseTestCase(unittest.TestCase):
    def test_decodes_algorithm_training_other_files_attributes_options(self):
        disc = discretise.Discretise()
        disc.parse(['-a', 'UEW', '-t', 'path', '-T', 'path1,path2', '-A', '3,4,5', '-o', '3,2,4'])
        algorithm = disc.values.ensure_value('algorithm', None)
        training = disc.values.ensure_value('training', None)
        test = disc.values.ensure_value('test', None)
        attributes = disc.values.ensure_value('attributes', None)
        options = disc.values.ensure_value('options', None)
        
        self.assertEqual('UEW', algorithm)
        self.assertEqual('path', training)
        self.assertEqual('path1,path2', test)
        self.assertEqual('3,4,5', attributes)
        self.assertEqual('3,2,4', options)
        
    def test_throws_error_when_any_of_the_attributes_are_missing(self):
        path = datasetsDir(self) + SEP + 'numerical' + SEP + 'person'
        disc = MockDiscretise()
        self.assertFalse(disc.error_called)
        disc.parse(['-a', 'UEW', '-t', path, '-T', path + '.test,' + path + 'extra.test', '-A', '3,4,5'])
        disc.execute()
        self.assertTrue(disc.error_called)
        self.assertEqual('Invalid arguments. One or more required arguments are not present.', disc.message)
        

class MockDiscretise(discretise.Discretise):
    def __init__(self):
        discretise.Discretise.__init__(self)
        self.error_called = False
        self.invoke_called = False
        self.message = None
        
    def error(self, message):
        #in reality error will display usage and quit
        self.message = message
        self.error_called = True
        
    def invoke(self, training, test, attributes, options, algorithm):
        #do nothing
        pass
