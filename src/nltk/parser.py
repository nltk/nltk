# Natural Language Toolkit: Taggers
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

# Todo:
#    - document more.  Clean up the documentation that's here.

"""
Interface for producing tree structures that represent pieces of text.
This task is known as X{parsing} the text, and the resulting tree
structures are called the text's X{parses}.  Typically, the text is a
single sentence, and the tree structure represents the syntactic
structure of the sentence.  However, parsers can also be used in other
domains.  For example, parsers could be used to derive the
morphological structure of the morphemes that make up a word, or to
derive the discourse structure of a list of utterances.

Sometimes, a single piece of text can be represented by more than one
tree structure.  Texts represented by more than one tree structure are
called X{ambiguous} texts.  Note that there are actually two ways in
which a text can be ambiguous:

    - The text has multiple correct parses.
    - There is not enough information to decide which of several
      candidate parses is correct.

However, the parser module does E{not} distinguish these two types of
ambiguity.
"""

class ParserI:
    """
    A processing interface for deriving tree structures that represent
    an ordered list of tokens.  Typically, these tree structures will
    indicate the syntactic structure of sentences.

    Parsing a text will generate zero or more tree structures, known
    as parses.  Abstractly, each of these parses has a X{quality}
    associated with it.  Usually, a parse's quality represents the
    probability that it is a correct parse; however, the exact
    definition of quality is left to individual parsers.  These
    quality ratings are used to decide which parses to return.  In
    particular, the methods C{parse()} and C{parseTypes()} can both
    return lists of the M{n} best parses, sorted in descending order
    of quality.
    """
    def __init__(self):
        """
        Construct a new C{Parser}.
        """

    def parse(self, tokens, n=None):
        """
        Parse the piece of text contained in the given list of
        tokens.  Return the C{n} best parses for the text (or all
        parses, if the number of parses is less than C{n})).
        
        @return: A list of the C{n} best parses for the given text,
            sorted in descending order of quality.  In other words,
            the first parse in the list will have the highest quality; 
            and each subsequent parse will have equal or lower
            quality.  The order among parses with the same quality is
            undefined.  Note that the empty list will be returned if
            no parses were found.
        @rtype: C{list} of C{TreeToken}

        @param n: The number of parses to generate.  At most C{n}
            parses will be returned.  If C{n} is C{None}, return all
            parses. 
        @type n: C{int}
        
        @param tokens: The list of tokens to be parsed.
        @type tokens: C{list} of C{Token}
        """
        assert 0, "ParserI is an abstract interface"

    def parseTypes(self, types, n=None):
        """
        Parse the piece of text contained in the given list of
        types.  Return the C{n} best parses for the text (or all
        parses, if the number of parses is less than C{n})).

        This method does not need to be overridden by implementations: 
        it has a default implementation using parse().
        
        @return: A list of the C{n} best parses for the given text,
            sorted in descending order of quality.  In other words,
            the first parse in the list will have the highest quality; 
            and each subsequent parse will have equal or lower
            quality.  The order among parses with the same quality is
            undefined.  Note that the empty list will be returned if
            no parses were found.
        @rtype: C{list} of C{Tree}

        @param n: The number of parses to generate.  At most C{n}
            parses will be returned.  If C{n} is C{None}, return all
            parses. 
        @type n: C{int}
        
        @param tokens: The list of tokens to be parsed.
        @type tokens: C{list} of C{Token}
        """
        # Convert the list of types to a list of tokens.  Use
        # arbitrary locations.  Unit is 't' for 'token'
        toks = [Token(t, i, unit='t' source='(ParserI)')
                for (t,i) in zip(types, range(len(types)))]

        # Run the normal parse method on the list of tokens.
        parses = self.parse(toks, n)

        # Extract Trees (instead of TreeTokens) to return.
        return [parse.type() for parse in parses]
