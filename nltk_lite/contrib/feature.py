# Contributed by Rob Speer

from nltk_lite.parse.featurestructure import *
from nltk_lite.parse import cfg
from nltk_lite.contrib import church
import string

import pdb

class Category(FeatureStructure, cfg.Nonterminal):
    """
    A C{Category} is a specialized feature structure, intended for use in
    parsing.  It can act as a C{Nonterminal}.

    A C{Category} differs from a C{FeatureStructure} in these ways:
        - Categories may not be re-entrant.
        
        - Categories use value-based equality, while FeatureStructures use
          identity-based equality.

        - Strings in Categories are compared case-insensitively.
          
        - Categories have one feature marked as the 'head', which prints
          differently than other features if it has a value. For example,
          in the C{repr()} representation of a Category, the head goes to the
          left, on the outside of the brackets. Subclasses of C{Category}
          may change the feature name that is designated as the head, which is
          _head by default.

        - Subclasses of C{Category} may contain a list of I{required features},
          which are names of features whose value is None if unspecified. A
          Category lacking a feature that is required in it will not unify with
          any Category that has that feature. If a required feature's value is
          C{None}, it is considered to be not present. (Mixing different
          subclasses of C{Category} is probably a bad idea.)
          
        - C{True} and C{False} are allowed as values. A feature named C{foo}
          with a value of C{True} is simply expressed as C{+foo}. Similarly, if
          it is C{False}, it is expressed as C{-foo}.
    """
    
    headname = '_head'
    requiredFeatures = []
    
    def __init__(self, **features):
        self._features = features
        self._required = self.__class__.requiredFeatures
        for name in self._required:
            if not self._features.has_key(name):
                self._features[name] = None
        items = self._features.items()
        items.sort()
        self._hash = None
        self._frozen = False
        self._memorepr = None

    def required_features(self):
        "@return: A list of the names of all required features."
        return self._required

    def __cmp__(self, other):
        return cmp(repr(self), repr(other))
    
    def __div__(self, other):
        """
        @return: A new Category based on this one, with its C{/} feature set to 
        C{other}.
        """
        temp = self.deepcopy()
        dict = temp._features
        dict['/'] = other
        return self.__class__(**dict)

    def __eq__(self, other):
        """
        @return: True if C{self} and C{other} assign the same value to
        to every feature.  In particular, return true if
        C{self[M{p}]==other[M{p}]} for every feature path M{p} such
        that C{self[M{p}]} or C{other[M{p}]} is a base value (i.e.,
        not a nested Category).
        @rtype: C{bool}
        """
        
        # Get the result of equal_values, and make it a real boolean while
        # we're at it.
        if not other.__class__ == self.__class__: return False
        if hash(self) != hash(other): return False
        return (self.equal_values(other) == True)

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        if self._hash is not None: return self._hash
        items = self._features.items()
        items.sort()
        return hash(tuple(items))
    
    def freeze(self):
        """
        Freezing a Category memoizes its hash value, to make comparisons on it
        faster. After freezing, the Category and all its values are immutable.

        @return: self
        """
        for val in self._features.values():
            if isinstance(val, Category) and not val.frozen():
                val.freeze()
        self._hash = hash(self)
        self._memorepr = self._repr({}, {})
        self._frozen = True
        return self

    def frozen(self):
        """
        Returns whether this Category is frozen (immutable).
        
        @rtype: C{bool}
        """
        return self._frozen
    
    def __setitem__(self, name, value):
        if self._frozen: raise "Cannot modify a frozen Category"
        self._features[name] = value
    
    def symbol(self):
        """
        @return: the one-line string representation of the Category.
        @rtype: C{str}

        If you want the symbol for the head of the category, use C{head()}.
        """
        return repr(self)

    def head(self):
        """
        @return: The head of this category (the value shown outside the
        brackets in its string representation). If there is no head, returns
        None.
        @rtype: C{str} or C{None}
        """
        return self._features.get(self.__class__.headname)
    
    def deepcopy(self, memo=None):
        """
        @return: A deep copy of C{self}.
        """
        newcopy = self.__class__()
        features = newcopy._features

        # Fill out the features.
        for (fname, fval) in self._features.items():
            if isinstance(fval, FeatureStructure):
                features[fname] = fval.deepcopy()
            else:
                features[fname] = fval

        return newcopy
    
    def reentrances(self):
        return []

    def feature_names(self):
        """
        @return: a list of all features that have values.
        """
        return filter(lambda x: not (x in self._required and self[x] is None),
        self._features.keys())
    
    def get_feature(self, *args):
        try:
            return self.__getitem__(*args)
        except IndexError:
            return StarValue()
    
    def has_feature(self, name):
        return (name in self.feature_names())

    def remove_unbound_vars(self):
        selfcopy = self.deepcopy()
        selfcopy._remove_unbound_vars()
        return selfcopy

    def _remove_unbound_vars(self):
        for (fname, fval) in self._features.items():
            if isinstance(fval, FeatureVariable):
                del self._features[fname]
            elif isinstance(fval, Category):
                fval._remove_unbound_vars()

                
    # EK: adapted from nltk.featurestructure
    # We need to deal with cases where the LHS of a rule
    # has a value which is an ApplicationExpression containing FeatureVariables
    def _apply_bindings(self, bindings, visited):
        # Visit each node only once:
        if visited.has_key(id(self)): return
        visited[id(self)] = 1
      
        for (fname, fval) in self._features.items():
            if isinstance(fval, FeatureVariable):
                if bindings.is_bound(fval):
                    self._features[fname] = bindings.lookup(fval)
            # fval is a church Expression of the form 'app(?x ?y)
            elif isinstance(fval, church.ApplicationExpression):
                newval = fval
                for semvar in fval.variables():
                    varstr = semvar.__str__()
                    # discard church Variables which are not FeatureVariables
                    if varstr.startswith('?'): 
                        var = FeatureVariable.parse(varstr)
                        if bindings.is_bound(var):
                            newval = newval.replace(semvar, bindings.lookup(var))
                self._features[fname] = newval                  
            elif isinstance(fval, FeatureStructure):
                fval._apply_bindings(bindings, visited)               
    
    # All this is unlikely to be necessary. All I've changed is to make
    # strings case-insensitive.
    def _destructively_unify(self, other, bindings, trace=False, depth=0):
        """
        Attempt to unify C{self} and C{other} by modifying them
        in-place.  If the unification succeeds, then C{self} will
        contain the unified value, and the value of C{other} is
        undefined.  If the unification fails, then a
        _UnificationFailureError is raised, and the values of C{self}
        and C{other} are undefined.
        """
        if trace:
            print '  '+'|   '*depth+'?', `self`, '==', `other`
        
        for (fname, otherval) in other._features.items():
            if trace:
                trace_otherval = otherval
                trace_selfval_defined = self._features.has_key(fname)
                trace_selfval = self._features.get(fname)
            if self._features.has_key(fname):
                selfval = self._features[fname]
                # If selfval or otherval is a bound variable, then
                # replace it by the variable's bound value.
                if isinstance(selfval, FeatureVariable):
                    selfval = bindings.lookup(selfval)
                    if trace:
                        print '  | Bound var:', bindings.lookup(selfval)
                if isinstance(otherval, FeatureVariable):
                    otherval = bindings.lookup(otherval)

                if trace:
                    print '  '+'|   '*(depth+1)
                    print '  '+'%s| Unify "%s" feature:' % ('|   '*(depth),fname)
                    
                # Case 1: unify 2 feature structures (recursive case)
                if (isinstance(selfval, FeatureStructure) and
                    isinstance(otherval, FeatureStructure)):
                    selfval._destructively_unify(otherval, bindings,
                                                 trace, depth+1)

                # Case 2: unify 2 variables
                elif (isinstance(selfval, FeatureVariable) and
                      isinstance(otherval, FeatureVariable)):
                    self._features[fname] = selfval.alias(otherval)
                
                # Case 3: unify a variable with a value
                elif isinstance(selfval, FeatureVariable):
                    bindings.bind(selfval, otherval)
                elif isinstance(otherval, FeatureVariable):
                    bindings.bind(otherval, selfval)

                # Case 4A: unify two strings.
                elif isinstance(selfval, str) and isinstance(otherval, str)\
                and selfval.upper() == otherval.upper(): pass
                    
                # Case 4: unify 2 non-equal values (failure case)
                elif selfval != otherval:
                    if trace: print '  '+'|   '*depth + 'X <-- FAIL'
                    raise FeatureStructure._UnificationFailureError()

                # Case 5: unify 2 equal values
                else: pass

                if trace and not isinstance(selfval, FeatureStructure):
                    # apply_forwards to get reentrancy links right:
                    if isinstance(trace_selfval, FeatureStructure):
                        trace_selfval._apply_forwards({})
                    if isinstance(trace_otherval, FeatureStructure):
                        trace_otherval._apply_forwards({})
                    print '  '+'%s|   ? %r == %r' % ('|   '*(depth), trace_selfval, trace_otherval)
                    print '  '+'%s|   > %r' % ('|   '*(depth),
                                            self._features[fname])
                    
            # Case 5: copy from other
            else:
                self._features[fname] = otherval

        if trace:
            print '  '+'|   '*depth+'|'
            print '  '+'|   '*depth+'>', `self`
            if len(bindings.bound_variables()) > 0:
                print '  '+'|   '*depth+'    '+`bindings`
    
    def __repr__(self):
        """
        @return: A string representation of this feature structure.
        """
        if self._memorepr is not None: return self._memorepr
        else: return self._repr({}, {})
        return self._memorepr
    
    def _repr(self, reentrances, reentrance_ids):
        segments = []

        items = self.feature_names()
        items.sort() # sorting note: keys are unique strings, so we'll
                     # never fall through to comparing values.
        for fname in items:
            if fname == self.__class__.headname: continue
            fval = self[fname]
            if isinstance(fval, bool):
                if fval: segments.append('+%s' % fname)
                else: segments.append('-%s' % fname)
            elif not isinstance(fval, Category):
                segments.append('%s=%r' % (fname, fval))
            else:
                fval_repr = fval._repr(reentrances, reentrance_ids)
                segments.append('%s=%s' % (fname, fval_repr))

        head = self._features.get(self.__class__.headname)
        if head is None: head = ''
        if head and not len(segments): return head
        return '%s[%s]' % (head, ', '.join(segments))

    def _str(self, reentrances, reentrance_ids):
        # Special case:
        if len(self.feature_names()) == 0:
            return ['[]']
        if self.feature_names() == [self.__class__.headname]:
            return ['%s[]' % self[self.__class__.headname]]
        
        
        # What's the longest feature name?  Use this to align names.
        maxfnamelen = max([len(k) for k in self.feature_names()])

        lines = []
        items = self.feature_names()
        items.sort() # sorting note: keys are unique strings, so we'll
                     # never fall through to comparing values.
        if self.__class__.headname in items:
            items.remove(self.__class__.headname)
            # items.insert(0, self.__class__.headname)
        for fname in items:
            fval = self[fname]
                
            if not isinstance(fval, FeatureStructure):
                # It's not a nested feature structure -- just print it.
                lines.append('%s = %r' % (fname.ljust(maxfnamelen), fval))

            else:
                # It's a new feature structure.  Separate it from
                # other values by a blank line.
                if lines and lines[-1] != '': lines.append('')

                # Recursively print the feature's value (fval).
                fval_lines = fval._str(reentrances, reentrance_ids)
                
                # Indent each line to make room for fname.
                fval_lines = [(' '*(maxfnamelen+3))+l for l in fval_lines]

                # Pick which line we'll display fname on.
                nameline = (len(fval_lines)-1)/2
                
                fval_lines[nameline] = (
                        fname.ljust(maxfnamelen)+' ='+
                        fval_lines[nameline][maxfnamelen+2:])

                # Add the feature structure to the output.
                lines += fval_lines
                            
                # Separate FeatureStructures by a blank line.
                lines.append('')

        # Get rid of any excess blank lines.
        if lines[-1] == '': lines = lines[:-1]
        
        # Add brackets around everything.
        headline = (len(lines) - 1)/2
        if self.has_feature(self.__class__.headname):
            head = self[self.__class__.headname]
        else: head = ''
        maxlen = max([len(line) for line in lines])
        for l in range(len(lines)):
            line = lines[l]
            if l == headline:
                lines[l] = ('%s[ %s%s ]' % (head, line, ' '*(maxlen-len(line))))
            else:
                lines[l] = ('%s[ %s%s ]' % (' '*len(head), line, ' '*(maxlen-len(line))))

        return lines

    # Regular expressions for parsing.
    _PARSE_RE = {'name': re.compile(r'\s*([^\s\(\)"\'\-=,\[\]]+)\s*'),
                 'categorystart': re.compile(r'\s*([^\s\(\)"\'\-=,\[\]]*)\s*\['),
                 'bool': re.compile(r'\s*([-\+])'),
                 'ident': re.compile(r'\s*\((\d+)\)\s*'),
                 'arrow': re.compile(r'\s*->\s*'),
                 'assign': re.compile(r'\s*=\s*'),
                 'bracket': re.compile(r'\s*]\s*'),
                 'comma': re.compile(r'\s*,\s*'),
                 'none': re.compile(r'None(?=\s|\]|,)'),
                 'int': re.compile(r'-?\d+(?=\s|\]|,)'),
                 'var': re.compile(r'\?[a-zA-Z_][a-zA-Z0-9_]*'+'|'+
                                   r'\?<[a-zA-Z_][a-zA-Z0-9_]*'+
                                   r'(=[a-zA-Z_][a-zA-Z0-9_]*)*>'),
                 'symbol': re.compile(r'\w+'),
#                 'application': re.compile(r'(app)\((\?[a-z][a-z]*)\s*,\s*(\?[a-z][a-z]*)\)'),
                 'disjunct': re.compile(r'\s*\|\s*'),
                 'whitespace': re.compile(r'\s*'),
                 'stringmarker': re.compile("['\"\\\\]")}
    
    def parse(cls, s):
        """
        Convert a string representation of a feature structure (as
        displayed by C{repr}) into a C{Category}.   This parse
        imposes the following restrictions on the string
        representation:
          - Feature names cannot contain any of the following:
            whitespace, parenthases, quote marks, equals signs,
            dashes, plus signs, and square brackets.
          - Only the following basic feature value are supported:
            strings, integers, variables, C{None}, C{True}, C{False},
            and unquoted alphanumeric strings.
          - A feature named C{foo} with a value of C{True} or C{False} should
            be expressed as C{+foo} or C{-foo} respectively, not as
            C{foo=True} or C{foo=False}.
        """
        try:
            value, position = cls._parse(s, 0, {})
        except ValueError, e:
            estr = ('Error parsing field structure\n\n\t' +
                    s + '\n\t' + ' '*e.args[1] + '^ ' +
                    'Expected %s\n' % e.args[0])
            raise ValueError, estr
        if position != len(s): raise ValueError()
        return value
    
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

        # Find the head, if there is one.
        match = _PARSE_RE['name'].match(s, position)
        if match is not None:
            head = match.group(1)
            position = match.end()
        else: head = None
        
        # Check that the name is followed by an open bracket.
        if position >= len(s) or s[position] != '[':
            return cls(**{cls.headname: head}), position
        position += 1

        # If it's immediately followed by a close bracket, then just
        # return an empty feature structure.
        match = _PARSE_RE['bracket'].match(s, position)
        if match is not None:
            if head is None: return cls(), match.end()
            else: return cls(**{cls.headname: head}), match.end()

        # Build a list of the features defined by the structure.
        # Each feature has one of the three following forms:
        #     name = value
        #     +name
        #     -name
        features = {}
        if head is not None: features[cls.headname] = head
        while position < len(s):
            # Use these variables to hold info about the feature:
            name = target = val = None

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
                return cls(**features), match.end()
                
            # Otherwise, there should be a comma
            match = _PARSE_RE['comma'].match(s, position)
            if match is None: raise ValueError('comma', position)
            position = match.end()
            
        # We never saw a close bracket.
        raise ValueError('close bracket', position)

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

        # EK: Semantic value, of the form <app(?x, ?y) >'; return an ApplicationExpression
 	match = _PARSE_RE['application'].match(s, position)
        if match is not None:
            fun = church.Parser(match.group(2)).next()
            arg = church.Parser(match.group(3)).next()
            return church.ApplicationExpression(fun, arg), match.end()	

 	# EK: Other semantic value enclosed by '< >'; return value given by the church parser
 	match = _PARSE_RE['semantics'].match(s, position)
        if match is not None:
            return church.Parser(match.group(1)).next(), match.end()	
        
        # String value
        if s[position] in "'\"":
            start = position
            quotemark = s[position:position+1]
            position += 1
            while 1: 
                match = _PARSE_RE['stringmarker'].search(s, position)
                if not match: raise ValueError('close quote', position)
                position = match.end()
                if match.group() == '\\': position += 1
                elif match.group() == quotemark:
                    return eval(s[start:position]), position

        # Nested category
        if _PARSE_RE['categorystart'].match(s, position) is not None:
            return cls._parse(s, position, reentrances)

        # Variable
        match = _PARSE_RE['var'].match(s, position)
        if match is not None:
            return FeatureVariable.parse(match.group()), match.end()

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
            return cls(**{cls.headname: match.group()}), match.end()

        # We don't know how to parse this value.
        raise ValueError('value', position)
    
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
            lhs, position = cls._parse(s, position)
        except ValueError, e:
            estr = ('Error parsing field structure\n\n\t' +
                    s + '\n\t' + ' '*e.args[1] + '^ ' +
                    'Expected %s\n' % e.args[0])
            raise ValueError, estr
        lhs.freeze()

        match = _PARSE_RE['arrow'].match(s, position)
        if match is None: raise ValueError('arrow', position)
        else: position = match.end()
        rules = []
        while position < len(s):
            rhs = []
            while position < len(s) and _PARSE_RE['disjunct'].match(s, position) is None:
                try:
                    val, position = cls._parseval(s, position, {})
                except ValueError, e:
                    estr = ('Error parsing field structure\n\n\t' +
                        s + '\n\t' + ' '*e.args[1] + '^ ' +
                        'Expected %s\n' % e.args[0])
                    raise ValueError, estr
                if isinstance(val, Category): val.freeze()
                rhs.append(val)
                position = _PARSE_RE['whitespace'].match(s, position).end()
            rules.append(cfg.Production(lhs, rhs))
            
            if position < len(s):
                match = _PARSE_RE['disjunct'].match(s, position)
                position = match.end()
        
        # Special case: if there's nothing after the arrow, it is one rule with
        # an empty RHS, instead of no rules.
        if len(rules) == 0: rules = [cfg.Production(lhs, ())]
        return rules

    _parseval=classmethod(_parseval)
    _parse=classmethod(_parse)
    parse=classmethod(parse)
    parse_rules=classmethod(parse_rules)


