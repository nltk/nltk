# -*- coding: utf-8 -*-
# Natural Language Toolkit: Python port of the tok-tok.pl tokenizer.
#
# Copyright (C) 2001-2015 NLTK Project
# Author:
# Contributors: Ozan Caglayan
#
# URL: <http://nltk.sourceforge.net>
# For license information, see LICENSE.TXT

"""
This is a NLTK port of the tokenizer used in the NIST BLEU evaluation script,
https://github.com/moses-smt/mosesdecoder/blob/master/scripts/generic/mteval-v14.pl#L926
which was also ported into Python in
https://github.com/lium-lst/nmtpy/blob/master/nmtpy/metrics/mtevalbleu.py#L162
"""

import io
import re
from six import text_type

from nltk.tokenize.api import TokenizerI
from nltk.tokenize.util import xml_unescape

class NISTTokenizer(TokenizerI):
    """
    This NIST tokenizer is sentence-based instead of the original
    paragraph-based tokenization from mteval-14.pl; The sentence-based
    tokenization is consistent with the other tokenizers available in NLTK.

    >>> from six import text_type
    >>> from nltk.tokenize.nist import NISTTokenizer
    >>> nist = NISTTokenizer()
    >>> s = "Good muffins cost $3.88 in New York."
    >>> expected_lower = [u'good', u'muffins', u'cost', u'$', u'3.88', u'in', u'new', u'york', u'.']
    >>> expected_cased = [u'Good', u'muffins', u'cost', u'$', u'3.88', u'in', u'New', u'York', u'.']
    >>> nist.tokenize(s, preserve_case=True) == expected_cased
    True
    >>> nist.tokenize(s, preserve_case=False) == expected_lower  # Lowercased.
    True
    """
    # Strip "skipped" tags
    STRIP_SKIP = re.compile('<skipped>'), ''
    #  Strip end-of-line hyphenation and join lines
    STRIP_EOL_HYPHEN = re.compile(u'\u2028'), ' '
    # Tokenize punctuation.
    PUNCT = re.compile('([\{-\~\[-\` -\&\(-\+\:-\@\/])'), ' \\1 '
    # Tokenize period and comma unless preceded by a digit.
    PERIOD_COMMA_PRECEED = re.compile('([^0-9])([\.,])'), '\\1 \\2 '
    # Tokenize period and comma unless followed by a digit.
    PERIOD_COMMA_FOLLOW = re.compile('([\.,])([^0-9])'), ' \\1 \\2'
    # Tokenize dash when preceded by a digit
    DASH_PRECEED_DIGIT = re.compile('([0-9])(-)'), '\\1 \\2 '

    LANG_DEPENDENT_REGEXES = [PUNCT, PERIOD_COMMA_PRECEED,
                              PERIOD_COMMA_FOLLOW, DASH_PRECEED_DIGIT]

    def lang_independent_sub(self, text):
        """Performs the language independent string substituitions. """
        # It's a strange order of regexes.
        # It'll be better to unescape after STRIP_EOL_HYPHEN
        # but let's keep it close to the original NIST implementation.
        regexp, subsitution = self.STRIP_SKIP
        text = regexp.sub(subsitution, text)
        text = xml_unescape(text)
        regexp, subsitution = self.STRIP_EOL_HYPHEN
        text = regexp.sub(subsitution, text)
        return text

    def tokenize(self, text, preserve_case=True,
                 western_lang=True, return_str=False):
        text = text_type(text)
        # Language independent regex.
        text = self.lang_independent_sub(text)
        # Language dependent regex.
        if western_lang:
            # Pad string with whitespace.
            text = ' ' + text + ' '
            if not preserve_case:
                text = text.lower()
            for regexp, subsitution in self.LANG_DEPENDENT_REGEXES:
                text = regexp.sub(subsitution, text)
        # Remove contiguous whitespaces.
        text = ' '.join(text.split())
        # Finally, strips heading and trailing spaces
        # and converts output string into unicode.
        text = text_type(text.strip())
        return text if return_str else text.split()

    def international_tokenize(self, text, preserve_case=True, return_str=False):
        text = text_type(text)
        # Language independent regex.
        text = self.lang_independent_sub(text)
        #
