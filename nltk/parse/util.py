# Natural Language Toolkit: Parser Utility Functions
#
# Author: Ewan Klein <ewan@inf.ed.ac.uk>
#         
# Copyright (C) 2001-2011 NLTK Project
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT


"""
Utility functions for parsers.
"""

from nltk.grammar import ContextFreeGrammar, FeatureGrammar, WeightedGrammar
from chart import Chart, ChartParser
from pchart import InsideChartParser
from featurechart import FeatureChart, FeatureChartParser 
import nltk.data

def load_parser(grammar_url, trace=0, 
                parser=None, chart_class=None, 
                beam_size=0, **load_args):
    """
    Load a grammar from a file, and build a parser based on that grammar. 
    The parser depends on the grammar format, and might also depend
    on properties of the grammar itself.
    
    The following grammar formats are currently supported:
      - C{'cfg'}  (CFGs: L{ContextFreeGrammar})
      - C{'pcfg'} (probabilistic CFGs: L{WeightedGrammar})
      - C{'fcfg'} (feature-based CFGs: L{ContextFreeGrammar})

    @type grammar_url: C{str}
    @param grammar_url: A URL specifying where the grammar is located.
        The default protocol is C{"nltk:"}, which searches for the file 
        in the the NLTK data package.
    @type trace: C{int}
    @param trace: The level of tracing that should be used when
        parsing a text.  C{0} will generate no tracing output;
        and higher numbers will produce more verbose tracing output.
    @param parser: The class used for parsing; should be L{ChartParser}
        or a subclass.
        If C{None}, the class depends on the grammar format.
    @param chart_class: The class used for storing the chart;
        should be L{Chart} or a subclass. 
        Only used for CFGs and feature CFGs.
        If C{None}, the chart class depends on the grammar format.
    @type beam_size: C{int}
    @param beam_size: The maximum length for the parser's edge queue.
        Only used for probabilistic CFGs.
    @param load_args: Keyword parameters used when loading the grammar.
        See L{data.load} for more information.
    """
    grammar = nltk.data.load(grammar_url, **load_args)
    if not isinstance(grammar, ContextFreeGrammar):
        raise ValueError("The grammar must be a ContextFreeGrammar, "
                         "or a subclass thereof.")
    if isinstance(grammar, WeightedGrammar):
        if parser is None: 
            parser = InsideChartParser
        return parser(grammar, trace=trace, beam_size=beam_size)
    
    elif isinstance(grammar, FeatureGrammar):
        if parser is None: 
            parser = FeatureChartParser
        if chart_class is None: 
            chart_class = FeatureChart
        return parser(grammar, trace=trace, chart_class=chart_class)
    
    else: # Plain ContextFreeGrammar.
        if parser is None: 
            parser = ChartParser
        if chart_class is None: 
            chart_class = Chart
        return parser(grammar, trace=trace, chart_class=chart_class)


######################################################################
#{ Test Suites
######################################################################

class TestGrammar(object):
    """
    Unit tests for  CFG.
    """
    def __init__(self, grammar, suite, accept=None, reject=None):
        self.test_grammar = grammar
        
        self.cp = load_parser(grammar, trace=0)
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

