# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
import unittest
from nltk.stem.snowball import SnowballStemmer

class SnowballTest(unittest.TestCase):

    def test_russian(self):
        # Russian words both consisting of Cyrillic
        # and Roman letters can be stemmed.
        stemmer_russian = SnowballStemmer("russian")
        assert stemmer_russian.stem("авантненькая") == "авантненьк"
        assert stemmer_russian.stem("avenantnen'kai^a") == "avenantnen'k"

    def test_german(self):
        stemmer_german = SnowballStemmer("german")
        stemmer_german2 = SnowballStemmer("german", ignore_stopwords=True)

        assert stemmer_german.stem("Schr\xe4nke") == 'schrank'
        assert stemmer_german2.stem("Schr\xe4nke") == 'schrank'

        assert stemmer_german.stem("keinen") == 'kein'
        assert stemmer_german2.stem("keinen") == 'keinen'

    def test_short_strings_bug(self):
        stemmer = SnowballStemmer('english')
        assert stemmer.stem("y's") == 'y'
