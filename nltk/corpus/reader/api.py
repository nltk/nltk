# Natural Language Toolkit: API for Corpus Readers
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
API for corpus readers.
"""

class CorpusReader(object):
    """
    Generally constructed from a path & a list of items..

    Reader functions take a list of items, specifying which document
    or documents to return.  The value of C{items} can be a single
    filename; a list of filenames; or a stream.  If no items are
    specified, then a default list of documents will be used.
    """
    def __repr__(self):
        if hasattr(self, '_root'):
            return '<%s in %r>' % (self.__class__.__name__, self._root)
        else:
            return '<%s>' % (self.__class__.__name__)
    
    def raw(items=None):
        """
        @return: the given document or documents as a single string.
        @rtype: C{str}
        """
        raise NotImplementedError()

    def words(items=None):
        """
        @return: the given document or documents as a list of words
            and punctuation symbols.
        @rtype: C{list} of C{str}
        """
        raise NotImplementedError()

    def sents(items=None):
        """
        @return: the given document or documents as a list of
            sentences or utterances, each encoded as a list of word
            strings.
        @rtype: C{list} of (C{list} of C{str})
        """
        raise NotImplementedError()

    def paras(items=None):
        """
        @return: the given document or documents as a list of
            paragraphs, each encoded as a list of sentences, which are
            in turn encoded as lists of word strings.
        @rtype: C{list} of (C{list} of (C{list} of C{str}))
        """
        raise NotImplementedError()

    def tagged_words(items=None):
        """
        @return: the given document or documents as a list of tagged
            words and punctuation symbols, encoded as tuples
            C{(word,tag)}.
        @rtype: C{list} of C{(str,str)}
        """
        raise NotImplementedError()

    def tagged_sents(items=None):
        """
        @return: the given document or documents as a list of
            sentences, each encoded as a list of C{(word,tag)} tuples.
            
        @rtype: C{list} of (C{list} of C{(str,str)})
        """
        raise NotImplementedError()

    def tagged_paras(items=None):
        """
        @return: the given document or documents as a list of
            paragraphs, each encoded as a list of sentences, which are
            in turn encoded as lists of C{(word,tag)} tuples.
        @rtype: C{list} of (C{list} of (C{list} of C{(str,str)}))
        """
        raise NotImplementedError()

        
    
