# Natural Language Toolkit (NLTK) Coreference API
#
# Copyright (C) 2008 NLTK Project 
# Author: Joseph Frazee <jfrazee@mail.utexas.edu>
# URL: http://nltk.org/
# For license information, see LICENSE.TXT

from nltk.corpus import CorpusReader
from nltk.tokenize.punkt import PunktWordTokenizer
from nltk.tag import HiddenMarkovModelTaggerTransformI

class TrainableI(object):
    """
    An interface for trainable classes.
    
    Subclasses must define L{train()}.
    """
    def __init__(self):
        if self.__class__ == TrainableI:
            raise AssertionError, "Interfaces can't be instantiated" 

    def train(self, labeled_sequence, test_sequence=None, 
              unlabeled_sequence=None, **kwargs):
        """
        Train a subclass instance of C{TrainableI}.
        
        @return: a subclass instance of C{TrainableI}
        @rtype: C{TrainableI}
        @param labeled_sequence: a C{list} of labeled training instances.
        @type labeled_sequence: C{list}
        @param test_sequence: a C{list} of labeled test instances.
        @type test_sequence: C{list}
        @param unlabeled_sequence: a C{list} of unlabeled training instances.
            An unlabeled sequence is useful for EM-like unsupervised
            training algorithms.
        @type unlabeled_sequence: C{list}
        @param kwargs: additional arguments to L{train()}.
        @type kwargs: C{dict}
        """
        raise AssertionError()
        
        
class HiddenMarkovModelChunkTaggerTransformI(HiddenMarkovModelTaggerTransformI):
    # Inherit the superclass documentation.
    def __init__(self):
        if self.__class__ == HiddenMarkovModelChunkTaggerTransformI:
            raise AssertionError, "Interfaces can't be instantiated"
    
    def path2tags(self, path):
        """
        Transform a viterbi/tag sequence of (word, tag) into a list of tags.
        
        @return: a C{list} of tags.
        @rtype: C{list}
        @param path: a C{list} of (word, tag) pairs.
        @type path: C{list} of C{tuple}
        """
        raise AssertionError()


class CorpusReaderDecoratorI(CorpusReader):
    """
    An interface for C{CorpusReader} decorators.  Instances of
    C{CorpusReaderDecoratorI} are useful for providing C{CorpusReader}
    instances with additional features.  For example, a tagging
    C{CorpusReaderDecoratorI} could add tagged_words() or tagged_sents()
    methods to the C{CorpusReader} of an untagged corpus.
    """
    def __init__(self):
        if self.__class__ == CorpusReaderDecorator:
            raise AssertionError, "Interfaces can't be instantiated"

    def reader(self):
        """
        Return the underlying C{CorpusReader} instance.
        
        @return: the underlying C{CorpusReader} instance.
        @rtype: C{CorpusReader}
        """
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


class CorefResolverI(object):
    """
    An interface for coreference resolvers.  Coreference resolvers identify
    and label co-referring L{mentions()} from a discourse or sequence of text.
    Instances of C{CorefResolverI} must implement L{mentions()}, 
    L{resolve_mentions()}, and L{resolve()}.
    """
    def __init__(self):
        if self.__class__ == CorefResolverI:
            raise AssertionError, "Interfaces can't be instatiated"
    
    def mentions(self, discourse):
        """
        Identify the mentions from a discourse or sequence of text.
        
        @return: a C{list} of mentions.
        @rtype: C{list} of C{tuple}
        @param discourse: a sequence of text.
        @type discourse: C{list} of C{str} or C{tuple}
        """
        raise AssertionError()
    
    def resolve_mentions(self, mentions):
        """
        Identify co-referring discourse mentions from a sequence of mentions.
        
        @return: a C{list} of resolved mentions.
        @rtype: C{list} of C{tuple}
        @param mentions: a C{list} of discourse mentions.
        @type mentions: C{list} of C{tuple}
        """
        raise AssertionError()
    
    def resolve(self, discourse):
        """
        Identify and resolve co-referring discourse mentions from a discourse
        or sequence of text.
        
        @return: a C{list} of discourse text with resolved mentions
        @rtype: C{list} of C{tuple}
        @param discourse: a C{list} of discourse text
        @type discourse: C{list} of C{str} or C{tuple}
        """
        raise AssertionError()