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

from nltk.tag.brill import template

class Word(template.Feature):
    """
    Feature which examines the text (word) of nearby tokens.
    """

    @staticmethod
    def extract_property(tokens, index):
        """@return: The given token's text."""
        return tokens[index][0]


class Tag(template.Feature):
    """
    Feature which examines the tags of nearby tokens.
    """

    @staticmethod
    def extract_property(tokens, index):
        """@return: The given token's tag."""
        return tokens[index][1]

