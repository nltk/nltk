# Natural Language Toolkit: Tokenizers
#
# Copyright (C) 2001-2013 NLTK Project
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Michael Heilman <mheilman@cmu.edu> (re-port from http://www.cis.upenn.edu/~treebank/tokenizer.sed)
#         
# URL: <http://nltk.sourceforge.net>
# For license information, see LICENSE.TXT

r"""

Penn Treebank Tokenizer

The Treebank tokenizer uses regular expressions to tokenize text as in Penn Treebank.
This implementation is a port of the tokenizer sed script written by Robert McIntyre
and available at http://www.cis.upenn.edu/~treebank/tokenizer.sed.
"""

import re
from nltk.tokenize.api import TokenizerI


class TreebankWordTokenizer(TokenizerI):
    """
    The Treebank tokenizer uses regular expressions to tokenize text as in Penn Treebank.
    This is the method that is invoked by ``word_tokenize()``.  It assumes that the
    text has already been segmented into sentences, e.g. using ``sent_tokenize()``.

    This tokenizer performs the following steps:

    - split standard contractions, e.g. ``don't`` -> ``do n't`` and ``they'll`` -> ``they 'll``
    - treat most punctuation characters as separate tokens
    - split off commas and single quotes, when followed by whitespace
    - separate periods that appear at the end of line

        >>> from nltk.tokenize import TreebankWordTokenizer
        >>> s = '''Good muffins cost $3.88\\nin New York.  Please buy me\\ntwo of them.\\nThanks.'''
        >>> TreebankWordTokenizer().tokenize(s)
        ['Good', 'muffins', 'cost', '$', '3.88', 'in', 'New', 'York.', 'Please', 'buy', 'me', 'two', 'of', 'them.', 'Thanks', '.']
        >>> s = "They'll save and invest more."
        >>> TreebankWordTokenizer().tokenize(s)
        ['They', "'ll", 'save', 'and', 'invest', 'more', '.']
    """

    # compile a sequence of regular expressions to make the overall
    # processing faster in situations where we are tokenizing many
    # text instances (e.g. tokenizing each document in the Brown
    # corpus separately). These data structures have a compiled regex
    # and the corresponding substitution pattern.
    SUBSTITUTIONS1 = [
        #starting quotes
        (re.compile(r'^\"'), r'``')
        (re.compile(r'(``)'), r' \1 ')
        (re.compile(r'([ (\[{<])"'), r'\1 `` ')

        #punctuation
        (re.compile(r'([:,])([^\d])'), r' \1 \2')
        (re.compile(r'\.\.\.'), r' ... ')
        (re.compile(r'[;@#$%&]'), r' \g<0> ')
        (re.compile(r'([^\.])(\.)([\]\)}>"\']*)\s*$'), r'\1 \2\3 ')
        (re.compile(r'[?!]'), r' \g<0> ')

        (re.compile(r"([^'])' "), r"\1 ' ")

        #parens, brackets, etc.
        (re.compile(r'[\]\[\(\)\{\}\<\>]'), r' \g<0> ')
        (re.compile(r'--'), r' -- ')
    ]
    SUBSTITUTIONS2 = [
        #ending quotes
        (re.compile(r'"'), " '' ")
        (re.compile(r'(\S)(\'\')'), r'\1 \2 ')

        (re.compile(r"([^' ])('[sS]|'[mM]|'[dD]|') "), r"\1 \2 ")
        (re.compile(r"([^' ])('ll|'LL|'re|'RE|'ve|'VE|n't|N'T) "), r"\1 \2 ")
    ]

    # List of contractions adapted from Robert MacIntyre's tokenizer.
    CONTRACTIONS2 = [re.compile(r"(?i)\b(can)(not)\b"),
                     re.compile(r"(?i)\b(d)('ye)\b"),
                     re.compile(r"(?i)\b(gim)(me)\b"),
                     re.compile(r"(?i)\b(gon)(na)\b"),
                     re.compile(r"(?i)\b(got)(ta)\b"),
                     re.compile(r"(?i)\b(lem)(me)\b"),
                     re.compile(r"(?i)\b(mor)('n)\b"),
                     re.compile(r"(?i)\b(wan)(na) ")]
    CONTRACTIONS3 = [re.compile(r"(?i) ('t)(is)\b"),
                     re.compile(r"(?i) ('t)(was)\b")]
    CONTRACTIONS4 = [re.compile(r"(?i)\b(whad)(dd)(ya)\b"),
                     re.compile(r"(?i)\b(wha)(t)(cha)\b")]

    def tokenize(self, text):

        for regexp, replacement_str in self.SUBSTITUTIONS1:
            text = regexp.sub(replacement_str, text)

        #add extra space to make things easier
        text = " " + text + " "

        for regexp, replacement_str in self.SUBSTITUTIONS2:
            text = regexp.sub(replacement_str, text)

        for regexp in self.CONTRACTIONS2:
            text = regexp.sub(r' \1 \2 ', text)
        for regexp in self.CONTRACTIONS3:
            text = regexp.sub(r' \1 \2 ', text)

        # We are not using CONTRACTIONS4 since
        # they are also commented out in the SED scripts
        # for regexp in self.CONTRACTIONS4:
        #     text = regexp.sub(r' \1 \2 \3 ', text)

        return text.split()


if __name__ == "__main__":
    import doctest
    doctest.testmod(optionflags=doctest.NORMALIZE_WHITESPACE)
