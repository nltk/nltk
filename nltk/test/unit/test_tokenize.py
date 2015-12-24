# -*- coding: utf-8 -*-
"""
Unit tests for nltk.tokenize.
See also nltk/test/tokenize.doctest
"""

from __future__ import unicode_literals
from nltk.tokenize import TweetTokenizer
import unittest

class TestTokenize(unittest.TestCase):

    def test_tweet_tokenizer(self):
        """
        Test TweetTokenizer using words with special and accented characters.
        """

        tokenizer = TweetTokenizer(strip_handles=True, reduce_len=True)
        s9 = "@myke: Let's test these words: resumé España München français"
        tokens = tokenizer.tokenize(s9)
        expected = [':', "Let's", 'test', 'these', 'words', ':', 'resumé',
                    'España', 'München', 'français']
        self.assertEqual(tokens, expected)
