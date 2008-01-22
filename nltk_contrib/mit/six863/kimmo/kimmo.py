# pykimmo 3.0.0 -- a two-level morphology tool for nltk 1.7
# by Rob Speer (rspeer@mit.edu)
# based on code from Carl de Marcken, Beracah Yankama, and Rob Speer

from rules import KimmoArrowRule, KimmoFSARule
from pairs import KimmoPair, sort_subsets
from morphology import *
from fsa import FSA
import yaml

def _pairify(state):
    newstate = {}
    for label, targets in state.items():
        newstate[KimmoPair.make(label)] = targets
    return newstate


class KimmoRuleSet(yaml.YAMLObject):
    """
    An object that represents the morphological rules for a language.
    
    The KimmoRuleSet stores a list of rules which must all succeed when they
    process a given string. These rules can be used for generating a surface
    form from a lexical form, or recognizing a lexical form from a surface
    form.
    """
    yaml_tag = '!KimmoRuleSet'
    def __init__(self, subsets, defaults, rules, morphology=None, null='0', boundary='#'):
        """
        Creates a KimmoRuleSet. You may not want to do this directly, but use
        KimmoRuleSet.load to load one from a YAML file.

        A KimmoRuleSet takes these parameters:
        subsets: a dictionary mapping strings to lists of strings. The strings
          in the map become subsets representing all of the strings in the
          list.
        defaults: a list of KimmoPairs that can appear without being
          specifically mentioned by a rule.
        rules: a list of KimmoFSARules or KimmoArrowRules that define the
          two-level morphology rules.
        morphology: a KimmoMorphology object that defines a lexicon of word
          roots and affixes.
        null: the symbol representing the empty string in rules.
        boundary: the symbol that will always appear at the end of lexical and
          surface forms.
        """
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

    def rules(self):
        "The list of rules in this ruleset."
        return self._rules
    def subsets(self):
        "The dictionary defining subsets of characters of the language."
        return self._subsets
    def is_subset(self, key):
        "Is this string a subset representing other strings?"
        return key[0] == '~' or key in self.subsets()
    def null(self):
        "The null symbol for this ruleset."
        return self._null
    def morphology(self):
        """The morphological lexicon (as a KimmoMorphology). Could be None, if
        the ruleset is only used for generation.
        """
        return self._morphology
    
    def _pairtext(self, char):
        if char == self._null: return ''
        else: return char
    
    def _generate(self, pairs, state_list, morphology_state=None, word='',
    lexical=None, surface=None, features='', log=None):
        if morphology_state:
            morph = self._morphology
            morphed = False
            for state, feat in morph.next_states(morphology_state, word):
                if feat is not None:
                    newfeat = combine_features(features, feat)
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
                # check that all rules are in accepting states
                for r in range(len(self._rules)):
                    rule = self._rules[r]
                    state = state_list[r]
                    if state not in rule.fsa().finals():
                        return
                if log:
                    log.succeed(pairs)
                yield pairs, features
                return
            
        next_pairs = [p for p in self._pair_alphabet if
          (lexical is None or startswith(lexical, self._pairtext(p.input()))) and
          (surface is None or startswith(surface, self._pairtext(p.output())))]
        for pair in next_pairs:
            if pair.input() == self._null and pair.output() == self._null:
                continue
            if lexical_chars is not None and pair.input() not in lexical_chars:
                continue
            new_states = state_list[:]
            for r in range(len(self._rules)):
                rule = self._rules[r]
                state = state_list[r]
                next_state = self._advance_rule(rule, state, pair)
                new_states[r] = next_state
            
            newword = word + self._pairtext(pair.input())

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
            if lexical: newlex = lexical[len(self._pairtext(pair.input())):]
            if surface: newsurf = surface[len(self._pairtext(pair.output())):]
            for result in self._generate(pairs+[pair], new_states,
            morphology_state, newword, newlex, newsurf, features, log):
                yield result
        
    def generate(self, lexical, log=None):
        """
        Given a lexical form, return all possible surface forms that fit
        these rules.

        Optionally, a 'log' object such as TextTrace(1) can be provided; this
        object will display to the user all the steps of the Kimmo algorithm.
        """
        if log: log.reset()
        if not lexical.endswith(self._boundary):
            lexical += self._boundary
        got = self._generate([], [rule.fsa().start() for rule in
        self._rules], lexical=lexical, log=log)
        results = []
        for (pairs, features) in got:
            results.append(''.join(self._pairtext(pair.output()).strip(self._boundary) for pair in pairs))
        return results
    
    def recognize(self, surface, log=None):
        """
        Given a surface form, return all possible lexical forms that fit
        these rules. Because the components of a lexical form can include
        features such as the grammatical part of speech, each surface form
        is returned as a 2-tuple of (surface text, features).

        Optionally, a 'log' object such as TextTrace(1) can be provided; this
        object will display to the user all the steps of the Kimmo algorithm.
        """
        if log: log.reset()
        if not surface.endswith(self._boundary):
            surface += self._boundary
        got = self._generate([], [rule.fsa().start() for rule in
        self._rules], morphology_state='Begin', surface=surface, log=log)
        results = []
        for (pairs, features) in got:
            results.append((''.join(self._pairtext(pair.input()).strip(self._boundary) for pair in pairs), features))
        return results

    def _advance_rule(self, rule, state, pair):
        trans = rule.fsa()._transitions[state]
        expected_pairs = sort_subsets(trans.keys(), self._subsets)
        for comppair in expected_pairs:
            if comppair.includes(pair, self._subsets):
                return rule.fsa().nextState(state, comppair)
        return None
    
    def _test_case(self, input, outputs, arrow, method):
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
        """
        Test a rule set by reading lines from a file.

        Each line contains one or more lexical forms on the left, and one or
        more surface forms on the right (separated by commas if there are more
        than one). In between, there is an arrow (=>, <=, or <=>), indicating
        whether recognition, generation, or both should be tested. Comments
        can be marked with ;.

        Each form should produce the exact list of forms on the other side of
        the arrow; if one is missing, or an extra one is produced, the test
        will fail.

        Examples of test lines:
          cat+s => cats             ; test generation only
          conoc+o <=> conozco       ; test generation and recognition
           <= conoco                ; this string should fail to be recognized
        """
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
                        self._test_case(input, outputs, '=>', self.generate)
                if arrow == '<=' or arrow == '<=>':
                    outputs = lexicals
                    for input in surfaces:
                        self._test_case(input, outputs, '<=', self.recognize)
        finally:
            f.close()
    
    @classmethod
    def from_yaml(cls, loader, node):
        """
        Loads a KimmoRuleSet from a parsed YAML node.
        """
        map = loader.construct_mapping(node)
        return cls.from_yaml_dict(map)
    
    @classmethod
    def load(cls, filename):
        """
        Loads a KimmoRuleSet from a YAML file.
        
        The YAML file should contain a dictionary, with the following keys:
          lexicon: the filename of the lexicon to load.
          subsets: a dictionary mapping subset characters to space-separated
            lists of symbols. One of these should usually be '@', mapping
            to the entire alphabet.
          defaults: a space-separated list of KimmoPairs that should be allowed
            without a rule explicitly mentioning them.
          null: the symbol that will be used to represent 'null' (usually '0').
          boundary: the symbol that represents the end of the word
            (usually '#').
          rules: a dictionary mapping rule names to YAML representations of
            those rules.
          
        A rule can take these forms:
        * a dictionary of states, where each state is a dictionary mapping
          input pairs to following states. The start state is named 'start',
          the state named 'reject' instantly rejects, and state names can be
          prefixed with the word 'rejecting' so that they reject if the machine
          ends in that state.

          i-y-spelling: 
            start:
              'i:y': step1
              '@': start
            rejecting step1:
              'e:0': step2
              '@': reject
            rejecting step2:
              '+:0': step3
              '@': reject
            rejecting step3:
              'i:i': start
              '@': reject

          
        * a block of text with a DFA table in it, of the form used by
          PC-KIMMO. The text should begin with a | so that YAML keeps your
          line breaks, and the next line should be 'FSA'. State 0 instantly
          rejects, and states with a period instead of a colon reject if the
          machine ends in that state.
          Examples:

          i-y-spelling: |        # this is the same rule as above
            FSA
                i  e  +  i      @
                y  0  0  i  @
            1:  2  1  1  1      1
            2.  0  3  0  0      0
            3.  0  0  4  0      0
            4.  0  0  0  1      0

          epenthesis: |
            FSA
               c h s Csib y + # 0 @
               c h s Csib i 0 # e @
            1: 2 1 4 3    3 1 1 0 1
            2: 2 3 3 3    3 1 1 0 1
            3: 2 1 3 3    3 5 1 0 1
            4: 2 3 3 3    3 5 1 0 1
            5: 2 1 2 2    2 1 1 6 1
            6. 0 0 7 0    0 0 0 0 0
            7. 0 0 0 0    0 1 1 0 0
          
        """
        f = open(filename)
        result = cls._from_yaml_dict(yaml.load(f))
        f.close()
        return result
    
    @classmethod
    def _from_yaml_dict(cls, map):
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

class TextTrace(object):
    """
    Supply a TextTrace object as the 'log' argument to KimmoRuleSet.generate or
    KimmoRuleSet.recognize, and it will output the steps it goes through
    on a text terminal.
    """
    def __init__(self, verbosity=1):
        """
        Creates a TextTrace. The 'verbosity' argument ranges from 1 to 3, and
        specifies how much text will be output to the screen.
        """
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

def load(filename):
    """
    Loads a ruleset from a file in YAML format.
    
    See KimmoRuleSet.load for a more detailed description.
    """
    return KimmoRuleSet.load(filename)

def guidemo():
    "An example of loading rules into the GUI."
    rules = load('turkish.yaml')
    rules.gui()

def main():
    """If a YAML file is specified on the command line, load it as a
    KimmoRuleSet in the GUI."""
    import sys
    if len(sys.argv) > 1:
        filename = sys.argv[1]
        k = load(filename)
        k.gui()

if __name__ == '__main__': main()
