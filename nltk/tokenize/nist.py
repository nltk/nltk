# -*- coding: utf-8 -*-
# Natural Language Toolkit: Python port of the tok-tok.pl tokenizer.
#
# Copyright (C) 2001-2015 NLTK Project
# Author: Ozan Caglayan
# Contributors: Liling Tan
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

class NISTTokenizer(TokenizerI):
    """

    """
    STRIP_SKIP = '<skipped>', ''
    # Tokenize punctuation.
    PUNCT = '([\{-\~\[-\` -\&\(-\+\:-\@\/])', ' \\1 '
    # Tokenize period and comma unless preceded by a digit.
    PERIOD_COMMA_PRECEED = '([^0-9])([\.,])', '\\1 \\2 '
    # Tokenize period and comma unless followed by a digit.
    PERIOD_COMMA_FOLLOW = '([\.,])([^0-9])', ' \\1 \\2'
    # Tokenize dash when preceded by a digit
    DASH_PRECEED_DIGIT = '([0-9])(-)', '\\1 \\2 '

    LANG_DEPENDENT_REGEXES = [PUNCT, PERIOD_COMMA_PRECEED,
                              PERIOD_COMMA_FOLLOW, DASH_PRECEED_DIGIT]

    def tokenize(self, text, preserve_case=True,
                 western_lang=True, return_str=False):
        text = text_type(text)
        # Language independent regex.
        regexp, subsitution = STRIP_SKIP
        text = regexp.sub(subsitution, text)
        # Language dependent regex.
        if western_lang:
            # Pad string with whitespace.
            text = ' ' + text + ' '
            if preserve_case:
                text = text.lower()
            for regexp, subsitution in self.LANG_DEPENDENT_REGEXES:
                text = regexp.sub(subsitution, text)
        # Remove contiguous whitespaces.
        text = ' '.join(text.split())
        # Finally, strips heading and trailing spaces
        # and converts output string into unicode.
        text = text_type(text.strip())
        return text if return_str else text.split()
