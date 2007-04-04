# Natural Language Toolkit - Discretiser
#  Capable of dicretising numeric values into dicrete attributes
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk_lite.contrib.classifier.exceptions import filenotfounderror as fnf, invaliddataerror as inv
from nltk_lite.contrib.classifier import instances as ins, attributes as attrs

class Discretiser:
    def __init__(self, path):
        self.files = [None, None, None]
        self.classes = [ins.TrainingInstances, ins.TestInstances, ins.GoldInstances]
        self.initialize(path)
        
    def initialize(self, path):
        self.attributes = attrs.Attributes(path)
        for index in range(len(self.files)):
            try:
                self.files[index] = self.classes[index](path)
            except fnf.FileNotFoundError:
                self.files[index] = None
        
    def check_validity(self):
        for instances in self.files:
            if instances is None: continue
            if not instances.are_valid(): raise inv.InvalidDataError('Data invalid')
    
    def unsupervised_equal_width(self, attribute_indices, widths):
        self.check_validity()
        for index in range(len(attribute_indices)):
            attribute_index = attribute_indices[index]
            attribute = self.attributes[attribute_index]
            attribute.unsupervised_equal_width(widths[index])
            
        