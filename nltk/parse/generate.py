# Natural Language Toolkit: Generating from a CFG
#
# Copyright (C) 2001-2026 NLTK Project
# Author: Steven Bird <stevenbird1@gmail.com>
#         Peter Ljunglöf <peter.ljunglof@heatherleaf.se>
#         Eric Kafe <kafe.eric@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
#

import itertools
import sys

from nltk.grammar import Nonterminal

#: Upper bound on the number of derivation-expansion steps a single
#: ``generate`` call may perform. A recursive grammar can derive an exponential
#: (doubly-exponential for a self-embedding rule) number of sentences, so with
#: the default ``depth`` and no ``n`` limit a tiny grammar (e.g. ``S -> S S |
#: 'a'``) makes generation hang or exhaust memory (CWE-400). Once this many
#: expansion steps have been taken, generation raises ``ValueError`` instead of
#: running unbounded. Raise it if you legitimately need to enumerate a larger
#: (terminating) grammar.
MAX_GENERATE_OPERATIONS = 1_000_000


class _GenerationBudget:
    """Counts derivation-expansion steps and aborts runaway generation.

    The whole enumeration shares one budget, so it bounds total work however
    the caller consumes the iterator (one ``next()`` or a full ``list()``).
    """

    __slots__ = ("remaining", "limit")

    def __init__(self, limit):
        self.remaining = limit
        self.limit = limit

    def spend(self):
        self.remaining -= 1
        if self.remaining < 0:
            raise ValueError(
                "Refusing to generate further: a recursive grammar can derive "
                "an exponential number of sentences, and generation exceeded "
                "the limit of %d derivation-expansion steps (CWE-400). Pass a "
                "smaller 'depth' or 'n', remove cyclic/self-embedding rules, or "
                "raise nltk.parse.generate.MAX_GENERATE_OPERATIONS." % self.limit
            )


def generate(grammar, start=None, depth=None, n=None):
    """
    Generates an iterator of all sentences from a CFG.

    :param grammar: The Grammar used to generate sentences.
    :param start: The Nonterminal from which to start generate sentences.
    :param depth: The maximal depth of the generated tree.
    :param n: The maximum number of sentences to return.
    :return: An iterator of lists of terminal tokens.
    :raise ValueError: if generation exceeds ``MAX_GENERATE_OPERATIONS``
        derivation-expansion steps, which a recursive grammar reaches with
        the default ``depth`` and no ``n`` limit (CWE-400).
    """
    if not start:
        start = grammar.start()
    if depth is None:
        # Safe default, assuming the grammar may be recursive:
        depth = (sys.getrecursionlimit() // 3) - 3

    budget = _GenerationBudget(MAX_GENERATE_OPERATIONS)
    iter = _generate_all(grammar, [start], depth, budget)

    # ``n is not None`` (not ``if n``) so that n=0 is honoured as "return no
    # sentences" rather than being treated as "no limit".
    if n is not None:
        iter = itertools.islice(iter, n)

    return iter


def _generate_all(grammar, items, depth, budget):
    if items:
        try:
            for frag1 in _generate_one(grammar, items[0], depth, budget):
                for frag2 in _generate_all(grammar, items[1:], depth, budget):
                    yield frag1 + frag2
        except RecursionError as error:
            # Helpful error message while still showing the recursion stack.
            raise RuntimeError(
                "The grammar has rule(s) that yield infinite recursion!\n\
Eventually use a lower 'depth', or a higher 'sys.setrecursionlimit()'."
            ) from error
    else:
        yield []


def _generate_one(grammar, item, depth, budget):
    # Count every expansion so a recursive grammar can't enumerate an
    # unbounded/exponential number of derivations (CWE-400).
    budget.spend()
    if depth > 0:
        if isinstance(item, Nonterminal):
            for prod in grammar.productions(lhs=item):
                yield from _generate_all(grammar, prod.rhs(), depth - 1, budget)
        else:
            yield [item]


demo_grammar = """
  S -> NP VP
  NP -> Det N
  PP -> P NP
  VP -> 'slept' | 'saw' NP | 'walked' PP
  Det -> 'the' | 'a'
  N -> 'man' | 'park' | 'dog'
  P -> 'in' | 'with'
"""


def demo(N=23):
    from nltk.grammar import CFG

    print("Generating the first %d sentences for demo grammar:" % (N,))
    print(demo_grammar)
    grammar = CFG.fromstring(demo_grammar)
    for n, sent in enumerate(generate(grammar, n=N), 1):
        print("%3d. %s" % (n, " ".join(sent)))


if __name__ == "__main__":
    demo()
