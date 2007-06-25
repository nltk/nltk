# Natural Language Toolkit - NaiveBayes
#  Capable of classifying the test or gold data using Naive Bayes algorithm
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk.contrib.classifier import instances as ins, decisionstump as ds, Classifier
from nltk.contrib.classifier.exceptions import invaliddataerror as inv

class NaiveBayes(Classifier):
    def __init__(self, training, attributes, klass, internal = False):
        Classifier.__init__(self, training, attributes, klass, internal)
        self.post_probs = self.training.posterior_probablities(self.attributes, self.klass)
        self.class_freq_dist = self.training.class_freq_dist()
        for klass_value in self.klass:
            self.class_freq_dist.inc(klass_value)#laplacian smoothing
            
    def classify(self, instances):
        for instance in instances:
            est_klass_value = self.estimate_klass(instance)
            instance.set_klass(est_klass_value)

    def estimate_klass(self, instance):
        estimates_using_prob = {}
        for klass_value in self.klass:
            class_cond_prob = 1.0
            for attribute in self.attributes:
                attr_value = instance.value(attribute)
                post_prob = self.post_probs.value(attribute, attr_value, klass_value)
                class_cond_prob *= post_prob
            prior_prob = self.class_freq_dist.freq(klass_value)
            estimates_using_prob[class_cond_prob * prior_prob] = klass_value
        keys = estimates_using_prob.keys()
        keys.sort()#find the one with max conditional prob
        return estimates_using_prob[keys[-1]]
    
    def can_handle_continuous_attributes(self):
        return True
    can_handle_continuous_attributes = classmethod(can_handle_continuous_attributes)
        
        
