# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
import unittest

from nltk.twitter import twitterclient

class TestCredentials(unittest.TestCase):

    def test_missingfile(self):
