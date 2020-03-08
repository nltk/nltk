# Natural Language Toolkit: Corpus Readers
#
# Copyright (C) 2001-2020 NLTK Project
# Author: Edward Loper <edloper@gmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

# TODO this docstring isn't up-to-date!
"""
NLTK corpus readers.  The modules in this package provide functions
that can be used to read corpus files in a variety of formats.  These
functions can be used to read both the corpus files that are
distributed in the NLTK corpus package, and corpus files that are part
of external corpora.

Available Corpora
=================

Please see http://www.nltk.org/nltk_data/ for a complete list.
Install corpora using nltk.download().

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
    >>> print(", ".join(brown.words()))
    The, Fulton, County, Grand, Jury, said, ...

"""

import re

from nltk.tokenize import RegexpTokenizer
from nltk.corpus.util import LazyCorpusLoader
from nltk.corpus.reader import *

abc = LazyCorpusLoader(
    "abc",
    PlaintextCorpusReader,
    r"(?!\.).*\.txt",
    encoding=[("science", "latin_1"), ("rural", "utf8")],
)
alpino = LazyCorpusLoader("alpino", AlpinoCorpusReader, tagset="alpino")
brown = LazyCorpusLoader(
    "brown",
    CategorizedTaggedCorpusReader,
    r"c[a-z]\d\d",
    cat_file="cats.txt",
    tagset="brown",
    encoding="ascii",
)
cess_cat = LazyCorpusLoader(
    "cess_cat",
    BracketParseCorpusReader,
    r"(?!\.).*\.tbf",
    tagset="unknown",
    encoding="ISO-8859-15",
)
cess_esp = LazyCorpusLoader(
    "cess_esp",
    BracketParseCorpusReader,
    r"(?!\.).*\.tbf",
    tagset="unknown",
    encoding="ISO-8859-15",
)
cmudict = LazyCorpusLoader("cmudict", CMUDictCorpusReader, ["cmudict"])
comtrans = LazyCorpusLoader("comtrans", AlignedCorpusReader, r"(?!\.).*\.txt")
comparative_sentences = LazyCorpusLoader(
    "comparative_sentences",
    ComparativeSentencesCorpusReader,
    r"labeledSentences\.txt",
    encoding="latin-1",
)
conll2000 = LazyCorpusLoader(
    "conll2000",
    ConllChunkCorpusReader,
    ["train.txt", "test.txt"],
    ("NP", "VP", "PP"),
    tagset="wsj",
    encoding="ascii",
)
conll2002 = LazyCorpusLoader(
    "conll2002",
    ConllChunkCorpusReader,
    ".*\.(test|train).*",
    ("LOC", "PER", "ORG", "MISC"),
    encoding="utf-8",
)
conll2007 = LazyCorpusLoader(
    "conll2007",
    DependencyCorpusReader,
    ".*\.(test|train).*",
    encoding=[("eus", "ISO-8859-2"), ("esp", "utf8")],
)
crubadan = LazyCorpusLoader("crubadan", CrubadanCorpusReader, ".*\.txt")
dependency_treebank = LazyCorpusLoader(
    "dependency_treebank", DependencyCorpusReader, ".*\.dp", encoding="ascii"
)
floresta = LazyCorpusLoader(
    "floresta",
    BracketParseCorpusReader,
    r"(?!\.).*\.ptb",
    "#",
    tagset="unknown",
    encoding="ISO-8859-15",
)
framenet15 = LazyCorpusLoader(
    "framenet_v15",
    FramenetCorpusReader,
    [
        "frRelation.xml",
        "frameIndex.xml",
        "fulltextIndex.xml",
        "luIndex.xml",
        "semTypes.xml",
    ],
)
framenet = LazyCorpusLoader(
    "framenet_v17",
    FramenetCorpusReader,
    [
        "frRelation.xml",
        "frameIndex.xml",
        "fulltextIndex.xml",
        "luIndex.xml",
        "semTypes.xml",
    ],
)
gazetteers = LazyCorpusLoader(
    "gazetteers", WordListCorpusReader, r"(?!LICENSE|\.).*\.txt", encoding="ISO-8859-2"
)
genesis = LazyCorpusLoader(
    "genesis",
    PlaintextCorpusReader,
    r"(?!\.).*\.txt",
    encoding=[
        ("finnish|french|german", "latin_1"),
        ("swedish", "cp865"),
        (".*", "utf_8"),
    ],
)
gutenberg = LazyCorpusLoader(
    "gutenberg", PlaintextCorpusReader, r"(?!\.).*\.txt", encoding="latin1"
)
ieer = LazyCorpusLoader("ieer", IEERCorpusReader, r"(?!README|\.).*")
inaugural = LazyCorpusLoader(
    "inaugural", PlaintextCorpusReader, r"(?!\.).*\.txt", encoding="latin1"
)
# [XX] This should probably just use TaggedCorpusReader:
indian = LazyCorpusLoader(
    "indian", IndianCorpusReader, r"(?!\.).*\.pos", tagset="unknown", encoding="utf8"
)

