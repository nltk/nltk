# Natural Language Toolkit
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT
from nltk_lite_contrib.classifier.exceptions import invaliddataerror as inv

class Classifier:
    def __init__(self, training_instances):
        self.training = training_instances
        self.validate_training()
        
    def validate_training(self):
        if not self.training.are_valid(): raise inv.InvalidDataError('Training data invalid')
    
    def test(self, path, printResults=True):
        raise AssertionError()
    
    def verify(self, path):
        raise AssertionError()

    