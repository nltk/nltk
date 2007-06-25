#!/usr/bin/env python2.5
from nltk.parse import chart
from nltk import cfg
from drawchart import ChartDemo
from nltk.tokenize.regexp import wordpunct
#from nltk_contrib.mit.six863.kimmo import *
import re, pickle

def chart_tagger(tagger):
    def insert_tags(thechart, tokens):
        """
        Initialize a chart parser based on the results of a tagger.
        """
        tagged_tokens = list(tagger.tag(tokens))
        for i in range(len(tagged_tokens)):
            word, tag = tagged_tokens[i]
            leafedge = chart.LeafEdge(word, i)
            thechart.insert(chart.TreeEdge((i, i+1),
              cfg.Nonterminal(tag), [word], dot=1), [leafedge])
    return insert_tags

def chart_kimmo(kimmorules):
    def insert_tags(thechart, tokens):
        for i in range(len(tokens)):
            word = tokens[i]
            results = kimmorules.recognize(word.lower())
            for surface, feat in results:
                match = re.match(r"PREFIX\('.*?'\)(.*?)\(.*", feat)
                if match: pos = match.groups()[0]
                else: pos = feat.split('(')[0]
                print surface, pos
                leafedge = chart.LeafEdge(word, i)
                thechart.insert(chart.TreeEdge((i, i+1),
                  cfg.Nonterminal(pos), [word], dot=1), [leafedge])
    return insert_tags

def tagged_chart_parse(sentence, grammar, tagger):
    tokens = list(wordpunct(sentence))
    demo = ChartDemo(grammar, tokens, initfunc=chart_tagger(tagger))
    demo.mainloop()

def kimmo_chart_parse(sentence, grammar, kimmo):
    tokens = list(wordpunct(sentence))
    demo = ChartDemo(grammar, tokens, initfunc=chart_kimmo(kimmo))
    demo.mainloop()

def read(filename):
    f = open(filename)
    return f.read()

def main():
    sentence = 'The quick brown fox jumped over the lazy dog'
    grammar = cfg.parse_grammar(read('demo.cfg'))
    # load from pickle so it's faster
    tagger = pickle.load(open('demo_tagger.pickle'))
    tagged_chart_parse(sentence, grammar, tagger)
    #kimmo = load('english.yaml')
    #kimmo_chart_parse(sentence, grammar, kimmo)
    
if __name__ == '__main__': main()

