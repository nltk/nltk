# Natural Language Toolkit: Shift-Reduce Parser
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
A shift-reduce parser is a simple kind of bottom-up parser which
returns a single tree.  This parser has been left incomplete
deliberately.  It is a student exercise to convert the shift-reduce
algorithm into Python and write code to test it.  Observe that rule
order is significant.  What are the issues here?
"""

from nltk.tree import *
from nltk.rule import *
from nltk.parser import ParserI
from nltk.token import WSTokenizer

class SRParser(ParserI):
    """
    """
    def __init__(self, rules, basecat):
        """
        Construct a new C{SRParser}.
        """

        self._rules = rules      # the grammar and lexical rules
        self._basecat = basecat  # the base category of the grammar
 
    # THE SHIFT RULE:
    # push the next token onto the stack
    # also maintain a another structure for the treetokens
    # (e.g. push the corresponding TreeToken onto another stack)
    def _shift(self, token):
        pass

    # THE REDUCE RULE:
    # check to see if any rule rhs matches the top n elements of
    # the stack.  For example, if the stack was [man, Det] then
    # the rule N->man would match, and we would replace the matching
    # material with the lhs of the rule to get [N, Det].  This would
    # then match NP->Det N and would be reduced to [NP].  Maintain another
    # structure containing the TreeTokens which have been created.
    # Note that a rule rhs matches the stack elements in reverse order
    # (unless the top of stack is changed to be the right end of the list).
    # Note that applying a grammar rule may create the context in which
    # some other grammar rule now applies.
    def _reduce(self):
        pass

    # THE PARSER
    def parse(self, tokens):
        # initialization
        self._stack = []
        # initialize a structure for keeping track of the tree fragments
        self._tree = ...

        # iterate through the tokens, pushing the token's type onto
        # the stack, then reducing the stack.
        for token in tokens:
            self._shift(token.type())
            self._reduce()

        # return a list consisting of a single TreeToken
        # does it have a root labelled self._basecat?
        # does it account for all the tokens in the sentence?
        return self._tree

# DEMONSTRATION CODE

grammar = (
    Rule('S',('NP','VP')),
    Rule('NP',('Det','N', 'PP')),
    Rule('NP',('Det','N')),
    Rule('VP',('V','NP', 'PP', 'PP')),
    Rule('VP',('V','NP', 'PP')),
    Rule('VP',('V','NP')),
    Rule('VP',('V','PP')),
    Rule('PP',('P','NP'))
)

lexicon = (
    Rule('NP',('I',)),
    Rule('Det',('the',)),
    Rule('Det',('a',)),
    Rule('N',('man',)),
    Rule('V',('saw',)),
    Rule('P',('in',)),
    Rule('P',('with',)),
    Rule('N',('park',)),
    Rule('N',('telescope',))
)

def demo():
    sent = 'I saw a man in the park with a telescope'

    # tokenize the sentence
    tok_sent = WSTokenizer().tokenize(sent)

    # initialize the chartparser
    parser = SRParser(grammar + lexicon, 'S')

    parses = parser.parse(tok_sent)
    parses[0].draw()

if __name__ == '__main__': demo()
