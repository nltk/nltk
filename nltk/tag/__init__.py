# -*- coding: utf-8 -*-
# Natural Language Toolkit: Taggers
#
# Copyright (C) 2001-2015 NLTK Project
# Author: Edward Loper <edloper@gmail.com>
#         Steven Bird <stevenbird1@gmail.com> (minor additions)
# URL: <http://nltk.org/>
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

    >>> from nltk.tag import pos_tag  # doctest: +SKIP
    >>> from nltk.tokenize import word_tokenize # doctest: +SKIP
    >>> pos_tag(word_tokenize("John's big idea isn't all that bad.")) # doctest: +SKIP
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
    >>> sent = ['Mitchell', 'decried', 'the', 'high', 'rate', 'of', 'unemployment']
    >>> for word, tag in tagger.tag(sent):
    ...     print(word, '->', tag)
    Mitchell -> NP
    decried -> None
    the -> AT
    high -> JJ
    rate -> NN
    of -> IN
    unemployment -> None

Note that words that the tagger has not seen during training receive a tag
of ``None``.

We evaluate a tagger on data that was not seen during training:

    >>> tagger.evaluate(brown.tagged_sents(categories='news')[500:600])
    0.73...

For more information, please consult chapter 5 of the NLTK Book.
"""
from __future__ import print_function

from nltk.tag.api           import TaggerI
from nltk.tag.util          import str2tuple, tuple2str, untag
from nltk.tag.sequential    import (SequentialBackoffTagger, ContextTagger,
                                    DefaultTagger, NgramTagger, UnigramTagger,
                                    BigramTagger, TrigramTagger, AffixTagger,
                                    RegexpTagger, ClassifierBasedTagger,
                                    ClassifierBasedPOSTagger)
from nltk.tag.brill         import BrillTagger
from nltk.tag.brill_trainer import BrillTaggerTrainer
from nltk.tag.tnt           import TnT
from nltk.tag.hunpos        import HunposTagger
from nltk.tag.stanford      import StanfordTagger, StanfordPOSTagger, StanfordNERTagger
from nltk.tag.hmm           import HiddenMarkovModelTagger, HiddenMarkovModelTrainer
from nltk.tag.senna         import SennaTagger, SennaChunkTagger, SennaNERTagger
from nltk.tag.mapping       import tagset_mapping, map_tag
from nltk.tag.crf           import CRFTagger

from nltk.data import load


# Standard treebank POS tagger
_POS_TAGGER = 'taggers/maxent_treebank_pos_tagger/english.pickle'

def pos_tag(tokens, tagset=None):
    """
    Use NLTK's currently recommended part of speech tagger to
    tag the given list of tokens.

        >>> from nltk.tag import pos_tag # doctest: +SKIP
        >>> from nltk.tokenize import word_tokenize # doctest: +SKIP
        >>> pos_tag(word_tokenize("John's big idea isn't all that bad.")) # doctest: +SKIP
        [('John', 'NNP'), ("'s", 'POS'), ('big', 'JJ'), ('idea', 'NN'), ('is',
        'VBZ'), ("n't", 'RB'), ('all', 'DT'), ('that', 'DT'), ('bad', 'JJ'),
        ('.', '.')]

    :param tokens: Sequence of tokens to be tagged
    :type tokens: list(str)
    :return: The tagged tokens
    :rtype: list(tuple(str, str))
    """
    tagger = load(_POS_TAGGER)
    if tagset:
        return [(token, map_tag('en-ptb', tagset, tag)) for (token, tag) in tagger.tag(tokens)]
    return tagger.tag(tokens)

def pos_tag_sents(sentences):
    """
    Use NLTK's currently recommended part of speech tagger to tag the
    given list of sentences, each consisting of a list of tokens.
    """
    tagger = load(_POS_TAGGER)
    return tagger.tag_sents(sentences)


if __name__ == "__main__":
    import doctest
    doctest.testmod(optionflags=doctest.NORMALIZE_WHITESPACE)
