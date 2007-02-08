from fsa import FSA
import yaml

class KimmoMorphology(object):
    def __init__(self, fsa):
        self._fsa = fsa
    def fsa(self): return self._fsa
    def valid_lexical(self, state, word):
        trans = self.fsa()._transitions[state]
        for label in trans.keys():
            if label is not None and label[0].startswith(word) and len(label[0]) > len(word):
                yield label[0][len(word)]
    def next_states(self, state, word):
        choices = self.fsa()._transitions[state]
        for (key, value) in choices.items():
            if key is None:
                if word == '':
                    for next in value: yield (next, None)
            else:
                if key[0] == word:
                    for next in value:
                        yield (next, key[1])
                    
    @staticmethod
    def load(filename):
        f = open(filename)
        result = KimmoMorphology.from_text(f.read())
        f.close()
        return result
    @staticmethod
    def from_text(text):
        fsa = FSA([], {}, 'Begin', ['End'])
        state = 'Begin'
        for line in text.split('\n'):
            line = line.strip()
            if not line: continue
            if line[-1] == ':':
                state = line[:-1]
            else:
                if line.split()[0].endswith(':'):
                    parts = line.split()
                    name = parts[0][:-1]
                    next_states = parts[1:]
                    for next in next_states:
                        fsa.insert_safe(name, None, next)
                elif len(line.split()) > 2:
                    # this is a lexicon entry
                    word, next, features = line.split(None, 2)
                    if word == "''":
                        word = ''
                    if features and features[0] in '\'"{' or features == 'None':
                        features = eval(features)
                    fsa.insert_safe(state, (word, features), next)
                elif len(line.split()) == 2:
                    word, next = line.split()
                    features = ''
                    if word == "''":
                        word = ''
                    fsa.insert_safe(state, (word, features), next)
                else:
                    print "Ignoring line in morphology: %r" % line
        return KimmoMorphology(fsa)

def demo():
    print KimmoMorphology.load('english.lex')

if __name__ == '__main__':
    demo()
