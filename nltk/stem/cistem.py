# -*- coding: utf-8 -*-
# Natural Language Toolkit: CISTEM Stemmer for German
# Copyright (C) 2001-2021 NLTK Project
# Author: Leonie Weissweiler <l.weissweiler@outlook.de>
# Algorithm: Leonie Weissweiler <l.weissweiler@outlook.de>
#            Alexander Fraser <fraser@cis.lmu.de>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

import re
from nltk.stem.api import StemmerI


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

    case_insensitive is a a boolean specifying if case-insensitive stemming
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

    def stem(self, word):
        """
        This method takes the word to be stemmed and returns the stemmed word.

        :param word: the word that is to be stemmed
        :type word: unicode
        :return word: the stemmed word
        :rtype: unicode

        >>> from nltk.stem.cistem import Cistem
        >>> stemmer = Cistem()
        >>> s1 = "Speicherbehältern"
        >>> stemmer.stem(s1)
        'speicherbehalt'
        >>> s2 = "Grenzpostens"
        >>> stemmer.stem(s2)
        'grenzpost'
        >>> s3 = "Ausgefeiltere"
        >>> stemmer.stem(s3)
        'ausgefeilt'
        >>> stemmer = Cistem(True)
        >>> stemmer.stem(s1)
        'speicherbehal'
        >>> stemmer.stem(s2)
        'grenzpo'
        >>> stemmer.stem(s3)
        'ausgefeil'
        """
        if len(word) == 0:
            return word

        upper = word[0].isupper()
        word = word.lower()

        word = word.replace("ü", "u")
        word = word.replace("ö", "o")
        word = word.replace("ä", "a")
        word = word.replace("ß", "ss")

        word = Cistem.strip_ge.sub(r"\1", word)
        word = Cistem.replace_to(word)

        while len(word) > 3:
            if len(word) > 5:
                (word, success) = Cistem.strip_emr.subn("", word)
                if success != 0:
                    continue

                (word, success) = Cistem.strip_nd.subn("", word)
                if success != 0:
                    continue

            if not upper or self._case_insensitive:
                (word, success) = Cistem.strip_t.subn("", word)
                if success != 0:
                    continue

            (word, success) = Cistem.strip_esn.subn("", word)
            if success != 0:
                continue
            else:
                break

        word = Cistem.replace_back(word)

        return word

    def segment(self, word):
        """
        This method works very similarly to stem (:func:'cistem.stem'). The difference is that in
        addition to returning the stem, it also returns the rest that was removed at
        the end. To be able to return the stem unchanged so the stem and the rest
        can be concatenated to form the original word, all subsitutions that altered
        the stem in any other way than by removing letters at the end were left out.

        :param word: the word that is to be stemmed
        :type word: unicode
        :return word: the stemmed word
        :rtype: unicode
        :return word: the removed suffix
        :rtype: unicode

        >>> from nltk.stem.cistem import Cistem
        >>> stemmer = Cistem()
        >>> s1 = "Speicherbehältern"
        >>> print("('" + stemmer.segment(s1)[0] + "', '" + stemmer.segment(s1)[1] + "')")
        ('speicherbehält', 'ern')
        >>> s2 = "Grenzpostens"
        >>> stemmer.segment(s2)
        ('grenzpost', 'ens')
        >>> s3 = "Ausgefeiltere"
        >>> stemmer.segment(s3)
        ('ausgefeilt', 'ere')
        >>> stemmer = Cistem(True)
        >>> print("('" + stemmer.segment(s1)[0] + "', '" + stemmer.segment(s1)[1] + "')")
        ('speicherbehäl', 'tern')
        >>> stemmer.segment(s2)
        ('grenzpo', 'stens')
        >>> stemmer.segment(s3)
        ('ausgefeil', 'tere')
        """

        rest_length = 0

        if len(word) == 0:
            return ("", "")

        upper = word[0].isupper()
        word = word.lower()

        original = word[:]

        word = Cistem.replace_to(word)

        while len(word) > 3:
            if len(word) > 5:
                (word, success) = Cistem.strip_emr.subn("", word)
                if success != 0:
                    rest_length += 2
                    continue

                (word, success) = Cistem.strip_nd.subn("", word)
                if success != 0:
                    rest_length += 2
                    continue

            if not upper or self._case_insensitive:
                (word, success) = Cistem.strip_t.subn("", word)
                if success != 0:
                    rest_length += 1
                    continue

            (word, success) = Cistem.strip_esn.subn("", word)
            if success != 0:
                rest_length += 1
                continue
            else:
                break

        word = Cistem.replace_back(word)

        if rest_length:
            rest = original[-rest_length:]
        else:
            rest = ""

        return (word, rest)
