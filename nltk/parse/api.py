# Natural Language Toolkit: Parser API
#
# Copyright (C) 2001-2011 NLTK Project
# Author: Steven Bird <sb@csse.unimelb.edu.au>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT
#

import itertools

from nltk.internals import overridden

class ParserI(object):
    """
    A processing class for deriving trees that represent possible
    structures for a sequence of tokens.  These tree structures are
    known as X{parses}.  Typically, parsers are used to derive syntax
    trees for sentences.  But parsers can also be used to derive other
    kinds of tree structure, such as morphological trees and discourse
    structures.
    
    Subclasses must define:
      - at least one of: L{parse()}, L{nbest_parse()}, L{iter_parse()},
        L{batch_parse()}, L{batch_nbest_parse()}, L{batch_iter_parse()}.

    Subclasses may define:
      - L{grammar()}
      - either L{prob_parse()} or L{batch_prob_parse()} (or both)
    """
    def grammar(self):
        """
        @return: The grammar used by this parser.
        """
        raise NotImplementedError()
    
    def parse(self, sent):
        """
        @return: A parse tree that represents the structure of the
        given sentence, or C{None} if no parse tree is found.  If
        multiple parses are found, then return the best parse.
        
        @param sent: The sentence to be parsed
        @type sent: L{list} of L{string}
        @rtype: L{Tree}
        """
        if overridden(self.batch_parse):
            return self.batch_parse([sent])[0]
        else:
            trees = self.nbest_parse(sent, 1)
            if trees: return trees[0]
            else: return None

    def nbest_parse(self, sent, n=None):
        """
        @return: A list of parse trees that represent possible
        structures for the given sentence.  When possible, this list is
        sorted from most likely to least likely.  If C{n} is
        specified, then the returned list will contain at most C{n}
        parse trees.
        
        @param sent: The sentence to be parsed
        @type sent: L{list} of L{string}
        @param n: The maximum number of trees to return.
        @type n: C{int}
        @rtype: C{list} of L{Tree}
        """
        if overridden(self.batch_nbest_parse):
            return self.batch_nbest_parse([sent],n)[0]
        elif overridden(self.parse) or overridden(self.batch_parse):
            tree = self.parse(sent)
            if tree: return [tree]
            else: return []
        else:
            return list(itertools.islice(self.iter_parse(sent), n))

    def iter_parse(self, sent):
        """
        @return: An iterator that generates parse trees that represent
        possible structures for the given sentence.  When possible,
        this list is sorted from most likely to least likely.
        
        @param sent: The sentence to be parsed
        @type sent: L{list} of L{string}
        @rtype: C{iterator} of L{Tree}
        """
        if overridden(self.batch_iter_parse):
            return self.batch_iter_parse([sent])[0]
        elif overridden(self.nbest_parse) or overridden(self.batch_nbest_parse):
            return iter(self.nbest_parse(sent))
        elif overridden(self.parse) or overridden(self.batch_parse):
            tree = self.parse(sent)
            if tree: return iter([tree])
            else: return iter([])
        else:
            raise NotImplementedError()

    def prob_parse(self, sent):
        """
        @return: A probability distribution over the possible parse
        trees for the given sentence.  If there are no possible parse
        trees for the given sentence, return a probability distribution
        that assigns a probability of 1.0 to C{None}.
        
        @param sent: The sentence to be parsed
        @type sent: L{list} of L{string}
        @rtype: L{ProbDistI} of L{Tree}
        """
        if overridden(self.batch_prob_parse):
            return self.batch_prob_parse([sent])[0]
        else:
            raise NotImplementedError

    def batch_parse(self, sents):
        """
        Apply L{self.parse()} to each element of C{sents}.  I.e.:

            >>> return [self.parse(sent) for sent in sents]

        @rtype: C{list} of L{Tree}
        """
        return [self.parse(sent) for sent in sents]

    def batch_nbest_parse(self, sents, n=None):
        """
        Apply L{self.nbest_parse()} to each element of C{sents}.  I.e.:

            >>> return [self.nbest_parse(sent, n) for sent in sents]

        @rtype: C{list} of C{list} of L{Tree}
        """
        return [self.nbest_parse(sent,n ) for sent in sents]

    def batch_iter_parse(self, sents):
        """
        Apply L{self.iter_parse()} to each element of C{sents}.  I.e.:

            >>> return [self.iter_parse(sent) for sent in sents]

        @rtype: C{list} of C{iterator} of L{Tree}
        """
        return [self.iter_parse(sent) for sent in sents]

    def batch_prob_parse(self, sents):
        """
        Apply L{self.prob_parse()} to each element of C{sents}.  I.e.:

            >>> return [self.prob_parse(sent) for sent in sents]

        @rtype: C{list} of L{ProbDistI} of L{Tree}
        """
        return [self.prob_parse(sent) for sent in sents]

