from rules import KimmoArrowRule, KimmoFSARule
from pairs import KimmoPair
from morphology import KimmoMorphology
from nltk_lite.contrib.fsa import FSA
import yaml

def sort_subsets(pairs, subsets):
    def subset_size(pair):
        if pair.input() in subsets: size1 = len(subsets[pair.input()])
        else: size1 = 1
        if pair.output() in subsets: size2 = len(subsets[pair.output()])
        else: size2 = 1
        return (min(size1, size2), max(size1, size2))
        
    sort_order = [(subset_size(pair), pair) for pair in pairs]
    sort_order.sort()
    return [item[1] for item in sort_order]
        
def pairify(state):
    newstate = {}
    for label, targets in state.items():
        newstate[KimmoPair.make(label)] = targets
    return newstate

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
    def _generate(self, pairs, state_sets, morphology_state=None, word='',
    lexical=None, surface=None, features='', log=None):
        pos = len(pairs)
        if lexical == '' or surface == '':
            yield pairs, features
            return
        next_pairs = [p for p in self._pair_alphabet if
          (lexical is None or p.input() == self._null or p.input() == lexical[0]) and
          (surface is None or p.output() == self._null or p.output() == surface[0])]
        if morphology_state:
            morph = self._morphology
            for state, feat in morph.next_states(morphology_state, word):
                if feat is not None:
                    newfeat = features + feat
                else: newfeat = features
                for result in self._generate(pairs, state_sets,
                state, '', lexical, surface, newfeat, log):
                    yield result
            lexical_chars = list(morph.valid_lexical(morphology_state,
            word))
        else: lexical_chars = None
                
        for pair in next_pairs:
            if lexical_chars is not None and pair.input() not in lexical_chars:
                continue
            for r in range(len(self._rules)):
                rule = self._rules[r]
                states = state_sets[r]
                next_states = self.advance_rule(rule, states, pair)
                if len(next_states) == 0:
                    continue
                new_sets = state_sets[:]
                new_sets[r] = next_states
                newlex, newsurf = lexical, surface
                newword = word
                if lexical and pair.input() != self._null:
                    newlex = lexical[1:]
                if surface and pair.output() != self._null:
                    newsurf = surface[1:]
                if pair.input() != self._null:
                    newword = word + pair.input()
                for result in self._generate(pairs+[pair], new_sets,
                morphology_state, newword, newlex, newsurf, features, log):
                    yield result
        
    def generate(self, lexical, log=None):
        got = self._generate([], [[rule.fsa().start()] for rule in
        self._rules], lexical=lexical, log=log)
        for (pairs, features) in got:
            yield ''.join(pair.output() if pair.output() != self._null else '' for pair
            in pairs)
    
    def recognize(self, surface, log=None):
        got = self._generate([], [[rule.fsa().start()] for rule in
        self._rules], morphology_state='Begin', surface=surface, log=log)
        for (pairs, features) in got:
            yield (''.join(pair.input() if pair.input() != self._null else '' for pair
            in pairs), features)

    def advance_rule(self, rule, states, pair):
        new_states = set()
        for state in states:
            trans = rule.fsa()._transitions[state]
            expected_pairs = sort_subsets(trans.keys(), self._subsets)
            for comppair in expected_pairs:
                if comppair.includes(pair, self._subsets):
                    new_states = new_states.union(trans[comppair])
                    break
        return list(new_states)
    
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
                states = rule['states']
                for (key, value) in states.items():
                    states[key] = pairify(value)
                rules.append(KimmoFSARule(name, FSA([], states,
                rule['start'])))
            elif isinstance(rule, basestring):
                rules.append(KimmoArrowRule(name, rule))
            else:
                raise ValueError, "Can't recognize the data structure in '%s' as a rule: %s" % (name, rule)
        return cls(subsets, defaults, rules, lexicon)
        
