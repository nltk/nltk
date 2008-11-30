# Natural Language Toolkit - NaiveBayes
#  Capable of classifying the test or gold data using Naive Bayes algorithm
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://www.nltk.org/>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk_contrib.classifier import instances as ins, decisionstump as ds, Classifier
from nltk_contrib.classifier.exceptions import invaliddataerror as inv

class NaiveBayes(Classifier):
    def __init__(self, training, attributes, klass):
        Classifier.__init__(self, training, attributes, klass)
        self.post_probs, self.class_freq_dist = None, None
        
    def train(self):
        Classifier.train(self)
        self.post_probs = self.training.posterior_probablities(self.attributes, self.klass)
        self.class_freq_dist = self.training.class_freq_dist()
        for klass_value in self.klass:
            self.class_freq_dist.inc(klass_value)#laplacian smoothing
            
    def classify(self, instances):
        for instance in instances:
            instance.classified_klass = self.estimate_klass(instance)

    def estimate_klass(self, instance):
        estimates_using_prob = {}
        for klass_value in self.klass:
            class_conditional_probability = self.class_conditional_probability(instance, klass_value)
            estimates_using_prob[class_conditional_probability] = klass_value
        keys = estimates_using_prob.keys()
        keys.sort()#find the one with max conditional prob
        return estimates_using_prob[keys[-1]]
    
    def prior_probability(self, klass_value):
        return self.class_freq_dist.freq(klass_value)
    
    def posterior_probability(self, attribute, attribute_value, klass_value):
        return self.post_probs.value(attribute, attribute_value, klass_value)
    
    def class_conditional_probability(self, instance, klass_value):
        class_cond_prob = 1.0
        for attribute in self.attributes:
            attr_value = instance.value(attribute)
            class_cond_prob *= self.posterior_probability(attribute, attr_value, klass_value)
        class_cond_prob *= self.prior_probability(klass_value)
        return class_cond_prob
    
    @classmethod
    def can_handle_continuous_attributes(self):
        return True
        
    def is_trained(self):
        return self.post_probs is not None and self.class_freq_dist is not None    
    
