import nltk

def parse(sent, grammar):
    gr = nltk.cfg.parse_cfg(grammar)
    parser = nltk.ChartParser(gr, nltk.parse.TD_STRATEGY)
    trees = parser.nbest_parse(sent.split())
    nltk.draw.draw_trees(*trees)

grammar = """
    S -> NP V NP
    NP -> NP Sbar
    Sbar -> NP V
    NP -> 'fish' | 'police'
    V -> 'fish' | 'police'
"""

sent = 'police police police police police police police police police'
parse(sent, grammar)

