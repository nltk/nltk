import nltk

def parse(sent, grammar):
    gr = nltk.cfg.parse_cfg(grammar)
    parser = nltk.ChartParser(gr, nltk.parse.TD_STRATEGY)
    trees = parser.nbest_parse(sent.split())
    nltk.draw.draw_trees(*trees)

grammar = """
   S -> NP VP
   VP -> V NP | VP PP
   NP -> Det N | NP PP
   PP -> P NP
   NP -> 'I'
   Det -> 'the' | 'a' | 'my'
   N -> 'elephant' | 'pajamas' | 'man' | 'park' | 'telescope'
   V -> 'shot' | 'saw'
   P -> 'in' | 'on' | 'with'
"""

sent = 'I saw the man in the park with a telescope'
parse(sent, grammar)
