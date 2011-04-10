# Natural Language Toolkit: Parsers
#
# Copyright (C) 2001-2011 NLTK Project
# Author: Steven Bird <sb@csse.unimelb.edu.au>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://www.nltk.org/>
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

The parser module defines C{ParserI}, a standard interface for parsing
texts; and two simple implementations of that interface,
C{ShiftReduceParser} and C{RecursiveDescentParser}.  It also contains
three sub-modules for specialized kinds of parsing:

  - C{nltk.parser.chart} defines chart parsing, which uses dynamic
    programming to efficiently parse texts.
  - C{nltk.parser.probabilistic} defines probabilistic parsing, which
    associates a probability with each parse.
"""

from api import *
from chart import *
from featurechart import *
from earleychart import *
from pchart import *
from rd import *
from sr import *
from util import *
from viterbi import *
from dependencygraph import *
from projectivedependencyparser import *
from nonprojectivedependencyparser import *
from malt import *

__all__ = [
    # Parser interface
    'ParserI',
    
    # Generic parser loading function
    'load_parser',

    # Parsers
    # from rd.py:
    'RecursiveDescentParser', 'SteppingRecursiveDescentParser',
    # from sr.py:
    'ShiftReduceParser', 'SteppingShiftReduceParser',
    # from chart.py:
    'ChartParser', 'SteppingChartParser',
    'TopDownChartParser', 'BottomUpChartParser', 
    'BottomUpLeftCornerChartParser', 'LeftCornerChartParser',
    # from pchart.py:
    'BottomUpProbabilisticChartParser', 'InsideChartParser', 'RandomChartParser',
    'UnsortedChartParser', 'LongestChartParser', 'ViterbiParser',
    # from featurechart.py:
    'FeatureChartParser', 'FeatureTopDownChartParser', 
    'FeatureBottomUpChartParser', 'FeatureBottomUpLeftCornerChartParser',
    # from earleychart.py:
    'IncrementalChartParser', 'EarleyChartParser', 
    'IncrementalTopDownChartParser', 'IncrementalBottomUpChartParser',
    'IncrementalBottomUpLeftCornerChartParser',
    'IncrementalLeftCornerChartParser',
    'FeatureIncrementalChartParser', 'FeatureEarleyChartParser',
    'FeatureIncrementalTopDownChartParser',
    'FeatureIncrementalBottomUpChartParser',
    'FeatureIncrementalBottomUpLeftCornerChartParser',
    # from dependencygraph.py, projectivedependencyparser.py,
    # projectivedependencyparser.py, malt.py:
    'DependencyGraph', 'nx_graph', 'ProjectiveDependencyParser',
    'ProbabilisticProjectiveDependencyParser',
    'NaiveBayesDependencyScorer', 'ProbabilisticNonprojectiveParser',
    'NonprojectiveDependencyParser', 'MaltParser',
    ]

