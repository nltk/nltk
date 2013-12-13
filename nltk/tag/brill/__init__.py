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
corpus, based on one or more rule templates, which is the main
mechanism for encoding domain knowledge to the system.
"""


#here goes imports which are re-exported for convenient top-level import
#(as nltk.tag.brill.*)

from nltk.tag.brill.template import (
    Template,         #API: Template(...), Template.expand(...)
    Feature           #API: Feature(...), Feature.expand(...)
    )
from nltk.tag.brill.rule import (
    Rule              #API: Rule.format(...), Rule.templatetid
    )

from nltk.tag.brill.erroranalysis import error_list

from nltk.tag.brill.trainer.fast import (
    TaggerTrainer     #API: TaggerTrainer(...), TaggerTrainer.train(...)
    )

from nltk.tag.brill.trainer.fast import (
    TaggerTrainer     #API: TaggerTrainer(...), TaggerTrainer.train(...);
    )

#for reference:
#API of nltk.tag.brill.tagger.BrillTagger,
#returned by TaggerTrainer.train(...):
#    t = TaggerTrainer.train(...)
#    t.rules(...)
#    t.train_stats(...)
#    t.tag(...)
#    t.batch_tag_incremental(...)
#    t.print_template_statistics(...)
#    t.batch_tag(...)
#    t.evaluate(...)



from nltk.tag.brill.trainer import TaggerTrainer
from nltk.tag.brill.tagger import BrillTagger
from nltk.tag.brill.erroranalysis import error_list
from nltk.tag.brill.template import Template

