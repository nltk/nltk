# Natural Language Toolkit
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT
from nltk_lite_contrib.classifier.exceptions import invaliddataerror as inv
from nltk_lite_contrib.classifier import instances as ins
from nltk_lite_contrib.classifier import attributes as attrs

from nltk_lite_contrib.classifier import klass as k

class Classifier:
    def __init__(self, path):
        self.attributes = attrs.Attributes(path)
        self.klass = k.Klass(path)

        self.training = ins.TrainingInstances(path)
        self.validate_training()
        
    def validate_training(self):
        if not self.training.are_valid(self.klass, self.attributes): raise inv.InvalidDataError('Training data invalid')
    
    def test(self, path, printResults=True):
        raise AssertionError()
    
    def verify(self, path):
        raise AssertionError()


    