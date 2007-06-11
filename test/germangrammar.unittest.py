from nltk.parse import *
from nltk.parse.featurechart import *
import unittest

class TestGermanGrammar(unittest.TestCase):
    """
    Unit tests for German CFG.
    """
    def setUp(self):
        self.test_grammar = 'german0.cfg'
    
    def evaluate(self, grammar, show_trees=False):
        """
        Sentences in the test suite are divided into two classes:
         - grammatical (C{accept}) and
         - ungrammatical (C{reject}). 
        If a sentence should parse accordng to the grammar, the value of
        C{trees} will be a non-empty list. If a sentence should be rejected
        according to the grammar, then the value of C{trees} will be C{None}.
        """
        for key in self.suite:
            for sent in self.suite[key]:
                tokens = list(tokenize.whitespace(sent))
                trees = grammar.parse(tokens)
                if show_trees and trees:
                    print
                    print sent
                    for tree in trees:
                        print tree
                if key=='accept':
                    self.failUnless(trees, "Sentence '%s' failed to parse'" % sent)
                else:
                    self.failIf(trees, "Sentence '%s' received a parse'" % sent)

    def testPerson(self):
        "Tests for person agreement"

        cp = load_earley(self.test_grammar, trace=0)
        self.suite = {} 
        #for some reason, 'ihr kommst' fails to parse
        #if it is processed after 'wir kommen'!??
        self.suite['accept'] = [
            'ich komme',
            'ich sehe mich',
            'du kommst',
            'du siehst mich',
            'sie kommt',
            'sie sieht mich',
            'ihr kommst',
            'wir kommen',
            'sie kommen',
            'du magst mich',
            'er mag mich',
            'du folgst mir',
            'sie hilft mir',
            ]
        self.suite['reject'] = [
            'ich kommt',
            'ich kommst',
            'ich siehst mich',
            'du komme',
            'du sehe mich',
            'du kommt',
            'er komme',
            'er siehst mich',
            'wir komme',
            'wir kommst',
            'die katzen kommst',
            'sie komme',
            'sie kommst',
            'du mag mich',
            'er magst mich',
            'du folgt mir',
            'sie hilfst mir',
        ]

        self.evaluate(cp)


    def testNumber(self):
        "Tests for number agreement"
        
        cp = load_earley(self.test_grammar, trace=0)
        self.suite = {} 
        self.suite['accept'] = [
            'der hund kommt',
            'die hunde kommen',
            'ich komme',
            'wir kommen',
            'ich sehe die katzen',
            'ich folge den katzen'
        ]
        self.suite['reject'] = [
            'ich kommen',
            'wir komme',
            'der hunde kommt',
            'der hunde kommen',
            'die katzen kommt',
            'ich sehe der hunde', 
            'ich folge den hund', 
        ]

        self.evaluate(cp)
        
    def testCase(self):
        "Tests for case government and subcategorization"

        cp = load_earley(self.test_grammar, trace=0)
        self.suite = {} 
        self.suite['accept'] = [
            'der hund sieht mich', 
            'der hund kommt',
            'ich sehe den hund',
            'ich helfe dem hund',
            ]
        self.suite['reject'] = [
            'ich sehe',
            'ich helfe',
            'ich komme den hund',
            'ich sehe den hund die katzen',
            'du hilfst mich',
            'du siehst mir',
            'du siehst ich',
            'der hunde kommt mich',
            'die hunde sehe die hunde', 
            'der hund sehe die hunde', 
            'ich hilft den hund',
            'ich hilft der hund',
            'ich sehe dem hund',
        ]

        self.evaluate(cp)


def testsuite():
    suite = unittest.makeSuite(TestGermanGrammar)
    return unittest.TestSuite(suite)

def test(verbosity):
    runner = unittest.TextTestRunner(verbosity=verbosity)
    runner.run(testsuite())

if __name__ == "__main__":
    test(verbosity=2) 
