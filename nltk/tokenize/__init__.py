# Natural Language Toolkit: Tokenizers
#
# Copyright (C) 2001-2019 NLTK Project
# Author: Christopher Hench <chris.l.hench@gmail.com>
#         Alex Estes
# URL: <http://nltk.sourceforge.net>
# For license information, see LICENSE.TXT

"""
The Sonority Sequencing Principle (SSP) is a language agnostic algorithm proposed
by Otto Jesperson in 1904. The sonorous quality of a phoneme is judged by the
openness of the lips. Syllable breaks occur before troughs in sonority. For more
on the SSP see Selkirk (1984).

The default implementation uses the English alphabet, but the `sonority_hiearchy`
can be modified to IPA or any other alphabet for the use-case. The SSP is a
universal syllabification algorithm, but that does not mean it performs equally
across languages. Bartlett et al. (2009) is a good benchmark for English accuracy
if utilizing IPA (pg. 311).

Importantly, if a custom hiearchy is supplied and vowels span across more than
one level, they should be given separately to the `vowels` class attribute.

References:
- Otto Jespersen. 1904. Lehrbuch der Phonetik.
  Leipzig, Teubner. Chapter 13, Silbe, pp. 185-203.
- Elisabeth Selkirk. 1984. On the major class features and syllable theory.
  In Aronoff & Oehrle (eds.) Language Sound Structure: Studies in Phonology.
  Cambridge, MIT Press. pp. 107-136.
- Susan Bartlett, et al. 2009. On the Syllabification of Phonemes.
  In HLT-NAACL. pp. 308-316.
"""

from __future__ import unicode_literals

import re

from nltk.tokenize.api import TokenizerI
from nltk.util import ngrams


class SyllableTokenizer(TokenizerI):
    """
    Syllabifies words based on the Sonority Sequencing Principle (SSP).

    >>> SSP = SyllableTokenizer()
    >>> SSP.tokenize('justification')
    ['jus', 'ti', 'fi', 'ca', 'tion']
    """

    def __init__(self, lang='en', sonority_hierarchy=False):
        # Sonority hierarchy should be provided in descending order.
        # If vowels are spread across multiple levels, they should be
        # passed assigned self.vowels var together, otherwise should be
        # placed in first index of hierarchy.
        if not sonority_hierarchy and lang == 'en':
            sonority_hierarchy = ['aeiouy',  # vowels.
                                  'lmnrw',  # nasals.
                                  'zvsf',  # fricatives.
                                  'bcdgtkpqxhj'  # stops.
                                  ]

        self.vowels = sonority_hierarchy[0]
        self.phoneme_map = {}
        for i, level in enumerate(sonority_hierarchy):
            for c in level:
                self.phoneme_map[c] = len(sonority_hierarchy) - i

    def assign_values(self, token):
        '''
        Assigns each phoneme its value from the sonority hierarchy
        '''
        syllables_values = []
        for c in token:
            try:
                syllables_values.append((c, self.phoneme_map[c]))
            except KeyError:
                print("Warning: '{}' not defined in hierarchy".format(c))
        return syllables_values

    def validate_syllables(self, syllabified):
        '''
        Ensures each syllable has at least one vowel.
        If the following syllable doesn't have vowel,
        add it to the current one.
        '''
        valid_syllables = []
        front = ""
        for i, syllable in enumerate(syllabified):

            if not re.search('|'.join(self.vowels), syllable):
                if len(valid_syllables) == 0:
                    front += syllable
                else:
                    valid_syllables = valid_syllables[:-1] + [valid_syllables[-1] + syllable]
            else:
                if len(valid_syllables) == 0:
                    valid_syllables.append(front + syllable)
                else:
                    valid_syllables.append(syllable)

        return valid_syllables

    def tokenize(self, token):
        '''
        Apply the SSP to return a list of syllables.
        '''
        # if only one vowel return word
        if sum(token.count(x) for x in self.vowels) <= 1:
            return [token]

        # assign values from hierarchy
        syllables_values = self.assign_values(token)

        syllable_list = []
        syllable = syllables_values[0][0]  # start syllable with first phoneme
        for trigram in ngrams(syllables_values, n=3):
            phonemes, values = zip(*trigram)
            # Sonority of previous, focal and following phoneme
            prev_value, focal_value, next_value = values
            # Focal phoneme.
            focal_phoneme = phonemes[1]

            # these cases trigger syllable break
            if prev_value >= focal_value == next_value:
                syllable += focal_phoneme
                syllable_list.append(syllable)
                syllable = ""

            elif prev_value > focal_value < next_value:
                syllable_list.append(syllable)
                syllable = ""
                syllable += focal_phoneme

            # no syllable break
            else:
                syllable += focal_phoneme

        syllable += syllables_values[-1][0]  # append last phoneme
        syllable_list.append(syllable)

        return self.validate_syllables(syllable_list)
