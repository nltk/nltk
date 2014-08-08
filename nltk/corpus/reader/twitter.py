# Natural Language Toolkit: Twitter Corpus Reader
#
# Copyright (C) 2001-2014 NLTK Project
# Author: Ewan Klein <ewan@inf.ed.ac.uk>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

"""
A reader for corpora that consist of Tweets. It is assumed that the Tweets
have been serialised into line-delimited JSON.
"""

import json
import os

from nltk import compat
from nltk.tokenize import TweetTokenizer

from nltk.corpus.reader.util import StreamBackedCorpusView, concat
from nltk.corpus.reader.api import CorpusReader


class TwitterCorpusReader(CorpusReader):
    """
    Reader for corpora that consist of Tweets represented as a list of line-delimited JSON.

    Individual Tweets can be tokenized using the default tokenizer, or by a
    custom tokenizer specified as a parameter to the constructor.
    """

    CorpusView = StreamBackedCorpusView
    """
    The corpus view class used by this reader.
    """

    def __init__(self, root, fileids,
                 word_tokenizer=TweetTokenizer(),
                 encoding='utf8'):
        """
        Construct a new Tweet corpus reader for a set of documents
        located at the given root directory.  Example usage:

            >>> root = os.environ['TWITTER']
            >>> reader = TwitterCorpusReader(root, '.*\.json') # doctest: +SKIP

        :param root: The root directory for this corpus.

        :param fileids: A list or regexp specifying the fileids in this corpus.

        :param word_tokenizer: Tokenizer for breaking the text of Tweets into
        smaller units, including but not limited to words.

        """
        CorpusReader.__init__(self, root, fileids, encoding)

        for path in self.abspaths(self._fileids):
            if os.path.getsize(path) == 0:
                raise ValueError("File {} is empty".format(path))
        """Check that all user-created corpus files are non-empty."""

        self._word_tokenizer = word_tokenizer



    def full_tweets(self, fileids=None):
        """
        Returns the full Tweet objects, as specified by `Twitter
        documentation on Tweets
        <https://dev.twitter.com/docs/platform-objects/tweets>`_

        :return: the given file(s) as a list of dictionaries deserialised
        from JSON.
        :rtype: list(dict)
        """
        return concat([self.CorpusView(path, self._read_tweets, encoding=enc)
                               for (path, enc, fileid)
                               in self.abspaths(fileids, True, True)])


    def tweets(self, fileids=None):
        """
        Returns only the text content of Tweets in the file(s)

        :return: the given file(s) as a list of Tweets.
        :rtype: list(str)
        """
        fulltweets = self.full_tweets(fileids)
        tweets = []
        for jsono in fulltweets:
            try:
                text = jsono['text']
                if isinstance(text, bytes):
                    text = text.decode(self.encoding)
                tweets.append(text)
            except KeyError:
                pass
        return tweets


    def tokenised_tweets(self, fileids=None):
        """
        :return: the given file(s) as a list of the text content of Tweets as
        as a list of words, screenanames, hashtags, URLs and punctuation symbols.

        :rtype: list(list(str))
        """
        tweets = self.tweets(fileids)
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


    def _read_tweets(self, stream):
        """
        Assumes that each line in ``stream`` is a JSON-serialised object.
        """
        tweets = []
        for i in range(10):
            line = stream.readline()
            if not line:
                return tweets
            tweet = json.loads(line)
            tweets.append(tweet)
        return tweets



