# Natural Language Toolkit: Finite State Automata
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
FSA class - deliberately simple so that the operations are easily understood.
Operations are based on Aho, Sethi & Ullman (1986) Chapter 3.
"""

from nltk.srparser import *
from nltk.token import CharTokenizer
from nltk.set import *

epsilon = None

# some helper functions

# inserting and deleting elements from sets stored in hashes
def _hashed_set_insert(hash, key, item):
    if hash.has_key(key):
        hash[key].insert(item)
    else:
        hash[key] = Set(item)
def _hashed_set_delete(hash, key, item):
    new = hash[key].difference(Set(item))
    if len(new) > 0:
        hash[key] = new
    else:
        del hash[key]

# TODO - check that parse was complete, and report error otherwise
# TODO - change parser to limit scope of unary operators
# to the most recent symbol

class FSA:
    # default fsa accepts the empty language
    def __init__(self, sigma):
        self._num = -1
        self._forward = {}  # forward transitions
        self._reverse = {}  # reverse transitions
        self._labels = {}
        self._finals = Set()
        self._sigma = sigma
        
    # the fsa accepts the empty string
    # only call this right after initializing
    def empty(self):
        self._num = 0
        self._finals = Set(0)
        
    def sigma(self):
        return self._sigma

    def check_in_sigma(self, label):
        if label and label not in self._sigma:
            raise ValueError('Label not in alphabet')

    def new_state(self):
        self._num += 1
        return self._num

    def start(self):
        return 0

    def finals(self):
        return self._finals.elements()

    def states(self):
        return range(self._num+1)

    def add_final(self, state):
        self._finals.insert(state)

    def delete_final(self, state):
        self._finals = self._finals.difference(Set(state))
#        del self._finals[state]

    def set_final(self, states):
        self._finals = Set(*states)

    def in_finals(self, list):
        return [state for state in list
                if state in self.finals()] != []

    def insert(self, s1, label, s2):
        self.check_in_sigma(label)
        _hashed_set_insert(self._forward, s1, s2)
        _hashed_set_insert(self._reverse, s2, s1)
        _hashed_set_insert(self._labels, (s1,s2), label)
        
#        if self._table.has_key((s1,label)):
#            self._table[(s1,label)].insert(s2)
#        else:
#            self._table[(s1,label)] = Set(s2)

    def inserts(self, state_set, label, s2):
        for s1 in state_set.elements():
            self.insert(s1, label, s2)

    def delete(self, s1, label, s2):
        _hashed_set_delete(self._forward, s1, s2)
        _hashed_set_delete(self._reverse, s2, s1)
        _hashed_set_delete(self._labels, (s1,s2), label)

    def delete_all(self, s1, s2):
        _hashed_set_delete(self._forward, s1, s2)
        _hashed_set_delete(self._reverse, s2, s1)
        del self._labels[(s1,s2)]

    def delete_state(self, state):
        for (s1,label,s2) in self.incident_transitions(state):
            self.delete_all(s1, s2)
        self._relabel_state(self._num, state)
        self._num -= 1

    def _relabel_state(self, orig, new):
        for forward in self.forward_traverse(orig):
            _hashed_set_delete(self._forward, orig, forward)
            _hashed_set_insert(self._forward, new, forward)
            _hashed_set_delete(self._reverse, forward, orig)
            _hashed_set_insert(self._reverse, forward, new)
            self._labels[(new,forward)] = self._labels[(orig,forward)]
            del self._labels[(orig,forward)]
        for reverse in self.reverse_traverse(orig):
            _hashed_set_delete(self._reverse, orig, reverse)
            _hashed_set_insert(self._reverse, new, reverse)
            _hashed_set_delete(self._forward, reverse, orig)
            _hashed_set_insert(self._forward, reverse, new)
            self._labels[(reverse,new)] = self._labels[(reverse,orig)]
            del self._labels[(reverse,orig)]
        if orig in self.finals():
            self.delete_final(orig)
            self.add_final(new)

    def incident_transitions(self, state):
        return [(s1,label,s2)
                for (s1,label,s2) in self.transitions()
                if s1 == state or s2 == state]

    def transitions(self):
        return [(s1,label,s2)
                for ((s1,s2),label) in self._labels.items()]

    def forward_traverse(self, state):
        if self._forward.has_key(state):
            return tuple(self._forward[state].elements())
        else:
            return ()

    def reverse_traverse(self, state):
        if self._reverse.has_key(state):
            return tuple(self._reverse[state].elements())
        else:
            return ()

    def next(self, s1, label):
        states = []
        for s2 in self.forward_traverse(s1):
            if self._labels[(s1,s2)].contains(label):
                states.append(s2)
        return tuple(states)

#        if self._table.has_key((state, label)):
#            return tuple(self._table[(state, label)].elements())
#        else:
#            return ()

    def move(self, states, label):
        moves = []
        for state in states:
            moves.extend(self.next(state, label))
        return tuple(moves)

    def outgoing_transitions(self, state):
        transitions = []
        if self._forward.has_key(s1):
            s2 = self._forward[s1]
            label = self._labels((s1,s2))
            transitions.append((s1, labels, s2))
        return transitions
            
#        return [(s1,labels,s2)
#                for (s1, labels, s2) in self.transitions()
#                if s1 == state]

    # delete inaccessible nodes and unused transitions
    def prune(self):
        acc = self.accessible()
        for state in self.states():
           if state not in acc:
               self.delete_state(state)

    # mark accessible nodes
    def accessible(self):
        acc = Set()
        for final in self.finals():
            reverse_acc = Set(final)
            self.reverse_accessible(final, reverse_acc)
            acc = acc.union(reverse_acc)

        forward_acc = Set(self.start())
        self.forward_accessible(self.start(), forward_acc)

        acc = acc.intersection(forward_acc)
        return tuple(acc.elements())

    def forward_accessible(self, s1, visited):
        for s2 in self.forward_traverse(s1):
            if not s2 in visited:
                visited.insert(s2)
                self.forward_accessible(s2, visited)
    def reverse_accessible(self, s1, visited):
        for s2 in self.reverse_traverse(s1):
            if not s2 in visited:
                visited.insert(s2)
                self.reverse_accessible(s2, visited)

    # From ASU page 119
    def e_closure(self, states):
        stack = list(states)
        closure = list(states)
        while stack:
            s1 = stack.pop()
            for s2 in self.next(s1, epsilon):
                if s2 not in closure:
                    closure.append(s2)
                    stack.append(s2)
        return tuple(closure)

    # return the corresponding DFA using subset construction (ASU p118)
    # NB representation of (a*) still isn't minimal; should have 1 state not 2
    def dfa(self):
        dfa = FSA(self.sigma())
        dfa_initial = dfa.new_state()
        nfa_initial = self.e_closure((self.start(),))
        map = {}
        map[dfa_initial] = nfa_initial
        map[nfa_initial] = dfa_initial
        if nfa_initial in self.finals():
            dfa.add_final(dfa_initial)
        unmarked = [dfa_initial]
        marked = []
        while unmarked:
            dfa_state = unmarked.pop()
            marked.append(dfa_state)
            # is a final state accessible via epsilon transitions?
            if self.in_finals(self.e_closure(map[dfa_state])):
                dfa.add_final(dfa_state)
            for label in self.sigma():
                nfa_next = self.e_closure(self.move(map[dfa_state], label))
                if map.has_key(nfa_next):
                    dfa_next = map[nfa_next]
                else:
                    dfa_next = dfa.new_state()
                    map[dfa_next] = nfa_next
                    map[nfa_next] = dfa_next
                    if self.in_finals(nfa_next):
                        dfa.add_final(dfa_next)
                    unmarked.append(dfa_next)
                dfa.insert(dfa_state, label, dfa_next)
        return dfa
        
    # STALE
    def optional(self, start = Set(0)):
#        self._finals = self._finals.intersection(start)
        self.inserts(start, epsilon, self._finals)

    # STALE
    def kleene_plus(self, start = Set(0)):
        self.inserts(self._finals, epsilon, start)

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
#        for final in self._finals:
#            self.insert(final, epsilon, self._count)
#        self._table.extend(fsa._table)

    # generate all strings in the language up to length maxlen
    def generate(self, maxlen, state=0, prefix=""):
        if maxlen > 0:
            if self._finals.contains(state):
                print prefix
            for (s1, labels, s2) in self.outgoing_transitions(state):
                for label in labels():
                    self.generate(maxlen-1, s2, prefix+label)

    def pp(self):
        t = self.transitions()
        t.sort()
        for (s1, label, s2) in t:
            print s1, ':', label, '->', s2
        print "Final:", self._finals

### FUNCTIONS TO BUILD FSA FROM REGEXP

# create NFA from regexp (Thompson's construction)
# assumes unique start and final states

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

def re2nfa(fsa, re):
    re_list = _tokenizer.tokenize(re)
    tree = _parser.parse(re_list)
    state = re2nfa_build(fsa, fsa.start(), tree)
    fsa.set_final([state])
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
    fsa.insert(node, char, new)
    return new

def re2nfa_qmk(fsa, node, tree):
    node1 = fsa.new_state()
    node2 = re2nfa_build(fsa, node1, tree)
    node3 = fsa.new_state()
    fsa.insert(node, epsilon, node1)
    fsa.insert(node, epsilon, node3)
    fsa.insert(node2, epsilon, node3)
    return node3

def re2nfa_plus(fsa, node, tree):
    node1 = re2nfa_build(fsa, node, tree[0])
    fsa.insert(node1, epsilon, node)
    return node1

def re2nfa_star(fsa, node, tree):
    node1 = fsa.new_state()
    node2 = re2nfa_build(fsa, node1, tree)
    node3 = fsa.new_state()
    fsa.insert(node, epsilon, node1)
    fsa.insert(node, epsilon, node3)
    fsa.insert(node2, epsilon, node1)
    fsa.insert(node2, epsilon, node3)
    return node3

def demo():
    alphabet = "ab"
    re = 'ab*'
    print 'Regular Expression:', re
    fsa = FSA(alphabet)
    fsa.empty()
    re2nfa(fsa, re)
    print "NFA:"
    fsa.pp()
    dfa = fsa.dfa()
    print "DFA:"
    dfa.pp()
    dfa.prune()
    print "PRUNED DFA:"
    dfa.pp()
#    fsa.generate(10)

if __name__ == '__main__': demo()
