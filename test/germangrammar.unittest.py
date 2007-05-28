from parse import *
import unittest

class TestGermanGrammar(unittest.TestCase):
    """
    Unit tests for German CFGs.
    """
    
    def evaluate(self, grammar):
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
                if key=='accept':
                    self.failUnless(trees, "Sentence '%s' failed to parse'" % sent)
                else:
                    self.failIf(trees, "Sentence '%s' received a parse'" % sent)

    def testPerson(self):
        "Tests for person agreement"

        cp = load_earley('german1.cfg', trace=0)
        self.suite = {}    
        self.suite['accept'] = [
            'ich komme',
            'ich sehe mich',
            'du kommst',
            'du siehst mich',
            'sie kommt',
            'sie sieht mich',
            'wir kommen',
            'ihr kommst',
            'sie kommen'
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
            'sie komme',
            'sie kommst'  
        ]

        self.evaluate(cp)


    def testNumber(self):
        "Tests for number agreement"
        
        cp = load_earley('german1.cfg', trace=0)
        self.suite = {} 
        self.suite['accept'] = [
            'der hund kommt',
            'die hunde kommen',
            'ich komme',
            'wir kommen',
            'ich sehe die katzen',
            'ich folge die hunde'
        ]
        self.suite['reject'] = [
            'ich kommen',
            'wir komme',
            'der hunde kommt',
            'der hunde kommen',
            'die katzen kommt',
            'die hunde sehe die hunde', 
            'der hund sehe die hunde', 
            'ich sehe ich',
            'ich hilft den hund',
            'ich hilft der hund',
            'ich sehe dem hund',
            'ich komme den hund'  
        ]

        self.evaluate(cp)
        
    def testCase(self):
        "Tests for case government"

        cp = load_earley('german1.cfg', trace=0)
        self.suite = {} 
        self.suite['accept'] = [
            'der hund sieht die katze', 
            'der hund kommt',
            'die katzen kommen',
            'ich sehe den hund',
            'ich helfe dem hund',
            ]
        self.suite['reject'] = [
            'der hunde kommt mich',
            #'die hunde sehe die hunde', 
            #'der hund sehe die hunde', 
            #'ich sehe ich',
            #'ich hilft den hund',
            #'ich hilft der hund',
            #'ich sehe dem hund',
            #'ich komme den hund'  
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
