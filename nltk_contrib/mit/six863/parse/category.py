# Natural Language Toolkit: Categories
#
# Copyright (C) 2001-2007 NLTK Project
# Author: Contributed by Rob Speer (NLTK version)
#         Steven Bird <sb@csse.unimelb.edu.au> (NLTK-Lite Port)
#         Ewan Klein <ewan@inf.ed.ac.uk> (Hooks for semantics)
#         Peter Wang <wangp@csse.unimelb.edu.au> (Overhaul)
# URL: <http://nltk.sourceforge.net>
# For license information, see LICENSE.TXT
#
# $Id: category.py 4162 2007-03-01 00:46:05Z stevenbird $

from nltk.semantics import logic
from cfg import *
from kimmo import kimmo

from featurelite import *
from copy import deepcopy
import yaml
# import nltk.yamltags

def makevar(varname):
    """
    Given a variable representation such as C{?x}, construct a corresponding
    Variable object.
    """
    return Variable(varname[1:])

class Category(Nonterminal, FeatureI):
    """
    A C{Category} is a wrapper for feature dictionaries, intended for use in
    parsing. It can act as a C{Nonterminal}.

    A C{Category} acts like a dictionary, except in the following ways:

        - Categories can be "frozen" so that they can act as hash keys;
          before they are frozen, they are mutable.

        - In addition to being hashable, Categories have consistent str()
          representations.

        - Categories have one feature marked as the 'head', which prints
          differently than other features if it has a value. For example,
          in the C{repr()} representation of a Category, the head goes to the
          left, on the outside of the brackets. Subclasses of C{Category}
          may change the feature name that is designated as the head, which is
          _head by default.

    Categories can contain any kind of object as their values, and can be
    recursive and even re-entrant. Categories are not necessarily "categories
    all the way down"; they can contain plain dictionaries as their values, and
    converting inner dictionaries to categories would probably lead to messier
    code for no gain.

    Because Categories can contain any kind of object, they do not try to
    keep control over what their inner objects do. If you freeze a Category
    but mutate its inner objects, undefined behavior will occur.
    """
    
    headname = 'head'
    
    def __init__(self, features=None, **morefeatures):
        if features is None: features = {}
        self._features = unify(features, morefeatures)
        self._hash = None
        self._frozen = False
        self._memostr = None

    def __cmp__(self, other):
        return cmp(repr(self), repr(other))
    
    def __div__(self, other):
        """
        @return: A new Category based on this one, with its C{/} feature set to 
        C{other}.
        """
        return unify(self, {'/': other})

    def __eq__(self, other):
        """
        Compare Categories for equality. This relies on Python's built-in
        __eq__ for dictionaries, which is fairly thorough in checking for
        recursion and reentrance.

        @return: True if C{self} and C{other} assign the same value to
        every feature.  In particular, return true if
        C{self[M{p}]==other[M{p}]} for every feature path M{p} such
        that C{self[M{p}]} or C{other[M{p}]} is a base value (i.e.,
        not a nested Category).
        @rtype: C{bool}
        """
        if not other.__class__ == self.__class__: return False
        return self._features == other._features

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        if self._hash is not None: return self._hash
        return hash(str(self))
    
    def freeze(self):
        """
        Freezing a Category memoizes its hash value, to make comparisons on it
        faster. After freezing, the Category and all its values are immutable.

        @return: self
        """
        self._memostr = str(self)
        self._hash = hash(self)
        self._frozen = True
        return self

    def frozen(self):
        """
        Returns whether this Category is frozen (immutable).
        
        @rtype: C{bool}
        """
        return self._frozen
    
    def get(self, key):
        return self._features.get(key)

    def __getitem__(self, key):
        return self._features.get(key)
    
    def __setitem__(self, key, value):
        if self._frozen: raise "Cannot modify a frozen Category"
        self._features[key] = value

    def items(self):
        return self._features.items()

    def keys(self):
        return self._features.keys()

    def values(self):
        return self._features.values()

    def has_key(self, key):
        return self._features.has_key(key)
    
    def symbol(self):
        """
        @return: The node value corresponding to this C{Category}. 
        @rtype: C{Category}
        """
        return self

    def head(self):
        """
        @return: The head of this category (the value shown outside the
        brackets in its string representation). If there is no head, returns
        None.
        @rtype: C{str} or C{None}
        """
        return self.get(self.__class__.headname)
    
    def copy(self):
        """
        @return: A deep copy of C{self}.
        """
        # Create a reentrant deep copy by round-tripping it through YAML.
        return deepcopy(self)
    
    def feature_names(self):
        """
        @return: a list of all features that have values.
        """
        return self._features.keys()
    
    has_feature = has_key

    #################################################################
    ## Variables
    #################################################################
    
    def remove_unbound_vars(self):
        selfcopy = self.copy()
        Category._remove_unbound_vars(self)
        return selfcopy

    @staticmethod
    def _remove_unbound_vars(obj):
        for (key, value) in obj.items():
            if isinstance(value, Variable):
                del obj[key]
            elif isinstance(value, (Category, dict)):
                Category._remove_unbound_vars(value)

    #################################################################
    ## String Representations
    #################################################################

    def __repr__(self):
        """
        @return: A string representation of this feature structure.
        """
        return str(self)
    
    def __str__(self):
        """
        @return: A string representation of this feature structure.
        """
        if self._memostr is not None: return self._memostr
        return self.__class__._str(self, {}, {})
    
    @classmethod
    def _str(cls, obj, reentrances, reentrance_ids):
        segments = []

        keys = obj.keys()
        keys.sort()
        for fname in keys:
            if fname == cls.headname: continue
            fval = obj[fname]
            if isinstance(fval, bool):
                if fval: segments.append('+%s' % fname)
                else: segments.append('-%s' % fname)
            elif not isinstance(fval, dict):
                segments.append('%s=%r' % (fname, fval))
            else:
                fval_repr = cls._str(fval, reentrances, reentrance_ids)
                segments.append('%s=%s' % (fname, fval_repr))

        head = obj.get(cls.headname)
        if head is None: head = ''
        if head and not len(segments): return str(head)
        return '%s[%s]' % (head, ', '.join(segments))
    
    yaml_tag = '!parse.Category'
    
    @classmethod
    def to_yaml(cls, dumper, data):
        node = dumper.represent_mapping(cls.yaml_tag, data._features)
        return node

    @classmethod
    def from_yaml(cls, loader, node):
        features = loader.construct_mapping(node, deep=True)
        return cls(features)

    #################################################################
    ## Parsing
    #################################################################

    # Regular expressions for parsing.
    _PARSE_RE = {'name': re.compile(r'\s*([^\s\(\)"\'=,\[\]/\?]+)\s*'),
                 'ident': re.compile(r'\s*\((\d+)\)\s*'),
                 'reentrance': re.compile(r'\s*->\s*'),
                 'assign': re.compile(r'\s*=?\s*'),
                 'bracket': re.compile(r'\s*]\s*'),
                 'comma': re.compile(r'\s*,\s*'),
                 'none': re.compile(r'None(?=\s|\]|,)'),
                 'int': re.compile(r'-?\d+(?=\s|\]|,)'),
                 'var': re.compile(r'\?[a-zA-Z_][a-zA-Z0-9_]*'+'|'+
                                   r'\?<[a-zA-Z_][a-zA-Z0-9_]*'+
                                   r'(=[a-zA-Z_][a-zA-Z0-9_]*)*>'),
                 'symbol': re.compile(r'\w+'),
                 'stringmarker': re.compile("['\"\\\\]"),
    
                 'categorystart':re.compile(r'\s*([^\s\(\)"\'\-=,\[\]/\?]*)\s*\['),
                 'bool': re.compile(r'\s*([-\+])'),
                 'arrow': re.compile(r'\s*->\s*'),
                 'disjunct': re.compile(r'\s*\|\s*'),
                 'whitespace': re.compile(r'\s*'),
                 'semantics': re.compile(r'<([^>]+)>'), 
                 'application': re.compile(r'<(app)\((\?[a-z][a-z]*)\s*,\s*(\?[a-z][a-z]*)\)>'),
                 'slash': re.compile(r'\s*/\s*'),
                }
    
    @classmethod
    def parse(cls, s):
        parsed, position = cls._parse(s, 0)
        if position != len(s):
            raise ValueError('end of string', position)
        return cls(parsed)

    @classmethod
    def inner_parse(cls, s, position, reentrances={}):
        if reentrances is None: reentrances = {}
        parsed, position = cls._parse(s, position)
        return cls(parsed), position
    
    @classmethod
    def _parse(cls, s, position=0, reentrances=None):
        """
        Helper function that parses a Category.
        @param s: The string to parse.
        @param position: The position in the string to start parsing.
        @param reentrances: A dictionary from reentrance ids to values.
        @return: A tuple (val, pos) of the feature structure created
            by parsing and the position where the parsed feature
            structure ends.
        """
        # A set of useful regular expressions (precompiled)
        _PARSE_RE = cls._PARSE_RE

        features = {}
        
        # Find the head, if there is one.
        match = _PARSE_RE['name'].match(s, position)
        if match is not None:
            features[cls.headname] = match.group(1)
            position = match.end()
        else:
            match = _PARSE_RE['var'].match(s, position)
            if match is not None:
                features[cls.headname] = makevar(match.group(0))
                position = match.end()

        
        # If the name is followed by an open bracket, start looking for
        # features.
        if position < len(s) and s[position] == '[':
            position += 1
    
            # Build a list of the features defined by the structure.
            # Each feature has one of the three following forms:
            #     name = value
            #     +name
            #     -name
            while True:
                if not position < len(s):
                    raise ValueError('close bracket', position)
            
                # Use these variables to hold info about the feature:
                name = target = val = None
                
                # Check for a close bracket at the beginning
                match = _PARSE_RE['bracket'].match(s, position)
                if match is not None:
                    position = match.end()
                    break   
                    
                # Is this a shorthand boolean value?
                match = _PARSE_RE['bool'].match(s, position)
                if match is not None:
                    if match.group(1) == '+': val = True
                    else: val = False
                    position = match.end()
                
                # Find the next feature's name.
                match = _PARSE_RE['name'].match(s, position)
                if match is None: raise ValueError('feature name', position)
                name = match.group(1)
                position = match.end()
                
                # If it's not a shorthand boolean, it must be an assignment.
                if val is None:
                    match = _PARSE_RE['assign'].match(s, position)
                    if match is None: raise ValueError('equals sign', position)
                    position = match.end()
    
                    val, position = cls._parseval(s, position, reentrances)
                features[name] = val
                        
                # Check for a close bracket
                match = _PARSE_RE['bracket'].match(s, position)
                if match is not None:
                    position = match.end()
                    break   
                    
                # Otherwise, there should be a comma
                match = _PARSE_RE['comma'].match(s, position)
                if match is None: raise ValueError('comma', position)
                position = match.end()
            
        return features, position
    
    @classmethod
    def _parseval(cls, s, position, reentrances):
        """
        Helper function that parses a feature value.  Currently
        supports: None, bools, integers, variables, strings, nested feature
        structures.
        @param s: The string to parse.
        @param position: The position in the string to start parsing.
        @param reentrances: A dictionary from reentrance ids to values.
        @return: A tuple (val, pos) of the value created by parsing
            and the position where the parsed value ends.
        """
        
        # A set of useful regular expressions (precompiled)
        _PARSE_RE = cls._PARSE_RE
        
        # End of string (error)
        if position == len(s): raise ValueError('value', position)

        # Semantic value of the form <app(?x, ?y) >'; return an ApplicationExpression
        match = _PARSE_RE['application'].match(s, position)
        if match is not None:
            fun = ParserSubstitute(match.group(2)).next()
            arg = ParserSubstitute(match.group(3)).next()
            return ApplicationExpressionSubst(fun, arg), match.end()       

        # other semantic value enclosed by '< >'; return value given by the lambda expr parser
        match = _PARSE_RE['semantics'].match(s, position)
        if match is not None:
            return ParserSubstitute(match.group(1)).next(), match.end()
        
        # String value
        if s[position] in "'\"":
            start = position
            quotemark = s[position:position+1]
            position += 1
            while 1: 
                match = cls._PARSE_RE['stringmarker'].search(s, position)
                if not match: raise ValueError('close quote', position)
                position = match.end()
                if match.group() == '\\': position += 1
                elif match.group() == quotemark:
                    return s[start+1:position-1], position

        # Nested category
        if _PARSE_RE['categorystart'].match(s, position) is not None:
            return cls._parse(s, position, reentrances)

        # Variable
        match = _PARSE_RE['var'].match(s, position)
        if match is not None:
            return makevar(match.group()), match.end()

        # None
        match = _PARSE_RE['none'].match(s, position)
        if match is not None:
            return None, match.end()

        # Integer value
        match = _PARSE_RE['int'].match(s, position)
        if match is not None:
            return int(match.group()), match.end()

        # Alphanumeric symbol (must be checked after integer)
        match = _PARSE_RE['symbol'].match(s, position)
        if match is not None:
            return match.group(), match.end()

        # We don't know how to parse this value.
        raise ValueError('value', position)
    
    @classmethod
    def parse_rules(cls, s):
        """
        Parse a L{CFG} line involving C{Categories}. A line has this form:
        
        C{lhs -> rhs | rhs | ...}

        where C{lhs} is a Category, and each C{rhs} is a sequence of
        Categories.
        
        @returns: a list of C{Productions}, one for each C{rhs}.
        """
        _PARSE_RE = cls._PARSE_RE
        position = 0
        try:
            lhs, position = cls.inner_parse(s, position)
            lhs = cls(lhs)
        except ValueError, e:
            estr = ('Error parsing field structure\n\n\t' +
                    s + '\n\t' + ' '*e.args[1] + '^ ' +
                    'Expected %s\n' % e.args[0])
            raise ValueError, estr
        lhs.freeze()

        match = _PARSE_RE['arrow'].match(s, position)
        if match is None:
            raise ValueError('expected arrow', s, s[position:])
        else: position = match.end()
        rules = []
        while position < len(s):
            rhs = []
            while position < len(s) and _PARSE_RE['disjunct'].match(s, position) is None:
                try:
                    val, position = cls.inner_parse(s, position, {})
                    if isinstance(val, dict): val = cls(val)
                except ValueError, e:
                    estr = ('Error parsing field structure\n\n\t' +
                        s + '\n\t' + ' '*e.args[1] + '^ ' +
                        'Expected %s\n' % e.args[0])
                    raise ValueError, estr
                if isinstance(val, Category): val.freeze()
                rhs.append(val)
                position = _PARSE_RE['whitespace'].match(s, position).end()
            rules.append(Production(lhs, rhs))
            
            if position < len(s):
                match = _PARSE_RE['disjunct'].match(s, position)
                position = match.end()
        
        # Special case: if there's nothing after the arrow, it is one rule with
        # an empty RHS, instead of no rules.
        if len(rules) == 0: rules = [Production(lhs, ())]
        return rules

