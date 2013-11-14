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

import yaml


######################################################################
## Brill Rules
######################################################################

class BrillRule(yaml.YAMLObject):
    """
    An interface for tag transformations on a tagged corpus, as
    performed by brill taggers.  Each transformation finds all tokens
    in the corpus that are tagged with a specific original tag and
    satisfy a specific condition, and replaces their tags with a
    replacement tag.  For any given transformation, the original
    tag, replacement tag, and condition are fixed.  Conditions may
    depend on the token under consideration, as well as any other
    tokens in the corpus.

    Brill rules must be comparable and hashable.
    """
    def __init__(self, original_tag, replacement_tag):
        assert self.__class__ != BrillRule, \
               "BrillRule is an abstract base class"

        self.original_tag = original_tag
        """The tag which this BrillRule may cause to be replaced."""

        self.replacement_tag = replacement_tag
        """The tag with which this BrillRule may replace another tag."""

    def apply(self, tokens, positions=None):
        """
        Apply this rule at every position in positions where it
        applies to the given sentence.  I.e., for each position p
        in *positions*, if *tokens[p]* is tagged with this rule's
        original tag, and satisfies this rule's condition, then set
        its tag to be this rule's replacement tag.

        :param tokens: The tagged sentence
        :type tokens: list(tuple(str, str))
        :type positions: list(int)
        :param positions: The positions where the transformation is to
            be tried.  If not specified, try it at all positions.
        :return: The indices of tokens whose tags were changed by this
            rule.
        :rtype: int
        """
        if positions is None:
            positions = list(range(len(tokens)))

        # Determine the indices at which this rule applies.
        change = [i for i in positions if self.applies(tokens, i)]

        # Make the changes.  Note: this must be done in a separate
        # step from finding applicable locations, since we don't want
        # the rule to interact with itself.
        for i in change:
            tokens[i] = (tokens[i][0], self.replacement_tag)

        return change

    def applies(self, tokens, index):
        """
        :return: True if the rule would change the tag of
            ``tokens[index]``, False otherwise
        :rtype: bool
        :param tokens: A tagged sentence
        :type tokens: list(str)
        :param index: The index to check
        :type index: int
        """
        assert False, "Brill rules must define applies()"

    # Rules must be comparable and hashable for the algorithm to work
    def __eq__(self):
        assert False, "Brill rules must be comparable"
    def __ne__(self):
        assert False, "Brill rules must be comparable"
    def __hash__(self):
        assert False, "Brill rules must be hashable"
