# Natural Language Toolkit - NaiveBayes
#  Capable of classifying the test or gold data using Naive Bayes algorithm
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk_lite.contrib.classifier import instances as ins, decisionstump as ds, Classifier
from nltk_lite.contrib.classifier.exceptions import invaliddataerror as inv

class NaiveBayes(Classifier):
    def __init__(self, training, attributes, klass, internal = False):
        Classifier.__init__(self, training, attributes, klass, internal)
        self.post_probs = self.training.posterior_probablities(self.attributes, self.klass)
        class_freq_dist = self.training.class_freq_dist()
        for klass_value in self.klass:
            class_freq_dist.inc(klass_value)#laplacian smoothing
        self.pri_probs = class_freq_dist
        
    def test(self, test_intances):
        self.classify(test_intances)
    
    def verify(self, gold_instances):
        self.classify(gold_instances)
        return gold_instances.confusion_matrix(self.klass)
    
    def classify(self, instances):
        self.convert_continuous_values_to_numbers(instances)
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
            estimates_using_prob[class_cond_prob * self.pri_probs.freq(klass_value)    ] = klass_value
        keys = estimates_using_prob.keys()
        keys.sort()#find the one with max conditional prob
        return estimates_using_prob[keys[-1]]
    
    def can_handle_continuous_attributes(self):
        return True
    can_handle_continuous_attributes = classmethod(can_handle_continuous_attributes)
        
        
