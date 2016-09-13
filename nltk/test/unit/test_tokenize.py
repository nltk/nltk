# -*- coding: utf-8 -*-
"""
Unit tests for nltk.tokenize.
See also nltk/test/tokenize.doctest
"""

from __future__ import unicode_literals
from nltk.tokenize import TweetTokenizer
from nltk.test.unit.utils import skipIf
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

    @skipIf(not os.environ.get('STANFORD_MODELS') or
            not os.environ.get('STANFORD_SEGMENTER'),
            "At least one of STANFORD_MODELS or STANFORD_SEGMENTER "
            "environment variables is not set")
    def test_stanford_segmenter(self):
        """
        The Stanford Word Segmenter for Arabic and Chinese
        """
        from nltk.tokenize.stanford_segmenter import StanfordSegmenter
        from nltk.internals import find_file, find_jar, find_dir

        _stanford_url = 'http://nlp.stanford.edu/software'
        _JAR = 'stanford-segmenter.jar'
        _SLF4J = 'slf4j-api.jar'

        path_to_jar = find_jar(_JAR, None, env_vars=('STANFORD_SEGMENTER',),
                               searchpath=(), url=_stanford_url, verbose=False)
        path_to_slf4j = find_jar(_SLF4J, None, env_vars=('STANFORD_SEGMENTER',),
                                 searchpath=(), url=_stanford_url, verbose=False)
        dict_filename = find_file('dict-chris6.ser.gz',
                                  env_vars=('STANFORD_MODELS',), verbose=False)

        # Arabic
        java_class = 'edu.stanford.nlp.international.arabic.process.ArabicSegmenter'
        model = find_file('arabic-segmenter-atb+bn+arztrain.ser.gz',
                          env_vars=('STANFORD_MODELS',), verbose=False)

        seg = StanfordSegmenter(
                 path_to_jar=path_to_jar,
                 path_to_slf4j=path_to_slf4j,
                 java_class=java_class,
                 path_to_model=model,
                 path_to_dict=dict_filename,
                 keep_whitespaces='false',
                 sihan_post_processing='false')

        sent = u'يبحث علم الحاسوب استخدام الحوسبة بجميع اشكالها لحل المشكلات'
        segmented_sent = seg.segment(sent.split())
        assert segmented_sent.split() == ['يبحث', 'علم', 'الحاسوب', 'استخدام',
                                          'الحوسبة', 'ب', 'جميع', 'اشكال',
                                          'ها', 'ل', 'حل', 'المشكلات']

        # Chinese
        java_class = 'edu.stanford.nlp.ie.crf.CRFClassifier'
        model = find_file('pku.gz', env_vars=('STANFORD_MODELS',), verbose=False)
        sihan_dir = find_dir('.', env_vars=('STANFORD_MODELS',), verbose=False)

        seg = StanfordSegmenter(
                 path_to_jar=path_to_jar,
                 path_to_slf4j=path_to_slf4j,
                 java_class=java_class,
                 path_to_model=model,
                 path_to_dict=dict_filename,
                 keep_whitespaces='false',
                 path_to_sihan_corpora_dict=sihan_dir,
                 sihan_post_processing='true')

        sent = u"这是斯坦福中文分词器测试"
        segmented_sent = seg.segment(sent.split())
        assert segmented_sent.split() == ['这', '是', '斯坦福',
                                          '中文', '分词器', '测试']