class GrammarCategory(Category):
    """
    A class of C{Category} for use in parsing.

    The name of the head feature in a C{GrammarCategory} is C{pos} (for "part
    of speech"). There is one required feature, C{/}, which is intended to
    indicate a type of phrase that is missing from the grammatical structure.

    In addition, GrammarCategories are displayed and parse differently, to be
    consistent with NLP teaching materials: the value of the C{/} feature can
    be written with a slash after the right bracket, so that the string
    representation looks like: C{head[...]/value}.

    An example of a C{GrammarCategory} is C{VP[+fin]/NP}, for a verb phrase
    that is finite and has an omitted noun phrase inside it.
    """
    
    headname = 'pos'
    requiredFeatures = ['/']
    
    def _repr(self, reentrances, reentrance_ids):
        segments = []

        items = self.feature_names()
        items.sort() # sorting note: keys are unique strings, so we'll
                     # never fall through to comparing values.
        for fname in items:
            if fname == self.__class__.headname or fname == '/': continue
            fval = self[fname]
            if isinstance(fval, bool):
                if fval: segments.append('+%s' % fname)
                else: segments.append('-%s' % fname)
 	    elif isinstance(fval, church.Expression): # EK: Use the church repr for expressions
 		segments.append('%s=%r' % (fname, fval.__str__()))
            elif not isinstance(fval, Category):
                segments.append('%s=%r' % (fname, fval))
            else:
                fval_repr = fval._repr(reentrances, reentrance_ids)
                segments.append('%s=%s' % (fname, fval_repr))
        
        head = self._features.get(self.__class__.headname)
        if head is None: head = ''
        if not len(segments): features = ''
        else: features = "[%s]" % ', '.join(segments)
        slash = self._features.get('/')
        if slash is None: slash = ''
        else: slash = '/%r' % slash
        
        return '%s%s%s' % (head, features, slash)

    _PARSE_RE = {'name': re.compile(r'\s*([^\s\(\)"\'\-=,\[\]/]+)\s*'),
                 'categorystart': re.compile(r'\s*([^\s\(\)"\'\-=,\[\]/]*)\s*(\[|/)'),
                 'bool': re.compile(r'\s*([-\+])'),
                 'ident': re.compile(r'\s*\((\d+)\)\s*'),
                 'arrow': re.compile(r'\s*->\s*'),
                 'assign': re.compile(r'\s*=\s*'),
                 'bracket': re.compile(r'\s*]\s*'),
                 'comma': re.compile(r'\s*,\s*'),
                 'none': re.compile(r'None(?=\s|\]|,)'),
                 'int': re.compile(r'-?\d+(?=\s|\]|,)'),
                 'var': re.compile(r'\?[a-zA-Z_][a-zA-Z0-9_]*'+'|'+
                                   r'\?<[a-zA-Z_][a-zA-Z0-9_]*'+
                                   r'(=[a-zA-Z_][a-zA-Z0-9_]*)*>'),
                 'symbol': re.compile(r'\w+'),
                 'semantics': re.compile(r'<([^>]+)>'), # EK
                 #EK: Assumes that Applications in sem always take FeatureVariable arguments
                 'application': re.compile(r'<(app)\((\?[a-z][a-z]*)\s*,\s*(\?[a-z][a-z]*)\)>'),
                 'disjunct': re.compile(r'\s*\|\s*'),
                 'slash': re.compile(r'\s*/\s*'),
                 'whitespace': re.compile(r'\s*'),
                 'stringmarker': re.compile("['\"\\\\]")}
    
    def _parse(cls, s, position=0, reentrances=None):
        # A set of useful regular expressions (precompiled)
        _PARSE_RE = cls._PARSE_RE

        features = {}
        
        # Find the head, if there is one.
        match = _PARSE_RE['name'].match(s, position)
        if match is not None:
            features[cls.headname] = match.group(1)
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
                    # Get out and check for a slash value.
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
                    # Get out and check for a slash value.
                    break   
                    
                # Otherwise, there should be a comma
                match = _PARSE_RE['comma'].match(s, position)
                if match is None: raise ValueError('comma', position)
                position = match.end()
            
        # Check for a slash value
        match = _PARSE_RE['slash'].match(s, position)
        if match is not None:
            position = match.end()
            slash, position = cls._parseval(s, position, 0)
            features['/'] = slash
        
        return cls(**features), position
        
    _parse = classmethod(_parse)

