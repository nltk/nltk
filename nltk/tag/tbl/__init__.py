# -*- coding: utf-8 -*-
# Natural Language Toolkit: Transformation-based learning
#
# Copyright (C) 2001-2013 NLTK Project
# Author: Marcus Uneson <marcus.uneson@gmail.com>
#   based on previous (nltk2) version by
#   Christopher Maloof, Edward Loper, Steven Bird
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
#(as nltk.tag.tbl.*)

from nltk.tag.tbl.template import Template
#API: Template(...), Template.expand(...)

from nltk.tag.tbl.task.api import Feature
#API: Feature(...), Feature.expand(...)

from nltk.tag.tbl.rule import Rule
#API: Rule.format(...), Rule.templatetid

from nltk.tag.tbl.erroranalysis import error_list

from nltk.tag.tbl.trainer.fast import TaggerTrainer
#API: TaggerTrainer(...), TaggerTrainer.train(...)

#for reference:
#API of nltk.tag.tbl.tagger.BrillTagger,
#returned by TaggerTrainer.train(...):
#    t = TaggerTrainer.train(...)
#    t.rules(...)
#    t.train_stats(...)
#    t.tag(...)
#    t.batch_tag_incremental(...)
#    t.print_template_statistics(...)
#    t.batch_tag(...)
#    t.evaluate(...)

#some additional exports, not part of the primary API but used in some doctests
#(candidates for deletion)
from nltk.tag.tbl.trainer.fast import FastBrillTaggerTrainer
from nltk.tag.tbl.trainer.brillorig import BrillTaggerTrainer
from nltk.tag.tbl.tagger import BrillTagger

