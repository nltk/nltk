# -*- coding: utf-8 -*-
"""
Unit tests for nltk.tree
"""

from __future__ import unicode_literals

import unittest

from nltk.tree import Tree

class TestTree(unittest.TestCase):
    
    def test_lt(self):
        vp = Tree('VP', [Tree('V', ['saw']), Tree('NP', ['him'])])
        s = Tree('S', [Tree('NP', ['I']), vp])
        assert vp > s
        
        
    def test_lt_different_class(self):
        vp = Tree('VP', [Tree('V', ['saw']), Tree('NP', ['him'])])
        assert vp < 's'

