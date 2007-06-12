# Natural Language Toolkit: Parsers
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Steven Bird <sb@csse.unimelb.edu.au>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#

"""
Classes and interfaces for producing tree structures that represent
the internal organization of a text.  This task is known as X{parsing}
the text, and the resulting tree structures are called the text's
X{parses}.  Typically, the text is a single sentence, and the tree
structure represents the syntactic structure of the sentence.
However, parsers can also be used in other domains.  For example,
parsers can be used to derive the morphological structure of the
morphemes that make up a word, or to derive the discourse structure
for a set of utterances.

Sometimes, a single piece of text can be represented by more than one
tree structure.  Texts represented by more than one tree structure are
called X{ambiguous} texts.  Note that there are actually two ways in
which a text can be ambiguous:

    - The text has multiple correct parses.
    - There is not enough information to decide which of several
      candidate parses is correct.

However, the parser module does I{not} distinguish these two types of
ambiguity.

The parser module defines C{ParseI}, a standard interface for parsing
texts; and two simple implementations of that interface,
C{ShiftReduce} and C{RecursiveDescent}.  It also contains
three sub-modules for specialized kinds of parsing:

  - C{nltk.parser.chart} defines chart parsing, which uses dynamic
    programming to efficiently parse texts.
  - C{nltk.parser.probabilistic} defines probabilistic parsing, which
    associates a probability with each parse.
"""

from api import *
from category import *
from chart import *
from featurechart import *
from treetransforms import *
from featurelite import *
from sr import *
from rd import *
from pchart import *
from viterbi import *
