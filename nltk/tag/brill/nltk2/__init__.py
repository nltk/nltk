# -*- coding: utf-8 -*-
# Natural Language Toolkit: Brill Tagger
#
# Copyright (C) 2001-2013 NLTK Project
# Authors: Christopher Maloof <cjmaloof@gradient.cis.upenn.edu>
#          Edward Loper <edloper@gmail.com>
#          Steven Bird <stevenbird1@gmail.com>
#          Marcus Uneson <marcus.uneson@gmail.com>
# URL: <http://nltk.org/>
# For license information, see  LICENSE.TXT

"""
Brill Tagger

The Brill Tagger is a transformational rule-based tagger.
It starts by running an initial tagger, and then
improves the tagging by applying a list of transformation rules.
These transformation rules are automatically learned from the training
corpus, based on one or more "rule templates."

    >>> from nltk.tag import RegexpTagger
    >>> from nltk.tag.brill import FastBrillTaggerTrainer
    >>> from nltk.tag.brill.nltk2 import ProximateTokensTemplate, SymmetricProximateTokensTemplate
    >>> from nltk.tag.brill.nltk2 import ProximateTagsRule, ProximateWordsRule
    >>> from nltk.corpus import brown
    >>> from nltk.tag import UnigramTagger
    >>> brown_train = list(brown.tagged_sents(categories='news')[:100])
    >>> brown_test = list(brown.tagged_sents(categories='news')[100:200])

    >>> backoff = RegexpTagger([
    ... (r'^-?[0-9]+(.[0-9]+)?$', 'CD'),   # cardinal numbers
    ... (r'(The|the|A|a|An|an)$', 'AT'),   # articles
    ... (r'.*able$', 'JJ'),                # adjectives
    ... (r'.*ness$', 'NN'),                # nouns formed from adjectives
    ... (r'.*ly$', 'RB'),                  # adverbs
    ... (r'.*s$', 'NNS'),                  # plural nouns
    ... (r'.*ing$', 'VBG'),                # gerunds
    ... (r'.*ed$', 'VBD'),                 # past tense verbs
    ... (r'.*', 'NN')                      # nouns (default)
    ... ])

    #!!TODO: update to use baseline = tag.UnigramTagger(training_data,
    #backoff=backoff) as soon as UT gives consistent results for different python versions
    >>> baseline = backoff
    >>> templates = [
    ...     SymmetricProximateTokensTemplate(ProximateTagsRule, (1,1)),
    ...     SymmetricProximateTokensTemplate(ProximateTagsRule, (2,2)),
    ...     SymmetricProximateTokensTemplate(ProximateTagsRule, (1,2)),
    ...     SymmetricProximateTokensTemplate(ProximateTagsRule, (1,3)),
    ...     SymmetricProximateTokensTemplate(ProximateWordsRule, (1,1)),
    ...     SymmetricProximateTokensTemplate(ProximateWordsRule, (2,2)),
    ...     SymmetricProximateTokensTemplate(ProximateWordsRule, (1,2)),
    ...     SymmetricProximateTokensTemplate(ProximateWordsRule, (1,3)),
    ...     ProximateTokensTemplate(ProximateTagsRule, (-1, -1), (1,1)),
    ...     ProximateTokensTemplate(ProximateWordsRule, (-1, -1), (1,1)),
    ...     ]
    >>> trainer = FastBrillTaggerTrainer(initial_tagger=baseline,
    ...                                  templates=templates, trace=3,
    ...                                  deterministic=True)
    >>> brill_tagger = trainer.train(brown_train, max_rules=10)
    TBL train (fast) (seqs: 100; tokens: 2268; tpls: 10; min score: 2; min acc: None)
    Finding initial useful rules...
        Found 17801 useful rules.
    <BLANKLINE>
               B      |
       S   F   r   O  |        Score = Fixed - Broken
       c   i   o   t  |  R     Fixed = num tags changed incorrect -> correct
       o   x   k   h  |  u     Broken = num tags changed correct -> incorrect
       r   e   e   e  |  l     Other = num tags changed incorrect -> incorrect
       e   d   n   r  |  e
    ------------------+-------------------------------------------------------
      68  71   3  86  | NN -> IN if the tag of the following word is 'AT'
      27  36   9   2  | VBD -> VBN if the tag of words i-3...i-1 is 'NNS'
      16  16   0   0  | IN -> VB if the text of the preceding word is 'to'
      16  16   0   0  | NN -> TO if the tag of the following word is 'VB'
      14  18   4   9  | NN -> VB if the text of the preceding word is 'to'
      24  24   0   7  | NN -> TO if the tag of the following word is 'VB'
      13  15   2  17  | NN -> NN-TL if the text of words i-3...i-1 is 'Fulton'
      12  15   3   5  | NN -> . if the text of the preceding word is ''''
      23  23   0   0  | NN -> '' if the tag of the following word is '.'
      12  14   2   0  | NN -> MD if the text of the following word is 'be'


    >>> brill_tagger.evaluate(brown_test) # doctest: +ELLIPSIS
    0.4088397...

"""



from nltk.tag.brill.nltk2.postagging import (ProximateTagsRule,
                                             ProximateWordsRule)
from nltk.tag.brill.nltk2.template import (ProximateTokensRule,
                                           ProximateTokensTemplate,
                                           SymmetricProximateTokensTemplate)
from nltk.tag.brill.trainer.fast import FastBrillTaggerTrainer
from nltk.tag.brill.trainer.brillorig import BrillTaggerTrainer
from nltk.tag.brill.tagger import BrillTagger
