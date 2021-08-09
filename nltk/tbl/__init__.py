# Natural Language Toolkit: Transformation-based learning
#
# Copyright (C) 2001-2021 NLTK Project
# Author: Marcus Uneson <marcus.uneson@gmail.com>
#   based on previous (nltk2) version by
#   Christopher Maloof, Edward Loper, Steven Bird
# URL: <http://nltk.org/>
# For license information, see  LICENSE.TXT

"""
Transformation Based Learning

A general purpose package for Transformation Based Learning,
currently used by nltk.tag.BrillTagger.
"""

from nltk.tbl.erroranalysis import error_list
from nltk.tbl.feature import Feature
from nltk.tbl.rule import Rule
from nltk.tbl.template import Template

# API: Template(...), Template.expand(...)


# API: Feature(...), Feature.expand(...)


# API: Rule.format(...), Rule.templatetid
