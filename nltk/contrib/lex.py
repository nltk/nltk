"""
Ewan Klein, March 2007

Experimental module to provide support for implementing English morphology by
feature unification.

Main challenge is to find way of encoding morphosyntactic rules. Current idea is to let a concatenated form such as 'walk + s' be encoded as a dictionary C{'stem': 'walk', 'affix': 's'}. This allows the morpho-phonological representation to undergo unification in the normal way.
"""

from nltk.featstruct import *
import re

class Phon(dict):
        """
        A Phon object is just a stem and an affix.
        """
        def __init__(self, stem=None, affix=None):
                dict.__init__(self)
                self['stem'] = stem
                self['affix'] = affix
                
        def __repr__(self):
                return "%s + %s" % (self['stem'] , self['affix'] )

"""
>>> print Phon('a', 'b')
         a + b
"""

def phon_representer(dumper, data):
        """
        Output 'phon' values in 'stem + affix' notation.
        """
        return dumper.represent_scalar(u'!phon', u'%s + %s' % \
                                       (data['stem'], data['affix']))

yaml.add_representer(Phon, phon_representer)

"""
>>> print yaml.dump({'phon': Phon('a', 'b')})
        {phon: !phon 'a + b'}
"""

def normalize(s):
        """
        Turn input into non-Unicode strings without spaces.
        Return a Variable if input is of the form '?name'.
        """
        s = str(s.strip())
        patt = re.compile(r'^\?\w+$')
        if patt.match(s):
                name = s[1:]
                return Variable(name)
        return s

def phon_constructor(loader, node):
        """
        Recognize 'stem + affix' as Phon objects in YAML.
        """     
        value = loader.construct_scalar(node)
        stem, affix = [normalize(s) for s in value.split('+')]
        return Phon(stem, affix)

yaml.add_constructor(u'!phon', phon_constructor)

#following causes YAML to barf for some reason:
#pattern = re.compile(r'^(\?)?\w+\s*\+\s*(\?)?\w+$')
#yaml.add_implicit_resolver(u'phon', pattern)

"""
We have to specify the input using the '!phon' constructor.

>>> print yaml.load('''
...        form: !phon 'walk + s'
...        ''')
{'form': 'walk + s'}

Unifying a stem and a phonological output:

>>> f1 = yaml.load('''
...      form: !phon ?x + s
...      stem: ?x
...      ''')

>>> f2 = yaml.load('''
...      stem: walk
...      ''')

>>> f3 = unify(f1, f2)
>>> print f3
{'form': walk + s, 'stem': 'walk'}

In the next example, we follow B&B in using 'sym' as the name of the semantic constant in the lexical entry. We might want to have a semantic constructor like Phon so that we could write things like '\\x. (?sem x)'. Or perhaps not.

>>> lex_walk = yaml.load('''
...      sym: 'walk'
...      stem: 'walk'
...      ''')

>>> thirdsg = yaml.load('''
...      sym: ?x
...      sem: ?x
...      stem: ?y
...      phon: !phon ?x + s
...      ''')


>>> walks = unify(lex_walk, thirdsg)
>>> print walks
{'sem': 'walk', 'phon': walk + s, 'sym': 'walk', 'stem': 'walk'}
"""

def test():
    "Run unit tests on unification."
    import doctest
    doctest.testmod()

if __name__ == "__main__":
    test()
