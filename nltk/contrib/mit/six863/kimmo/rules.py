from nltk.parse import Tree
from fsa import FSA
from nltk import tokenize
from pairs import KimmoPair, sort_subsets
from copy import deepcopy
import re, yaml

_kimmo_terminal_regexp    = '[a-zA-Z0-9\+\'\-\#\@\$\%\!\^\`\}\{]+' # \}\{\<\>\,\.\~ # (^|\s)?\*(\s|$) !!! * is already covered in the re tokenizer
_kimmo_terminal_regexp_fsa    = '[^:\s]+' # for FSA, only invalid chars are whitespace and :
                                          # '[a-zA-Z0-9\+\'\-\#\@\$\%\!\^\`\}\{\<\>\,\.\~\*]+'
_kimmo_terminal_regexp_ext= '~?' + _kimmo_terminal_regexp

_kimmo_defaults           = _kimmo_terminal_regexp + '|\:'
_kimmo_defaults_fsa       = _kimmo_terminal_regexp_fsa + '|\:'
_kimmo_rule               = _kimmo_terminal_regexp_ext + '|[\:\(\)\[\]\?\&\*\_]|<=>|==>|<==|/<='
_arrows = ['==>', '<=>', '<==', '/<=']


_special_tokens = ['(', ')', '[', ']', '*', '&', '_', ':']
_special_tokens.extend(_arrows)
_non_list_initial_special_tokens = [')', ']', '*', '&', '_', ':']
_non_list_initial_special_tokens.extend(_arrows)
epsilon = None

class KimmoFSARule(object):
    """
    A rule for two-level morphology, expressed as a deterministic finite
    automaton.
    """
    def __init__(self, name, fsa, subsets):
        self._name = name
        self._fsa = fsa
        self._pairs = set()
        self._subsets = subsets
        for (start, pair, finish) in self._fsa.generate_transitions():
            self._pairs.add(pair)

    def fsa(self): return self._fsa
    def pairs(self): return self._pairs
    def name(self): return self._name

    def show_pygraph(self, root=None):
        return self.fsa().show_pygraph(self.name(), root=root)
    
    def complete_fsa(self, fsa, fail_state=None):
        fsa = deepcopy(fsa)
        if fail_state is None:
            fail_state = fsa.add_state('Fail')
            fsa.insert('Fail', KimmoPair.make('@'), 'Fail')
        sorted_pairs = sort_subsets(self._pairs, self._subsets)
        for state in fsa.states():
            trans = fsa._transitions[state]
            for pair in self._pairs:
                if pair not in trans:
                    for sp in sorted_pairs:
                        if sp in trans and sp.includes(pair, self._subsets):
                            trans[pair] = trans[sp]
                            break
                    trans[pair] = [fail_state]
                if trans[pair] == []: trans[pair] = [fail_state]
        fsa._build_reverse_transitions()
        return fsa

    @staticmethod
    def parse_table(name, table, subsets):
        lines = table.split('\n')
        if len(lines) < 4:
            raise ValueError,\
            "Rule %s has too few lines to be an FSA table." % name
        pairs1 = lines[1].strip().split()
        pairs2 = lines[2].strip().split()
        if len(pairs1) != len(pairs2):
            raise ValueError,\
            "Rule %s has pair definitions that don't line up." % name
        pairs = [KimmoPair(p1, p2) for p1, p2 in zip(pairs1, pairs2)]
        finals = []
        fsa = FSA()
        for line in lines[3:]:
            line = line.strip()
            if not line: continue
            groups = re.match(r'(\w+)(\.|:)\s*(.*)', line)
            if groups is None:
                raise ValueError,\
                "Can't parse this line of the state table for rule %s:\n%s"\
                % (name, line)
            state, char, morestates = groups.groups()
            if fsa.start() == 0: fsa.set_start(state)
            if char == ':': finals.append(state)
            fsa.add_state(state)
            morestates = morestates.split()
            if len(morestates) != len(pairs):
                raise ValueError,\
                "Rule %s has a row of the wrong length:\n%s\ngot %d items, should be %d"\
                % (name, line, len(morestates), len(pairs))
            for pair, nextstate in zip(pairs, morestates):
                fsa.insert_safe(state, pair, nextstate)
        fsa.set_final(finals)
        return KimmoFSARule(name, fsa, subsets)
    
    @staticmethod 
    def from_dfa_dict(name, states, subsets):
        fsa = FSA()
        pairs = set([KimmoPair.make('@')])
        for (statename, trans) in states.items():
            for label in trans:
                if label != 'others':
                    pairs.add(KimmoPair.make(label))
        for (statename, trans) in states.items():
            parts = statename.split()
            source = parts[-1]
            if not parts[0].startswith('rej'):
                fsa.add_final(source)
            
            if fsa.start() == 0 and source in ['begin', 'Begin', '1', 1]:
                fsa.set_start(source)
            if source in ['start', 'Start']:
                fsa.set_start(source)
                
            used_pairs = set()
            for label in trans:
                if label != 'others':
                    used_pairs.add(KimmoPair.make(label))
            for label, target in trans.items():
                if label.lower() == 'others':
                    fsa.insert_safe(source, KimmoPair.make('@'), target)
                    for pair in pairs.difference(used_pairs):
                        fsa.insert_safe(source, pair, target)
                else:
                    fsa.insert_safe(source, KimmoPair.make(label), target)
        return KimmoFSARule(name, fsa, subsets)

