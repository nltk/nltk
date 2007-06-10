#!/usr/bin/python
#
# lexicon.py
#
# Edward Loper
# Created [12/10/00 11:51 PM]
# $Id$
#

"""Lexicon!

Files have lines of the form:
<word> : <lambda-term> : <type>

"""

from term import *
from typedterm import *

# Map from word to TypedTerm
class Lexicon:
    def __init__(self):
        self._map = {}

    def load(self, file):
        for line in file.readlines():
            line = (line.split('#')[0]).strip()
            if len(line) == 0:  continue
            try:
                (word, term, type) = line.split(':')
                te = TypedTerm(parse_term(term), parse_type(type)) 
            except ValueError:
                print 'Bad line:', line
                continue
            
            word = word.strip().lower()
            if self._map.has_key(word):
                print 'Duplicate definitions for', word
            self._map[word] = te

    def words(self):
        return self._map.keys()
            
    def __getitem__(self, word):
        word = word.strip().lower()
        if word[0] == '[' and word[-1] == ']':
            try: return TypedTerm(Var(), parse_type(word[1:-1]))
            except ValueError: return None
        return self._map[word]

    def parse(self, str):
        """parse(self, str)
        Return a list of TypedTerms, for each word.  You can use
        forms like [np] and [s/np\n] to specify anonymous typed
        things.."""
        return [self[w] for w in str.split() if w != '']

    def __setitem__(self, word, te):
        word = word.strip().lower()
        if type(word) != type('') or \
           not isinstance(te, TypedTerm):
            raise ValueError('Expected string and TypedTerm')
        self._map[word] = te
