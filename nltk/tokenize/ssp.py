# Natural Language Toolkit: Tokenizers
#
# Copyright (C) 2001-2019 NLTK Project
# Author: Christopher Hench <chris.l.hench@gmail.com>
#         Alex Estes
# URL: <http://nltk.sourceforge.net>
# For license information, see LICENSE.TXT
#
# Reference: Otto Jespersen, Lehrbuch der Phonetik.
#            University of Toronto (Leipzig, Teubner, 1904).

"""
The Sonority Sequencing Principle is a language agnostic algorithm developed
by Otto Jesperson in 1904. The sonorous quality of a phoneme is judged by the
openness of the lips. Syllable breaks occur before troughs in sonority.

The default implementation uses the English alphabet, but the `sonority_hiearchy`
can be modified to IPA or any other alphabet for the use-case.

Importantly, if a custom hiearchy is supplied and vowels span across more than
one level, they should be given separately to the `vowels` attribute.
"""

from __future__ import unicode_literals
from nltk.tokenize.api import TokenizerI


class SonoritySequencingPrinciple:
    '''
    Syllabifies words based on the Sonority Sequencing Principle (SSP)

    >>> SSP = SonoritySequencingPrinciple()
    >>> SSP.tokenize('justification')
    ['jus', 'ti', 'fi', 'ca', 'tion']
    '''

    def __init__(self, sonority_hierarchy=False):
        '''
        Sonority hierarchy should be provided in descending order.
        If vowels are spread across multiple levels, they should be
        passed assigned self.vowels var together.
        '''

        if not sonority_hierarchy:
            sonority_hierarchy = [
                'aeiouy',  # vowels
                'lmnrw',  # nasals
                'zvsf',  # fricatives
                'bcdgtkpqxhj'  # stops
            ]

        self.vowels = sonority_hierarchy[0]
        self.char_map = {}
        for i, level in enumerate(sonority_hierarchy):
            for c in level:
                self.char_map[c] = len(sonority_hierarchy) - i

    def assign_values(self, token):
        '''
        Assigns each character its value from the sonority hierarchy
        '''
        self.syllables_values = []
        for c in token:
            try:
                self.syllables_values.append((c, self.char_map[c]))
            except KeyError:
                print("Warning: '{}' not defined in hierarchy".format(c))

    def validate_syllables(self, syllabified):
        '''
        Ensures each syllable has at least one vowel.
        If the following syllable doesn't have vowel,
        add it to the current one.
        '''
        valid_syllables = []
        front = ""
        for i, syllable in enumerate(syllabified):

            if not any(char in self.vowels for char in syllable):
                if len(valid_syllables) == 0:
                    front += syllable
                else:
                    valid_syllables = valid_syllables[
                        :-1] + [valid_syllables[-1] + syllable]
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
        self.assign_values(token)

        syllable_list = []
        syllable = ''
        for i, tup in enumerate(self.syllables_values):
            c, v = tup

            if i == 0:  # if it's the first char, append automatically
                syllable += c

            else:
                # main algorithm
                if (i < len(self.syllables_values) - 1):

                    # these cases trigger syllable break
                    if v == self.syllables_values[i + 1][1] and \
                            v == self.syllables_values[i - 1][1]:
                        syllable += c
                        syllable_list.append(syllable)
                        syllable = ""

                    elif v == self.syllables_values[i + 1][1] and \
                            v < self.syllables_values[i - 1][1]:
                        syllable += c
                        syllable_list.append(syllable)
                        syllable = ""

                    elif v < self.syllables_values[i + 1][1] and \
                            v < self.syllables_values[i - 1][1]:
                        syllable_list.append(syllable)
                        syllable = ""
                        syllable += c

                    # no syllable break
                    else:
                        syllable += c
                else:
                    syllable += c
                    syllable_list.append(syllable)

        return self.validate_syllables(syllable_list)
