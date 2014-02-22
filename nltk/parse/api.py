# Natural Language Toolkit: Parser API
#
# Copyright (C) 2001-2014 NLTK Project
# Author: Steven Bird <stevenbird1@gmail.com>
#         Edward Loper <edloper@gmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT
#

import itertools

from nltk.internals import overridden

class ParserI(object):
    """
    A processing class for deriving trees that represent possible
    structures for a sequence of tokens.  These tree structures are
    known as "parses".  Typically, parsers are used to derive syntax
    trees for sentences.  But parsers can also be used to derive other
    kinds of tree structure, such as morphological trees and discourse
    structures.

    Subclasses must define:
      - at least one of: ``parse()``, ``parse_sents()``.

    Subclasses may define:
      - ``grammar()``
      - either ``prob_parse()`` or ``prob_parse_sents()`` (or both)
    """
    def grammar(self):
        """
        :return: The grammar used by this parser.
        """
        raise NotImplementedError()

    def parse(self, sent):
        """
        :return: A list of parse trees for the sentence.
        When possible this list is sorted from most likely to least likely.

        :param sent: The sentence to be parsed
        :type sent: list(str)
        :rtype: list(Tree)
        """
        if overridden(self.parse_sents):
            return self.parse_sents([sent])[0]
        elif overridden(self.parse):
            return self.parse(sent)
        else:
            raise NotImplementedError()

    def prob_parse(self, sent):
        """
        :return: A probability distribution over the possible parse
        trees for the given sentence.  If there are no possible parse
        trees for the given sentence, return a probability distribution
        that assigns a probability of 1.0 to None.

        :param sent: The sentence to be parsed
        :type sent: list(str)
        :rtype: ProbDistI(Tree)
        """
        if overridden(self.prob_parse_sents):
            return self.prob_parse_sents([sent])[0]
        else:
            raise NotImplementedError()

    def parse_sents(self, sents):
        """
        Apply ``self.parse()`` to each element of ``sents``.
        :rtype: list(Tree)
        """
        return [self.parse(sent) for sent in sents]

    def prob_parse_sents(self, sents):
        """
        Apply ``self.prob_parse()`` to each element of ``sents``.  I.e.:

            return [self.prob_parse(sent) for sent in sents]

        :rtype: list(ProbDistI(Tree))
        """
        return [self.prob_parse(sent) for sent in sents]

