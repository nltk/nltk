# Natural Language Toolkit: Product Reviews Corpus Reader
#
# Copyright (C) 2001-2015 NLTK Project
# Author: Pierpaolo Pantone <24alsecondo@gmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

"""
CorpusReader for the Pros and Cons dataset.

- Pros and Cons dataset information -

Contact: Bing Liu, liub@cs.uic.edu
        http://www.cs.uic.edu/~liub

Distributed with permission.

Related papers:

- Murthy Ganapathibhotla and Bing Liu. "Mining Opinions in Comparative Sentences".
    Proceedings of the 22nd International Conference on Computational Linguistics
    (Coling-2008), Manchester, 18-22 August, 2008.

- Bing Liu, Minqing Hu and Junsheng Cheng. "Opinion Observer: Analyzing and Comparing
    Opinions on the Web". Proceedings of the 14th international World Wide Web
    conference (WWW-2005), May 10-14, 2005, in Chiba, Japan.
"""
import re

from nltk.compat import string_types
from nltk.corpus.reader.api import *
from nltk.tokenize import *


class ProsConsCorpusReader(CategorizedCorpusReader, CorpusReader):
    """
    Reader for the Pros and Cons sentence dataset.

        >>> from nltk.corpus import pros_cons
        >>> pros_cons.sents(categories='Cons')
        [(['East', 'batteries', '!', 'On', '-', 'off', 'switch', 'too', 'easy',
            'to', 'maneuver', '.'], 'Cons'), (['Eats', '...', 'no', ',', 'GULPS',
            'batteries'], 'Cons'), ...]
        >>> pros_cons.words('IntegratedPros.txt')
        [['Easy', 'to', 'use', ',', 'economical', '!'], 'Pros', ...]
    """
    CorpusView = StreamBackedCorpusView

    def __init__(self, root, fileids,
                 word_tokenizer=WordPunctTokenizer(),
                 encoding='utf8', *args, **kwargs):

        CorpusReader.__init__(self, root, fileids, encoding)
        CategorizedCorpusReader.__init__(self, kwargs)
        self._word_tokenizer = word_tokenizer

    def sents(self, fileids=None, categories=None):
        """
        :return: the given file(s) as a list of (sentence, label) tuples.
            Each sentence is tokenized using the specified word_tokenizer.
        :rtype: list(tuple(list, str))
        """
        fileids = self._resolve(fileids, categories)
        if fileids is None: fileids = self._fileids
        elif isinstance(fileids, compat.string_types): fileids = [fileids]
        return concat([self.CorpusView(path, self._read_sent_block, encoding=enc)
            for (path, enc, fileid) in self.abspaths(fileids, True, True)])

    def words(self, fileids=None, categories=None):
        """
        :return: the given file(s) as a list of words and punctuation symbols.
        :rtype: list(str)
        """
        fileids = self._resolve(fileids, categories)
        if fileids is None: fileids = self._fileids
        elif isinstance(fileids, compat.string_types): fileids = [fileids]
        return concat([self.CorpusView(path, self._read_word_block, encoding=enc)
            for (path, enc, fileid) in self.abspaths(fileids, True, True)])

    def _read_sent_block(self, stream):
        sents = []
        for i in range(20): # Read 20 lines at a time.
            line = stream.readline()
            if not line:
                continue
            sent = re.match(r"^(?!\n)\s*<(Pros|Cons)>(.*)</(?:Pros|Cons)>", line)
            if sent:
                sents.append((self._word_tokenizer.tokenize(sent.group(2).strip()), sent.group(1)))
                # sents.append(self._word_tokenizer.tokenize(sent.group(2).strip()))
        return sents

    def _read_word_block(self, stream):
        words = []
        for sent in self._read_sent_block(stream):
            words.extend(sent)
        return words

    def _resolve(self, fileids, categories):
        if fileids is not None and categories is not None:
            raise ValueError('Specify fileids or categories, not both')
        if categories is not None:
            return self.fileids(categories)
        else:
            return fileids
