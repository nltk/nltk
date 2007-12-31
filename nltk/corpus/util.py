# Natural Language Toolkit: Corpus Reader Utility Functions
#
# Copyright (C) 2001-2008 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

######################################################################
#{ Lazy Corpus Loader
######################################################################
import nltk

class LazyCorpusLoader(object):
    """
    A proxy object which is used to stand in for a corpus object
    before the corpus is loaded.  This allows NLTK to create an object
    for each corpus, but defer the costs associated with loading those
    corpora until the first time that they're actually accessed.

    The first time this object is accessed in any way, it will load
    the corresponding corpus, and transform itself into that corpus
    (by modifying its own C{__class__} and C{__dict__} attributes).

    If the corpus can not be found, then accessing this object will
    raise an exception, displaying installation instructions for the
    NLTK data package.  Once they've properly installed the data
    package (or modified C{nltk.data.path} to point to its location),
    they can then use the corpus object without restarting python.
    """
    def __init__(self, name, reader_cls, *args, **kwargs):
        from nltk.corpus.reader.api import CorpusReader
        assert issubclass(reader_cls, CorpusReader)
        self.__name = name
        self.__reader_cls = reader_cls
        self.__args = args
        self.__kwargs = kwargs

    def __load(self):
        # Find the corpus root directory, and load the corpus.
        root = nltk.data.find('corpora/' + self.__name)
        corpus = self.__reader_cls(root, *self.__args, **self.__kwargs)
        
        # This is where the magic happens!  Transform ourselves into
        # the corpus by modifying our own __dict__ and __class__ to
        # match that of the corpus.
        self.__dict__ = corpus.__dict__
        self.__class__ = corpus.__class__

    def __getattr__(self, attr):
        self.__load()
        # This looks circular, but its not, since __load() changes our
        # __class__ to something new:
        return getattr(self, attr)

    def __repr__(self):
        self.__load()
        # This looks circular, but its not, since __load() changes our
        # __class__ to something new:
        return '%r' % self

