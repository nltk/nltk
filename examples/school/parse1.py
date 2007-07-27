from parser import *

grammar = """
   NP -> P | D J N
   D -> 'a'
   J -> 'red' | 'green'
   N -> 'chair' | 'house'
"""

phrase = 'a red chair'

parse_draw(phrase, grammar)