jeita = LazyCorpusLoader("jeita", ChasenCorpusReader, r".*\.chasen", encoding="utf-8")
knbc = LazyCorpusLoader("knbc/corpus1", KNBCorpusReader, r".*/KN.*", encoding="euc-jp")
lin_thesaurus = LazyCorpusLoader("lin_thesaurus", LinThesaurusCorpusReader, r".*\.lsp")
mac_morpho = LazyCorpusLoader(
    "mac_morpho",
    MacMorphoCorpusReader,
    r"(?!\.).*\.txt",
    tagset="unknown",
    encoding="latin-1",
)
machado = LazyCorpusLoader(
    "machado",
    PortugueseCategorizedPlaintextCorpusReader,
    r"(?!\.).*\.txt",
    cat_pattern=r"([a-z]*)/.*",
    encoding="latin-1",
)
masc_tagged = LazyCorpusLoader(
    "masc_tagged",
    CategorizedTaggedCorpusReader,
    r"(spoken|written)/.*\.txt",
    cat_file="categories.txt",
    tagset="wsj",
    encoding="utf-8",
    sep="_",
)
movie_reviews = LazyCorpusLoader(
    "movie_reviews",
    CategorizedPlaintextCorpusReader,
    r"(?!\.).*\.txt",
    cat_pattern=r"(neg|pos)/.*",
    encoding="ascii",
)
multext_east = LazyCorpusLoader(
    "mte_teip5", MTECorpusReader, r"(oana).*\.xml", encoding="utf-8"
)
names = LazyCorpusLoader(
    "names", WordListCorpusReader, r"(?!\.).*\.txt", encoding="ascii"
)
nps_chat = LazyCorpusLoader(
    "nps_chat", NPSChatCorpusReader, r"(?!README|\.).*\.xml", tagset="wsj"
)
opinion_lexicon = LazyCorpusLoader(
    "opinion_lexicon",
    OpinionLexiconCorpusReader,
    r"(\w+)\-words\.txt",
    encoding="ISO-8859-2",
)
ppattach = LazyCorpusLoader(
    "ppattach", PPAttachmentCorpusReader, ["training", "test", "devset"]
)
product_reviews_1 = LazyCorpusLoader(
    "product_reviews_1", ReviewsCorpusReader, r"^(?!Readme).*\.txt", encoding="utf8"
)
product_reviews_2 = LazyCorpusLoader(
    "product_reviews_2", ReviewsCorpusReader, r"^(?!Readme).*\.txt", encoding="utf8"
)
pros_cons = LazyCorpusLoader(
    "pros_cons",
    ProsConsCorpusReader,
    r"Integrated(Cons|Pros)\.txt",
    cat_pattern=r"Integrated(Cons|Pros)\.txt",
    encoding="ISO-8859-2",
)
ptb = LazyCorpusLoader(  # Penn Treebank v3: WSJ and Brown portions
    "ptb",
    CategorizedBracketParseCorpusReader,
    r"(WSJ/\d\d/WSJ_\d\d|BROWN/C[A-Z]/C[A-Z])\d\d.MRG",
    cat_file="allcats.txt",
    tagset="wsj",
)
qc = LazyCorpusLoader(
    "qc", StringCategoryCorpusReader, ["train.txt", "test.txt"], encoding="ISO-8859-2"
)
reuters = LazyCorpusLoader(
    "reuters",
    CategorizedPlaintextCorpusReader,
    "(training|test).*",
    cat_file="cats.txt",
    encoding="ISO-8859-2",
)
rte = LazyCorpusLoader("rte", RTECorpusReader, r"(?!\.).*\.xml")
senseval = LazyCorpusLoader("senseval", SensevalCorpusReader, r"(?!\.).*\.pos")
sentence_polarity = LazyCorpusLoader(
    "sentence_polarity",
    CategorizedSentencesCorpusReader,
    r"rt-polarity\.(neg|pos)",
    cat_pattern=r"rt-polarity\.(neg|pos)",
    encoding="utf-8",
)
sentiwordnet = LazyCorpusLoader(
    "sentiwordnet", SentiWordNetCorpusReader, "SentiWordNet_3.0.0.txt", encoding="utf-8"
)
shakespeare = LazyCorpusLoader("shakespeare", XMLCorpusReader, r"(?!\.).*\.xml")
sinica_treebank = LazyCorpusLoader(
    "sinica_treebank",
    SinicaTreebankCorpusReader,
    ["parsed"],
    tagset="unknown",
    encoding="utf-8",
)
state_union = LazyCorpusLoader(
    "state_union", PlaintextCorpusReader, r"(?!\.).*\.txt", encoding="ISO-8859-2"
)
stopwords = LazyCorpusLoader(
    "stopwords", WordListCorpusReader, r"(?!README|\.).*", encoding="utf8"
)
subjectivity = LazyCorpusLoader(
    "subjectivity",
    CategorizedSentencesCorpusReader,
    r"(quote.tok.gt9|plot.tok.gt9)\.5000",
    cat_map={"quote.tok.gt9.5000": ["subj"], "plot.tok.gt9.5000": ["obj"]},
    encoding="latin-1",
)
swadesh = LazyCorpusLoader(
    "swadesh", SwadeshCorpusReader, r"(?!README|\.).*", encoding="utf8"
)
swadesh110 = LazyCorpusLoader(
    'panlex_swadesh', PanlexSwadeshCorpusReader, r'swadesh110/.*\.txt', encoding='utf8'
)
swadesh207 = LazyCorpusLoader(
    'panlex_swadesh', PanlexSwadeshCorpusReader, r'swadesh207/.*\.txt', encoding='utf8'
)
switchboard = LazyCorpusLoader("switchboard", SwitchboardCorpusReader, tagset="wsj")
timit = LazyCorpusLoader("timit", TimitCorpusReader)
timit_tagged = LazyCorpusLoader(
    "timit", TimitTaggedCorpusReader, ".+\.tags", tagset="wsj", encoding="ascii"
)
toolbox = LazyCorpusLoader(
    "toolbox", ToolboxCorpusReader, r"(?!.*(README|\.)).*\.(dic|txt)"
)
treebank = LazyCorpusLoader(
    "treebank/combined",
    BracketParseCorpusReader,
    r"wsj_.*\.mrg",
    tagset="wsj",
    encoding="ascii",
)
treebank_chunk = LazyCorpusLoader(
    "treebank/tagged",
    ChunkedCorpusReader,
    r"wsj_.*\.pos",
    sent_tokenizer=RegexpTokenizer(r"(?<=/\.)\s*(?![^\[]*\])", gaps=True),
    para_block_reader=tagged_treebank_para_block_reader,
    tagset="wsj",
    encoding="ascii",
)
treebank_raw = LazyCorpusLoader(
    "treebank/raw", PlaintextCorpusReader, r"wsj_.*", encoding="ISO-8859-2"
)
twitter_samples = LazyCorpusLoader("twitter_samples", TwitterCorpusReader, ".*\.json")
udhr = LazyCorpusLoader("udhr", UdhrCorpusReader)
udhr2 = LazyCorpusLoader("udhr2", PlaintextCorpusReader, r".*\.txt", encoding="utf8")
universal_treebanks = LazyCorpusLoader(
    "universal_treebanks_v20",
    ConllCorpusReader,
    r".*\.conll",
    columntypes=(
        "ignore",
        "words",
        "ignore",
        "ignore",
        "pos",
        "ignore",
        "ignore",
        "ignore",
        "ignore",
        "ignore",
    ),
)
verbnet = LazyCorpusLoader("verbnet", VerbnetCorpusReader, r"(?!\.).*\.xml")
webtext = LazyCorpusLoader(
    "webtext", PlaintextCorpusReader, r"(?!README|\.).*\.txt", encoding="ISO-8859-2"
)
wordnet = LazyCorpusLoader(
    "wordnet",
    WordNetCorpusReader,
    LazyCorpusLoader("omw", CorpusReader, r".*/wn-data-.*\.tab", encoding="utf8"),
)
wordnet_ic = LazyCorpusLoader("wordnet_ic", WordNetICCorpusReader, ".*\.dat")
words = LazyCorpusLoader(
    "words", WordListCorpusReader, r"(?!README|\.).*", encoding="ascii"
)

# defined after treebank
propbank = LazyCorpusLoader(
    "propbank",
    PropbankCorpusReader,
    "prop.txt",
    "frames/.*\.xml",
    "verbs.txt",
    lambda filename: re.sub(r"^wsj/\d\d/", "", filename),
    treebank,
)  # Must be defined *after* treebank corpus.
nombank = LazyCorpusLoader(
    "nombank.1.0",
    NombankCorpusReader,
    "nombank.1.0",
    "frames/.*\.xml",
    "nombank.1.0.words",
    lambda filename: re.sub(r"^wsj/\d\d/", "", filename),
    treebank,
)  # Must be defined *after* treebank corpus.
propbank_ptb = LazyCorpusLoader(
    "propbank",
    PropbankCorpusReader,
    "prop.txt",
    "frames/.*\.xml",
    "verbs.txt",
    lambda filename: filename.upper(),
    ptb,
)  # Must be defined *after* ptb corpus.
nombank_ptb = LazyCorpusLoader(
    "nombank.1.0",
    NombankCorpusReader,
    "nombank.1.0",
    "frames/.*\.xml",
    "nombank.1.0.words",
    lambda filename: filename.upper(),
    ptb,
)  # Must be defined *after* ptb corpus.
semcor = LazyCorpusLoader(
    "semcor", SemcorCorpusReader, r"brown./tagfiles/br-.*\.xml", wordnet
)  # Must be defined *after* wordnet corpus.

nonbreaking_prefixes = LazyCorpusLoader(
    "nonbreaking_prefixes",
    NonbreakingPrefixesCorpusReader,
    r"(?!README|\.).*",
    encoding="utf8",
)
perluniprops = LazyCorpusLoader(
    "perluniprops",
    UnicharsCorpusReader,
    r"(?!README|\.).*",
    nltk_data_subdir="misc",
    encoding="utf8",
)

# mwa_ppdb = LazyCorpusLoader(
#     'mwa_ppdb', MWAPPDBCorpusReader, r'(?!README|\.).*', nltk_data_subdir='misc', encoding='utf8')

# See https://github.com/nltk/nltk/issues/1579
# and https://github.com/nltk/nltk/issues/1716
#
# pl196x = LazyCorpusLoader(
#     'pl196x', Pl196xCorpusReader, r'[a-z]-.*\.xml',
#     cat_file='cats.txt', textid_file='textids.txt', encoding='utf8')
#
# ipipan = LazyCorpusLoader(
#     'ipipan', IPIPANCorpusReader, r'(?!\.).*morph\.xml')
#
# nkjp = LazyCorpusLoader(
#     'nkjp', NKJPCorpusReader, r'', encoding='utf8')
#
# panlex_lite = LazyCorpusLoader(
#    'panlex_lite', PanLexLiteCorpusReader)
#
# ycoe = LazyCorpusLoader(
#     'ycoe', YCOECorpusReader)
#
# corpus not available with NLTK; these lines caused help(nltk.corpus) to break
# hebrew_treebank = LazyCorpusLoader(
#    'hebrew_treebank', BracketParseCorpusReader, r'.*\.txt')

# FIXME:  override any imported demo from various corpora, see https://github.com/nltk/nltk/issues/2116
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

if __name__ == "__main__":
    # demo()
    pass

# ** this is for nose **
# unload all corpus after tests
def teardown_module(module=None):
    import nltk.corpus

    for name in dir(nltk.corpus):
        obj = getattr(nltk.corpus, name, None)
        if isinstance(obj, CorpusReader) and hasattr(obj, "_unload"):
            obj._unload()
