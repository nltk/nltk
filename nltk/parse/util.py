# Natural Language Toolkit: Parser Utility Functions
#
# Author: Ewan Klein <ewan@inf.ed.ac.uk>
#         
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT


"""
Utility functions for parsers.
"""

######################################################################
#{ Test Suites
######################################################################


from featurechart import load_earley

class TestGrammar(object):
    """
    Unit tests for  CFG.
    """
    def __init__(self, grammar, suite, accept=None, reject=None):
        self.test_grammar = grammar
        
        self.cp = load_earley(grammar, trace=0)
        self.suite = suite
        self._accept = accept
        self._reject = reject
        
    
    def run(self, show_trees=False):
        """
        Sentences in the test suite are divided into two classes:
         - grammatical (C{accept}) and
         - ungrammatical (C{reject}). 
        If a sentence should parse accordng to the grammar, the value of
        C{trees} will be a non-empty list. If a sentence should be rejected
        according to the grammar, then the value of C{trees} will be C{None}.
        """
        for test in self.suite:
            print test['doc'] + ":",
            for key in ['accept', 'reject']:
                for sent in test[key]:
                    tokens = sent.split()
                    trees = self.cp.parse(tokens)
                    if show_trees and trees:
                        print
                        print sent
                        for tree in trees:
                            print tree
                    if key=='accept':
                        if trees == []:
                            raise ValueError, "Sentence '%s' failed to parse'" % sent
                        else:
                            accepted = True
                    else:
                        if trees:
                            raise ValueError, "Sentence '%s' received a parse'" % sent
                        else:
                            rejected = True
            if accepted and rejected:
                print "All tests passed!"



