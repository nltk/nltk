# Natural Language Toolkit
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT
from nltk.contrib.classifier.exceptions import invaliddataerror as inv
from nltk import probability as prob
import math

class Classifier:
    def __init__(self, training, attributes, klass, internal):
        """
        The internal parameter is to used only internally while operating on datasets while selecting features.
        When classifiers are invoked from command line this parameter is set to the default value of False.
        """
        self.attributes = attributes
        self.training = training
        self.internal = internal
        self.convert_continuous_values_to_numbers(self.training)
        sorted_klass_values = self.training.class_freq_dist().sorted_samples()
        for each in klass:
            if not sorted_klass_values.__contains__(each):
                sorted_klass_values.append(each)
        self.klass = sorted_klass_values
        if not self.internal:
            self.validate_training()
        
    def convert_continuous_values_to_numbers(self, instances):
        if self.attributes.has_continuous():
            instances.convert_to_float(self.attributes.continuous_attribute_indices())
        
    def validate_training(self):
        if not self.training.are_valid(self.klass, self.attributes): 
            raise inv.InvalidDataError('Training data invalid.')
        if not self.can_handle_continuous_attributes() and self.attributes.has_continuous(): 
            raise inv.InvalidDataError('One or more attributes are continuous.')
    
    def test(self, test_instances):
        self.convert_continuous_values_to_numbers(test_instances)
        self.test_instances = test_instances
        self.classify(self.test_instances)
            
    def verify(self, gold_instances):
        self.convert_continuous_values_to_numbers(gold_instances)
        self.gold_instances = gold_instances
        self.classify(self.gold_instances)
        return self.gold_instances.confusion_matrix(self.klass)
    
    def classify(self, instances):
        AssertionError('Classify called on abstract class')
    
    def can_handle_continuous_attributes(klass):
        return False
    can_handle_continuous_attributes = classmethod(can_handle_continuous_attributes)

def split_ignore_space(comma_sep_string):
    _file_names = []
    for name in comma_sep_string.split(','):
        _file_names.append(name.strip())
    return _file_names

def min_entropy_breakpoint(values):
    position, min_entropy = 0, None
    for index in range(len(values) -1):
        first, second = values[:index + 1], values[index + 1:]
        e = entropy(first) + entropy(second)
        if min_entropy is None: min_entropy = e
        if e < min_entropy: min_entropy, position = e, index
    return [position, min_entropy]
    
def entropy(values):
    freq_dist = prob.FreqDist()
    for value in values: freq_dist.inc(value)
    return entropy_of_freq_dist(freq_dist)

def entropy_of_key_counts(dictionary):
    freq_dist = prob.FreqDist()
    klasses = dictionary.keys()
    for klass in klasses:
        freq_dist.inc(klass, dictionary[klass])
    return entropy_of_freq_dist(freq_dist)

def entropy_of_freq_dist(freq_dist):
    sum = 0
    for sample in freq_dist.samples():
        freq = freq_dist.freq(sample)
        sum += (freq * math.log(freq, 2))
    return sum *  -1
    
