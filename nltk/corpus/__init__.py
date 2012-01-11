# Natural Language Toolkit: Corpus Readers
#
# Copyright (C) 2001-2012 NLTK Project
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
Each corpus module defines one or more "corpus reader functions",
which can be used to read documents from that corpus.  These functions
take an argument, ``item``, which is used to indicate which document
should be read from the corpus:

- If ``item`` is one of the unique identifiers listed in the corpus
  module's ``items`` variable, then the corresponding document will
  be loaded from the NLTK corpus package.
- If ``item`` is a filename, then that file will be read.

Additionally, corpus reader functions can be given lists of item
names; in which case, they will return a concatenation of the
corresponding documents.

Corpus reader functions are named based on the type of information
they return.  Some common examples, and their return types, are:

- words(): list of str
- sents(): list of (list of str)
- paras(): list of (list of (list of str))
- tagged_words(): list of (str,str) tuple
- tagged_sents(): list of (list of (str,str))
- tagged_paras(): list of (list of (list of (str,str)))
- chunked_sents(): list of (Tree w/ (str,str) leaves)
- parsed_sents(): list of (Tree with str leaves)
- parsed_paras(): list of (list of (Tree with str leaves))
- xml(): A single xml ElementTree
- raw(): unprocessed corpus contents

For example, to read a list of the words in the Brown Corpus, use
``nltk.corpus.brown.words()``:

    >>> from nltk.corpus import brown
    >>> print brown.words()
    ['The', 'Fulton', 'County', 'Grand', 'Jury', 'said', ...]

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
comtrans = LazyCorpusLoader(
    'comtrans', AlignedCorpusReader, r'(?!\.).*\.txt')
conll2000 = LazyCorpusLoader(
    'conll2000', ConllChunkCorpusReader,
    ['train.txt', 'test.txt'], ('NP','VP','PP'),
    tag_mapping_function=simplify_wsj_tag)
conll2002 = LazyCorpusLoader(
    'conll2002', ConllChunkCorpusReader, '.*\.(test|train).*',
    ('LOC', 'PER', 'ORG', 'MISC'), encoding='utf-8')
conll2007 = LazyCorpusLoader(
    'conll2007', DependencyCorpusReader, '.*\.(test|train).*',
    encoding='utf-8')
dependency_treebank = LazyCorpusLoader(
    'dependency_treebank', DependencyCorpusReader, '.*\.dp')
floresta = LazyCorpusLoader(
    'floresta', BracketParseCorpusReader, r'(?!\.).*\.ptb', '#',
    tag_mapping_function=simplify_tag)
gazetteers = LazyCorpusLoader(
    'gazetteers', WordListCorpusReader, r'(?!LICENSE|\.).*\.txt')
genesis = LazyCorpusLoader(
    'genesis', PlaintextCorpusReader, r'(?!\.).*\.txt', encoding=[
        ('finnish|french|german', 'latin_1'),
        ('swedish', 'cp865'),
        ('.*', 'utf_8')])
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
ipipan = LazyCorpusLoader(
    'ipipan', IPIPANCorpusReader, r'(?!\.).*morph\.xml')
jeita = LazyCorpusLoader(
    'jeita', ChasenCorpusReader, r'.*\.chasen', encoding='utf-8')
knbc = LazyCorpusLoader(
    'knbc/corpus1', KNBCorpusReader, r'.*/KN.*', encoding='euc-jp')
mac_morpho = LazyCorpusLoader(
    'mac_morpho', MacMorphoCorpusReader, r'(?!\.).*\.txt',
    tag_mapping_function=simplify_tag, encoding='latin-1')
machado = LazyCorpusLoader(
    'machado', PortugueseCategorizedPlaintextCorpusReader,
    r'(?!\.).*\.txt', cat_pattern=r'([a-z]*)/.*', encoding='latin-1')
movie_reviews = LazyCorpusLoader(
    'movie_reviews', CategorizedPlaintextCorpusReader,
    r'(?!\.).*\.txt', cat_pattern=r'(neg|pos)/.*')
names = LazyCorpusLoader(
    'names', WordListCorpusReader, r'(?!\.).*\.txt')
nps_chat = LazyCorpusLoader(
    'nps_chat', NPSChatCorpusReader, r'(?!README|\.).*\.xml',
    tag_mapping_function=simplify_wsj_tag)
pl196x = LazyCorpusLoader(
    'pl196x', Pl196xCorpusReader, r'[a-z]-.*\.xml',
    cat_file='cats.txt', textid_file='textids.txt')
ppattach = LazyCorpusLoader(
    'ppattach', PPAttachmentCorpusReader, ['training', 'test', 'devset'])
# ptb = LazyCorpusLoader( # Penn Treebank v3: WSJ and Brown portions
#    'ptb3', CategorizedBracketParseCorpusReader, r'(WSJ/\d\d/WSJ_\d\d|BROWN/C[A-Z]/C[A-Z])\d\d.MRG',
#    cat_file='allcats.txt', tag_mapping_function=simplify_wsj_tag)
qc = LazyCorpusLoader(
    'qc', StringCategoryCorpusReader, ['train.txt', 'test.txt'])
reuters = LazyCorpusLoader(
    'reuters', CategorizedPlaintextCorpusReader, '(training|test).*',
    cat_file='cats.txt')
rte = LazyCorpusLoader(
    'rte', RTECorpusReader, r'(?!\.).*\.xml')
semcor = LazyCorpusLoader(
    'semcor', XMLCorpusReader, r'brown./tagfiles/br-.*\.xml')
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
    'switchboard', SwitchboardCorpusReader,
    tag_mapping_function=simplify_wsj_tag)
timit = LazyCorpusLoader(
    'timit', TimitCorpusReader)
timit_tagged = LazyCorpusLoader(
    'timit', TimitTaggedCorpusReader, '.+\.tags',
    tag_mapping_function=simplify_wsj_tag)
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
nombank = LazyCorpusLoader(
    'nombank.1.0', NombankCorpusReader,
    'nombank.1.0', 'frames/.*\.xml', 'nombank.1.0.words',
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

