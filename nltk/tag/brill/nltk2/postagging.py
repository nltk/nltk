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

from __future__ import print_function

from nltk.tag.brill.nltk2.template import ProximateTokensRule


class ProximateTagsRule(ProximateTokensRule):
    """
    A rule which examines the tags of nearby tokens.
    See ``ProximateTokensRule`` for details.
    Also see ``SymmetricProximateTokensTemplate`` which generates these rules.
    """
    PROPERTY_NAME = 'tag' # for printing.
    yaml_tag = '!ProximateTagsRule'
    @staticmethod
    def extract_property(token):
        """:return: The given token's tag."""
        return token[1]


class ProximateWordsRule(ProximateTokensRule):
    """
    A rule which examines the base types of nearby tokens.
    See ``ProximateTokensRule`` for details.
    Also see ``SymmetricProximateTokensTemplate`` which generates these rules.
    """
    PROPERTY_NAME = 'text' # for printing.
    yaml_tag = '!ProximateWordsRule'
    @staticmethod
    def extract_property(token):
        """:return: The given token's text."""
        return token[0]

