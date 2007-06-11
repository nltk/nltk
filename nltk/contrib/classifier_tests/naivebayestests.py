# Natural Language Toolkit
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk.contrib.classifier import instances as ins, instance, attribute as a, naivebayes, format
from nltk.contrib.classifier_tests import *

class NaiveBayesTestCase(unittest.TestCase):
    def test_naive_bayes_classification(self):
        path = datasetsDir(self) + 'loan' + SEP + 'loan'
        training = format.C45_FORMAT.get_training_instances(path)
        attributes = format.C45_FORMAT.get_attributes(path)
        test = format.C45_FORMAT.get_test_instances(path)
        klass = format.C45_FORMAT.get_klass(path)
        nb = naivebayes.NaiveBayes(training, attributes, klass)
        nb.test(test)
        self.assertEqual('no', test[0].classified_klass)
        
        self.assertAlmostEqual(0.5555555, nb.post_probs.value(attributes[0], 'no', 'no'), 6)
