# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
import unittest
import os.path

from nltk.corpus.reader import *

class TestRaw(unittest.TestCase):
    CORPORA = (AlignedCorpusReader, ChasenCorpusReader, ChunkedCorpusReader,
               ComparativeSentencesCorpusReader, IEERCorpusReader,
               IndianCorpusReader, PlaintextCorpusReader,
               PPAttachmentCorpusReader, ReviewsCorpusReader,
               SensevalCorpusReader, StringCategoryCorpusReader,
               TaggedCorpusReader, ToolboxCorpusReader, TwitterCorpusReader,
               WordListCorpusReader, XMLCorpusReader, SyntaxCorpusReader)

    FILE_PATH = os.path.join(os.path.dirname(__file__), 'files')
    def test_raw(self):
        for reader in self.CORPORA:
            r = reader(self.FILE_PATH, '.*\.json')
            assert r.raw(None) == '{"test":"json", "number":5}\n'

    def test_raw_fileid(self):
        for reader in self.CORPORA:
            r = reader(self.FILE_PATH, '.*\.csv')
            assert r.raw('test_corpus_reader.json') == '{"test":"json", "number":5}\n'