class KimmoArrowRule(KimmoFSARule):
    def arrow(self): return self._arrow
    def lhpair(self): return self._lhpair

    def __init__(self, name, description, subsets):
        self._name = name
        self._description = description
        self._negated = False
        self._pairs = set()
        self._subsets = subsets
        desc = list(tokenize.regexp(description, _kimmo_rule))
        self._parse(desc)

    def __repr__(self):
        return '<KimmoArrowRule %s: %s>' % (self._name, self._description)

    def _parse(self, tokens):
        (end_pair, tree)  = self._parse_pair(tokens, 0)
        lhpair = self._pair_from_tree(tree)
        self._lhpair = lhpair
        self._pairs.add(lhpair)

        end_arrow         = self._parse_arrow(tokens, end_pair)
        (end_left, lfsa)  = self._parse_context(tokens, end_arrow, True)
        end_slot          = self._parse_slot(tokens, end_left)
        (end_right, rfsa) = self._parse_context(tokens, end_slot, False)
        if not(end_right == len(tokens)):
            raise ValueError('unidentified tokens')

        self._left_fsa  = lfsa
        self._right_fsa = rfsa
        self._merge_fsas()

    def _next_token(self, tokens, i, raise_error=False):
        if i >= len(tokens):
            if raise_error:
                raise ValueError('ran off end of input')
            else:
                return None
        return tokens[i]

    def _pair_from_tree(self, tree):
        if (tree.node != 'Pair'): raise RuntimeException('expected Pair, got ' + str(tree))
        if len(tree) == 1:
            return KimmoPair(tree[0], tree[0])
        else:
            return KimmoPair(tree[0], tree[2])

    def _parse_pair(self, tokens, i):
        # print 'parsing pair at ' + str(i)
        t1 = self._next_token(tokens, i, True)
        if t1 in _special_tokens: raise ValueError('expected identifier, not ' + t1)
        t2 = t1
        j = i + 1
        if self._next_token(tokens, j) == ':':
            t2 = self._next_token(tokens, j+1, True)
            if t2 in _special_tokens: raise ValueError('expected identifier, not ' + t2)
            j = j + 2
            tree = Tree('Pair', tokens[i:j])
        else:
            tree = Tree('Pair', [tokens[i]])
        #print str(self._pair_from_tree(tree)) + ' from ' + str(i) + ' to ' + str(j)
        return (j, tree)


    def _parse_arrow(self, tokens, i):
        self._arrow = self._next_token(tokens, i, True)
        if not(self.arrow() in _arrows):
            raise ValueError('expected arrow, not ' + self.arrow())
        #print 'arrow from ' + str(i) + ' to ' + str(i+1)
        return i + 1


    def _parse_slot(self, tokens, i):
        slot = self._next_token(tokens, i, True)
        if slot != '_':
            raise ValueError('expected _, not ' + slot)
        # print 'slot from ' + str(i) + ' to ' + str(i+1)
        return i + 1


    def _parse_context(self, tokens, i, reverse):
        (j, tree) = self._parse_list(tokens, i)
        if j == i: return (i, None)

        sigma = set()
        self._collect_alphabet(tree, sigma)
        fsa = FSA(sigma)
        final_state = self._build_fsa(fsa, fsa.start(), tree, reverse)
        fsa.set_final([final_state])
        #fsa.pp()
        dfa = fsa.dfa()
        #dfa.pp()
        dfa.prune()
        #dfa.pp()
        return (j, dfa)


    def _collect_alphabet(self, tree, sigma):
        if tree.node == 'Pair':
            pair = self._pair_from_tree(tree)
            sigma.add(pair)
            self._pairs.add(pair)
        else:
            for d in tree: self._collect_alphabet(d, sigma)


    def _parse_list(self, tokens, i, type='Cons'):
        # print 'parsing list at ' + str(i)
        t = self._next_token(tokens, i)
        if t == None or t in _non_list_initial_special_tokens:
            # print '  failing immediately '
            return (i, None)
        (j, s) = self._parse_singleton(tokens, i)
        (k, r) = self._parse_list(tokens, j, type)
        # print (k,r)
        if r == None:
            # print '  returning (%d, %s)' % (j, s)
            return (j, s)
        tree = Tree(type, [s, r])
        # print '  returning (%d, %s)' % (k, tree)
        return (k, tree)


    def _parse_singleton(self, tokens, i):
        # print 'parsing singleton at ' + str(i)
        t = self._next_token(tokens, i, True)
        j = i
        result = None
        if t == '(':
            (j, result) = self._parse_list(tokens, i + 1, 'Cons')
            if result == None: raise ValueError('missing contents of (...)')
            t = self._next_token(tokens, j, True)
            if t != ')': raise ValueError('missing final parenthesis, instead found ' + t)
            j = j + 1
        elif t == '[':
            (j, result) = self._parse_list(tokens, i + 1, 'Or')
            if result == None: raise ValueError('missing contents of [...]')
            t = self._next_token(tokens, j, True)
            if t != ']': raise ValueError('missing final bracket, instead found ' + t)
            j = j + 1
        elif t in _special_tokens:
            raise ValueError('expected identifier, found ' + t)
        else:
            (j, tree) = self._parse_pair(tokens, i)
            result = tree
        t = self._next_token(tokens, j)
        if t in ['*', '&', '?']:
            j = j + 1
            result = Tree(t, [result])
        return (j, result)


    def _build_fsa(self, fsa, entry_node, tree, reverse):
        if tree.node == 'Pair':
            return self._build_terminal(fsa, entry_node, self._pair_from_tree(tree))
        elif tree.node == 'Cons':
            return self._build_seq(fsa, entry_node, tree[0], tree[1], reverse)
        elif tree.node == 'Or':
            return self._build_or(fsa, entry_node, tree[0], tree[1], reverse)
        elif tree.node == '*':
            return self._build_star(fsa, entry_node, tree[0], reverse)
        elif tree.node == '&':
            return self._build_plus(fsa, entry_node, tree[0], reverse)
        elif tree.node == '?':
            return self._build_qmk(fsa, entry_node, tree[0], reverse)
        else:
            raise RuntimeError('unknown tree node'+tree.node)


    def _build_terminal(self, fsa, entry_node, terminal):
        new_exit_node = fsa.new_state()
        fsa.insert(entry_node, terminal, new_exit_node)
        #print '_build_terminal(%d,%s) -> %d' % (entry_node, terminal, new_exit_node)
        return new_exit_node


    def _build_plus(self, fsa, node, tree, reverse):
        node1 = self._build_fsa(fsa, node, tree[0], reverse)
        fsa.insert(node1, epsilon, node)
        return node1


    def _build_qmk(self, fsa, node, tree, reverse):
        node1 = fsa.new_state()
        node2 = self._build_fsa(fsa, node1, tree, reverse)
        node3 = fsa.new_state()
        fsa.insert(node, epsilon, node1)
        fsa.insert(node, epsilon, node3)
        fsa.insert(node2, epsilon, node3)
        return node3


    def _build_star(self, fsa, node, tree, reverse):
        node1 = fsa.new_state()
        node2 = self._build_fsa(fsa, node1, tree, reverse)
        node3 = fsa.new_state()
        fsa.insert(node, epsilon, node1)
        fsa.insert(node, epsilon, node3)
        fsa.insert(node2, epsilon, node1)
        fsa.insert(node2, epsilon, node3)
        return node3


    def _build_seq(self, fsa, node, tree0, tree1, reverse):
        (d0, d1) = (tree0, tree1)
        if reverse: (d0, d1) = (d1, d0)
        node1 = self._build_fsa(fsa, node, d0, reverse)
        node2 = self._build_fsa(fsa, node1, d1, reverse)
        # print '_build_seq(%d,%s,%s) -> %d,%d' % (node, tree0, tree1, node1, node2)
        return node2

    def _build_or(self, fsa, node, tree0, tree1, reverse):
        node0 = fsa.new_state()
        node1 = fsa.new_state()
        node2 = self._build_fsa(fsa, node0, tree0, reverse)
        node3 = self._build_fsa(fsa, node1, tree1, reverse)
        node4 = fsa.new_state()
        fsa.insert(node, epsilon, node0)
        fsa.insert(node, epsilon, node1)
        fsa.insert(node2, epsilon, node4)
        fsa.insert(node3, epsilon, node4)
        return node4
        
    def left_arrow(self):
        working = deepcopy(self._left_fsa)
        right = self._right_fsa.dfa()
        lstates = left.states()
        for state in lstates:
            working.relabel_state(state, 'L%s' % state)
        working.add_state('Trash')
        for state in working.finals():
            workng.insert_safe(source, KimmoPair)
        
def demo():
    rule = KimmoArrowRule("elision-e", "e:0 <== CN u _ +:@ VO", {'@':
    'aeiouhklmnpw', 'VO': 'aeiou', 'CN': 'hklmnpw'})
    print rule
    print rule._left_fsa
    print rule._right_fsa
    print
    print rule._fsa

if __name__ == '__main__':
    demo()

# vim:et:ts=4:sts=4:sw=4:
