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
        self._num = 0
        self._finals = Set(0)
        self._table = {}
        re_list = _tokenizer.tokenize(re)
        tree = _parser.parse(re_list)
        self._build(tree)
        self.remove_epsilons()
        self.minimize()

    def _new_state(self):
        self._num += 1
        return self._num

    def _build(self, tree):
        if len(tree) == 0:
            self.concat_char(tree.node())
        elif len(tree) == 1:
            self._build(tree[0])
        elif tree[0] == Tree('(') and tree[2] == Tree(')'):
            self._build(tree[1])
        elif tree[1] == Tree('*'):
            start_states = self._finals
            self._build(tree[0])
            self.kleene_star(start_states)
        elif tree[1] == Tree('+'):
            start_states = self._finals
            self._build(tree[0])
            self.kleene_plus(start_states)
        elif tree[1] == Tree('?'):
            start = self._finals
            self._build(tree[0])
            self.optional(start_states)
        else:
            self._build(tree[0])
            self._build(tree[1])
        
    def insert_transition(self, s1, label, s2):
        if self._table.has_key((s1,label)):
            self._table[(s1,label)].union(s2)
        else:
            self._table[(s1,label)] = s2

    def insert_transitions(self, state_set, label, s2):
        for s1 in state_set.elements():
            self.insert_transition(s1, label, s2)

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

    # CONSIDER CHANGING DATA STRUCTURE SO THAT THIS IS EFFICIENT
    def outgoing_transitions(self, node):
        return [(s1,label,s2)
                for (s1, label, s2) in self.transitions()
                if s1 == node]

    def concat_char(self, char):
        new_final = Set(self._new_state())
        for state in self._finals.elements():
            self.insert_transition(state, char, new_final)
        self._finals = new_final
        
    def optional(self, start = Set(0)):
#        self._finals = self._finals.intersection(start)
        self.insert_transitions(start, epsilon, self._finals)

    def kleene_plus(self, start = Set(0)):
        self.insert_transitions(self._finals, epsilon, start)

    def kleene_star(self, start = Set(0)):
        self.kleene_plus(start)
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
#        for final in self._finalss:
#            self.insert_transition(final, epsilon, self._count)
#        self._table.extend(fsa._table)

    # this algorithm breaks when there are two epsilons in a row
    def remove_epsilons(self):
        while self.epsilon_transitions() != []:
            for (s1, label1, s2) in self.epsilon_transitions():
                if self._finals.intersection(s2):
                    self._finals.insert(s1)
                for state in s2.elements():
                    for (s3, label2, s4) in self.outgoing_transitions(state):
                        self.insert_transition(s1, label2, s4)
                self.delete_transition(s1, label1, s2)
    
    def minimize(self):
        pass

    # generate all strings in the language up to length maxlen
    def generate(self, maxlen, state=0, prefix=""):
        if maxlen > 0:
            if self._finals.contains(state):
                print prefix
            for (s1, label, states) in self.outgoing_transitions(state):
                for s2 in states.elements():
                    self.generate(maxlen-1, s2, prefix+label)

    def pp(self):
        t = self.transitions()
        t.sort()
        for (s1, label, s2) in t:
            print s1, ':', label, '->', s2
        print "Final:", self._finals

    # TODO - epsilon removal, minimization

def demo():
    re = 'a(b+)(c+)d'
    print 'Regular Expression:', re
    fsa = FSA(re)
    fsa.pp()
    fsa.generate(10)

if __name__ == '__main__': demo()
