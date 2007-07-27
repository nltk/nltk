from parser import *

grammar = """
   S -> NP VP | VP
   PP -> P NP
   NP -> N | Det N | N N | NP PP | N VP
   VP -> V | V NP | VP PP | VP ADVP
   ADVP -> ADV NP
   Det -> 'a' | 'an' | 'the'
   N -> 'flies' | 'banana' | 'fruit' | 'arrow' | 'time'
   V -> 'like' | 'flies' | 'time'
   P -> 'on' | 'in' | 'by'
   ADV -> 'like'
"""

sent = 'time flies like an arrow'

parse_draw(sent, grammar)




