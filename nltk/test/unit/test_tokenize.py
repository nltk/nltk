# -*- coding: utf-8 -*-
"""
Unit tests for nltk.tokenize.
See also nltk/test/tokenize.doctest
"""

from __future__ import unicode_literals
from nltk.tokenize import TweetTokenizer, StanfordSegmenter
from nose import SkipTest
import unittest
import os


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

    def test_stanford_segmenter_arabic(self):
        """
        Test the Stanford Word Segmenter for Arabic (default config)
        """
        try:
            seg = StanfordSegmenter()
            seg.default_config('ar')
            sent = u'يبحث علم الحاسوب استخدام الحوسبة بجميع اشكالها لحل المشكلات'
            segmented_sent = seg.segment(sent.split())
            assert segmented_sent.split() == ['يبحث', 'علم', 'الحاسوب', 'استخدام',
                                              'الحوسبة', 'ب', 'جميع', 'اشكال',
                                              'ها', 'ل', 'حل', 'المشكلات']
        except LookupError as e:
            raise SkipTest(str(e))

    def test_stanford_segmenter_chinese(self):
        """
        Test the Stanford Word Segmenter for Chinese (default config)
        """
        try:
            seg = StanfordSegmenter()
            seg.default_config('zh')
            sent = u"这是斯坦福中文分词器测试"
            segmented_sent = seg.segment(sent.split())
            assert segmented_sent.split() == ['这', '是', '斯坦福',
                                              '中文', '分词器', '测试']
        except LookupError as e:
            raise SkipTest(str(e))