class GrammarCategory(Category):
    """
    A class of C{Category} for use in parsing.

    The name of the head feature in a C{GrammarCategory} is C{pos} (for "part
    of speech").
    
    In addition, GrammarCategories are displayed and parse differently, to be
    consistent with NLP teaching materials: the value of the C{/} feature can
    be written with a slash after the right bracket, so that the string
    representation looks like: C{head[...]/value}.

    Every GrammarCategory has a / feature implicitly present; if it is not
    explicitly written, it has the value False. This is so that "slashed"
    features cannot unify with "unslashed" ones.

    An example of a C{GrammarCategory} is C{VP[+fin]/NP}, for a verb phrase
    that is finite and has an omitted noun phrase inside it.
    """
    
    headname = 'pos'
    yaml_tag = '!parse.GrammarCategory'
    
    @classmethod
    def _str(cls, obj, reentrances, reentrance_ids):
        segments = []

        keys = obj.keys()
        keys.sort()
        for fname in keys:
            if fname == cls.headname: continue
            if isinstance(obj, GrammarCategory) and fname == '/': continue
            fval = obj[fname]
            if isinstance(fval, bool):
                if fval: segments.append('+%s' % fname)
                else: segments.append('-%s' % fname)
            elif not isinstance(fval, dict):
                segments.append('%s=%r' % (fname, fval))
            else:
                fval_repr = cls._str(fval, reentrances, reentrance_ids)
                segments.append('%s=%s' % (fname, fval_repr))

        if segments: features = '[%s]' % ', '.join(segments)
        else: features = ''
        head = obj.get(cls.headname)
        if head is None: head = ''
        slash = None
        if isinstance(obj, GrammarCategory): slash = obj.get('/')
        if not slash: slash = ''
        else:
            if isinstance(slash, dict):
                slash = '/%s' % cls._str(slash, reentrances, reentrance_ids)
            else:
                slash = '/%r' % slash

        
        return '%s%s%s' % (head, features, slash)
    
    @staticmethod
    def parse(s, position=0):
        return GrammarCategory.inner_parse(s, position)[0]
    
    @classmethod
    def inner_parse(cls, s, position, reentrances=None):
        if reentrances is None: reentrances = {}
        if s[position] in "'\"":
            start = position
            quotemark = s[position:position+1]
            position += 1
            while 1: 
                match = cls._PARSE_RE['stringmarker'].search(s, position)
                if not match: raise ValueError('close quote', position)
                position = match.end()
                if match.group() == '\\': position += 1
                elif match.group() == quotemark:
                    return s[start+1:position-1], position

        body, position = GrammarCategory._parse(s, position, reentrances)
        slash_match = Category._PARSE_RE['slash'].match(s, position)
        if slash_match is not None:
            position = slash_match.end()
            slash, position = GrammarCategory._parseval(s, position, reentrances)
            if isinstance(slash, basestring): slash = {'pos': slash}
            body['/'] = unify(body.get('/'), slash)
        elif not body.has_key('/'):
            body['/'] = False
        return cls(body), position
    
