# Natural Language Toolkit: Corpus Readers
#
# Copyright (C) 2001-2009 NLTK Project
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

# [xx] this docstring isnt' up-to-date!
"""
NLTK corpus readers.  The modules in this package provide functions
that can be used to read corpus files in a variety of formats.  These
functions can be used to read both the corpus files that are
distributed in the NLTK corpus package, and corpus files that are part
of external corpora.

Available Corpora
=================

Please see http://nltk.googlecode.com/svn/trunk/nltk_data/index.xml
for a complete list.  Install corpora using nltk.download().

Corpus Reader Functions
=======================
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
C{nltk.corpus.brown.words()}:

    >>> from nltk.corpus import brown
    >>> print brown.words()
    ['The', 'Fulton', 'County', 'Grand', 'Jury', 'said', ...]

Corpus Metadata
===============
Metadata about the NLTK corpora, and their individual documents, is
stored using U{Open Language Archives Community (OLAC)
<http://www.language-archives.org/>} metadata records.  These records
can be accessed using C{nltk.corpus.I{corpus}.olac()}.
"""

import re

from nltk.tokenize import RegexpTokenizer
from nltk.tag import simplify_brown_tag, simplify_wsj_tag,\
                     simplify_alpino_tag, simplify_indian_tag,\
                     simplify_tag

from util import LazyCorpusLoader
from reader import *

abc = LazyCorpusLoader(
    'abc', PlaintextCorpusReader, r'(?!\.).*\.txt')
alpino = LazyCorpusLoader(
    'alpino', AlpinoCorpusReader, tag_mapping_function=simplify_alpino_tag)
brown = LazyCorpusLoader(
    'brown', CategorizedTaggedCorpusReader, r'c[a-z]\d\d',
    cat_file='cats.txt', tag_mapping_function=simplify_brown_tag)
cess_cat = LazyCorpusLoader(
    'cess_cat', BracketParseCorpusReader, r'(?!\.).*\.tbf',
    tag_mapping_function=simplify_tag)
cess_esp = LazyCorpusLoader(
    'cess_esp', BracketParseCorpusReader, r'(?!\.).*\.tbf',
    tag_mapping_function=simplify_tag)
cmudict = LazyCorpusLoader(
    'cmudict', CMUDictCorpusReader, ['cmudict'])
conll2000 = LazyCorpusLoader(
    'conll2000', ConllChunkCorpusReader,
    ['train.txt', 'test.txt'], ('NP','VP','PP'))
conll2002 = LazyCorpusLoader(
    'conll2002', ConllChunkCorpusReader, '.*\.(test|train).*', 
    ('LOC', 'PER', 'ORG', 'MISC'))
conll2007 = LazyCorpusLoader(
    'conll2007', DependencyCorpusReader, '.*\.(test|train).*') 
dependency_treebank = LazyCorpusLoader(
    'dependency_treebank', DependencyCorpusReader, '.*\.dp') 
floresta = LazyCorpusLoader(
    'floresta', BracketParseCorpusReader, r'(?!\.).*\.ptb', '#',
    tag_mapping_function=simplify_tag)
gazetteers = LazyCorpusLoader(
    'gazetteers', WordListCorpusReader, r'(?!LICENSE|\.).*\.txt')  
genesis = LazyCorpusLoader(
    'genesis', PlaintextCorpusReader, r'(?!\.).*\.txt')
gutenberg = LazyCorpusLoader(
    'gutenberg', PlaintextCorpusReader, r'(?!\.).*\.txt')
# corpus not available with NLTK; these lines caused help(nltk.corpus) to break
#hebrew_treebank = LazyCorpusLoader(
#    'hebrew_treebank', BracketParseCorpusReader, r'.*\.txt')
ieer = LazyCorpusLoader(
    'ieer', IEERCorpusReader, r'(?!README|\.).*')
inaugural = LazyCorpusLoader(
    'inaugural', PlaintextCorpusReader, r'(?!\.).*\.txt')
# [XX] This should probably just use TaggedCorpusReader:
indian = LazyCorpusLoader(
    'indian', IndianCorpusReader, r'(?!\.).*\.pos',
    tag_mapping_function=simplify_indian_tag)
mac_morpho = LazyCorpusLoader(
    'mac_morpho', MacMorphoCorpusReader, r'(?!\.).*\.txt',
    tag_mapping_function=simplify_tag)
movie_reviews = LazyCorpusLoader(
    'movie_reviews', CategorizedPlaintextCorpusReader,
    r'(?!\.).*\.txt', cat_pattern=r'(neg|pos)/.*')
