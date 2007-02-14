from rules import KimmoArrowRule, KimmoFSARule
from pairs import KimmoPair, sort_subsets
from morphology import KimmoMorphology
from fsa import FSA
import yaml

def pairify(state):
    newstate = {}
    for label, targets in state.items():
        newstate[KimmoPair.make(label)] = targets
    return newstate

def mixfeatures(a, b):
    return '%s%s' % (a, b)

class TextTrace(object):
    def __init__(self, verbosity):
        self.verbosity = verbosity
    def reset(self): pass
    def step(self, pairs, curr, rules, prev_states, states,
    morphology_state, word):
        lexical = ''.join(p.input() for p in pairs)
        surface = ''.join(p.output() for p in pairs)
        indent = ' '*len(lexical)
        if self.verbosity > 2:
            print '%s%s<%s>' % (indent, lexical, curr.input())
            print '%s%s<%s>' % (indent, surface, curr.output())
            for rule, state1, state2 in zip(rules, prev_states, states):
                print '%s%s: %s => %s' % (indent, rule.name(), state1, state2)
            if morphology_state:
                print '%sMorphology: %r => %s' % (indent, word, morphology_state)
            print
        elif self.verbosity > 1:
            print '%s%s<%s>' % (indent, lexical, curr.input())
            print '%s%s<%s>' % (indent, surface, curr.output())
            z = zip(prev_states, states)
            if morphology_state:
                z.append((word, morphology_state))
            print indent + (" ".join('%s>%s' % (old, new) for old, new in z))
            blocked = []
            for rule, state in zip(rules, states):
                if str(state).lower() in ['0', 'reject']:
                    blocked.append(rule.name())
            if blocked:
                print '%s[blocked by %s]' % (indent, ", ".join(blocked))
            print
        else:
            print '%s%s<%s> | %s<%s>' % (indent, lexical, curr.input(),
              surface, curr.output()),
            if morphology_state:
                print '\t%r => %s' % (word, morphology_state),
            blocked = []
            for rule, state in zip(rules, states):
                if str(state).lower() in ['0', 'reject']:
                    blocked.append(rule.name())
            if blocked:
                print ' [blocked by %s]' % (", ".join(blocked)),
            print

    def succeed(self, pairs):
        lexical = ''.join(p.input() for p in pairs)
        surface = ''.join(p.output() for p in pairs)
        indent = ' '*len(lexical)

        print '%s%s' % (indent, lexical)
        print '%s%s' % (indent, surface)
        print '%sSUCCESS: %s <=> %s' % (indent, lexical, surface)
        print
        print

