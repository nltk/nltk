# Natural Language Toolkit: Corpus Readers
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Corpus readers.
"""

from nltk.corpus.reader.plaintext import *
from nltk.corpus.reader.util import *
from nltk.corpus.reader.tagged import *
from nltk.corpus.reader.cmudict import *
from nltk.corpus.reader.conll import *
from nltk.corpus.reader.wordlist import *
from nltk.corpus.reader.gutenberg import *
from nltk.corpus.reader.xmldocs import *
from nltk.corpus.reader.ppattach import *
from nltk.corpus.reader.senseval import *
from nltk.corpus.reader.ieer import *
from nltk.corpus.reader.treebank import *
from nltk.corpus.reader.sinica_treebank import *
from nltk.corpus.reader.bracket_parse import *
from nltk.corpus.reader.indian import *
from nltk.corpus.reader.toolbox import *
from nltk.corpus.reader.timit import *
from nltk.corpus.reader.ycoe import *

__all__ = [
    'PlaintextCorpusReader', 'find_corpus_items',
    'TaggedCorpusReader', 'CMUDictCorpusReader',
    'ConllChunkCorpusReader', 'WordListCorpusReader',
    'GutenbergCorpusReader', 'XMLCorpusReader',
    'PPAttachmentCorpusReader', 'SensevalCorpusReader',
    'IEERCorpusReader', 'TreebankCorpusReader',
    'SinicaTreebankCorpusReader', 'BracketParseCorpusReader',
    'IndianCorpusReader', 'ToolboxCorpusReader',
    'TimitCorpusReader', 'YCOECorpusReader',
    'MacMorphoCorpusReader',
]
