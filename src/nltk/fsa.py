"""
FSA class - deliberately simple so that the operations are easily understood.
"""

from nltk.srparser import *
from nltk.token import CharTokenizer

_grammar = (
    Rule('S', ('S', '*')),
    Rule('S', ('S', '+')),
    Rule('S', ('S', '?')),
    Rule('S', ('S', 'S')),
    Rule('S', ('(', 'S', ')')),
    Rule('S',('a')),
    Rule('S',('b')),
    Rule('S',('c')),
    Rule('S',('d')),
    Rule('S',('e'))
)

_parser = SRParser(_grammar, 'S')
_tokenizer = CharTokenizer()

epsilon = 0

# TODO - check that parse was complete, and report error otherwise
# TODO - change parser to limit scope of unary operators
# to the most recent symbol

class FSA:
    def __init__(self, re):
        self._final = 0
        self._table = {}
        re_list = _tokenizer.tokenize(re)
        tree = _parser.parse(re_list)
        self._build(tree)
        self.remove_epsilons()
        self.minimize()

    def _build(self, tree):
        if len(tree) == 0:
            self._atomic(tree.node())
        elif len(tree) == 1:
            self._build(tree[0])
        elif tree[0] == Tree('(') and tree[2] == Tree(')'):
            self._build(tree[1])
        elif tree[1] == Tree('*'):
            start = self._final
            self._build(tree[0])
            self.star(start)
        elif tree[1] == Tree('+'):
            start = self._final
            self._build(tree[0])
            self.plus(start)
        elif tree[1] == Tree('?'):
            start = self._final
            self._build(tree[0])
            self.optional(start)
        else:
            self._build(tree[0])
            self._build(tree[1])
        
    def add_transition(self, s1, label, s2):
        if self._table.has_key((s1,label)):
            if s2 not in self._table[(s1,label)]:
                self._table[(s1,label)].append(s2)
        else:
            self._table[(s1,label)] = [s2]

    def transitions(self):
        return self._table.items()

    def _atomic(self, char):
        state = self._final
        self.add_transition(state, char, state+1)
        self._final += 1
        
    def optional(self, start):
        self.add_transition(start, epsilon, self._final)

    def plus(self, start):
        self.add_transition(self._final, epsilon, start)

    def star(self, start):
        self.plus(start)
        self.optional(start)

#    # add num to every state identifier
#    def add(self, num):
#        newtable = {}
#        for ((s1, label), s2) in self.transitions():
#            newtable[(s1+num, label)] = map(lambda x,num:x+num, s2)
#        self._table = newtable
#
#    def concat(self, fsa):
#        fsa.add(self._count) # relabel states for uniqueness
#
#        # TODO - add epsilon transition from finals to initials
#        for final in self._finals:
#            self.add_transition(final, epsilon, self._count)
#        self._table.extend(fsa._table)

    def remove_epsilons():
        pass
    
    def minimize():
        pass

    def pp(self):
        t = self.transitions()
        t.sort()
        for ((s1, label), s2) in t:
            print s1, ':', label, '->', s2
        print "Final:", self._final

    # TODO - epsilon removal, minimization

def demo():
    re = 'a(b*)c'
    print 'Regular Expression:', re
    fsa = FSA(re)
    fsa.pp()

if __name__ == '__main__': demo()
