# Natural Language Toolkit
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT
from nltk_lite.contrib.classifier.exceptions import invaliddataerror as inv
from nltk_lite import probability as prob
import math

class Classifier:
    def __init__(self, training, attributes, klass, internal):
        self.attributes = attributes
        self.klass = klass
        self.training = training
        self.internal = internal
        if not self.internal:
            self.validate_training()
        
    def validate_training(self):
        if not self.training.are_valid(self.klass, self.attributes): 
            raise inv.InvalidDataError('Training data invalid.')
        if not self.can_handle_continuous_attributes() and self.attributes.has_continuous_attributes(): 
            raise inv.InvalidDataError('One or more attributes are continuous.')
    
    def test(self, path, printResults=True):
        raise AssertionError()
    
    def verify(self, path):
        raise AssertionError()
    
    def can_handle_continuous_attributes(self):
        return False

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
    