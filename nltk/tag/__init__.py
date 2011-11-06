# Natural Language Toolkit: Taggers
#
# Copyright (C) 2001-2011 NLTK Project
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au> (minor additions)
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
NLTK Taggers

Classes and interfaces for tagging each token of a sentence with
supplementary information, such as its part of speech.  This task,
which is known as X{tagging}, is defined by the L{TaggerI} interface.
"""

from .api        import TaggerI
from .util       import str2tuple, tuple2str, untag
from .simplify   import simplify_brown_tag, simplify_wsj_tag,\
                        simplify_indian_tag, simplify_alpino_tag, simplify_tag
from .sequential import SequentialBackoffTagger, ContextTagger, DefaultTagger,\
                        NgramTagger, UnigramTagger, BigramTagger, TrigramTagger,\
                        AffixTagger, RegexpTagger, ClassifierBasedTagger,\
                        ClassifierBasedPOSTagger 
from .brill      import BrillTagger, BrillTaggerTrainer, FastBrillTaggerTrainer   
from .tnt        import TnT
from .hunpos     import HunposTagger
from .stanford   import StanfordTagger
from .crf        import MalletCRF 

from ..data      import load

# Import hmm module if numpy is installed
try:
    import numpy
    from .hmm import HiddenMarkovModelTagger, HiddenMarkovModelTrainer
except ImportError:
    pass

# Standard treebank POS tagger
_POS_TAGGER = 'taggers/maxent_treebank_pos_tagger/english.pickle'
def pos_tag(tokens):
    """
    Use NLTK's currently recommended part of speech tagger to
    tag the given list of tokens.
    """
    tagger = load(_POS_TAGGER)
    return tagger.tag(tokens)

def batch_pos_tag(sentences):
    """
    Use NLTK's currently recommended part of speech tagger to tag the
    given list of sentences, each consisting of a list of tokens.
    """
    tagger = load(_POS_TAGGER)
    return tagger.batch_tag(sentences)
