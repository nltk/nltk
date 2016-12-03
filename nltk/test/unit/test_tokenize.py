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
        expected = ['`', '~', '(', ')', '-', '=', '+', '\\', '|', '[', ']', '{', '}', ';', ':', "'", '"', '/', '?', '.', ',', '<', '>', 'ñ', '.', 'ü', '.', 'ç', '.']
        result = tokenizer.tokenize(test2)
        self.assertEqual(result, expected)


        # Handles are NOT allowed to follow any of the following characters
        test3 = "a@n j@n z@n A@n L@n Z@n 1@n 4@n 7@n 9@n 0@n _@n !@n @@n #@n $@n %@n &@n *@n"
        expected = ['a', '@n', 'j', '@n', 'z', '@n', 'A', '@n', 'L', '@n', 'Z', '@n', '1', '@n', '4', '@n', '7', '@n', '9', '@n', '0', '@n', '_', '@n', '!', '@n', '@', '@n', '#', '@n', '$', '@n', '%', '@n', '&', '@n', '*', '@n']
        result = tokenizer.tokenize(test3)
        self.assertEqual(result, expected)


        # Handles are allowed to precede the following characters
        test4 = "@n!a @n#a @n$a @n%a @n&a @n*a"
        expected = ['!', 'a', '#', 'a', '$', 'a', '%', 'a', '&', 'a', '*', 'a']
        result = tokenizer.tokenize(test4)
        self.assertEqual(result, expected)


        # Tests interactions with special symbols and multiple @
        test5 = "@n!@n @n#@n @n$@n @n%@n @n&@n @n*@n @n@n @@n @n@@n @n_@n @n7@n @nj@n"
        expected = ['!', '@n', '#', '@n', '$', '@n', '%', '@n', '&', '@n', '*', '@n', '@n', '@n', '@', '@n', '@n', '@', '@n', '@n_', '@n', '@n7', '@n', '@nj', '@n']
        result = tokenizer.tokenize(test5)
        self.assertEqual(result, expected)


        # Tests that handles can have a max length of 20
        test6 = "@abcdefghijklmnopqrstuvwxyz @abcdefghijklmnopqrst1234 @abcdefghijklmnopqrst_ @abcdefghijklmnopqrstendofhandle"
        expected = ['uvwxyz', '1234', '_', 'endofhandle']
        result = tokenizer.tokenize(test6)
        self.assertEqual(result, expected)


        # Edge case where an @ comes directly after a long handle
        test7 = "@abcdefghijklmnopqrstu@abcde @abcdefghijklmnopqrst@abcde @abcdefghijklmnopqrst_@abcde @abcdefghijklmnopqrst5@abcde"
        expected = ['u', '@abcde', '@abcdefghijklmnopqrst', '@abcde', '_', '@abcde', '5', '@abcde']
        result = tokenizer.tokenize(test7)
        self.assertEqual(result, expected)
