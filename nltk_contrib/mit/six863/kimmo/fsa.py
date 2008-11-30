# Natural Language Toolkit: Finite State Automata
#
# Copyright (C) 2001-2006 NLTK Project
# Authors: Steven Bird <sb@ldc.upenn.edu>
#          Rob Speer <rspeer@mit.edu>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
A module for finite state automata. 
Operations are based on Aho, Sethi & Ullman (1986) Chapter 3.
"""

from nltk import tokenize, cfg, Tree
from nltk.parse import pchart
import yaml

epsilon = None

# some helper functions

# TODO - check that parse was complete, and report error otherwise

class FSA(yaml.YAMLObject):
    """
    A class for finite state automata. In general, it represents
    nondetermnistic finite state automata, with DFAs being a special case.
    """
    yaml_tag = '!FSA'
    def __init__(self, sigma='', transitions=None, start=0, finals=None):
        """Set up the FSA.

        @param sigma: the alphabet of the FSA
        @type sigma: sequence
        @param transitions: A dictionary representing the states and
        transitions in the FSA. The keys are state identifiers (any hashable
        object), and the values are dictionaries that map input symbols to the
        sets of states they lead to.
        @type transitions: dict
        @param start: The identifier of the start state
        @type start: hashable object
        @param finals: The identifiers of the accept states
        @type finals: sequence
        """
        self._transitions = transitions or {}
        self._start = start
        self._reverse = {}
        self._build_reverse_transitions()
        if finals: self._finals = set(finals)
        else: self._finals = set([0])
        self._sigma = set(sigma)
        assert isinstance(self._transitions, dict)
        self._next_state_num = 0

    def _build_reverse_transitions(self):
        for state in self._transitions:
            self._reverse.setdefault(state, {})
        for (state, symbol, target) in self.generate_transitions():
            self._add_transition(self._reverse, target, symbol, state)

    def generate_transitions(self):
        """
        A generator that yields each transition arrow in the FSA in the form
        (source, label, target).
        """
        for (state, map) in self._transitions.items():
            for (symbol, targets) in map.items():
                for target in targets:
                    yield (state, symbol, target)

    def labels(self, s1, s2):
        """
        A generator for all possible labels taking state s1 to state s2.
        """
        map = self._transitions.get(s1, {})
        for (symbol, targets) in map.items():
            if s2 in targets: yield symbol
    
    def sigma(self):
        "The alphabet of the FSA."
        return self._sigma
    alphabet = sigma

    def check_in_sigma(self, label):
        "Check whether a given object is in the alphabet."
        if label and label not in self._sigma:
            raise ValueError('Label "%s" not in alphabet: %s' % (label, str(self._sigma)))
    
    def __len__(self):
        "The number of states in the FSA."
        return len(self._transitions)
    
    def new_state(self):
        """
        Add a new state to the FSA.
        @returns: the ID of the new state (a sequentially-assigned number).
        @rtype: int
        """
        while self._next_state_num in self._transitions:
            self._next_state_num += 1
        self._transitions[self._next_state_num] = {}
        self._reverse[self._next_state_num] = {}
        return self._next_state_num

    def add_state(self, name):
        self._transitions[name] = {}
        self._reverse[name] = {}
        return name

    def start(self):
        """
        @returns: the ID of the FSA's start state.
        """
        return self._start

    def finals(self):
        """
        @returns: the IDs of all accept states.
        @rtype: set
        """
        # was a tuple before
        return self._finals
    
    def nonfinals(self):
        """
        @returns: the IDs of all accept states.
        @rtype: set
        """
        # was a tuple before
        return set(self.states()).difference(self._finals)

    def states(self):
        """
        @returns: a list of all states in the FSA.
        @rtype: list
        """
        return self._transitions.keys()
    
    def add_final(self, state):
        """
        Make a state into an accept state.
        """
        self._finals.add(state)

    def delete_final(self, state):
        """
        Make an accept state no longer be an accept state.
        """
        self._finals = self._finals.difference(set([state]))
#        del self._finals[state]

    def set_final(self, states):
        """
        Set the list of accept states.
        """
        self._finals = set(states)

    def set_start(self, start):
        """
        Set the start state of the FSA.
        """
        self._start = start
    
    def in_finals(self, list):
        """
        Check whether a sequence contains any final states.
        """
        return [state for state in list
                if state in self.finals()] != []

    def insert_safe(self, s1, label, s2):
        if s1 not in self.states():
            self.add_state(s1)
        if s2 not in self.states():
            self.add_state(s2)
        self.insert(s1, label, s2)

    def insert(self, s1, label, s2):
        """
        Add a new transition to the FSA.

        @param s1: the source of the transition
        @param label: the element of the alphabet that labels the transition
        @param s2: the destination of the transition
        """
        if s1 not in self.states():
            raise ValueError, "State %s does not exist in %s" % (s1,
            self.states())
        if s2 not in self.states():
            raise ValueError, "State %s does not exist in %s" % (s2,
            self.states())
        self._add_transition(self._transitions, s1, label, s2)
        self._add_transition(self._reverse, s2, label, s1)

    def _add_transition(self, map, s1, label, s2):
        mapping = map[s1]
        targets = mapping.setdefault(label, [])
        targets.append(s2)

    def _del_transition(self, map, s1, label, s2):
        mapping = map[s1]
        targets = mapping.setdefault(label, [])
        targets.remove(s2)
        if len(targets) == 0: del mapping[label]

    def delete(self, s1, label, s2):
        """
        Removes a transition from the FSA.

        @param s1: the source of the transition
        @param label: the element of the alphabet that labels the transition
        @param s2: the destination of the transition
        """
        if s1 not in self.states():
            raise ValueError, "State %s does not exist" % s1
        if s2 not in self.states():
            raise ValueError, "State %s does not exist" % s1
        self._del_transition(self._transitions, s1, label, s2)
        self._del_transition(self._reverse, s2, label, s1)

    def delete_state(self, state):
        "Removes a state and all its transitions from the FSA."
        if state not in self.states():
            raise ValueError, "State %s does not exist" % state
        for (s1, label, s2) in self.incident_transitions(state):
            self.delete(s1, label, s2)
        del self._transitions[state]
        del self._reverse[state]

    def incident_transitions(self, state):
        """
        @returns: a set of transitions into or out of a state.
        @rtype: set
        """
        result = set()
        forward = self._transitions[state]
        backward = self._reverse[state]
        for label, targets in forward.items():
            for target in targets:
                result.add((state, label, target))
        for label, targets in backward.items():
            for target in targets:
                result.add((target, label, state))
        return result

    def relabel_state(self, old, new):
        """
        Assigns a state a new identifier.
        """
        if old not in self.states():
            raise ValueError, "State %s does not exist" % old
        if new in self.states():
            raise ValueError, "State %s already exists" % new
        changes = []
        for (s1, symbol, s2) in self.generate_transitions():
            if s1 == old and s2 == old:
                changes.append((s1, symbol, s2, new, symbol, new))
            elif s1 == old:
                changes.append((s1, symbol, s2, new, symbol, s2))
            elif s2 == old:
                changes.append((s1, symbol, s2, s1, symbol, new))
        for (leftstate, symbol, rightstate, newleft, newsym, newright)\
        in changes:
            print leftstate, symbol, rightstate, newleft, newsym, newright
            self.delete(leftstate, symbol, rightstate)
            self.insert_safe(newleft, newsym, newright)
        del self._transitions[old]
        del self._reverse[old]

    def next(self, state, symbol):
        "The set of states reached from a certain state via a given symbol."
        return self.e_closure(self._transitions[state].get(symbol, set()))
    nextStates = next
    
    def move(self, states, symbol):
        "The set of states reached from a set of states via a given symbol."
        result = set()
        for state in states:
            result = result.union(self.next(state, symbol))
        return self.e_closure(result)

    def is_deterministic(self):
        """
        Return whether this is a DFA
        (every symbol leads from a state to at most one target state).
        """
        for map in self._transitions.values():
            for targets in map.values():
                if len(targets) > 1: return False
        return True
    
    def nextState(self, state, symbol):
        """
        The single state reached from a state via a given symbol.
        If there is more than one such state, raises a ValueError.
        If there is no such state, returns None.
        """
        next = self.next(state, symbol)
        if len(next) > 1:
            raise ValueError, "This FSA is nondeterministic -- use nextStates instead."
        elif len(next) == 1: return list(next)[0]
        else: return None

    def forward_traverse(self, state):
        "All states reachable by following transitions from a given state."
        result = set()
        for (symbol, targets) in self._transitions[state].items():
            result = result.union(targets)
        return result

    def reverse_traverse(self, state):
        """All states from which a given state is reachable by following
        transitions."""
        result = set()
        for (symbol, targets) in self._reverse[state].items():
            result = result.union(targets)
        return result
    
    def _forward_accessible(self, s1, visited):
        for s2 in self.forward_traverse(s1):
            if not s2 in visited:
                visited.add(s2)
                self._forward_accessible(s2, visited)
        return visited
                
    def _reverse_accessible(self, s1, visited):
        for s2 in self.reverse_traverse(s1):
            if not s2 in visited:
                visited.add(s2)
                self._reverse_accessible(s2, visited)
        return visited
        
    # delete inaccessible nodes and unused transitions
    def prune(self):
        """
        Modifies an FSA to remove inaccessible states and unused transitions.
        """
        acc = self.accessible()
        for state in self.states():
            if state not in acc:
               self.delete_state(state)
            else:
                self._clean_map(self._transitions[state])
                self._clean_map(self._reverse[state])

    def _clean_map(self, map):
        for (key, value) in map.items():
            if len(value) == 0:
                del map[key]

    # mark accessible nodes
    def accessible(self):
        acc = set()
        for final in self.finals():
            reverse_acc = set([final])
            self._reverse_accessible(final, reverse_acc)
            acc = acc.union(reverse_acc)

        forward_acc = set([self.start()])
        self._forward_accessible(self.start(), forward_acc)

        acc = acc.intersection(forward_acc)
        return acc
    
    def e_closure(self, states):
        """
        Given a set of states, return the set of states reachable from
        those states by following epsilon transitions.

        @param states: the initial set of states
        @type states: sequence
        @returns: a superset of the given states, reachable by epsilon
        transitions
        @rtype: set
        """
        stack = list(states)
        closure = list(states)
        while stack:
            s1 = stack.pop()
            for s2 in self.next(s1, epsilon):
                if s2 not in closure:
                    closure.append(s2)
                    stack.append(s2)
        return set(closure)
    
    # return the corresponding DFA using subset construction (ASU p118)
    # NB representation of (a*) still isn't minimal; should have 1 state not 2
    def dfa(self):
        "Return a DFA that is equivalent to this FSA."
        dfa = FSA(self.sigma())
        dfa_initial = dfa.start()
        nfa_initial = tuple(self.e_closure((self.start(),)))
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
                nfa_next = tuple(self.e_closure(self.move(map[dfa_state],
                label)))
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
    
    def generate(self, maxlen, state=0, prefix=""):
        "Generate all accepting sequences of length at most maxlen."
        if maxlen > 0:
            if state in self._finals:
                print prefix
            for (s1, labels, s2) in self.outgoing_transitions(state):
                for label in labels():
                    self.generate(maxlen-1, s2, prefix+label)

    def pp(self):
        """
        Print a representation of this FSA (in human-readable YAML format).
        """
        print yaml.dump(self)
    
    @classmethod
    def from_yaml(cls, loader, node):
        map = loader.construct_mapping(node)
        result = cls(map.get('sigma', []), {}, map.get('finals', []))
        for (s1, map1) in map['transitions'].items():
            for (symbol, targets) in map1.items():
                for s2 in targets:
                    result.insert(s1, symbol, s2)
        return result
    
    @classmethod
    def to_yaml(cls, dumper, data):
        sigma = data.sigma()
        transitions = {}
        for (s1, symbol, s2) in data.generate_transitions():
            map1 = transitions.setdefault(s1, {})
            map2 = map1.setdefault(symbol, [])
            map2.append(s2)
        try: sigma = "".join(sigma)
        except: sigma = list(sigma)
        node = dumper.represent_mapping(cls.yaml_tag, dict(
            sigma = sigma,
            finals = list(data.finals()),
            start = data._start,
            transitions = transitions))
        return node

    def show_pygraph(self, title='FSA', outfile=None, labels=True, root=None):
        from pygraph import pygraph, tkgraphview
        graph = pygraph.Grapher('directed')

        for state in self.states():
            color = '#eee'
            if state in self.finals():
                shape = 'oval'
            else:
                shape = 'rect'
            if state == self.start():
                color = '#afa'
            term = ''
            if state == self.start(): term = 'start'
            elif state == 'End': term = 'end'
            if state in [0, '0', 'reject', 'Reject']: color='#e99'
            
            graph.addNode(state, state, color, shape, term)

        #for source, trans in self._transitions.items():
        for source, label, target in self.generate_transitions():
            if not labels: label = ''
            graph.addEdge(source, target, label, color='black', dup=False)
        
        if outfile is None: outfile = title
        
        return tkgraphview.tkGraphView(graph, title, outfile, root=root,
        startTk=(not root))
        
    def __str__(self):
        return yaml.dump(self)

### FUNCTIONS TO BUILD FSA FROM REGEXP

# the grammar of regular expressions
# (probabilities ensure that unary operators
# have stronger associativity than juxtaposition)

def grammar(terminals):
    (S, Expr, Star, Plus, Qmk, Paren) = [cfg.Nonterminal(s) for s in 'SE*+?(']
    rules = [cfg.WeightedProduction(Expr, [Star], prob=0.2),
             cfg.WeightedProduction(Expr, [Plus], prob=0.2),
             cfg.WeightedProduction(Expr, [Qmk], prob=0.2),
             cfg.WeightedProduction(Expr, [Paren], prob=0.2),
             cfg.WeightedProduction(S, [Expr], prob=0.5),
             cfg.WeightedProduction(S, [S, Expr], prob=0.5),
             cfg.WeightedProduction(Star, [Expr, '*'], prob=1),
             cfg.WeightedProduction(Plus, [Expr, '+'], prob=1),
             cfg.WeightedProduction(Qmk, [Expr, '?'], prob=1),
             cfg.WeightedProduction(Paren, ['(', S, ')'], prob=1)]

    prob_term = 0.2/len(terminals) # divide remaining pr. mass
    for terminal in terminals:
        rules.append(cfg.WeightedProduction(Expr, [terminal], prob=prob_term))

    return cfg.WeightedGrammar(S, rules)

_parser = pchart.InsideParse(grammar('abcde'))

# create NFA from regexp (Thompson's construction)
# assumes unique start and final states

def re2nfa(fsa, re):
    tokens = tokenize.regexp(re, pattern=r'.')
    tree = _parser.parse(tokens)
    if tree is None: raise ValueError('Bad Regexp')
    state = re2nfa_build(fsa, fsa.start(), tree)
    fsa.set_final([state])
#        fsa.minimize()

def re2nfa_build(fsa, node, tree):
    # Terminals.
    if not isinstance(tree, Tree):
        return re2nfa_char(fsa, node, tree)
    elif len(tree) == 1:
        return re2nfa_build(fsa, node, tree[0])
    elif tree.node == '(':
        return re2nfa_build(fsa, node, tree[1])
    elif tree.node == '*': return re2nfa_star(fsa, node, tree[0])
    elif tree.node == '+': return re2nfa_plus(fsa, node, tree[0])
    elif tree.node == '?': return re2nfa_qmk(fsa, node, tree[0])
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

#################################################################
# Demonstration
#################################################################

def demo():
    """
    A demonstration showing how FSAs can be created and used.
    """
    # Define an alphabet.
    alphabet = "abcd"

    # Create a new FSA.
    fsa = FSA(alphabet)
    
    # Use a regular expression to initialize the FSA.
    re = 'abcd'
    print 'Regular Expression:', re
    re2nfa(fsa, re)
    print "NFA:"
    fsa.pp()

    # Convert the (nondeterministic) FSA to a deterministic FSA.
    dfa = fsa.dfa()
    print "DFA:"
    dfa.pp()

    # Prune the DFA
    dfa.prune()
    print "PRUNED DFA:"
    dfa.pp()

    # Use the FSA to generate all strings of length less than 3
    # (broken)
    #fsa.generate(3)

if __name__ == '__main__': demo()
