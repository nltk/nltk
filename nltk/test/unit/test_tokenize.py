# -*- coding: utf-8 -*-
"""
Unit tests for nltk.tokenize.
See also nltk/test/tokenize.doctest
"""

from __future__ import unicode_literals

import unittest

from nose import SkipTest
from nose.tools import assert_equal

from nltk.tokenize import (
    punkt,
    word_tokenize,
    TweetTokenizer,
    StanfordSegmenter,
    TreebankWordTokenizer,
)


class TestTokenize(unittest.TestCase):
    def test_tweet_tokenizer(self):
        """
        Test TweetTokenizer using words with special and accented characters.
        """

        tokenizer = TweetTokenizer(strip_handles=True, reduce_len=True)
        s9 = "@myke: Let's test these words: resumé España München français"
        tokens = tokenizer.tokenize(s9)
        expected = [
            ':',
            "Let's",
            'test',
            'these',
            'words',
            ':',
            'resumé',
            'España',
            'München',
            'français',
        ]
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
            assert segmented_sent.split() == [
                'يبحث',
                'علم',
                'الحاسوب',
                'استخدام',
                'الحوسبة',
                'ب',
                'جميع',
                'اشكال',
                'ها',
                'ل',
                'حل',
                'المشكلات',
            ]
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
            assert segmented_sent.split() == ['这', '是', '斯坦福', '中文', '分词器', '测试']
        except LookupError as e:
            raise SkipTest(str(e))

    def test_phone_tokenizer(self):
        """
        Test a string that resembles a phone number but contains a newline
        """

        # Should be recognized as a phone number, albeit one with multiple spaces
        tokenizer = TweetTokenizer()
        test1 = "(393)  928 -3010"
        expected = ['(393)  928 -3010']
        result = tokenizer.tokenize(test1)
        self.assertEqual(result, expected)

        # Due to newline, first three elements aren't part of a phone number;
        # fourth is
        test2 = "(393)\n928 -3010"
        expected = ['(', '393', ')', "928 -3010"]
        result = tokenizer.tokenize(test2)
        self.assertEqual(result, expected)

    def test_remove_handle(self):
        """
        Test remove_handle() from casual.py with specially crafted edge cases
        """

        tokenizer = TweetTokenizer(strip_handles=True)

        # Simple example. Handles with just numbers should be allowed
        test1 = "@twitter hello @twi_tter_. hi @12345 @123news"
        expected = ['hello', '.', 'hi']
        result = tokenizer.tokenize(test1)
        self.assertEqual(result, expected)

        # Handles are allowed to follow any of the following characters
        test2 = "@n`@n~@n(@n)@n-@n=@n+@n\\@n|@n[@n]@n{@n}@n;@n:@n'@n\"@n/@n?@n.@n,@n<@n>@n @n\n@n ñ@n.ü@n.ç@n."
        expected = [
            '`',
            '~',
            '(',
            ')',
            '-',
            '=',
            '+',
            '\\',
            '|',
            '[',
            ']',
            '{',
            '}',
            ';',
            ':',
            "'",
            '"',
            '/',
            '?',
            '.',
            ',',
            '<',
            '>',
            'ñ',
            '.',
            'ü',
            '.',
            'ç',
            '.',
        ]
        result = tokenizer.tokenize(test2)
        self.assertEqual(result, expected)

        # Handles are NOT allowed to follow any of the following characters
        test3 = "a@n j@n z@n A@n L@n Z@n 1@n 4@n 7@n 9@n 0@n _@n !@n @@n #@n $@n %@n &@n *@n"
        expected = [
            'a',
            '@n',
            'j',
            '@n',
            'z',
            '@n',
            'A',
            '@n',
            'L',
            '@n',
            'Z',
            '@n',
            '1',
            '@n',
            '4',
            '@n',
            '7',
            '@n',
            '9',
            '@n',
            '0',
            '@n',
            '_',
            '@n',
            '!',
            '@n',
            '@',
            '@n',
            '#',
            '@n',
            '$',
            '@n',
            '%',
            '@n',
            '&',
            '@n',
            '*',
            '@n',
        ]
        result = tokenizer.tokenize(test3)
        self.assertEqual(result, expected)

        # Handles are allowed to precede the following characters
        test4 = "@n!a @n#a @n$a @n%a @n&a @n*a"
        expected = ['!', 'a', '#', 'a', '$', 'a', '%', 'a', '&', 'a', '*', 'a']
        result = tokenizer.tokenize(test4)
        self.assertEqual(result, expected)

        # Tests interactions with special symbols and multiple @
        test5 = "@n!@n @n#@n @n$@n @n%@n @n&@n @n*@n @n@n @@n @n@@n @n_@n @n7@n @nj@n"
        expected = [
            '!',
            '@n',
            '#',
            '@n',
            '$',
            '@n',
            '%',
            '@n',
            '&',
            '@n',
            '*',
            '@n',
            '@n',
            '@n',
            '@',
            '@n',
            '@n',
            '@',
            '@n',
            '@n_',
            '@n',
            '@n7',
            '@n',
            '@nj',
            '@n',
        ]
        result = tokenizer.tokenize(test5)
        self.assertEqual(result, expected)

        # Tests that handles can have a max length of 20
        test6 = "@abcdefghijklmnopqrstuvwxyz @abcdefghijklmnopqrst1234 @abcdefghijklmnopqrst_ @abcdefghijklmnopqrstendofhandle"
        expected = ['uvwxyz', '1234', '_', 'endofhandle']
        result = tokenizer.tokenize(test6)
        self.assertEqual(result, expected)

        # Edge case where an @ comes directly after a long handle
        test7 = "@abcdefghijklmnopqrstu@abcde @abcdefghijklmnopqrst@abcde @abcdefghijklmnopqrst_@abcde @abcdefghijklmnopqrst5@abcde"
        expected = [
            'u',
            '@abcde',
            '@abcdefghijklmnopqrst',
            '@abcde',
            '_',
            '@abcde',
            '5',
            '@abcde',
        ]
        result = tokenizer.tokenize(test7)
        self.assertEqual(result, expected)

    def test_treebank_span_tokenizer(self):
        """
        Test TreebankWordTokenizer.span_tokenize function
        """

        tokenizer = TreebankWordTokenizer()

        # Test case in the docstring
        test1 = "Good muffins cost $3.88\nin New (York).  Please (buy) me\ntwo of them.\n(Thanks)."
        expected = [
            (0, 4),
            (5, 12),
            (13, 17),
            (18, 19),
            (19, 23),
            (24, 26),
            (27, 30),
            (31, 32),
            (32, 36),
            (36, 37),
            (37, 38),
            (40, 46),
            (47, 48),
            (48, 51),
            (51, 52),
            (53, 55),
            (56, 59),
            (60, 62),
            (63, 68),
            (69, 70),
            (70, 76),
            (76, 77),
            (77, 78),
        ]
        result = list(tokenizer.span_tokenize(test1))
        self.assertEqual(result, expected)

        # Test case with double quotation
        test2 = "The DUP is similar to the \"religious right\" in the United States and takes a hardline stance on social issues"
        expected = [
            (0, 3),
            (4, 7),
            (8, 10),
            (11, 18),
            (19, 21),
            (22, 25),
            (26, 27),
            (27, 36),
            (37, 42),
            (42, 43),
            (44, 46),
            (47, 50),
            (51, 57),
            (58, 64),
            (65, 68),
            (69, 74),
            (75, 76),
            (77, 85),
            (86, 92),
            (93, 95),
            (96, 102),
            (103, 109),
        ]
        result = list(tokenizer.span_tokenize(test2))
        self.assertEqual(result, expected)

        # Test case with double qoutation as well as converted quotations
        test3 = "The DUP is similar to the \"religious right\" in the United States and takes a ``hardline'' stance on social issues"
        expected = [
            (0, 3),
            (4, 7),
            (8, 10),
            (11, 18),
            (19, 21),
            (22, 25),
            (26, 27),
            (27, 36),
            (37, 42),
            (42, 43),
            (44, 46),
            (47, 50),
            (51, 57),
            (58, 64),
            (65, 68),
            (69, 74),
            (75, 76),
            (77, 79),
            (79, 87),
            (87, 89),
            (90, 96),
            (97, 99),
            (100, 106),
            (107, 113),
        ]
        result = list(tokenizer.span_tokenize(test3))
        self.assertEqual(result, expected)

    def test_word_tokenize(self):
        """
        Test word_tokenize function
        """
        
        sentence = "The 'v', I've been fooled but I'll seek revenge."
        expected = ['The', "'", 'v', "'", ',', 'I', "'ve", 'been', 'fooled', 
                    'but', 'I', "'ll", 'seek', 'revenge', '.']
        self.assertEqual(word_tokenize(sentence), expected)
        
        sentence = "'v' 're'"
        expected = ["'", 'v', "'", "'re", "'"]
        self.assertEqual(word_tokenize(sentence), expected)

    def test_punkt_pair_iter(self):

        test_cases = [
            ('12', [('1', '2'), ('2', None)]),
            ('123', [('1', '2'), ('2', '3'), ('3', None)]),
            ('1234', [('1', '2'), ('2', '3'), ('3', '4'), ('4', None)]),
        ]

        for (test_input, expected_output) in test_cases:
            actual_output = [x for x in punkt._pair_iter(test_input)]

            assert_equal(actual_output, expected_output)

    def test_punkt_pair_iter_handles_stop_iteration_exception(self):
        # test input to trigger StopIteration from next()
        it = iter([])
        # call method under test and produce a generator
        gen = punkt._pair_iter(it)
        # unpack generator, ensure that no error is raised
        list(gen)

    def test_punkt_tokenize_words_handles_stop_iteration_exception(self):
        obj = punkt.PunktBaseClass()

        class TestPunktTokenizeWordsMock:
            def word_tokenize(self, s):
                return iter([])

        obj._lang_vars = TestPunktTokenizeWordsMock()
        # unpack generator, ensure that no error is raised
        list(obj._tokenize_words('test'))
