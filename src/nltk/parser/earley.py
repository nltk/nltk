# Natural Language Toolkit: Earley Parser
#
# Copyright (C) 2003 University of Pennsylvania
# Author: Robert Berwick <berwick@ai.mit.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

from nltk import cfg
from nltk.cfg import Nonterminal
from nltk.cfg import CFGProduction as Rule
from nltk.parser import chart as chartmod
from nltk.token import Location

class EarleyCFG(cfg.CFG):
    def __init__(self, start, grammar, lexicon):
        grammar.extend(lexicon)
        cfg.CFG.__init__(self, start, grammar)

        self.grammar = {}
        self.lexicon = {}
        self.partsOfSpeech = {} #prevents duplicate elements
        for rule in grammar:
            if self.grammar.has_key(rule.lhs()):
                self.grammar[rule.lhs()].append(rule)
            else:
                self.grammar[rule.lhs()] = [rule]
                
            if len(rule.rhs())==1 and type(rule.rhs()[0])==type(""):
                #it's a word definition, not a rule
                if self.lexicon.has_key(rule.rhs()[0]):
                    self.lexicon[rule.rhs()[0]].append(rule.lhs())
                else:
                    self.lexicon[rule.rhs()[0]] = [rule.lhs()]
                self.partsOfSpeech[rule.lhs()] = None
            
    def getRules(self, nonterminal):
        if type(nonterminal) == type(""):
            nonterminal = cfg.Nonterminal(nonterminal)
        if self.grammar.has_key(nonterminal):
            return self.grammar[nonterminal]
        else:
            return []

    def getPartsOfSpeech(self, word):
        if self.lexicon.has_key(word):
            return self.lexicon[word]
        else:
            return []

    def isPartOfSpeech(self, nonterminal):
        if type(nonterminal) == type(""):
            nonterminal = cfg.Nonterminal(nonterminal)
        return self.partsOfSpeech.has_key(nonterminal)

class EarleyChart(chartmod.Chart):
    def __init__(self, text):
        loc = Location(text[0].loc().start(), text[-1].loc().end(),
                       unit=text[0].loc().unit(),
                       source=text[0].loc().source())
        chartmod.Chart.__init__(self, loc)
        self.text = text

    def wordAt(self, i):
        return self.text[i].type()
    def textLength(self):
        return len(self.text)
        
class SteppingEarleyParser(chartmod.SteppingChartParser):     
    def _create_chart(self, text):
        """
        @param text: The text to be parsed
        @rtype: C{Chart}
        """
        chart = EarleyChart(text)

        # Add an edge for each lexical item.
        #if self._trace: print 'Adding lexical edges...'
        for tok in text:
            new_edge = chartmod.TokenEdge(tok)
            if chart.insert(new_edge):
                if self._trace > 1:
                    print '%-20s %s' % ('Lexical Insertion',
                                        chart.pp_edge(new_edge))

        # Return the new chart
        return chart


class EarleyInitRule(chartmod.ChartRuleI):
    def apply(self, chart, grammar):
        edges = []
        for production in grammar.getRules(grammar.start()):
            loc = chart.loc().start_loc()
            edges.append(chartmod.self_loop_edge(production, loc))
        return edges
    def __str__(self): return 'Earley Initializer'

    
class EarleyScanner(chartmod.ChartRuleI):
    def apply(self, chart, grammar):
        edges = []
        for edge in chart.incomplete_edges():
            nextcat = edge.next()
            if grammar.isPartOfSpeech(nextcat):
                if edge.loc().end() >= chart.textLength():
                    continue
                word = chart.wordAt(edge.loc().end())
                if nextcat in grammar.getPartsOfSpeech(word):
                    prod = cfg.CFGProduction(nextcat, word)
                    loc = edge.loc().end_loc()                      
                    edges.append(chartmod.self_loop_edge(prod, loc))
        return edges
    def __str__(self): return 'Earley Scanner'

class EarleyPredictor(chartmod.ChartRuleI):
    def apply(self, chart, grammar):
        edges = []
        for edge in chart.incomplete_edges():
            nextcat = edge.next()
            if not grammar.isPartOfSpeech(nextcat):
                for prod in grammar.getRules(nextcat):
                    loc = edge.loc().end_loc()
                    edges.append(chartmod.self_loop_edge(prod, loc))
        return edges
    def __str__(self): return 'Earley Predictor'


class EarleyCompleter(chartmod.ChartRuleI):
    def apply(self, chart, grammar):
        edges = []
        for edge in chart.incomplete_edges():
            for edge2 in chart.complete_edges():
                if (edge.next() == edge2.lhs() and
                    edge.end() == edge2.start()):
                    edges.append(chartmod.fr_edge(edge, edge2))
        return edges
    def __str__(self): return 'Earley Completer'


def parseRule(text):
    tokens = text.split()
    return Rule(cfg.Nonterminal(tokens[0]),
                *map(lambda x: cfg.Nonterminal(x), tokens[2:]))

def parseLexicon(text):
    word, pos = text.split()
    return Rule(cfg.Nonterminal(pos), word)


grammar = EarleyCFG(cfg.Nonterminal('S'),
                    map(lambda x:parseRule(x),
                        ["S -> NP VP", "NP -> N", "NP -> Det N",
                         "VP -> V", "VP -> V NP"]),
                    map(lambda x:parseLexicon(x),
                        ["Poirot N", "sent V", "the Det", "solutions N"]))


def demo():
    sentence = 'Poirot sent the solutions'
    print "Sentence:\n", sentence

    # tokenize the sentence
    from nltk.tokenizer import WSTokenizer
    tok_sent = WSTokenizer().tokenize(sentence)

    cp = SteppingEarleyParser(grammar, [EarleyInitRule(), EarleyPredictor(),
                                EarleyScanner(), EarleyCompleter()],
                      trace=2)
    
    for parse in cp.parse_n(tok_sent): print parse

if __name__ == '__main__': demo()
