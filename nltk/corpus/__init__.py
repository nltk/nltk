# Natural Language Toolkit: Corpus Readers
#
# Copyright (C) 2001-2008 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
NLTK corpus readers.  The modules in this package provide functions
that can be used to read corpus files in a variety of formats.  These
functions can be used to read both the corpus files that are
distributed in the NLTK corpus package, and corpus files that are part
of external corpora.

Corpus Reader Functions
-----------------------
Each corpus module defines one or more X{corpus reader functions},
which can be used to read documents from that corpus.  These functions
take an argument, C{item}, which is used to indicate which document
should be read from the corpus:

  - If C{item} is one of the unique identifiers listed in the corpus
    module's C{items} variable, then the corresponding document will
    be loaded from the NLTK corpus package.

  - If C{item} is a filename, then that file will be read.

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
L{nltk.corpus.brown.words()}:

    >>> from nltk.corpus import brown
    >>> print brown.words()
    ['The', 'Fulton', 'County', 'Grand', 'Jury', 'said', ...]

Corpus Metadata
---------------
Metadata about the NLTK corpora, and their individual documents, is
stored using L{Open Language Archives Community (OLAC)
<http://www.language-archives.org/>} metadata records.  These records
can be accessed using C{nltk.corpus.I{corpus}.olac()}.
"""

from nltk.corpus.util import LazyCorpusLoader
from nltk.corpus.reader import *
from nltk.tokenize import RegexpTokenizer
import nltk.corpus.chat80
import re

abc = LazyCorpusLoader(
    'abc', PlaintextCorpusReader, r'(?!\.svn).*\.txt')
alpino = LazyCorpusLoader(
    'alpino', AlpinoCorpusReader)
brown = LazyCorpusLoader(
    'brown', CategorizedTaggedCorpusReader, r'c[a-z]\d\d',
    cat_pattern=r'c([a-z])\d\d')
cess_cat = LazyCorpusLoader(
    'cess_cat', BracketParseCorpusReader, r'(?!\.svn).*\.tbf')
cess_esp = LazyCorpusLoader(
    'cess_esp', BracketParseCorpusReader, r'(?!\.svn).*\.tbf')
cmudict = LazyCorpusLoader(
    'cmudict', CMUDictCorpusReader, ['cmudict'])
conll2000 = LazyCorpusLoader(
    'conll2000', ConllChunkCorpusReader,
    ['train.txt', 'test.txt'], ('NP','VP','PP'))
conll2002 = LazyCorpusLoader(
    'conll2002', ConllChunkCorpusReader, '.*\.(test|train).*', 
    ('LOC', 'PER', 'ORG', 'MISC'))
floresta = LazyCorpusLoader(
    'floresta', BracketParseCorpusReader, r'(?!\.svn).*\.ptb', '#')
genesis = LazyCorpusLoader(
    'genesis', PlaintextCorpusReader, r'(?!\.svn).*\.txt')
gutenberg = LazyCorpusLoader(
    'gutenberg', GutenbergCorpusReader, r'(?!\.svn).*\.txt')
ieer = LazyCorpusLoader(
    'ieer', IEERCorpusReader, r'(?!README|\.svn).*')
inaugural = LazyCorpusLoader(
    'inaugural', PlaintextCorpusReader, r'(?!\.svn).*\.txt')
# [XX] This should probably just use TaggedCorpusReader:
indian = LazyCorpusLoader(
    'indian', IndianCorpusReader, r'(?!\.svn).*\.pos')
mac_morpho = LazyCorpusLoader(
    'mac_morpho', MacMorphoCorpusReader, r'(?!\.svn).*\.txt')
movie_reviews = LazyCorpusLoader(
    'movie_reviews', CategorizedPlaintextCorpusReader,
    r'(?!\.svn).*\.txt', cat_pattern=r'(neg|pos)/.*')
names = LazyCorpusLoader(
    'names', WordListCorpusReader, r'(?!\.svn).*\.txt')
ppattach = LazyCorpusLoader(
    'ppattach', PPAttachmentCorpusReader, ['training', 'test', 'devset'])
qc = LazyCorpusLoader(
    'qc', StringCategoryCorpusReader, ['train.txt', 'test.txt'])
reuters = LazyCorpusLoader(
    'reuters', CategorizedPlaintextCorpusReader, '(training|test).*',
    cat_file='cats.txt')
rte = LazyCorpusLoader(
    'rte', RTECorpusReader, r'(?!\.svn).*\.xml')
senseval = LazyCorpusLoader(
    'senseval', SensevalCorpusReader, r'(?!\.svn).*\.pos')
shakespeare = LazyCorpusLoader(
    'shakespeare', XMLCorpusReader, r'(?!\.svn).*\.xml')
sinica_treebank = LazyCorpusLoader(
    'sinica_treebank', SinicaTreebankCorpusReader, ['parsed'])
state_union = LazyCorpusLoader(
    'state_union', PlaintextCorpusReader, r'(?!\.svn).*\.txt')
stopwords = LazyCorpusLoader(
    'stopwords', WordListCorpusReader, r'(?!README|\.svn).*')
timit = LazyCorpusLoader(
    'timit', TimitCorpusReader)
toolbox = LazyCorpusLoader(
    'toolbox', ToolboxCorpusReader, r'(?!.*(README|\.svn)).*\.(dic|txt)')
treebank = LazyCorpusLoader(
    'treebank/combined', BracketParseCorpusReader, r'wsj_.*\.mrg')
propbank = LazyCorpusLoader(
    'propbank', PropbankCorpusReader,
    'prop.txt', 'frames/.*\.xml', 'verbs.txt',
    lambda filename: re.sub(r'^wsj/\d\d/', '', filename),
    treebank) # Must be defined *after* treebank corpus.
treebank_chunk = LazyCorpusLoader(
    'treebank/tagged', ChunkedCorpusReader, r'wsj_.*\.pos',
    sent_tokenizer=RegexpTokenizer(r'(?<=/\.)\s*(?![^\[]*\])', gaps=True),
    para_block_reader=tagged_treebank_para_block_reader)
treebank_raw = LazyCorpusLoader(
    'treebank/raw', PlaintextCorpusReader, r'wsj_.*')
udhr = LazyCorpusLoader(
    'udhr', PlaintextCorpusReader, r'(?!README|\.svn).*')
verbnet = LazyCorpusLoader(
    'verbnet', VerbnetCorpusReader, r'(?!\.svn).*\.xml')
webtext = LazyCorpusLoader(
    'webtext', PlaintextCorpusReader, r'(?!README|\.svn).*')
words = LazyCorpusLoader(
    'words', WordListCorpusReader, r'(?!README|\.svn).*')
ycoe = LazyCorpusLoader(
    'ycoe', YCOECorpusReader)


def demo():
    # This is out-of-date:
    abc.demo()
    brown.demo()
#    chat80.demo()
    cmudict.demo()
    conll2000.demo()
    conll2002.demo()
    genesis.demo()
    gutenberg.demo()
    ieer.demo()
    inaugural.demo()
    indian.demo()
    names.demo()
    ppattach.demo()
    senseval.demo()
    shakespeare.demo()
    sinica_treebank.demo()
    state_union.demo()
    stopwords.demo()
    timit.demo()
    toolbox.demo()
    treebank.demo()
    udhr.demo()
    webtext.demo()
    words.demo()
#    ycoe.demo()

if __name__ == '__main__':
    #demo()
    pass
    
