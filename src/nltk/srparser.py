# Natural Language Toolkit: Shift-Reduce Parser
#
# Copyright (C) 2002 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Scott Currie <sccurrie@seas.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#

"""
A shift-reduce parser is a simple kind of bottom-up parser which
returns a single tree.
"""

from nltk.parser import ParserI
from nltk.cfg import *
from nltk.tree import TreeToken
from nltk.token import Token

class SRParser(ParserI):
    """
    Shift-reduce parser.

    Maintain two stacks: one for tokens, one for types/Nonterminals.
    Match the Nonterminals/types stack against the RHS of rules when
    trying to reduce.  Use the token stack to record the structures
    we've built so far.
    """
    def __init__(self, grammar, trace=0):
        """
        Construct a new C{SRParser}.
        """
        self._grammar = grammar
        self._trace = trace
        self.check_grammar()

    def _shift(self, token, stack, tokstack, remaining_text):
        """
        Push the next token onto the stack.
        """
        stack.append(token.type())
        tokstack.append(token)
        if self._trace: self._trace_shift(stack, remaining_text)

    def _reduce(self, stack, tokstack, remaining_text):
        # scan through the rule set
        for rule in self._grammar.rules():
            rhslen = len(rule.rhs())
                
            # check if the RHS of a rule matches the top of the stack
            if tuple(stack[-rhslen:]) == rule.rhs():

                # replace the top of the stack with the LHS of the rule
                stack[-rhslen:] = [rule.lhs()]

                # combine the tree to reflect the reduction
                treetok = TreeToken(rule.lhs().symbol(), *tokstack[-rhslen:])
                tokstack[-rhslen:] = [treetok]

                # We reduced something
                if self._trace:
                    self._trace_reduce(stack, rule, remaining_text)
                return rule

        # We didn't reduce anything
        return 0

    def parse(self, text):
        # Inherit documentation from ParserI.

        # initialize the stacks.
        stack = []
        tokstack = []

        # Trace output.
        remaining_text = text
        if self._trace: self._trace_stack(stack, remaining_text)

        # iterate through the text, pushing the token's type onto
        # the stack, then reducing the stack.
        for token in text:
            remaining_text = remaining_text[1:]
            self._shift(token, stack, tokstack, remaining_text)
            while self._reduce(stack, tokstack, remaining_text): pass

        # Did we reduce everything?
        if len(stack) != 1: return None

        # Did we end up with the right category?
        if stack[0] != self._grammar.start(): return None
        
        # We parsed successfully!
        return tokstack[0]

    def _trace_stack(self, stack, remaining_text, marker=' '):
        print ('  '+marker+' [' + ' '.join([`s` for s in stack])+' * '+
               ' '.join([`s.type()` for s in remaining_text]) + ']')

    def _trace_shift(self, stack, remaining_text):
        if self._trace > 2: print 'Shift %r:' % stack[0]
        if self._trace == 2: self._trace_stack(stack, remaining_text, 'S')
        elif self._trace > 0: self._trace_stack(stack, remaining_text)

    def _trace_reduce(self, stack, rule, remaining_text):
        if self._trace > 2:
            print 'Reduce %r <- %s' % (rule.lhs(),
                                       ' '.join([`s` for s in rule.rhs()]))
        if self._trace == 2: self._trace_stack(stack, remaining_text, 'R')
        elif self._trace > 1: self._trace_stack(stack, remaining_text)

    # Delegate to parse
    def parse_n(self, text):
        # Inherit documentation from ParserI; delegate to parse.
        treetok = self.parse(text)
        if treetok is None: return []
        else: return [treetok]

    def trace(self, trace=2):
        """
        Set the level of tracing output that should be generated when
        parsing a text.

        @type trace: C{int}
        @param trace: The trace level.  A trace level of C{0} will
            generate no tracing output; and higher trace levels will
            produce more verbose tracing output.
        @rtype: C{None}
        """
        self._trace = trace

    def check_grammar(self):
        """
        Check that all the rules in the grammar are useful.
        """
        rules = self._grammar.rules()

        # Any rule whose RHS is an extension of another rule's RHS
        # will never be used. 
        for i in range(len(rules)):
            for j in range(i+1, len(rules)):
                rhs1 = rules[i].rhs()
                rhs2 = rules[j].rhs()
                if rhs1[:len(rhs2)] == rhs2:
                    print 'Warning: %r will never be used' % rules[i]

# DEMONSTRATION CODE
def demo():
    nonterminals = 'S VP NP PP P N Name V Det'
    (S, VP, NP, PP, P, N, Name, V, Det) = [Nonterminal(s)
                                           for s in nonterminals.split()]

    rules = (
        # Syntactic Rules
        CFG_Rule(S, NP, VP),
        CFG_Rule(NP, Det, N),
        CFG_Rule(VP, V, NP, PP),
        CFG_Rule(PP, P, NP),

        CFG_Rule(VP, V, PP),

        # Lexical Rules
        CFG_Rule(NP, 'I'),
        CFG_Rule(Det, 'the'),
        CFG_Rule(Det, 'a'),
        CFG_Rule(N, 'man'),
        CFG_Rule(V, 'saw'),
        CFG_Rule(P, 'in'),
        CFG_Rule(P, 'with'),
        CFG_Rule(N, 'park'),
        CFG_Rule(N, 'telescope')
        )
    cfg = CFG(S, rules)

    # Sample Sentence
    sent = 'I saw a man in the park'

    # Tokenize the sentence
    from nltk.token import WSTokenizer
    tok_sent = WSTokenizer().tokenize(sent)

    # Initialize the SR Parser
    parser = SRParser(cfg)

    # Run the parse on the token stream
    parser.trace(3)
    parses = parser.parse(tok_sent)

    # Display the results in text (and graphically)
    print parses
    #parses[0].draw()

if __name__ == '__main__': demo()
