# Natural Language Toolkit: Corpus Readers
#
# Copyright (C) 2001-2011 NLTK Project
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
NLTK corpus readers.  The modules in this package provide functions
that can be used to read corpus fileids in a variety of formats.  These
functions can be used to read both the corpus fileids that are
distributed in the NLTK corpus package, and corpus fileids that are part
of external corpora.

Corpus Reader Functions
=======================
Each corpus module defines one or more X{corpus reader functions},
which can be used to read documents from that corpus.  These functions
take an argument, C{item}, which is used to indicate which document
should be read from the corpus:

  - If C{item} is one of the unique identifiers listed in the corpus
    module's C{items} variable, then the corresponding document will
    be loaded from the NLTK corpus package.

  - If C{item} is a fileid, then that file will be read.

Additionally, corpus reader functions can be given lists of item
names; in which case, they will return a concatenation of the
corresponding documents.

Corpus reader functions are named based on the type of information
they return.  Some common examples, and their return types, are:

  - I{corpus}.words(): list of str
  - I{corpus}.sents(): list of (list of str)
  - I{corpus}.paras(): list of (list of (list of str))
  - I{corpus}.tagged_words(): list of (str,str) tuple
  - I{corpus}.tagged_sents(): list of (list of (str,str))
  - I{corpus}.tagged_paras(): list of (list of (list of (str,str)))
  - I{corpus}.chunked_sents(): list of (Tree w/ (str,str) leaves)
  - I{corpus}.parsed_sents(): list of (Tree with str leaves)
  - I{corpus}.parsed_paras(): list of (list of (Tree with str leaves))
  - I{corpus}.xml(): A single xml ElementTree
  - I{corpus}.raw(): unprocessed corpus contents

For example, to read a list of the words in the Brown Corpus, use
C{nltk.corpus.brown.words()}:

    >>> from nltk.corpus import brown
    >>> print brown.words()
    ['The', 'Fulton', 'County', 'Grand', 'Jury', 'said', ...]

[Work in Progress:
Corpus Metadata
===============
Metadata about the NLTK corpora, and their individual documents, is
stored using U{Open Language Archives Community (OLAC)
<http://www.language-archives.org/>} metadata records.  These records
can be accessed using C{nltk.corpus.I{corpus}.olac()}.]
"""

from nltk.corpus.reader.plaintext import *
from nltk.corpus.reader.util import *
from nltk.corpus.reader.api import *
from nltk.corpus.reader.tagged import *
from nltk.corpus.reader.cmudict import *
from nltk.corpus.reader.conll import *
from nltk.corpus.reader.chunked import *
from nltk.corpus.reader.wordlist import *
from nltk.corpus.reader.xmldocs import *
from nltk.corpus.reader.ppattach import *
from nltk.corpus.reader.senseval import *
from nltk.corpus.reader.ieer import *
from nltk.corpus.reader.sinica_treebank import *
from nltk.corpus.reader.bracket_parse import *
from nltk.corpus.reader.indian import *
from nltk.corpus.reader.toolbox import *
from nltk.corpus.reader.timit import *
from nltk.corpus.reader.ycoe import *
from nltk.corpus.reader.rte import *
from nltk.corpus.reader.string_category import *
from nltk.corpus.reader.propbank import *
from nltk.corpus.reader.verbnet import *
from nltk.corpus.reader.bnc import *
from nltk.corpus.reader.nps_chat import *
from nltk.corpus.reader.wordnet import *
from nltk.corpus.reader.switchboard import *
from nltk.corpus.reader.dependency import *
from nltk.corpus.reader.nombank import *
from nltk.corpus.reader.ipipan import *
from nltk.corpus.reader.pl196x import *
from nltk.corpus.reader.knbc import *
from nltk.corpus.reader.chasen import *
from nltk.corpus.reader.childes import *
from nltk.corpus.reader.aligned import *

# Make sure that nltk.corpus.reader.bracket_parse gives the module, not
# the function bracket_parse() defined in nltk.tree:
import bracket_parse

__all__ = [
    'CorpusReader', 'CategorizedCorpusReader',
    'PlaintextCorpusReader', 'find_corpus_fileids',
    'TaggedCorpusReader', 'CMUDictCorpusReader',
    'ConllChunkCorpusReader', 'WordListCorpusReader',
    'PPAttachmentCorpusReader', 'SensevalCorpusReader',
    'IEERCorpusReader', 'ChunkedCorpusReader',
    'SinicaTreebankCorpusReader', 'BracketParseCorpusReader',
    'IndianCorpusReader', 'ToolboxCorpusReader',
    'TimitCorpusReader', 'YCOECorpusReader',
    'MacMorphoCorpusReader', 'SyntaxCorpusReader',
    'AlpinoCorpusReader', 'RTECorpusReader',
    'StringCategoryCorpusReader','EuroparlCorpusReader',
    'CategorizedTaggedCorpusReader',
    'CategorizedPlaintextCorpusReader',
    'PortugueseCategorizedPlaintextCorpusReader',
    'tagged_treebank_para_block_reader',
    'PropbankCorpusReader', 'VerbnetCorpusReader',
    'BNCCorpusReader', 'ConllCorpusReader',
    'XMLCorpusReader', 'NPSChatCorpusReader',
    'SwadeshCorpusReader', 'WordNetCorpusReader',
    'WordNetICCorpusReader', 'SwitchboardCorpusReader',
    'DependencyCorpusReader', 'NombankCorpusReader',
    'IPIPANCorpusReader', 'Pl196xCorpusReader',
    'TEICorpusView', 'KNBCorpusReader', 'ChasenCorpusReader',
    'CHILDESCorpusReader', 'AlignedCorpusReader',
    'TimitTaggedCorpusReader'
]
