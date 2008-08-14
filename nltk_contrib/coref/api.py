# Natural Language Toolkit (NLTK) Coreference API
#
# Copyright (C) 2008 Joseph Frazee
# Author: Joseph Frazee <jfrazee@mail.utexas.edu>
# URL: http://nltk.org/
# For license information, see LICENSE.TXT

from nltk.corpus import CorpusReader
from nltk.tokenize.punkt import PunktWordTokenizer
from nltk.tag import HiddenMarkovModelTaggerTransformI

class TrainableI(object):
    def __init__(self):
        if self.__class__ == TrainableI:
            raise AssertionError, "Interfaces can't be instantiated" 

    def train(self, labeled_sequence, test_sequence=None, 
              unlabeled_sequence=None, **kwargs):
        raise AssertionError()
        
        
class HiddenMarkovModelChunkTaggerTransformI(HiddenMarkovModelTaggerTransformI):
    def __init__(self):
        if self.__class__ == HiddenMarkovModelChunkTaggerTransformI:
            raise AssertionError, "Interfaces can't be instantiated"
    
    def path2tags(self, path):
        raise AssertionError()


class CorpusReaderDecoratorI(CorpusReader):
    def __init__(self):
        if self.__class__ == CorpusReaderDecorator:
            raise AssertionError, "Interfaces can't be instantiated"

    def reader(self):
        raise AssertionError()


class NamedEntityI(str):
    IN = 'I'
    OUT = 'O'
    BEGINS = 'B'

    def __new__(self, s, **kwargs):
        return str.__new__(self, s)
            
    def __init__(self, s, **kwargs):
        if self.__class__ == NamedEntityI:
            raise AssertionError, "Interfaces can't be instantiated"
        self._iob_tag = kwargs.get('iob_tag', self.BEGINS)
    
    def iob_in(self):
        return self._iob_tag == self.IN

    def iob_begins(self):
        return self._iob_tag == self.BEGINS
    
    def iob_out(self):
        return self._iob_tag == self.OUT
        
    def iob_tag(self):
        return self._iob_tag

    def ne_type(self):
        return self.__class__.__name__.upper()

    def ne_tag(self):
        return '%s-%s' % (self.iob_tag(), self.ne_type())
    
    def split(self, sep=None, maxsplit=-1):
        if not sep and maxsplit == -1:
            tokens = PunktWordTokenizer().tokenize(self)
        else:
            tokens = str.split(self, sep, maxsplit)
        result = []            
        for (index, token) in enumerate(tokens):
            if self.iob_out():
                iob_tag = self.OUT
            elif self.iob_begins() and index == 0:
                iob_tag = self.BEGINS
            else:
                iob_tag = self.IN
            result.append(self.__class__(token, iob_tag=iob_tag))            
        return result
