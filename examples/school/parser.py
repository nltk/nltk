from __future__ import print_statement

import nltk

def parse(sent, grammar):
    gr = nltk.parse_cfg(grammar)
    parser = nltk.parse.ChartParse(gr, nltk.parse.TD_STRATEGY)
    return parser.get_parse_list(sent.split())

def parse_draw(sent, grammar):
    trees = parse(sent, grammar)
    nltk.draw.draw_trees(*trees)

def parse_print(sent, grammar):
    trees = parse(sent, grammar)
    for tree in trees:
        print(tree)

