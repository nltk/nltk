"""
FSA class - deliberately simple so that the operations are easily understood.
"""

from nltk.srparser import *
from nltk.token import CharTokenizer
from nltk.set import *

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
            self.insert_transition(self._final, epsilon, Set(start))
            self.insert_transition(start, epsilon, Set(self._final))
        elif tree[1] == Tree('+'):
            start = self._final
            self._build(tree[0])
            self.insert_transition(self._final, epsilon, Set(start))
        elif tree[1] == Tree('?'):
            start = self._final
            self._build(tree[0])
            self.insert_transition(start, epsilon, Set(self._final))
        else:
            self._build(tree[0])
            self._build(tree[1])
        
    def insert_transition(self, s1, label, s2):
        if self._table.has_key((s1,label)):
            self._table[(s1,label)].union(s2)
        else:
            self._table[(s1,label)] = s2

    def delete_transition(self, s1, label, s2):
        if self._table.has_key((s1,label)):
            new = self._table[(s1,label)].difference(s2)
            if len(new) > 0:
                self._table[(s1,label)] = new
            else:
                del self._table[(s1,label)]
        else:
            print "Error: attempt to delete non-existent transition"

    def transitions(self):
        return [(s1,label,s2)
                for ((s1,label),s2) in self._table.items()]

    def epsilon_transitions(self):
        return [(s1,label,s2)
                for (s1, label, s2) in self.transitions()
                if label == epsilon]

    def outgoing_transitions(self, node):
        return [(s1,label,s2)
                for (s1, label, s2) in self.transitions()
                if s1 == node]

    def _atomic(self, char):
        state = self._final
        self.insert_transition(state, char, Set(state+1))
        self._final += 1
        
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
#            self.insert_transition(final, epsilon, self._count)
#        self._table.extend(fsa._table)

    def remove_epsilons(self):
        while self.epsilon_transitions() != []:
            print self.epsilon_transitions()
            for (s1, label1, s2) in self.epsilon_transitions():
                for state in s2.elements():
                    for (s3, label2, s4) in self.outgoing_transitions(state):
                        self.insert_transition(s1, label2, s4)
                self.delete_transition(s1, label1, s2)
    
    def minimize(self):
        pass

    def pp(self):
        t = self.transitions()
        t.sort()
        for (s1, label, s2) in t:
            print s1, ':', label, '->', s2
        print "Final:", self._final

    # TODO - epsilon removal, minimization

def demo():
    re = 'a(b*)c'
    print 'Regular Expression:', re
    fsa = FSA(re)
    fsa.pp()

if __name__ == '__main__': demo()
