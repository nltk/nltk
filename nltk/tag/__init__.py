# Natural Language Toolkit: Taggers
#
# Copyright (C) 2001-2012 NLTK Project
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au> (minor additions)
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
NLTK Taggers

This package contains classes and interfaces for part-of-speech
tagging, or simply "tagging".

A "tag" is a case-sensitive string that specifies some property of a token,
such as its part of speech.  Tagged tokens are encoded as tuples
``(tag, token)``.  For example, the following tagged token combines
the word ``'fly'`` with a noun part of speech tag (``'NN'``):

    >>> tagged_tok = ('fly', 'NN')

An off-the-shelf tagger is available.  It uses the Penn Treebank tagset:

    >>> from nltk.tag import pos_tag
    >>> from nltk.tokenize import word_tokenize
    >>> pos_tag(word_tokenize("John's big idea isn't all that bad."))
    [('John', 'NNP'), ("'s", 'POS'), ('big', 'JJ'), ('idea', 'NN'), ('is',
    'VBZ'), ("n't", 'RB'), ('all', 'DT'), ('that', 'DT'), ('bad', 'JJ'),
    ('.', '.')]

This package defines several taggers, which take a token list (typically a
sentence), assign a tag to each token, and return the resulting list of
tagged tokens.  Most of the taggers are built automatically based on a
training corpus.  For example, the unigram tagger tags each word *w*
by checking what the most frequent tag for *w* was in a training corpus:

    >>> from nltk.corpus import brown
    >>> from nltk.tag import UnigramTagger
    >>> tagger = UnigramTagger(brown.tagged_sents(categories='news')[:500])
    >>> tagger.tag(['Mitchell', 'decried', 'the', 'high', 'rate', 'of', 'unemployment'])
    [('Mitchell', 'NP'), ('decried', None), ('the', 'AT'), ('high', 'JJ'),
    ('rate', 'NN'), ('of', 'IN'), ('unemployment', None)]

Note that words that the tagger has not seen during training receive a tag
of ``None``.

We evaluate a tagger on data that was not seen during training:

    >>> tagger.evaluate(brown.tagged_sents(categories='news')[500:600]) # doctest: +ELLIPSIS
    0.734...

For more information, please consult chapter 5 of the NLTK Book.
"""

from nltk.tag.api        import TaggerI
from nltk.tag.util       import str2tuple, tuple2str, untag
from nltk.tag.simplify   import (simplify_brown_tag, simplify_wsj_tag,
                                 simplify_indian_tag, simplify_alpino_tag,
                                 simplify_tag)
from nltk.tag.sequential import (SequentialBackoffTagger, ContextTagger,
                                 DefaultTagger, NgramTagger, UnigramTagger,
                                 BigramTagger, TrigramTagger, AffixTagger,
                                 RegexpTagger, ClassifierBasedTagger,
                                 ClassifierBasedPOSTagger)
from nltk.tag.brill      import BrillTagger, BrillTaggerTrainer, FastBrillTaggerTrainer
from nltk.tag.tnt        import TnT
from nltk.tag.hunpos     import HunposTagger
from nltk.tag.stanford   import StanfordTagger
from nltk.tag.crf        import MalletCRF

from nltk.data      import load

# Import hmm module if numpy is installed
try:
    import numpy
    from nltk.tag.hmm import HiddenMarkovModelTagger, HiddenMarkovModelTrainer
except ImportError:
    pass

# Standard treebank POS tagger
_POS_TAGGER = 'taggers/maxent_treebank_pos_tagger/english.pickle'
def pos_tag(tokens):
    """
    Use NLTK's currently recommended part of speech tagger to
    tag the given list of tokens.

        >>> from nltk.tag import pos_tag
        >>> from nltk.tokenize import word_tokenize
        >>> pos_tag(word_tokenize("John's big idea isn't all that bad."))
        [('John', 'NNP'), ("'s", 'POS'), ('big', 'JJ'), ('idea', 'NN'), ('is',
        'VBZ'), ("n't", 'RB'), ('all', 'DT'), ('that', 'DT'), ('bad', 'JJ'),
        ('.', '.')]

    :param tokens: Sequence of tokens to be tagged
    :type tokens: list(str)
    :return: The tagged tokens
    :rtype: list(tuple(str, str))
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


if __name__ == "__main__":
    import doctest
    doctest.testmod(optionflags=doctest.NORMALIZE_WHITESPACE)
