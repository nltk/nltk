# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals

import unittest
from contextlib import closing

from nltk import data
from nltk.stem.porter import PorterStemmer
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

    def test_spanish(self):
        stemmer = SnowballStemmer('spanish')

        assert stemmer.stem("Visionado") == 'vision'

        # The word 'algue' was raising an IndexError
        assert stemmer.stem("algue") == 'algu'

    def test_short_strings_bug(self):
        stemmer = SnowballStemmer('english')
        assert stemmer.stem("y's") == 'y'


class PorterTest(unittest.TestCase):
    def _vocabulary(self):
        with closing(data.find('stemmers/porter_test/porter_vocabulary.txt').open(encoding='utf-8')) as fp:
            return fp.read().splitlines()

    def _test_against_expected_output(self, stemmer_mode, expected_stems):
        stemmer = PorterStemmer(mode=stemmer_mode)
        for word, true_stem in zip(self._vocabulary(), expected_stems):
            our_stem = stemmer.stem(word)
            assert our_stem == true_stem, (
                "%s should stem to %s in %s mode but got %s" % (
                    word, true_stem, stemmer_mode, our_stem
                )
            )

    def test_vocabulary_martin_mode(self):
        """Tests all words from the test vocabulary provided by M Porter
        
        The sample vocabulary and output were sourced from:
            http://tartarus.org/martin/PorterStemmer/voc.txt
            http://tartarus.org/martin/PorterStemmer/output.txt
        and are linked to from the Porter Stemmer algorithm's homepage
        at
            http://tartarus.org/martin/PorterStemmer/
        """
        with closing(data.find('stemmers/porter_test/porter_martin_output.txt').open(encoding='utf-8')) as fp:
            self._test_against_expected_output(
                PorterStemmer.MARTIN_EXTENSIONS,
                fp.read().splitlines()
            )

    def test_vocabulary_nltk_mode(self):
        with closing(data.find('stemmers/porter_test/porter_nltk_output.txt').open(encoding='utf-8')) as fp:
            self._test_against_expected_output(
                PorterStemmer.NLTK_EXTENSIONS,
                fp.read().splitlines()
            )

    def test_vocabulary_original_mode(self):
        # The list of stems for this test was generated by taking the
        # Martin-blessed stemmer from
        # http://tartarus.org/martin/PorterStemmer/c.txt
        # and removing all the --DEPARTURE-- sections from it and
        # running it against Martin's test vocabulary.

        with closing(data.find('stemmers/porter_test/porter_original_output.txt').open(encoding='utf-8')) as fp:
            self._test_against_expected_output(
                PorterStemmer.ORIGINAL_ALGORITHM,
                fp.read().splitlines()
            )

        self._test_against_expected_output(
            PorterStemmer.ORIGINAL_ALGORITHM,
            data.find('stemmers/porter_test/porter_original_output.txt')
                .open(encoding='utf-8')
                .read()
                .splitlines()
        )

    def test_oed_bug(self):
        """Test for bug https://github.com/nltk/nltk/issues/1581

        Ensures that 'oed' can be stemmed without throwing an error.
        """
        assert PorterStemmer().stem('oed') == 'o'
