from nltk_lite.parse import cfg

def generate(self, start=None):
    if not start:
        start = self._start
    return self._generate_all([start])[0]

def _generate_all(self, items):
    frags = []
    if len(items) == 1:
        if isinstance(items[0], Nonterminal):
            for prod in self.productions(lhs=items[0]):
                frags.append(self._generate_all(prod.rhs()))
        else:
            frags.append(items[0])
    else:
        for frag1 in self._generate_all([items[0]]):
            for frag2 in self._generate_all(items[1:]):
                for frag in _multiply(frag1, frag2):
                    frags.append(frag)
    return frags
            
def _multiply(frag1, frag2):
    frags = []
    if len(frag1) == 1:
        frag1 = [frag1]
    if len(frag2) == 1:
        frag2 = [frag2]
    for f1 in frag1:
        for f2 in frag2:
            frags.append(f1+f2)
    return frags

grammar = cfg.parse_grammar("""
  S -> NP VP
  NP -> Det N
  VP -> V NP
  Det -> 'the'
  Det -> 'a'
  N -> 'man' | 'park' | 'dog' | 'telescope'
  V -> 'saw' | 'walked'
  P -> 'in' | 'with'
""")

for sent in generate(grammar):
    print sent
    
