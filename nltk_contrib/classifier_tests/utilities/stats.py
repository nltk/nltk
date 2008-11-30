# Natural Language Toolkit
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://www.nltk.org/>
# This software is distributed under GPL, for license information see LICENSE.TXT
from nltk import probability
from nltk_contrib.classifier import format
import os

def class_distribution(base_path):
    training = format.C45_FORMAT.get_training_instances(base_path)
    freq_dist = probability.FreqDist()
    for each in training:
        freq_dist.inc(each.klass_value)
    return freq_dist

def disc_attribute_values(base_path):
    attributes = format.C45_FORMAT.get_attributes(base_path)
    indices = attributes.continuous_attribute_indices()
    
        
