# Natural Language Toolkit
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk_contrib.classifier import instances as ins, instance, attribute as a, naivebayes, format
from nltk_contrib.classifier_tests import *

class NaiveBayesTestCase(unittest.TestCase):
    def setUp(self):
        path = datasetsDir(self) + 'loan' + SEP + 'loan'
        self.training = format.C45_FORMAT.get_training_instances(path)
        self.attributes = format.C45_FORMAT.get_attributes(path)
        self.test = format.C45_FORMAT.get_test_instances(path)
        self.klass = format.C45_FORMAT.get_klass(path)
        self.nb = naivebayes.NaiveBayes(self.training, self.attributes, self.klass)    
        
    def test_naive_bayes_classification(self):
        self.nb.train()
        self.nb.test(self.test)
        self.assertEqual('no', self.test[0].classified_klass)
        
        self.assertAlmostEqual(0.5555555, self.nb.post_probs.value(self.attributes[0], 'no', 'no'), 6)
        
    def test_prior_probability_calculations(self):
        self.nb.train()
        self.assertAlmostEqual((7.0 + 1.0)/(10 + 2), self.nb.prior_probability('no'), 6)
        self.assertAlmostEqual((3.0 + 1.0)/(10 + 2), self.nb.prior_probability('yes'), 6)
        
    def test_posterior_probability_calculations(self):
        self.nb.train()
        self.assertAlmostEqual((2.0 + 1.0)/(4 + 2), self.nb.posterior_probability(self.attributes[1], 'single', 'no'), 6)
        self.assertAlmostEqual((2.0 + 1.0)/(4 + 2), self.nb.posterior_probability(self.attributes[1], 'single', 'yes'), 6)
        self.assertAlmostEqual((4.0 + 1.0)/(4 + 2), self.nb.posterior_probability(self.attributes[1], 'married', 'no'), 6)
        self.assertAlmostEqual((0 + 1.0)/(4 + 2), self.nb.posterior_probability(self.attributes[1], 'married', 'yes'), 6)
        self.assertAlmostEqual((1.0 + 1.0)/(2 + 2), self.nb.posterior_probability(self.attributes[1], 'divorced', 'no'), 6)
        self.assertAlmostEqual((1.0 + 1.0)/(2 + 2), self.nb.posterior_probability(self.attributes[1], 'divorced', 'yes'), 6)
        
    def test_class_conditional_probability(self):
        #sunny,hot,high,false,no
        #sunny,hot,high,true,no
        #overcast,hot,high,false,yes
        #rainy,mild,high,false,yes
        #rainy,cool,normal,false,yes
        #rainy,cool,normal,true,no
        #overcast,cool,normal,true,yes
        #sunny,mild,high,false,no
        #sunny,cool,normal,false,yes
        nominal_path = datasetsDir(self) + 'minigolf' + SEP + 'weather'
        training = format.C45_FORMAT.get_training_instances(nominal_path)
        attributes = format.C45_FORMAT.get_attributes(nominal_path)
        klass = format.C45_FORMAT.get_klass(nominal_path)
        test = format.C45_FORMAT.get_test_instances(nominal_path)
        nb = naivebayes.NaiveBayes(training, attributes, klass)    
        
        nb.train()
        #test[0] = overcast,mild,high,true
        expected_no = ((0 + 1.0)/(2 + 2)) * ((1.0 + 1.0)/ (2 + 2)) * ((3.0 + 1.0) / (5 + 2)) * ((2.0 + 1.0)/ (3 + 2))
        self.assertAlmostEqual(expected_no, nb.class_conditional_probability(test[0], 'no'), 6)
        
        expected_yes = ((2.0 + 1.0)/(2 + 2)) * ((1.0 + 1.0)/ (2 + 2)) * ((2.0 + 1.0) / (5 + 2)) * ((1.0 + 1.0)/ (3 + 2))
        self.assertAlmostEqual(expected_yes, nb.class_conditional_probability(test[0], 'yes'), 6)
        