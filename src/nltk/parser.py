# Natural Language Toolkit: Parsers
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

# Todo:
#    - Rewrite the module-level docstring

"""
Interface for producing tree structures that represent the internal
organziation of a text.  This task is known as X{parsing} the text,
and the resulting tree structures are called the text's X{parses}.
Typically, the text is a single sentence, and the tree structure
represents the syntactic structure of the sentence.  However, parsers
can also be used in other domains.  For example, parsers could be used
to derive the morphological structure of the morphemes that make up a
word, or to derive the discourse structure of a list of utterances.

Sometimes, a single piece of text can be represented by more than one
tree structure.  Texts represented by more than one tree structure are
called X{ambiguous} texts.  Note that there are actually two ways in
which a text can be ambiguous:

    - The text has multiple correct parses.
    - There is not enough information to decide which of several
      candidate parses is correct.

However, the parser module does I{not} distinguish these two types of
ambiguity.
"""

class ParserI:
    """
    A processing interface for deriving trees that represent possible
    structures for a sequence of tokens.  These tree structures are
    known as X{parses}.  Typically, parsers are used to derive syntax
    trees for sentences.  But parsers can also be used to derive other
    kinds of tree structure, such as morphological trees and discourse
    structures.

    A parse for a text assigns a tree structure to that text, but does
    not modify the text itself.  In particular, if M{t} is a text,
    then the leaves of any parse of M{t} should be M{t}.

    Parsing a text generates zero or more parses.  Abstractly, each of
    these parses has a X{quality} associated with it.  These quality
    ratings are used to decide which parses to return.  In particular,
    the C{parse} method returns the parse with the highest quality;
    and the C{parse_n} method returns a list of parses, sorted by
    their quality.

    If multiple parses have the same quality, then C{parse} and
    C{parse_n} can choose between them arbitrarily.  In particular,
    for some parsers, all parses have the same quality.  For these
    parsers, C{parse} returns a single arbitrary parse, and C{parse_n}
    returns an list of parses in arbitrary order.
    """
    def __init__(self):
        """
        Construct a new C{Parser}.
        """
        assert 0, "ParserI is an abstract interface"

    def parse(self, text):
        """
        Return the best parse for the given text, or C{None} if no
        parses are available.
        
        @return: The highest-quality parse for the given text.  If
            multiple parses are tied for the highest quality, then
            choose one arbitrarily.  If no parse is available for the
            given text, return C{None}.
        @rtype: C{TreeToken} or C{None}
        @param text: The text to be parsed.  This text consists
            of a list of C{Tokens}, ordered by their C{Location}.
        @type text: C{list} of C{Token}
        """
        assert 0, "ParserI is an abstract interface"

    def parse_n(self, text, n=None):
        """
        @return: a list of the C{n} best parses for the given text,
            sorted in descending order of quality (or all parses, if
            the text has less than C{n} parses).  The order among
            parses with the same quality is undefined.  I.e., the
            first parse in the list will have the highest quality; and
            each subsequent parse will have equal or lower quality.
            Note that the empty list will be returned if no parses
            were found.
        @rtype: C{list} of C{TreeToken}

        @param n: The number of parses to generate.  At most C{n}
            parses will be returned.  If C{n} is C{None}, return all
            parses. 
        @type n: C{int}
        @param text: The text to be parsed.  This text consists
            of a list of C{Tokens}, ordered by their C{Location}.
        @type text: C{list} of C{Token}
        """
        assert 0, "ParserI is an abstract interface"

class ProbabilisticParserI(ParserI):
    """
    A processing interface for associating proabilities with trees
    that represent possible structures for a sequence of tokens.  A
    C{ProbabilisticParser} is a C{Parser} whose quality ratings are
    probabilities.  In particular, the quality of a parse for a given
    text is the probability that the parse is the correct
    representation for the structure of the text.

    In order to allow access to the probabilities associated with each
    parse, the parses are returned as C{ProbabilisticTreeToken}s.
    C{ProbabilisticTreeToken}s are C{TreeToken}s that have
    probabilities associated with them.

    In addition to the methods defined by the C{Parser} interface,
    C{ProbabilisticParser} defines the C{parse_dist} method, which
    returns a C{ProbDist} whose samples are C{parses}.

    @see: C{ProbabilisticTreeToken}
    """
    def __init__(self):
        """
        Construct a new C{ProbabilisticParser}.
        """
        assert 0, "ProbabilisticParserI is an abstract interface"

    def parse(self, text):
        """
        Return the best parse for the given text, or C{None} if no
        parses are available.
        
        @return: The highest-quality parse for the given text.  If
            multiple parses are tied for the highest quality, then
            choose one arbitrarily.  If no parse is available for the
            given text, return C{None}.
        @rtype: C{ProbabilisticTreeToken} or C{None}
        @param text: The text to be parsed.  This text consists
            of a list of C{Tokens}, ordered by their C{Location}.
        @type text: C{list} of C{Token}
        """
        assert 0, "ParserI is an abstract interface"

    def parse_n(self, text, n=None):
        """
        @return: a list of the C{n} best parses for the given text,
            sorted in descending order of quality (or all parses, if
            the text has less than C{n} parses).  The order among
            parses with the same quality is undefined.  I.e., the
            first parse in the list will have the highest quality; and
            each subsequent parse will have equal or lower quality.
            Note that the empty list will be returned if no parses
            were found.
        @rtype: C{list} of C{ProbabilisticTreeToken}
        @param n: The number of parses to generate.  At most C{n}
            parses will be returned.  If C{n} is C{None}, return all
            parses. 
        @type n: C{int}
        @param text: The text to be parsed.  This text consists
            of a list of C{Tokens}, ordered by their C{Location}.
        @type text: C{list} of C{Token}
        """
        assert 0, "ParserI is an abstract interface"

    def parse_dist(self, text):
        """
        @return: a C{ProbDist} that specifies probabilities of parses
            for the given text.  The samples of this C{ProbDist}
            are the possible parses for the given text; and their
            probabilities indicate the likelihood that they are the
            correct representation for the structure of the given
            text.
        @rtype: C{ProbDist} with C{TreeToken} samples
        @param text: The text to be parsed.  This text consists
            of a list of C{Tokens}, ordered by their C{Location}.
        @type text: C{list} of C{Token}
        """
        assert 0, "ProbabilisticParserI is an abstract interface"

    