class KimmoRuleSet(yaml.YAMLObject):
    yaml_tag = '!KimmoRuleSet'
    def __init__(self, subsets, defaults, rules, morphology=None, null='0', boundary='#'):
        self.debug = False
        self._rules = list(rules)
        self._pair_alphabet = set()
        self._subsets = {}
        self._null = null
        self._boundary = boundary
        self._subsets = subsets
        self._morphology = morphology
        
        for pair in defaults:
            # defaults shouldn't contain subsets
            if self.is_subset(pair.input()) or self.is_subset(pair.output()):
                raise ValueError('default ' + str(pair) + ' contains subset')
            self._pair_alphabet.add( pair )
        
        for r in self.rules():
            for kp in r.pairs():
                if (not (self.is_subset(kp.input()) or self.is_subset(kp.output()))):
                    self._pair_alphabet.add( kp )

    def rules(self): return self._rules
    def subsets(self): return self._subsets
    def is_subset(self, key):
        return key[0] == '~' or key in self.subsets()
    def null(self): return self._null
    def morphology(self): return self._morphology
    
    def pairtext(self, char):
        if char == self._null: return ''
        else: return char
    
    def _generate(self, pairs, state_list, morphology_state=None, word='',
    lexical=None, surface=None, features='', log=None):
        if morphology_state:
            morph = self._morphology
            morphed = False
            for state, feat in morph.next_states(morphology_state, word):
                if feat is not None:
                    newfeat = mixfeatures(features, feat)
                else: newfeat = features
                for result in self._generate(pairs, state_list,
                state, '', lexical, surface, newfeat, log):
                    yield result
                    morphed = True
            if morphed: return
            lexical_chars = list(morph.valid_lexical(morphology_state,
            word, self._pair_alphabet)) + list(self._null)
        else: lexical_chars = None
        
        if lexical == '' or surface == '':
            if morphology_state is None or morphology_state.lower() == 'end':
                if log:
                    log.succeed(pairs)
                yield pairs, features
                return
            
        next_pairs = [p for p in self._pair_alphabet if
          (lexical is None or lexical.startswith(self.pairtext(p.input()))) and
          (surface is None or surface.startswith(self.pairtext(p.output())))]
        for pair in next_pairs:
            if pair.input() == self._null and pair.output() == self._null:
                continue
            if lexical_chars is not None and pair.input() not in lexical_chars:
                continue
            new_states = state_list[:]
            for r in range(len(self._rules)):
                rule = self._rules[r]
                state = state_list[r]
                next_state = self.advance_rule(rule, state, pair)
                new_states[r] = next_state
            
            newword = word + self.pairtext(pair.input())

            if log:
                log.step(pairs, pair, self._rules, state_list, new_states,
                morphology_state, newword)
            fail = False
            for new_state in new_states:
                if new_state is None or str(new_state) == '0'\
		or str(new_state) == 'reject':
                    fail = True
                    break
            if fail: continue
            newlex, newsurf = lexical, surface
            if lexical: newlex = lexical[len(self.pairtext(pair.input())):]
            if surface: newsurf = surface[len(self.pairtext(pair.output())):]
            for result in self._generate(pairs+[pair], new_states,
            morphology_state, newword, newlex, newsurf, features, log):
                yield result
        
    def generate(self, lexical, log=None):
        if log: log.reset()
        if not lexical.endswith(self._boundary):
            lexical += self._boundary
        got = self._generate([], [rule.fsa().start() for rule in
        self._rules], lexical=lexical, log=log)
        results = []
        for (pairs, features) in got:
            results.append(''.join(self.pairtext(pair.output()).strip(self._boundary) for pair in pairs))
        return results
    
    def recognize(self, surface, log=None):
        if log: log.reset()
        if not surface.endswith(self._boundary):
            surface += self._boundary
        got = self._generate([], [rule.fsa().start() for rule in
        self._rules], morphology_state='Begin', surface=surface, log=log)
        results = []
        for (pairs, features) in got:
            results.append((''.join(self.pairtext(pair.input()).strip(self._boundary) for pair in pairs), features))
        return results

    def advance_rule(self, rule, state, pair):
        trans = rule.fsa()._transitions[state]
        expected_pairs = sort_subsets(trans.keys(), self._subsets)
        for comppair in expected_pairs:
            if comppair.includes(pair, self._subsets):
                return rule.fsa().nextState(state, comppair)
        return None
    
    def test_case(self, input, outputs, arrow, method):
        outputs.sort()
        if arrow == '<=':
            print '%s %s %s' % (', '.join(outputs), arrow, input)
        else:
            print '%s %s %s' % (input, arrow, ', '.join(outputs))
        value = method(input)
        if len(value) and isinstance(value[0], tuple):
            results = [v[0] for v in value]
        else: results = value
        results.sort()
        if outputs != results:
            print '  Failed: got %s' % (', '.join(results) or 'no results')
            return False
        else: return True
    
    def batch_test(self, filename):
        f = open(filename)
        try:
            for line in f:
                line = line[:line.find(';')].strip()
                if not line: continue
                arrow = None
                for arrow_to_try in ['<=>', '=>', '<=']:
                    if line.find(arrow_to_try) >= 0:
                        lexicals, surfaces = line.split(arrow_to_try)
                        arrow = arrow_to_try
                        break
                if arrow is None:
                    raise ValueError, "Can't find arrow in line: %s" % line
                lexicals = lexicals.strip().split(', ')
                surfaces = surfaces.strip().split(', ')
                if lexicals == ['']: lexicals = []
                if surfaces == ['']: surfaces = []
                if arrow == '=>' or arrow == '<=>':
                    outputs = surfaces
                    for input in lexicals:
                        self.test_case(input, outputs, '=>', self.generate)
                if arrow == '<=' or arrow == '<=>':
                    outputs = lexicals
                    for input in surfaces:
                        self.test_case(input, outputs, '<=', self.recognize)
        finally:
            f.close()
    
    @classmethod
    def from_yaml(cls, loader, node):
        map = loader.construct_mapping(node)
        return cls.from_yaml_dict(map)
    
    @classmethod
    def load(cls, filename):
        f = open(filename)
        result = cls.from_yaml_dict(yaml.load(f))
        f.close()
        return result
    
    @classmethod
    def from_yaml_dict(cls, map):
        lexicon = map.get('lexicon')
        if lexicon:
            lexicon = KimmoMorphology.load(lexicon)
        subsets = map['subsets']
        for key, value in subsets.items():
            if isinstance(value, basestring):
                subsets[key] = value.split()
        defaults = map['defaults']
        if isinstance(defaults, basestring):
            defaults = defaults.split()
        defaults = [KimmoPair.make(text) for text in defaults]
        ruledic = map['rules']
        rules = []
        for (name, rule) in ruledic.items():
            if isinstance(rule, dict):
                rules.append(KimmoFSARule.from_dfa_dict(name, rule, subsets))
            elif isinstance(rule, basestring):
                if rule.strip().startswith('FSA'):
                    rules.append(KimmoFSARule.parse_table(name, rule, subsets))
                else: rules.append(KimmoArrowRule(name, rule, subsets))
            else:
                raise ValueError, "Can't recognize the data structure in '%s' as a rule: %s" % (name, rule)
        return cls(subsets, defaults, rules, lexicon)
    
    def gui(self, startTk=True):
        import draw
        return draw.KimmoGUI(self, startTk)
    draw_graphs = gui

def load(filename):
    return KimmoRuleSet.load(filename)

def guidemo():
    rules = load('spanish.yaml')
    rules.gui()

def batchdemo():
    rules = load('spanish.yaml')
    rules.batch_test('spanish.test')

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        filename = sys.argv[1]
        k = load(filename)
        k.gui()

