# Natural Language Toolkit: Europarl Corpus Readers
#
# Copyright (C) 2001-2020 NLTK Project
# Author:  Nitin Madnani <nmadnani@umiacs.umd.edu>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

import re
from nltk.corpus.util import LazyCorpusLoader
from nltk.corpus.reader import *

# Create a new corpus reader instance for each European language
danish = LazyCorpusLoader(
    "europarl_raw/danish", EuroparlCorpusReader, r"ep-.*\.da", encoding="utf-8"
)

dutch = LazyCorpusLoader(
    "europarl_raw/dutch", EuroparlCorpusReader, r"ep-.*\.nl", encoding="utf-8"
)

english = LazyCorpusLoader(
    "europarl_raw/english", EuroparlCorpusReader, r"ep-.*\.en", encoding="utf-8"
)

finnish = LazyCorpusLoader(
    "europarl_raw/finnish", EuroparlCorpusReader, r"ep-.*\.fi", encoding="utf-8"
)

french = LazyCorpusLoader(
    "europarl_raw/french", EuroparlCorpusReader, r"ep-.*\.fr", encoding="utf-8"
)

german = LazyCorpusLoader(
    "europarl_raw/german", EuroparlCorpusReader, r"ep-.*\.de", encoding="utf-8"
)

greek = LazyCorpusLoader(
    "europarl_raw/greek", EuroparlCorpusReader, r"ep-.*\.el", encoding="utf-8"
)

italian = LazyCorpusLoader(
    "europarl_raw/italian", EuroparlCorpusReader, r"ep-.*\.it", encoding="utf-8"
)

portuguese = LazyCorpusLoader(
    "europarl_raw/portuguese", EuroparlCorpusReader, r"ep-.*\.pt", encoding="utf-8"
)

spanish = LazyCorpusLoader(
    "europarl_raw/spanish", EuroparlCorpusReader, r"ep-.*\.es", encoding="utf-8"
)

swedish = LazyCorpusLoader(
    "europarl_raw/swedish", EuroparlCorpusReader, r"ep-.*\.sv", encoding="utf-8"
)
