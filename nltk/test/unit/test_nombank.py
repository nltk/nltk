# -*- coding: utf-8 -*-
"""
Unit tests for nltk.corpus.nombank
"""

from __future__ import unicode_literals

from nltk.corpus import nombank

class NombankDemo(unittest.TestCase):
    def test_numbers(self):
        # No. of instances.
        self.assertEqual(len(nombank.instances()), 114574)
        # No. of rolesets
        self.assertEqual(len(nombank.rolesets()), 5577)
        # No. of nouns.
        self.assertEqual(len(nombank.nouns()), 4704)


    def test_instance(self):
        self.assertEqual(nombank.instances()[0].roleset, 'perc-sign.01')

    def test_framefiles_subset_of_fileids(self):
        self.assertTrue(set(nombank._framefiles).issubset(set(nombank.fileids())))
