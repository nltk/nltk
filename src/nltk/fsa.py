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

epsilon = 0

# TODO - check that parse was complete, and report error otherwise
# TODO - change parser to limit scope of unary operators
# to the most recent symbol
# TODO - code up minimization algorithm from ASU

class FSA:
    def __init__(self, sigma):
        self._num = 0
        self._table = {}
        self._finals = Set(0)
        self._sigma = sigma
        
    def sigma(self):
        return self._sigma

    def new_state(self):
        self._num += 1
        return self._num

    def start(self):
        return 0

    def finals(self):
        return self._finals.elements()

    def add_final(self, state):
        self._finals.insert(state)

    def set_final(self, states):
        self._finals = states

    def finals_intersect(self, list):
        return [state for state in list
                if state in self.finals()]

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

    def next(self, state, label):
        if self._table.has_key((state, label)):
            return self._table[(state, label)]
        else:
            return []

    def move(self, states, label):
        next = []
        for state in states:
            next.extend(self.next(state, label))
        return next

    def epsilon_transitions(self):
        return [(s1,label,s2)
                for (s1, label, s2) in self.transitions()
                if label == epsilon]

    # From ASU page 119
    def epsilon_closure(self, states):
        stack = states
        closure = states
        while stack:
            s1 = stack.pop()
            for s2 in self.next(s1, epsilon):
                if s2 not in closure:
                    closure.append(s2)
                    stack.append(s2)
        return closure

    # return the corresponding DFA using subset construction (ASU p118)
    def dfa(self):
        dfa = FSA(self.sigma())
        dfa_initial = dfa.new_state()
        nfa_initial = self.epsilon_closure([self.start()])
        map = {}
        map[dfa_initial] = nfa_initial
        if nfa_initial in self.finals():
            dfa.add_final(dfa_initial)
        unmarked = [dfa_initial]
        marked = []
        while unmarked:
            dfa_state = unmarked.pop()
            marked.append(dfa_state)
            for label in self.sigma():
                nfa_next = self.epsilon_closure(self.move(map[dfa_state], label))
                if nfa_next not in map.keys():
                    dfa_next = dfa.new_state()
                    map[dfa_next] = nfa_next
                    if self.finals_intersect(nfa_next):
                        dfa.add_final(dfa_next)
                dfa.insert_transition(dfa_state, label, dfa_next)
        return dfa
        
    # CONSIDER CHANGING DATA STRUCTURE SO THAT THIS IS EFFICIENT
    def outgoing_transitions(self, state):
        return [(s1,label,s2)
                for (s1, label, s2) in self.transitions()
                if s1 == state]

    # STALE
    def optional(self, start = Set(0)):
#        self._finals = self._finals.intersection(start)
        self.insert_transitions(start, epsilon, self._finals)

    # STALE
    def kleene_plus(self, start = Set(0)):
        self.insert_transitions(self._finals, epsilon, start)

    # STALE
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

### FUNCTIONS TO BUILD FSA FROM REGEXP

# create NFA from regexp (Thompson's construction)
# assumes unique start and final states

_STAR = Tree('*')
_PLUS = Tree('+')
_QMK = Tree('?')
_OPAREN = Tree('(')
_CPAREN = Tree(')')

def re2nfa(fsa, re):
    re_list = _tokenizer.tokenize(re)
    tree = _parser.parse(re_list)
    state = re2nfa_build(fsa, fsa.start(), tree)
    fsa.set_final(Set(state))
#        fsa.minimize()

def re2nfa_build(fsa, node, tree):
    if len(tree) == 0:
        return re2nfa_char(fsa, node, tree.node())
    elif len(tree) == 1:
        return re2nfa_build(fsa, node, tree[0])
    elif tree[0] == _OPAREN and tree[2] == _CPAREN:
        return re2nfa_build(fsa, node, tree[1])
    elif tree[1] == _STAR: return re2nfa_star(fsa, node, tree[0])
    elif tree[1] == _PLUS: return re2nfa_plus(fsa, node, tree[0])
    elif tree[1] == _QMK:  return re2nfa_qmk(fsa, node, tree[0])
    else:
        node = re2nfa_build(fsa, node, tree[0])
        return re2nfa_build(fsa, node, tree[1])

def re2nfa_char(fsa, node, char):
    new = fsa.new_state()
    fsa.insert_transition(node, char, new)
    return new

def re2nfa_qmk(fsa, node, tree):
    node1 = fsa.new_state()
    node2 = re2nfa_build(fsa, node1, tree)
    node3 = fsa.new_state()
    fsa.insert_transition(node, epsilon, node1)
    fsa.insert_transition(node, epsilon, node3)
    fsa.insert_transition(node2, epsilon, node3)
    return node3

def re2nfa_plus(fsa, node, tree):
    node1 = re2nfa_build(fsa, node, tree[0])
    fsa.insert_transition(node1, epsilon, node)
    return node1

def re2nfa_star(fsa, node, tree):
    node1 = fsa.new_state()
    node2 = re2nfa_build(fsa, node1, tree)
    node3 = fsa.new_state()
    fsa.insert_transition(node, epsilon, node1)
    fsa.insert_transition(node, epsilon, node3)
    fsa.insert_transition(node2, epsilon, node1)
    fsa.insert_transition(node2, epsilon, node3)
    return node3


def demo():
    re = 'a(b*)c'
    print 'Regular Expression:', re
    fsa = FSA("abc")
    re2nfa(fsa, re)
    fsa.pp()
    dfa = fsa.dfa()
    dfa.pp()
#    fsa.generate(10)

if __name__ == '__main__': demo()
