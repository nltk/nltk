# -*- coding: utf-8 -*-
# Natural Language Toolkit: Taggers
#
# Copyright (C) 2001-2017 NLTK Project
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

    >>> from nltk import pos_tag, word_tokenize
    >>> pos_tag(word_tokenize("John's big idea isn't all that bad."))
    [('John', 'NNP'), ("'s", 'POS'), ('big', 'JJ'), ('idea', 'NN'), ('is', 'VBZ'),
    ("n't", 'RB'), ('all', 'PDT'), ('that', 'DT'), ('bad', 'JJ'), ('.', '.')]

This package defines several taggers, which take a list of tokens,
assign a tag to each one, and return the resulting list of tagged tokens.
Most of the taggers are built automatically based on a training corpus.
For example, the unigram tagger tags each word *w* by checking what
the most frequent tag for *w* was in a training corpus:

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
from nltk.tag.perceptron    import PerceptronTagger

from nltk.data import load, find

RUS_PICKLE = 'taggers/averaged_perceptron_tagger_ru/averaged_perceptron_tagger_ru.pickle'


def _get_tagger(lang=None):
    if lang == 'rus':
        tagger = PerceptronTagger(False)
        ap_russian_model_loc = 'file:' + str(find(RUS_PICKLE))
        tagger.load(ap_russian_model_loc)
    elif lang == 'eng':
        tagger = PerceptronTagger()
    else:
        tagger = PerceptronTagger()
    return tagger


def _pos_tag(tokens, tagset, tagger):
    tagged_tokens = tagger.tag(tokens)
    if tagset:
        tagged_tokens = [(token, map_tag('en-ptb', tagset, tag)) for (token, tag) in tagged_tokens]
    return tagged_tokens


def pos_tag(tokens, tagset=None, lang='eng'):
    """
    Use NLTK's currently recommended part of speech tagger to
    tag the given list of tokens.

        >>> from nltk.tag import pos_tag
        >>> from nltk.tokenize import word_tokenize
        >>> pos_tag(word_tokenize("John's big idea isn't all that bad."))
        [('John', 'NNP'), ("'s", 'POS'), ('big', 'JJ'), ('idea', 'NN'), ('is', 'VBZ'),
        ("n't", 'RB'), ('all', 'PDT'), ('that', 'DT'), ('bad', 'JJ'), ('.', '.')]
        >>> pos_tag(word_tokenize("John's big idea isn't all that bad."), tagset='universal')
        [('John', 'NOUN'), ("'s", 'PRT'), ('big', 'ADJ'), ('idea', 'NOUN'), ('is', 'VERB'),
        ("n't", 'ADV'), ('all', 'DET'), ('that', 'DET'), ('bad', 'ADJ'), ('.', '.')]

    NB. Use `pos_tag_sents()` for efficient tagging of more than one sentence.

    :param tokens: Sequence of tokens to be tagged
    :type tokens: list(str)
    :param tagset: the tagset to be used, e.g. universal, wsj, brown
    :type tagset: str
    :param lang: the ISO 639 code of the language, e.g. 'eng' for English, 'rus' for Russian
    :type lang: str
    :return: The tagged tokens
    :rtype: list(tuple(str, str))
    """
    tagger = _get_tagger(lang)
    return _pos_tag(tokens, tagset, tagger)    


def pos_tag_sents(sentences, tagset=None, lang='eng'):
    """
    Use NLTK's currently recommended part of speech tagger to tag the
    given list of sentences, each consisting of a list of tokens.

    :param tokens: List of sentences to be tagged
    :type tokens: list(list(str))
    :param tagset: the tagset to be used, e.g. universal, wsj, brown
    :type tagset: str
    :param lang: the ISO 639 code of the language, e.g. 'eng' for English, 'rus' for Russian
    :type lang: str
    :return: The list of tagged sentences
    :rtype: list(list(tuple(str, str)))
    """
    tagger = _get_tagger(lang)
    return [_pos_tag(sent, tagset, tagger) for sent in sentences]