class SubstituteBindingsI:
    """
    An interface for classes that can perform substitutions for feature
    variables.
    """
    def substitute_bindings(self, bindings):
        """
        @return: The object that is obtained by replacing
        each variable bound by C{bindings} with its values.
        @rtype: (any)
        """
        raise NotImplementedError

class ParserSubstitute(logic.Parser):
    """
    A lambda calculus expression parser, extended to create application
    expressions which support the SubstituteBindingsI interface.
    """
    def make_ApplicationExpression(self, first, second):
        return ApplicationExpressionSubst(first, second)

class ApplicationExpressionSubst(logic.ApplicationExpression, SubstituteBindingsI):
    """
    A lambda application expression, extended to implement the
    SubstituteBindingsI interface.
    """
    def substitute_bindings(self, bindings):
        newval = self
        for semvar in self.variables():
            varstr = str(semvar)
            # discard Variables which are not FeatureVariables
            if varstr.startswith('?'): 
                var = makevar(varstr)
                if bindings.is_bound(var):
                    newval = newval.replace(semvar, bindings.lookup(var))
        return newval

############################################################################
# Read a grammar from a file
############################################################################

class GrammarFile(object):
    def __init__(self):
        self.grammatical_productions = []
        self.lexical_productions = []
        self.start = GrammarCategory(pos='Start')
        self.kimmo = None
        
    def grammar(self):
        return Grammar(self.start, self.grammatical_productions +\
        self.lexical_productions)
        
    def earley_grammar(self):
        return Grammar(self.start, self.grammatical_productions)
    
    def earley_lexicon(self):
        lexicon = {}
        for prod in self.lexical_productions:
            lexicon.setdefault(prod.rhs()[0].upper(), []).append(prod.lhs())
        def lookup(word):
            return lexicon.get(word.upper(), [])
        return lookup

    def kimmo_lexicon(self):
        def lookup(word):
            kimmo_results = self.kimmo.recognize(word.lower())
            return [GrammarCategory(k[1]) for k in kimmo_results]
        return lookup

    def earley_parser(self, trace=1):
        from featurechart import FeatureEarleyChartParse
        if self.kimmo is None: lexicon = self.earley_lexicon()
        else: lexicon = self.kimmo_lexicon()
        
        return FeatureEarleyChartParse(self.earley_grammar(),
                           lexicon, trace=trace)

    def apply_lines(self, lines):
        for line in lines:
            line = line.strip()
            if not len(line): continue
            if line[0] == '#': continue
            if line[0] == '%':
                parts = line[1:].split()
                directive = parts[0]
                args = " ".join(parts[1:])
                if directive == 'start':
                    self.start = GrammarCategory.parse(args).freeze()
                elif directive == 'include':
                    filename = args.strip('"')
                    self.apply_file(filename)
                elif directive == 'tagger_file':
                    import yaml, nltk.yamltags
                    filename = args.strip('"')
                    tagger = yaml.load(filename)
                    self.tagproc = chart_tagger(tagger)
                elif directive == 'kimmo':
                    filename = args.strip('"')
                    kimmorules = kimmo.load(filename)
                    self.kimmo = kimmorules
            else:
                rules = GrammarCategory.parse_rules(line)
                for rule in rules:
                    if len(rule.rhs()) == 1 and isinstance(rule.rhs()[0], str):
                        self.lexical_productions.append(rule)
                    else:
                        self.grammatical_productions.append(rule)

    def apply_file(self, filename):
        f = open(filename)
        lines = f.readlines()
        self.apply_lines(lines)
        f.close()
    
    @staticmethod
    def read_file(filename):
        result = GrammarFile()
        result.apply_file(filename)
        return result

yaml.add_representer(Category, Category.to_yaml)
yaml.add_representer(GrammarCategory, GrammarCategory.to_yaml)

def demo():
    print "Category(pos='n', agr=dict(number='pl', gender='f')):"
    print
    print Category(pos='n', agr=dict(number='pl', gender='f'))
    print repr(Category(pos='n', agr=dict(number='pl', gender='f')))
    print
    print "GrammarCategory.parse('NP/NP'):"
    print
    print GrammarCategory.parse('NP/NP')
    print repr(GrammarCategory.parse('NP/NP'))
    print
    print "GrammarCategory.parse('?x/?x'):"
    print
    print GrammarCategory.parse('?x/?x')
    print repr(GrammarCategory.parse('?x/?x'))
    print
    print "GrammarCategory.parse('VP[+fin, agr=?x, tense=past]/NP[+pl, agr=?x]'):"
    print
    print GrammarCategory.parse('VP[+fin, agr=?x, tense=past]/NP[+pl, agr=?x]')
    print repr(GrammarCategory.parse('VP[+fin, agr=?x, tense=past]/NP[+pl, agr=?x]'))
    print
    g = GrammarFile.read_file("speer.cfg")
    print g.grammar()
    
if __name__ == '__main__':
    demo()
    
