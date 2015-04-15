# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
import unittest

from nltk.twitter import credsfromfile
from nltk.twitter import Streamer, Query, Twitter, TweetViewer,\
     TweetWriter




class TestCredentials(unittest.TestCase):

    def test_missingfile(self):
        self.assertRaises(OSError, credsfromfile, creds_file='foobar')

    def test_missingdir(self):
        self.assertRaises(OSError, credsfromfile, subdir='/nosuchdir')


    def test_badfile1(self):
        self.assertRaises(ValueError, credsfromfile, creds_file='bad_oauth1-1.txt',
                      subdir='.')

    def test_badfile2(self):
        self.assertRaises(ValueError, credsfromfile, creds_file='bad_oauth1-2.txt',
                      subdir='.')






if __name__ == '__main__':
    unittest.main()