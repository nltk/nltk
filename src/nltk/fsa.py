"""
FSA class - deliberately simple so that the operations are easily understood.
Operations are based on Aho, Sethi & Ullman (1986) Chapter 3.
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

_STAR = Tree('*')
_PLUS = Tree('+')
_QMK = Tree('?')
_OPAREN = Tree('(')
_CPAREN = Tree(')')

epsilon = 0

# TODO - check that parse was complete, and report error otherwise
# TODO - change parser to limit scope of unary operators
# to the most recent symbol
# TODO - code up minimization algorithm from ASU

class FSA:
    def __init__(self, re):
        self._num = 0
        self._table = {}
        re_list = _tokenizer.tokenize(re)
        tree = _parser.parse(re_list)
        node = self._build(self._num, tree)
        self._finals = Set(node)
#        self.minimize()

    def _new_state(self):
        self._num += 1
        return self._num

    # create NFA from regexp (Thompson's construction)
    # assumes unique start and final states
    def _build(self, node, tree):
        if len(tree) == 0:
            return self._build_char(node, tree.node())
        elif len(tree) == 1:
            return self._build(node, tree[0])
        elif tree[0] == _OPAREN and tree[2] == _CPAREN:
            return self._build(node, tree[1])
        elif tree[1] == _STAR: return self._build_star(node, tree[0])
        elif tree[1] == _PLUS: return self._build_plus(node, tree[0])
        elif tree[1] == _QMK:  return self._build_qmk(node, tree[0])
        else:
            node = self._build(node, tree[0])
            return self._build(node, tree[1])
        
    def _build_char(self, node, char):
        new = self._new_state()
        self.insert_transition(node, char, new)
        return new
        
    def _build_qmk(self, node, tree):
        node1 = self._new_state()
        node2 = self._build(node1, tree)
        node3 = self._new_state()
        self.insert_transition(node, epsilon, node1)
        self.insert_transition(node, epsilon, node3)
        self.insert_transition(node2, epsilon, node3)
        return node3

    def _build_plus(self, node, tree):
        node1 = self._build(node, tree[0])
        self.insert_transition(node1, epsilon, node)
        return node1

    def _build_star(self, node, tree):
        node1 = self._new_state()
        node2 = self._build(node1, tree)
        node3 = self._new_state()
        self.insert_transition(node, epsilon, node1)
        self.insert_transition(node, epsilon, node3)
        self.insert_transition(node2, epsilon, node1)
        self.insert_transition(node2, epsilon, node3)
        return node3

    def insert_transition(self, s1, label, s2):
        if self._table.has_key((s1,label)):
            self._table[(s1,label)].insert(s2)
        else:
            self._table[(s1,label)] = Set(s2)

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
    # replace with the ASU algorithm
    def minimize(self):
        while self.epsilon_transitions() != []:
            for (s1, label1, s2) in self.epsilon_transitions():
                if self._finals.intersection(s2):
                    self._finals.insert(s1)
                for state in s2.elements():
                    for (s3, label2, s4) in self.outgoing_transitions(state):
                        self.insert_transition(s1, label2, s4)
                self.delete_transition(s1, label1, s2)
    
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
    re = 'a(b*)c'
    print 'Regular Expression:', re
    fsa = FSA(re)
    fsa.pp()
#    fsa.generate(10)

if __name__ == '__main__': demo()
