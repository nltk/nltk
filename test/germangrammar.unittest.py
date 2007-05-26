from parse import *

import unittest

class TestGermanGrammar(unittest.TestCase):
    """
    Unit tests for German CFGs
    """
    
    def setUp(self):

        self.cp1 = load_earley('german_ma2.cfg', trace=0)
        
        
    def testCase(self):
        "Tests for case government"