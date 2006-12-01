# Natural Language Toolkit: Chunk format conversions
#
# Copyright (C) 2001-2006 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au> (minor additions)
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

from nltk_lite.chunk import *
import re

def tag_pattern2re_pattern(tag_pattern):
    """
    Convert a tag pattern to a regular expression pattern.  A X{tag
    pattern} is a modified version of a regular expression, designed
    for matching sequences of tags.  The differences between regular
    expression patterns and tag patterns are:

        - In tag patterns, C{'<'} and C{'>'} act as parentheses; so 
          C{'<NN>+'} matches one or more repetitions of C{'<NN>'}, not
          C{'<NN'} followed by one or more repetitions of C{'>'}.
        - Whitespace in tag patterns is ignored.  So
          C{'<DT> | <NN>'} is equivalant to C{'<DT>|<NN>'}
        - In tag patterns, C{'.'} is equivalant to C{'[^{}<>]'}; so
          C{'<NN.*>'} matches any single tag starting with C{'NN'}.

    In particular, C{tag_pattern2re_pattern} performs the following
    transformations on the given pattern:

        - Replace '.' with '[^<>{}]'
        - Remove any whitespace
        - Add extra parens around '<' and '>', to make '<' and '>' act
          like parentheses.  E.g., so that in '<NN>+', the '+' has scope
          over the entire '<NN>'; and so that in '<NN|IN>', the '|' has
          scope over 'NN' and 'IN', but not '<' or '>'.
        - Check to make sure the resulting pattern is valid.

    @type tag_pattern: C{string}
    @param tag_pattern: The tag pattern to convert to a regular
        expression pattern.
    @raise ValueError: If C{tag_pattern} is not a valid tag pattern.
        In particular, C{tag_pattern} should not include braces; and it
        should not contain nested or mismatched angle-brackets.
    @rtype: C{string}
    @return: A regular expression pattern corresponding to
        C{tag_pattern}. 
    """
    # Clean up the regular expression
    tag_pattern = re.sub(r'\s', '', tag_pattern)
    tag_pattern = re.sub(r'<', '(<(', tag_pattern)
    tag_pattern = re.sub(r'>', ')>)', tag_pattern)

    # Check the regular expression
    if not CHUNK_TAG_PATTERN.match(tag_pattern):
        raise ValueError('Bad tag pattern: %s' % tag_pattern)

    # Replace "." with CHUNK_TAG_CHAR.
    # We have to do this after, since it adds {}[]<>s, which would
    # confuse CHUNK_TAG_PATTERN.
    # PRE doesn't have lookback assertions, so reverse twice, and do
    # the pattern backwards (with lookahead assertions).  This can be
    # made much cleaner once we can switch back to SRE.
    def reverse_str(str):
        lst = list(str)
        lst.reverse()
        return ''.join(lst)
    tc_rev = reverse_str(CHUNK_TAG_CHAR)
    reversed = reverse_str(tag_pattern)
    reversed = re.sub(r'\.(?!\\(\\\\)*($|[^\\]))', tc_rev, reversed)
    tag_pattern = reverse_str(reversed)

    return tag_pattern

