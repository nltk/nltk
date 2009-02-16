# Natural Language Toolkit (NLTK) Coreference API
#
# Copyright (C) 2001-2009 NLTK Project 
# Author: Joseph Frazee <jfrazee@mail.utexas.edu>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

from nltk.corpus import CorpusReader
from nltk.tokenize.punkt import PunktWordTokenizer
from nltk.tag import TaggerI, HiddenMarkovModelTaggerTransformI

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


class CorpusReaderDecorator(CorpusReaderDecoratorI):
    def __init__(self, reader, **kwargs):
        self._reader = reader

    def __getattr__(self, name):
        if name != '_reader':
            return getattr(self._reader, name)

    def reader(self):
        wrapped_reader = self._reader
        while isinstance(wrapped_reader, CorpusReaderDecoratorI):
            wrapped_reader = wrapped_reader.reader()
        return wrapped_reader


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


class ChunkTaggerI(TaggerI):
    """
    An interface for a chunk tagger class.
    """
    def __init__(self):
        if self.__class__ == ChunkTaggerI:
            raise AssertionError, "Interfaces can't be instantiated"
    
    def tag(self, sent):
        """
        Returns an IOB tagged sentence.
        
        @return: a C{list} of IOB-tagged tokens.
        @rtype: C{list} or C{tuple}
        @param sent: a C{list} of tokens
        @type sent: C{list} of C{str} or C{tuple}
        """
        raise AssertionError()
        
    def chunk(self, sent):
        """
        Returns a chunked sentence.
        
        @return: a C{list} of chunked tokens.
        @rtype: C{list} of C{list} or C{tuple}
        @param sent: a C{list} of tokens
        @type sent: C{list} of C{str} or C{tuple}
        """
        raise AssertionError()
        
      
class CorefResolverI(object):
    """
    An interface for coreference resolvers.  Coreference resolvers identify
    and label co-referring L{mentions()} from a list of sentences.  Instances 
    of C{CorefResolverI} must implement L{mentions()}, L{resolve_mention()},
    L{resolve_mentions()}, and L{resolve()}.
    """
    def __init__(self):
        if self.__class__ == CorefResolverI:
            raise AssertionError, "Interfaces can't be instantiated"
    
    def mentions(self, sentences):
        """
        Identify the mentions from a list of sentences.
        
        For a list of sentences consisting of words [[w1, w2, w3], [w4, w5, w6]]
        where w2, w4, and w6 are mentions, L{mentions()} will yield the indexed
        list [(w2, 1, 0, 2), (w4, 2, 1, 0), (w6, 3, 1, 2)] which contains 
        4-tuples of the form (mention, mention id, sentence index, chunk index).
        
        @return: a C{list} of mentions.
        @rtype: C{list} of C{tuple}
        @param sentences: a C{list} of C{list} corresponding to a list of
            sentences.
        @type sentences: C{list} of C{list} of C{str} or C{tuple}
        """
        raise AssertionError()
        
    def resolve_mention(self, mentions, index, history):
        """
        Identify the coreferent, if any, for a mention in the mentions list.
        
        For a list of mentions consisting of 4-tuples of the form
        (mention, mention id, sentence, index, chunk index), 
        L{resolve_mention()} will yield the single coreferent 4-tuple for the
        mention located at index in the mentions list.
        
        @return: a C{tuple} of mention, mention id, sentence id, and chunk id.
        @rtype: C{tuple}
        @param mentions: a C{list} of mentions.
        @type mentions: C{list} of C{tuple}
        @param index: the index of the mention to resolve.
        @type index: C{int}
        @param history: the C{list} of previous (or future) mentions that can
            serve as coreferents.
        @type history: C{list} of C{tuple}
        """
        raise AssertionError()
    
    def resolve_mentions(self, mentions):
        """
        Identify co-referring discourse mentions from an indexed list of
        mentions.
        
        For a list of mentions [(w2, 1, 0, 2), (w4, 2, 1, 0), (w6, 3, 1, 2)],
        L{resolve_mentions()} will yield 
        [(w2, 1, 0, 2), (w4, 2, 1, 0), (w6, 1, 1, 2)] 
        iff. w2 and w6 co-refer and w4 does not co-refer with either w2 or w6.
        In other words, L{resolve_mentions()} indexes the indexed list of
        mentions so that each co-referring mention contains a matching index
        in the second element of its 4-tuple and non-co-referring mentions.
        
        @return: a C{list} of resolved mentions.
        @rtype: C{list} of C{tuple}
        @param mentions: a C{list} of mentions.
        @type mentions: C{list} of C{tuple}
        """
        raise AssertionError()
    
    def resolve(self, sentences):
        """
        Identify and resolve co-referring discourse mentions from a discourse
        or sequence of text.
        
        For a discourse consisting of words [[w1, w2, w3], [w4, w5, w6]] where
        w2, w4, and w6 are mentions and w2 and w6 co-refer L{resolve()} will
        yield the indexed list 
        [[(w1, None), (w2, 1), (w3, None)], [(w4, None), (w5, None), (w6, 1)]].
        
        @return: a C{list} of C{list} corresponding to a list of coreference
            resolved sentences.
        @rtype: C{list} of C{tuple}
        @param sentences: a C{list} of C{list} corresponding to a list of 
            sentences.
        @type sentences: C{list} of C{list} of C{str} or C{tuple}
        """
        raise AssertionError()
        
        
            