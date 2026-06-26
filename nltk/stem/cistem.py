# Natural Language Toolkit: CISTEM Stemmer for German
# Copyright (C) 2001-2026 NLTK Project
# Author: Leonie Weissweiler <l.weissweiler@outlook.de>
#         Tom Aarsen <> (modifications)
# Algorithm: Leonie Weissweiler <l.weissweiler@outlook.de>
#            Alexander Fraser <fraser@cis.lmu.de>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

import re
from typing import Tuple

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
    https://www.cis.lmu.de/~weissweiler/cistem/

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
    repl_xx_back = re.compile(r"(.)\*")
    # The end-anchored suffix patterns (e[mr]$, nd$, t$, [esn]$) are applied by
    # direct end-of-string character checks in ``_segment_inner`` (see there),
    # not via ``re``, so that stemming is linear rather than quadratic in the
    # word length (CWE-770; CVE-2026-12868).

    def __init__(self, case_insensitive: bool = False):
        self._case_insensitive = case_insensitive

    @staticmethod
    def replace_to(word: str) -> str:
        word = word.replace("sch", "$")
        word = word.replace("ei", "%")
        word = word.replace("ie", "&")
        word = Cistem.repl_xx.sub(r"\1*", word)

        return word

    @staticmethod
    def replace_back(word: str) -> str:
        word = Cistem.repl_xx_back.sub(r"\1\1", word)
        word = word.replace("%", "ei")
        word = word.replace("&", "ie")
        word = word.replace("$", "sch")

        return word

    def stem(self, word: str) -> str:
        """Stems the input word.

        :param word: The word that is to be stemmed.
        :type word: str
        :return: The stemmed word.
        :rtype: str

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

        return self._segment_inner(word, upper)[0]

    def segment(self, word: str) -> tuple[str, str]:
        """
        This method works very similarly to stem (:func:'cistem.stem'). The difference is that in
        addition to returning the stem, it also returns the rest that was removed at
        the end. To be able to return the stem unchanged so the stem and the rest
        can be concatenated to form the original word, all subsitutions that altered
        the stem in any other way than by removing letters at the end were left out.

        :param word: The word that is to be stemmed.
        :type word: str
        :return: A tuple of the stemmed word and the removed suffix.
        :rtype: Tuple[str, str]

        >>> from nltk.stem.cistem import Cistem
        >>> stemmer = Cistem()
        >>> s1 = "Speicherbehältern"
        >>> stemmer.segment(s1)
        ('speicherbehält', 'ern')
        >>> s2 = "Grenzpostens"
        >>> stemmer.segment(s2)
        ('grenzpost', 'ens')
        >>> s3 = "Ausgefeiltere"
        >>> stemmer.segment(s3)
        ('ausgefeilt', 'ere')
        >>> stemmer = Cistem(True)
        >>> stemmer.segment(s1)
        ('speicherbehäl', 'tern')
        >>> stemmer.segment(s2)
        ('grenzpo', 'stens')
        >>> stemmer.segment(s3)
        ('ausgefeil', 'tere')
        """
        if len(word) == 0:
            return ("", "")

        upper = word[0].isupper()
        word = word.lower()

        return self._segment_inner(word, upper)

    def _segment_inner(self, word: str, upper: bool):
        """Inner method for iteratively applying the code stemming regexes.
        This method receives a pre-processed variant of the word to be stemmed,
        or the word to be segmented, and returns a tuple of the word and the
        removed suffix.

        :param word: A pre-processed variant of the word that is to be stemmed.
        :type word: str
        :param upper: Whether the original word started with a capital letter.
        :type upper: bool
        :return: A tuple of the stemmed word and the removed suffix.
        :rtype: Tuple[str, str]
        """

        rest_length = 0
        word_copy = word[:]

        # Pre-processing before applying the substitution patterns
        word = Cistem.replace_to(word)
        rest = ""

        # Apply the substitution patterns. Each pattern (e[mr]$, nd$, t$, [esn]$)
        # only ever strips one or two characters anchored at the end of the
        # string. The original loop rebuilt the whole remaining string on every
        # removal via the compiled ``re`` patterns' ``Pattern.subn`` -- O(n) work
        # per step over O(n) steps, i.e. O(n**2) in the word length, so a single
        # long word pins a CPU core (CWE-770; CVE-2026-12868). Strip characters
        # off the end of a list in O(1) per step instead, joining once at the end.
        #
        # Python's ``$`` matches at the end of the string *or* just before a
        # single trailing newline, so such a newline is transparent to the
        # anchored patterns and is preserved (``_strip`` pops it aside and
        # restores it); ``j`` is the index of the last character the patterns
        # act on.
        chars = list(word)

        def _strip(count):
            if chars[-1] == "\n":
                newline = chars.pop()
                del chars[-count:]
                chars.append(newline)
            else:
                del chars[-count:]

        while len(chars) > 3:
            j = -2 if chars[-1] == "\n" else -1
            if len(chars) > 5:
                if chars[j] in "mr" and chars[j - 1] == "e":  # e[mr]$
                    _strip(2)
                    rest_length += 2
                    continue

                if chars[j] == "d" and chars[j - 1] == "n":  # nd$
                    _strip(2)
                    rest_length += 2
                    continue

            if not upper or self._case_insensitive:
                if chars[j] == "t":  # t$
                    _strip(1)
                    rest_length += 1
                    continue

            if chars[j] in "esn":  # [esn]$
                _strip(1)
                rest_length += 1
                continue
            else:
                break

        word = "".join(chars)

        # Post-processing after applying the substitution patterns
        word = Cistem.replace_back(word)

        if rest_length:
            rest = word_copy[-rest_length:]

        return (word, rest)
