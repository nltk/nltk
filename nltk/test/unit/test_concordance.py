# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals


import unittest
from nose import with_setup

from nltk.corpus import gutenberg
from nltk.text import Text

import contextlib
import sys

try:
    from StringIO import StringIO
except ImportError as e:
    from io import StringIO

@contextlib.contextmanager
def stdout_redirect(where):
    sys.stdout = where
    try:
        yield where
    finally:
        sys.stdout = sys.__stdout__
        
class TestConcordance(unittest.TestCase):
    """Using this tutorial: http://www.nltk.org/book/ch01.html 
    to construct texts"""

    @classmethod
    def setup_class(cls):
        cls.corpus = gutenberg.words('melville-moby_dick.txt')
        
    @classmethod
    def teardown_class(cls):
        pass
    
    def setUp(self):
        self.text = Text(TestConcordance.corpus)
        self.query = "monstrous"
        
    def tearDown(self):
        pass
    
    def test_concordance_list(self):
        list_out = ["ong the former , one was of a most monstrous size . ... This came towards us",
        "ON OF THE PSALMS . \" Touching that monstrous bulk of the whale or ork we have r",
        "ll over with a heathenish array of monstrous clubs and spears . Some were thick",
        "d as you gazed , and wondered what monstrous cannibal and savage could ever hav",
        "that has survived the flood ; most monstrous and most mountainous ! That Himmal",
        "they might scout at Moby Dick as a monstrous fable , or still worse and more de",	
        "th of Radney .'\" CHAPTER 55 Of the monstrous Pictures of Whales . I shall ere l",
        "ing Scenes . In connexion with the monstrous pictures of whales , I am strongly",
        "ere to enter upon those still more monstrous stories of them which are to be fo",
        "ght have been rummaged out of this monstrous cabinet there is no telling . But",
        "of Whale - Bones ; for Whales of a monstrous size are oftentimes cast up dead u"]
        self.assertListEqual(list_out, 
                   self.text.concordance(self.query))
        return
    
    def test_concordance_print(self):
        print_out = """Displaying 11 of 11 matches:
            ong the former , one was of a most monstrous size . ... This came towards us ,
            ON OF THE PSALMS . \" Touching that monstrous bulk of the whale or ork we have r
            ll over with a heathenish array of monstrous clubs and spears . Some were thick
            d as you gazed , and wondered what monstrous cannibal and savage could ever hav
            that has survived the flood ; most monstrous and most mountainous ! That Himmal
            they might scout at Moby Dick as a monstrous fable , or still worse and more de
            th of Radney .'\" CHAPTER 55 Of the monstrous Pictures of Whales . I shall ere l
            ing Scenes . In connexion with the monstrous pictures of whales , I am strongly
            ere to enter upon those still more monstrous stories of them which are to be fo
            ght have been rummaged out of this monstrous cabinet there is no telling . But
            of Whale - Bones ; for Whales of a monstrous size are oftentimes cast up dead u"""
        
        with stdout_redirect(StringIO()) as stdout:
            self.text.concordance(self.query)
        
        clean = lambda rstr: rstr.lower().split()
        
        self.assertListEqual(clean(print_out), 
                             clean(stdout.getvalue()))
        
        return