# Natural Language Toolkit: Generating from a CFG
#
# Copyright (C) 2001-2012 NLTK Project
# Author: Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT
#

from nltk.grammar import Nonterminal, parse_cfg

def all_combsi(lol):
    lens = map(lambda x: len(x), lol)
    num_combs = reduce(lambda x, y: x*y, lens, 1)
    for i in xrange(num_combs):
        tmp = [0]*len(lol)
        for j in xrange(len(tmp)):
            tmp[j] = lol[j][i % lens[j]]
            i = i / lens[j]
        yield tmp

def expand_nonterm(symbol, grammar):
    if isinstance(symbol, Nonterminal):
        return map(lambda prod: list(prod.rhs()), grammar.productions(lhs=symbol))
    else:
        return symbol

def tree_traverse(root, get_children, isleaf, maxdepth):
    if isleaf(root):
        yield root
    elif maxdepth > 0:
        for child in get_children(root):
            for x in tree_traverse(child, get_children, isleaf, maxdepth - 1):
                yield x

def flatten(lst):
    val = []
    for x in lst:
        if isinstance(x, list):
            val = val + x
        else:
            val.append(x)
    return val

def generate(grammar, start=None, depth=10):
    def is_terminal(lofs):
        tmp = map(lambda x: not isinstance(x, Nonterminal), lofs)
        return all(tmp)

    def get_children(l_of_symbols):
        x = map(lambda x: expand_nonterm(x, grammar), l_of_symbols)
        x = map(lambda x: x if isinstance(x, list) else [x], x)
        for comb in all_combsi(x):
            yield flatten(comb)

    if not start:
        start = grammar.start()
    return [x for x in tree_traverse([start], get_children, is_terminal, depth)]

def _generate_demo():
    g = parse_cfg("""
      S -> NP VP
      NP -> Det N
      VP -> V NP
      Det -> 'the'
      Det -> 'a'
      N -> 'man' | 'park' | 'dog' | 'telescope'
      V -> 'saw' | 'walked'
      P -> 'in' | 'with'
    """)
    for s in generate(g):
        print ' '.join(s)

if __name__ == "__main__":
    _generate_demo()
