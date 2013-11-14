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

from collections import defaultdict
import yaml

from nltk.tag.api import TaggerI

__author__ = 'ling-mun'

######################################################################
## The Brill Tagger
######################################################################

class BrillTagger(TaggerI, yaml.YAMLObject):
    """
    Brill's transformational rule-based tagger.  Brill taggers use an
    initial tagger (such as ``tag.DefaultTagger``) to assign an initial
    tag sequence to a text; and then apply an ordered list of
    transformational rules to correct the tags of individual tokens.
    These transformation rules are specified by the ``BrillRule``
    interface.

    Brill taggers can be created directly, from an initial tagger and
    a list of transformational rules; but more often, Brill taggers
    are created by learning rules from a training corpus, using either
    ``BrillTaggerTrainer`` or ``FastBrillTaggerTrainer``.
    """

    yaml_tag = '!nltk.BrillTagger'
    def __init__(self, initial_tagger, rules):
        """
        :param initial_tagger: The initial tagger
        :type initial_tagger: TaggerI
        :param rules: An ordered list of transformation rules that
            should be used to correct the initial tagging.
        :type rules: list(BrillRule)
        """
        self._initial_tagger = initial_tagger
        self._rules = tuple(rules)

    def rules(self):
        return self._rules

    def tag(self, tokens):
        # Inherit documentation from TaggerI

        # Run the initial tagger.
        tagged_tokens = self._initial_tagger.tag(tokens)

        # Create a dictionary that maps each tag to a list of the
        # indices of tokens that have that tag.
        tag_to_positions = defaultdict(set)
        for i, (token, tag) in enumerate(tagged_tokens):
            tag_to_positions[tag].add(i)

        # Apply each rule, in order.  Only try to apply rules at
        # positions that have the desired original tag.
        for rule in self._rules:
            # Find the positions where it might apply
            positions = tag_to_positions.get(rule.original_tag, [])
            # Apply the rule at those positions.
            changed = rule.apply(tagged_tokens, positions)
            # Update tag_to_positions with the positions of tags that
            # were modified.
            for i in changed:
                tag_to_positions[rule.original_tag].remove(i)
                tag_to_positions[rule.replacement_tag].add(i)

        return tagged_tokens

