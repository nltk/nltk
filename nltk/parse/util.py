# Natural Language Toolkit: Parser Utility Functions
#
# Author: Ewan Klein <ewan@inf.ed.ac.uk>
#         
# URL: <http://www.nltk.org/>
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


def extract_test_sentences(string, comment_chars="#%;"):
    """
    Parses a string with one test sentence per line.
    Lines can optionally begin with:
      - a C{bool}, saying if the sentence is grammatical or not, or
      - an C{int}, giving the number of parse trees is should have,
    The result information is followed by a colon, and then the sentence.
    Empty lines and lines beginning with a comment char are ignored.

    @return: a C{list} of C{tuple} of sentences and expected results,
        where a sentence is a C{list} of C{str},
        and a result is C{None}, or C{bool}, or C{int}

    @param comment_chars: L{str} of possible comment characters.
    """
    sentences = []
    for sentence in string.split('\n'):
        if sentence=='' or sentence[0] in comment_chars: continue
        split_info = sentence.split(':', 1)
        result = None
        if len(split_info)==2: 
            if split_info[0] in ['True','true','False','false']:
                result = split_info[0] in ['True','true']
                sentence = split_info[1]
            else: 
                result = int(split_info[0])
                sentence = split_info[1]
        tokens = sentence.split()
        if tokens==[]: continue
        sentences += [(tokens, result)]
    return sentences

