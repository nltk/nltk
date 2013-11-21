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

    >>> from nltk.tag.brill import FastBrillTaggerTrainer
    >>> from nltk.tag.brill.nltk2 import ProximateTokensTemplate, SymmetricProximateTokensTemplate
    >>> from nltk.tag.brill.nltk2 import ProximateTagsRule, ProximateWordsRule
    >>> from nltk.corpus import brown
    >>> from nltk.tag import UnigramTagger
    >>> brown_train = list(brown.tagged_sents(categories='news')[:500])
    >>> brown_test = list(brown.tagged_sents(categories='news')[500:600])
    >>> unigram_tagger = UnigramTagger(brown_train)
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
    >>> trainer = FastBrillTaggerTrainer(initial_tagger=unigram_tagger,
    ...                                  templates=templates, trace=3,
    ...                                  deterministic=True)
    >>> brill_tagger = trainer.train(brown_train, max_rules=10)
    TBL train (fast) (seqs: 500; tokens: 11711; tpls: 10; min score: 2; min acc: None)
    Finding initial useful rules...
        Found 10203 useful rules.
    <BLANKLINE>
               B      |
       S   F   r   O  |        Score = Fixed - Broken
       c   i   o   t  |  R     Fixed = num tags changed incorrect -> correct
       o   x   k   h  |  u     Broken = num tags changed correct -> incorrect
       r   e   e   e  |  l     Other = num tags changed incorrect -> incorrect
       e   d   n   r  |  e
    ------------------+-------------------------------------------------------
      46  46   0   0  | TO -> IN if the tag of the following word is 'AT'
      18  20   2   0  | TO -> IN if the tag of words i+1...i+3 is 'CD'
      14  14   0   0  | IN -> IN-TL if the tag of the preceding word is 'NN-TL',
                      |   and the tag of the following word is 'NN-TL'
      11  16   5   0  | NP -> NP-TL if the tag of the following word is 'NN-TL'
      11  11   0   0  | TO -> IN if the tag of the following word is 'JJ'
      11  11   0   1  | TO -> IN if the tag of the following word is 'NNS'
       9   9   0   0  | , -> ,-HL if the tag of the preceding word is 'NP-HL'
       9  11   2   0  | PPS -> PPO if the tag of words i-3...i-1 is 'VB'
       8  13   5   0  | NN -> VB if the tag of the preceding word is 'TO'
       7   7   0   1  | NN -> VB if the tag of the preceding word is 'MD'
    >>> round(brill_tagger.evaluate(brown_test), 4)
    0.7445

"""



from nltk.tag.brill.nltk2.postagging import (ProximateTagsRule,
                                             ProximateWordsRule)
from nltk.tag.brill.nltk2.template import (ProximateTokensRule,
                                           ProximateTokensTemplate,
                                           SymmetricProximateTokensTemplate)
from nltk.tag.brill.trainer.fast import FastBrillTaggerTrainer
from nltk.tag.brill.trainer.brillorig import BrillTaggerTrainer
from nltk.tag.brill.tagger import BrillTagger

