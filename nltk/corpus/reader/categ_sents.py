# Natural Language Toolkit: Categorized Sentences Corpus Reader
#
# Copyright (C) 2001-2015 NLTK Project
# Author: Pierpaolo Pantone <24alsecondo@gmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

"""
CorpusReader structured for corpora that contain one instance on each row.
This CorpusReader is specifically used for the Subjectivity Dataset and the
Sentence Polarity Dataset.

- Subjectivity Dataset information -

Authors: Bo Pang and Lillian Lee.
Url: http://www.cs.cornell.edu/people/pabo/movie-review-data

Distributed with permission.

Related papers:

- Bo Pang and Lillian Lee. "A Sentimental Education: Sentiment Analysis Using
    Subjectivity Summarization Based on Minimum Cuts". Proceedings of the ACL,
    2004.

- Sentence Polarity Dataset information -

Authors: Bo Pang and Lillian Lee.
Url: http://www.cs.cornell.edu/people/pabo/movie-review-data

Related papers:

- Bo Pang and Lillian Lee. "Seeing stars: Exploiting class relationships for
    sentiment categorization with respect to rating scales". Proceedings of the
    ACL, 2005.
"""

from nltk.corpus.reader.api import *
from nltk.tokenize import *

class CategorizedSentencesCorpusReader(CategorizedCorpusReader, CorpusReader):
    """
    A reader for corpora in which each row represents a single instance, mainly
    a sentence. Istances are divided into categories based on their file identifiers
    (see CategorizedCorpusReader).
    Since many corpora allow rows that contain more than one sentence, it is
    possible to specify a sentence tokenizer to retrieve all sentences instead
    than all rows.
    """

    CorpusView = StreamBackedCorpusView

    def __init__(self, root, fileids,
                 word_tokenizer=WhitespaceTokenizer(),
                 sent_tokenizer=None,
                 encoding='utf8', *args, **kwargs):

        CorpusReader.__init__(self, root, fileids, encoding)
        CategorizedCorpusReader.__init__(self, kwargs)
        self._word_tokenizer = word_tokenizer
        self._sent_tokenizer = sent_tokenizer

    def _resolve(self, fileids, categories):
        if fileids is not None and categories is not None:
            raise ValueError('Specify fileids or categories, not both')
        if categories is not None:
            return self.fileids(categories)
        else:
            return fileids

    def raw(self, fileids=None, categories=None):
        """
        :return: the given file(s) as a single string.
        :rtype: str
        """
        fileids = self._resolve(fileids, categories)
        if fileids is None:
            fileids = self._fileids
        elif isinstance(fileids, string_types):
            fileids = [fileids]
        return concat([self.open(f).read() for f in fileids])

    def readme(self):
        """
        Return the contents of the corpus Readme.txt file.
        """
        return self.open("README").read()

    def sents(self, fileids=None, categories=None):
        """
        :return: the given file(s) as a list of sentences.
            Each sentence is tokenized using the specified word_tokenizer.
        :rtype: list(list(str))
        """
        fileids = self._resolve(fileids, categories)
        if fileids is None:
            fileids = self._fileids
        elif isinstance(fileids, compat.string_types):
            fileids = [fileids]
        return concat([self.CorpusView(path, self._read_sent_block, encoding=enc)
            for (path, enc, fileid) in self.abspaths(fileids, True, True)])

    def words(self, fileids=None, categories=None):
        """
        :return: the given file(s) as a list of words and punctuation symbols.
        :rtype: list(str)
        """
        fileids = self._resolve(fileids, categories)
        if fileids is None:
            fileids = self._fileids
        elif isinstance(fileids, compat.string_types):
            fileids = [fileids]
        return concat([self.CorpusView(path, self._read_word_block, encoding=enc)
            for (path, enc, fileid) in self.abspaths(fileids, True, True)])

    def _read_sent_block(self, stream):
        sents = []
        for i in range(20): # Read 20 lines at a time.
            line = stream.readline()
            if not line:
                continue
            if self._sent_tokenizer:
                sents.extend([self._word_tokenizer.tokenize(sent)
                          for sent in self._sent_tokenizer.tokenize(line)])
            else:
                sents.append(self._word_tokenizer.tokenize(line))
        return sents

    def _read_word_block(self, stream):
        words = []
        for sent in self._read_sent_block(stream):
            words.extend(sent)
        return words
