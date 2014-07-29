# Natural Language Toolkit: Twitter Corpus Reader
#
# Copyright (C) 2001-2014 NLTK Project
# Author: Ewan Klein <ewan@inf.ed.ac.uk>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

"""
A reader for corpora that consist of Tweets.
"""

import json

from nltk import compat
import nltk.data
from nltk.tokenize import *

from nltk.corpus.reader.util import StreamBackedCorpusView
from nltk.corpus.reader.api import CorpusReader

from nltk.tokenizer.twitter import TweetTokenizer

class TwitterCorpusReader(CorpusReader):
    """
    Reader for corpora that consist of Tweets represented as a list of line-delimited JSON. 
    
    Individual Tweets can be tokenized using the default tokenizers, or by
    custom tokenizers specificed as parameters to the constructor    
    """

    CorpusView = StreamBackedCorpusView
    """
    The corpus view class used by this reader. Subclasses of
    ``PlaintextCorpusReader`` may specify alternative corpus view classes
    (e.g., to skip the preface sections of documents.)
    """

    def __init__(self, root, fileids,
                 word_tokenizer=TweetTokenizer(),                
                 encoding='utf8'):
        """
        Construct a new plaintext corpus reader for a set of documents
        located at the given root directory.  Example usage:

            >>> root = '/usr/local/share/nltk_data/corpora/webtext/'
            >>> reader = PlaintextCorpusReader(root, '.*\.txt') # doctest: +SKIP

        :param root: The root directory for this corpus.
        :param fileids: A list or regexp specifying the fileids in this corpus.
        :param word_tokenizer: Tokenizer for breaking sentences or
            paragraphs into words.

        """
        CorpusReader.__init__(self, root, fileids, encoding)
        self._word_tokenizer = word_tokenizer
        
       

    def jsonlist(self, fileid=None):
        """
        Return the contents of the file as a list of JSON-style dictionaries.
        """
        
        if fileid is None and len(self._fileids) == 1:
            fileid = self._fileids[0]
        if not isinstance(fileid, compat.string_types):
            raise TypeError('Expected a single file identifier string')
        return (json.loads(l.decode(self.encoding(fileid))) for l in self.abspath(fileid).open())
    

    def tweets(self, fileid=None):
        """
        Returns a list of Tweets as strings.
        
        :return: the given file(s) as a list of strings.
        :rtype: list(str)
        """
        jsonlist = self.jsonlist(fileid)
        encoding = self.encoding(fileid)    
        out = []
        for jsono in jsonlist:
            text = jsono['text']
            if isinstance(text, bytes):
                text = text.decode(encoding)
            out.append(text)
        return out
    
    
    def tokenised_tweets(self, fileid=None):
        """
        Return a list of Tweets as lists of words.
        
        :rtype: list(list(str))
        """
        tweets = self.tweets(fileid)
        tokenizer = self._word_tokenizer
        return [tokenizer.tokenize(t) for t in tweets]
    
    
    def raw(self, fileids=None):
        """
        Return the corpora in their raw form.
        """
        if fileids is None: 
            fileids = self._fileids
        elif isinstance(fileids, compat.string_types): 
            fileids = [fileids]
        return concat([self.open(f).read() for f in fileids]) 
    
    

        
        


    #def words(self, fileid=None):
        #"""
        #:return: the given file(s) as a list of words
            #and punctuation symbols.
        #:rtype: list(str)
        #"""
        #jsonlist = self.jsonlist(fileid)
        #encoding = self.encoding(fileid)
        #tokenizer = self._word_tokenizer
        #out = []
        #for jsono in jsonlist:
            #text = jsono['text']
            #if isinstance(text, bytes):
                #text = text.decode(encoding)
            #toks = tokenizer.tokenize(text)
            #out.extend(toks)
        #return out
            

    #def sents(self, fileids=None):
        #"""
        #:return: the given file(s) as a list of
            #sentences or utterances, each encoded as a list of word
            #strings.
        #:rtype: list(list(str))
        #"""
        #if self._sent_tokenizer is None:
            #raise ValueError('No sentence tokenizer for this corpus')

        #return concat([self.CorpusView(path, self._read_sent_block, encoding=enc)
                       #for (path, enc, fileid)
                       #in self.abspaths(fileids, True, True)])