names = LazyCorpusLoader(
    'names', WordListCorpusReader, r'(?!\.).*\.txt')
nps_chat = LazyCorpusLoader(
    'nps_chat', NPSChatCorpusReader, r'(?!README|\.).*\.xml',
    tag_mapping_function=simplify_wsj_tag)
ppattach = LazyCorpusLoader(
    'ppattach', PPAttachmentCorpusReader, ['training', 'test', 'devset'])
qc = LazyCorpusLoader(
    'qc', StringCategoryCorpusReader, ['train.txt', 'test.txt'])
reuters = LazyCorpusLoader(
    'reuters', CategorizedPlaintextCorpusReader, '(training|test).*',
    cat_file='cats.txt')
rte = LazyCorpusLoader(
    'rte', RTECorpusReader, r'(?!\.).*\.xml')
senseval = LazyCorpusLoader(
    'senseval', SensevalCorpusReader, r'(?!\.).*\.pos')
shakespeare = LazyCorpusLoader(
    'shakespeare', XMLCorpusReader, r'(?!\.).*\.xml')
sinica_treebank = LazyCorpusLoader(
    'sinica_treebank', SinicaTreebankCorpusReader, ['parsed'],
    tag_mapping_function=simplify_tag)
state_union = LazyCorpusLoader(
    'state_union', PlaintextCorpusReader, r'(?!\.).*\.txt')
stopwords = LazyCorpusLoader(
    'stopwords', WordListCorpusReader, r'(?!README|\.).*')
swadesh = LazyCorpusLoader(
    'swadesh', SwadeshCorpusReader, r'(?!README|\.).*')
switchboard = LazyCorpusLoader(
    'switchboard', SwitchboardCorpusReader)
timit = LazyCorpusLoader(
    'timit', TimitCorpusReader)
toolbox = LazyCorpusLoader(
    'toolbox', ToolboxCorpusReader, r'(?!.*(README|\.)).*\.(dic|txt)')
treebank = LazyCorpusLoader(
    'treebank/combined', BracketParseCorpusReader, r'wsj_.*\.mrg',
    tag_mapping_function=simplify_wsj_tag)
treebank_chunk = LazyCorpusLoader(
    'treebank/tagged', ChunkedCorpusReader, r'wsj_.*\.pos',
    sent_tokenizer=RegexpTokenizer(r'(?<=/\.)\s*(?![^\[]*\])', gaps=True),
    para_block_reader=tagged_treebank_para_block_reader)
treebank_raw = LazyCorpusLoader(
    'treebank/raw', PlaintextCorpusReader, r'wsj_.*')
udhr = LazyCorpusLoader(
    'udhr', PlaintextCorpusReader, r'(?!README|\.).*',
    # Encodings specified in filenames but not mapped to anything:
    # DallakHelv, VIQR, Cyrillic+Abkh, WinResearcher, font,
    # Afenegus6..60375, VG2Main, VPS, Turkish, TCVN, Az.Times.Lat0117,
    # EUC, Baltic, err, Az.Times.Cyr.Normal0117, T61, Amahuaca, Agra
    encoding=[('.*-UTF8$', 'utf-8'), ('.*-Latin1$', 'latin-1'),
              ('.*-Hebrew$', 'hebrew'), ('.*-Arabic$', 'arabic'),
              ('.*-Cyrillic$', 'cyrillic'), ('.*-SJIS$', 'SJIS'),
              ('.*-GB2312$', 'GB2312'), ('.*-Latin2$', 'ISO-8859-2'),
              ('.*-Greek$', 'greek'), ('.*-UFT8$', 'utf-8'),
              ('Hungarian_Magyar-Unicode', 'utf-16-le')]
    )
verbnet = LazyCorpusLoader(
    'verbnet', VerbnetCorpusReader, r'(?!\.).*\.xml')
webtext = LazyCorpusLoader(
    'webtext', PlaintextCorpusReader, r'(?!README|\.).*\.txt')
wordnet = LazyCorpusLoader(
    'wordnet', WordNetCorpusReader)
wordnet_ic = LazyCorpusLoader(
    'wordnet_ic', WordNetICCorpusReader, '.*\.dat')
words = LazyCorpusLoader(
    'words', WordListCorpusReader, r'(?!README|\.).*')
ycoe = LazyCorpusLoader(
    'ycoe', YCOECorpusReader)
# defined after treebank
propbank = LazyCorpusLoader(
    'propbank', PropbankCorpusReader,
    'prop.txt', 'frames/.*\.xml', 'verbs.txt',
    lambda filename: re.sub(r'^wsj/\d\d/', '', filename),
    treebank) # Must be defined *after* treebank corpus.


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
    
