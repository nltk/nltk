# -*- coding: utf-8 -*-
# Natural Language Toolkit: CISTEM Stemmer for German
# Copyright (C) 2001-2018 NLTK Project
# Author: Leonie Weissweiler <l.weissweiler@outlook.de>
# Algorithm: Leonie Weissweiler <l.weissweiler@outlook.de>
#            Alexander Fraser <fraser@cis.lmu.de>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

from __future__ import unicode_literals
import re
from nltk.stem.api import StemmerI
from nltk.compat import python_2_unicode_compatible

@python_2_unicode_compatible
class Cistem(StemmerI):
    """
    CISTEM Stemmer for German

    This is the official Python implementation of the CISTEM stemmer.
    It is based on the paper
    Leonie Weissweiler, Alexander Fraser (2017). Developing a Stemmer for German
    Based on a Comparative Analysis of Publicly Available Stemmers.
    In Proceedings of the German Society for Computational Linguistics and Language
    Technology (GSCL)
    which can be read here:
    http://www.cis.lmu.de/~weissweiler/cistem/

    In the paper, we conducted an analysis of publicly available stemmers,
    developed two gold standards for German stemming and evaluated the stemmers
    based on the two gold standards. We then proposed the stemmer implemented here
    and show that it achieves slightly better f-measure than the other stemmers and
    is thrice as fast as the Snowball stemmer for German while being about as fast
    as most other stemmers.

    case_insensitive is a a boolean specifiying if case-insensitive stemming
    should be used. Case insensitivity improves performance only if words in the
    text may be incorrectly upper case. For all-lowercase and correctly cased
    text, best performance is achieved by setting case_insensitive for false.

    :param case_insensitive: if True, the stemming is case insensitive. False by default.
    :type case_insensitive: bool
    """
    strip_ge = re.compile(r"^ge(.{4,})")
    repl_xx = re.compile(r"(.)\1")
    strip_emr = re.compile(r"e[mr]$")
    strip_nd = re.compile(r"nd$")
    strip_t = re.compile(r"t$")
    strip_esn = re.compile(r"[esn]$")
    repl_xx_back = re.compile(r"(.)\*")

    def __init__(self, case_insensitive=False):
        self._case_insensitive = case_insensitive

    @staticmethod
    def replace_to(word):
        word = word.replace("sch", "$")
        word = word.replace("ei", "%")
        word = word.replace("ie", "&")
        word = Cistem.repl_xx.sub(r"\1*", word)

        return word

    @staticmethod
    def replace_back(word):
        word = Cistem.repl_xx_back.sub(r"\1\1", word)
        word = word.replace("%", "ei")
        word = word.replace("&", "ie")
        word = word.replace("$", "sch")

        return word
