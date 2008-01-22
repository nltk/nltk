# Natural Language Toolkit: Tagger Interface
#
# Copyright (C) 2001-2008 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au> (minor additions)
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Interface for tagging each token in a sentence with supplementary
information, such as its part of speech.
"""

from nltk.internals import overridden

class TaggerI(object):
    """
    A processing interface for assigning a tag to each token in a list.
    Tags are case sensitive strings that identify some property of each
    token, such as its part of speech or its sense.

    Subclasses must define:
      - either L{tag()} or L{batch_tag()} (or both)
    """
    def tag(self, tokens):
        """
        Determine the most appropriate tag sequence for the given
        token sequence, and return a corresponding list of tagged
        tokens.  A tagged token is encoded as a tuple C{(token, tag)}.

        @rtype: C{list} of C{(token, tag)}
        """
        if overridden(self.batch_tag):
            return self.batch_tag([tokens])[0]
        else:
            raise NotImplementedError()

    def batch_tag(self, sentences):
        """
        Apply L{self.tag()} to each element of C{sentences}.  I.e.:

            >>> return [self.tag(tokens) for tokens in sentences]
        """
        return [self.tag(tokens) for tokens in sentences]
