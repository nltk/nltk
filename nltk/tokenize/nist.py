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
    >>> s = text_type(u'''Но в тоже время сегодняшнее событие не праздник , '''
    ...               u'''а день памяти о тех , кого не вернуло море &quot; , '''
    ...               u'''- отметил председатель совета ветеранов Северного '''
    ...               u'''морского пароходства Борис Карпов .''')
    >>> expected = text_type(u'''но в тоже время сегодняшнее событие не праздник , '''
    ...                      u'''а день памяти о тех , кого не вернуло море " , - '''
    ...                      u'''отметил председатель совета ветеранов северного '''
    ...                      u'''морского пароходства борис карпов .''')
    >>> nist.tokenize(s, return_str=True) == expected
    True
    """
    STRIP_SKIP = re.compile('<skipped>'), ''
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

    def tokenize(self, text, preserve_case=True,
                 western_lang=True, return_str=False):
        text = text_type(text)
        # Language independent regex.
        regexp, subsitution = self.STRIP_SKIP
        text = regexp.sub(subsitution, text)
        text = xml_unescape(text)
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
