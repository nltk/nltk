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
      - at least one of: ``parse()``, ``nbest_parse()``, ``iter_parse()``,
        ``parse_sents()``, ``nbest_parse_sents()``, ``iter_parse_sents()``.

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
        :return: A parse tree that represents the structure of the
        given sentence, or None if no parse tree is found.  If
        multiple parses are found, then return the best parse.

        :param sent: The sentence to be parsed
        :type sent: list(str)
        :rtype: Tree
        """
        if overridden(self.parse_sents):
            return self.parse_sents([sent])[0]
        else:
            trees = self.nbest_parse(sent, 1)
            if trees: return trees[0]
            else: return None

    def nbest_parse(self, sent, n=None):
        """
        :return: A list of parse trees that represent possible
        structures for the given sentence.  When possible, this list is
        sorted from most likely to least likely.  If ``n`` is
        specified, then the returned list will contain at most ``n``
        parse trees.

        :param sent: The sentence to be parsed
        :type sent: list(str)
        :param n: The maximum number of trees to return.
        :type n: int
        :rtype: list(Tree)
        """
        if overridden(self.nbest_parse_sents):
            return self.nbest_parse_sents([sent],n)[0]
        elif overridden(self.parse) or overridden(self.parse_sents):
            tree = self.parse(sent)
            if tree: return [tree]
            else: return []
        else:
            return list(itertools.islice(self.iter_parse(sent), n))

    def iter_parse(self, sent):
        """
        :return: An iterator that generates parse trees that represent
        possible structures for the given sentence.  When possible,
        this list is sorted from most likely to least likely.

        :param sent: The sentence to be parsed
        :type sent: list(str)
        :rtype: iter(Tree)
        """
        if overridden(self.iter_parse_sents):
            return self.iter_parse_sents([sent])[0]
        elif overridden(self.nbest_parse) or overridden(self.nbest_parse_sents):
            return iter(self.nbest_parse(sent))
        elif overridden(self.parse) or overridden(self.parse_sents):
            tree = self.parse(sent)
            if tree: return iter([tree])
            else: return iter([])
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
            raise NotImplementedError

    def parse_sents(self, sents):
        """
        Apply ``self.parse()`` to each element of ``sents``.  I.e.:

            return [self.parse(sent) for sent in sents]

        :rtype: list(Tree)
        """
        return [self.parse(sent) for sent in sents]

    def nbest_parse_sents(self, sents, n=None):
        """
        Apply ``self.nbest_parse()`` to each element of ``sents``.  I.e.:

            return [self.nbest_parse(sent, n) for sent in sents]

        :rtype: list(list(Tree))
        """
        return [self.nbest_parse(sent,n ) for sent in sents]

    def iter_parse_sents(self, sents):
        """
        Apply ``self.iter_parse()`` to each element of ``sents``.  I.e.:

            return [self.iter_parse(sent) for sent in sents]

        :rtype: list(iter(Tree))
        """
        return [self.iter_parse(sent) for sent in sents]

    def prob_parse_sents(self, sents):
        """
        Apply ``self.prob_parse()`` to each element of ``sents``.  I.e.:

            return [self.prob_parse(sent) for sent in sents]

        :rtype: list(ProbDistI(Tree))
        """
        return [self.prob_parse(sent) for sent in sents]

