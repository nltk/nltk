# Natural Language Toolkit
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://www.nltk.org/>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk_contrib.classifier import instances as ins, instance, attribute as a, naivebayes
from nltk_contrib.classifier_tests import *

class NaiveBayesTestCase(unittest.TestCase):
    def setUp(self):
        path = datasetsDir(self) + 'loan' + SEP + 'loan'
        self._training = training(path)
        self._attributes, self._klass = metadata(path)
        self._test = test(path)
        self.nb = naivebayes.NaiveBayes(self._training, self._attributes, self._klass)    
        
    def test_naive_bayes_classification(self):
        self.nb.train()
        self.nb.test(self._test)
        self.assertEqual('no', self._test[0].classified_klass)
        
        self.assertAlmostEqual(0.5555555, self.nb.post_probs.value(self._attributes[0], 'no', 'no'), 6)
        
    def test_prior_probability_calculations(self):
        self.nb.train()
        self.assertAlmostEqual((7.0 + 1.0)/(10 + 2), self.nb.prior_probability('no'), 6)
        self.assertAlmostEqual((3.0 + 1.0)/(10 + 2), self.nb.prior_probability('yes'), 6)
        
    def test_posterior_probability_calculations(self):
        self.nb.train()
        self.assertAlmostEqual((2.0 + 1.0)/(4 + 2), self.nb.posterior_probability(self._attributes[1], 'single', 'no'), 6)
        self.assertAlmostEqual((2.0 + 1.0)/(4 + 2), self.nb.posterior_probability(self._attributes[1], 'single', 'yes'), 6)
        self.assertAlmostEqual((4.0 + 1.0)/(4 + 2), self.nb.posterior_probability(self._attributes[1], 'married', 'no'), 6)
        self.assertAlmostEqual((0 + 1.0)/(4 + 2), self.nb.posterior_probability(self._attributes[1], 'married', 'yes'), 6)
        self.assertAlmostEqual((1.0 + 1.0)/(2 + 2), self.nb.posterior_probability(self._attributes[1], 'divorced', 'no'), 6)
        self.assertAlmostEqual((1.0 + 1.0)/(2 + 2), self.nb.posterior_probability(self._attributes[1], 'divorced', 'yes'), 6)
        
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
        _training = training(nominal_path)
        _attributes = attributes(nominal_path)
        _klass = klass(nominal_path)
        _test = test(nominal_path)
        nb = naivebayes.NaiveBayes(_training, _attributes, _klass)    
        
        nb.train()
        #test[0] = overcast,mild,high,true
        expected_no = ((0 + 1.0)/(2 + 2)) * ((1.0 + 1.0)/(2 + 2)) * ((3.0 + 1.0)/(5 + 2)) * ((2.0 + 1.0)/(3 + 2)) * ((4.0 + 1.0)/(9 + 2))
        self.assertAlmostEqual(expected_no, nb.class_conditional_probability(_test[0], 'no'), 6)
        
        expected_yes = ((2.0 + 1.0)/(2 + 2)) * ((1.0 + 1.0)/(2 + 2)) * ((2.0 + 1.0)/(5 + 2)) * ((1.0 + 1.0)/(3 + 2)) * ((5.0 + 1.0)/(9 + 2))
        self.assertAlmostEqual(expected_yes, nb.class_conditional_probability(_test[0], 'yes'), 6)
                
    def test_expected_class(self):
        nominal_path = datasetsDir(self) + 'minigolf' + SEP + 'weather'
        _training = training(nominal_path)
        _attributes = attributes(nominal_path)
        _klass = klass(nominal_path)
        _test = test(nominal_path)
        nb = naivebayes.NaiveBayes(_training, _attributes, _klass)    

        nb.train()
        
        self.assertEqual('yes', nb.estimate_klass(_test[0]))
