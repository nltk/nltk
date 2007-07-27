from parser import *

grammar = """
   S -> NP VP | VP
   VP -> V NP | VP PP
   NP -> Det N | NP PP
   PP -> P NP
   NP -> 'I'
   Det -> 'the' | 'my'
   N -> 'elephant' | 'pajamas'
   V -> 'shot'
   P -> 'in'
"""

sent = 'I shot the elephant in my pajamas'
parse_draw(sent, grammar)

