# Natural Language Toolkit: Utility functions
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Rob Speer <rspeer@mit.edu>
#         Ewan Klein <ewan@inf.ed.ac.uk>
#         Steven Bird <sb@csse.unimelb.edu.au>
#         Edward Loper <edloper@gradient.cis.upenn.edu>,
#         
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

from copy import copy, deepcopy
import re, yaml

class FS(dict):
    def __init__(self, *args, **d):
        dict.__init__(self, *args, **d)
        self._bindings = {}

    def unify(self, other):
        return FS(unify(self, other, self._bindings))

    def unify_update(self, other):
        dict.__init__(self, unify(self, other))

    def __str__(self):
        return yaml.dump(self, default_flow_style=False).strip()

    def __repr__(self):
        return self.__str__()

    #################################################################
    ## Parsing
    #################################################################

    # [classmethod]
    def parse(cls, s):
        """
        Convert a string representation of a feature structure (as
        displayed by repr) into a C{FeatureStructure}.  This parse
        imposes the following restrictions on the string
        representation:
          - Feature names cannot contain any of the following:
            whitespace, parenthases, quote marks, equals signs,
            dashes, and square brackets.
          - Only the following basic feature value are supported:
            strings, integers, variables, C{None}, and unquoted
            alphanumeric strings.
          - For reentrant values, the first mention must specify
            a reentrance identifier and a value; and any subsequent
            mentions must use arrows (C{'->'}) to reference the
            reentrance identifier.
        """
        try:
            value, position = cls._parse(s, 0, {})
        except ValueError, e:
            estr = ('Error parsing field structure\n\n    ' +
                    s + '\n    ' + ' '*e.args[1] + '^ ' +
                    'Expected %s\n' % e.args[0])
            raise ValueError, estr
        if position != len(s): raise ValueError()
        return value

    # Regular expressions for parsing.
    _PARSE_RE = {'name': re.compile(r'\s*([^\s\(\)"\'\-=\[\]]+)\s*'),
                 'ident': re.compile(r'\s*\((\d+)\)\s*'),
                 'reentrance': re.compile(r'\s*->\s*'),
                 'assign': re.compile(r'\s*=\s*'),
                 'bracket': re.compile(r'\s*]\s*'),
                 'comma': re.compile(r'\s*,\s*'),
                 'none': re.compile(r'None(?=\s|\]|,)'),
                 'int': re.compile(r'-?\d+(?=\s|\]|,)'),
                 'var': re.compile(r'\?[a-zA-Z_][a-zA-Z0-9_]*'+'|'+
                                   r'\?<[a-zA-Z_][a-zA-Z0-9_]*'+
                                   r'(=[a-zA-Z_][a-zA-Z0-9_]*)*>'),
                 'symbol': re.compile(r'\w+'),
                 'stringmarker': re.compile("['\"\\\\]")}

    # [classmethod]
    def _parse(cls, s, position=0, reentrances=None):
        """
        Helper function that parses a feature structure.
        @param s: The string to parse.
        @param position: The position in the string to start parsing.
        @param reentrances: A dictionary from reentrance ids to values.
        @return: A tuple (val, pos) of the feature structure created
            by parsing and the position where the parsed feature
            structure ends.
        """
        # A set of useful regular expressions (precompiled)
        _PARSE_RE = cls._PARSE_RE

        # Check that the string starts with an open bracket.
        if s[position] != '[': raise ValueError('open bracket', position)
        position += 1

        # If it's immediately followed by a close bracket, then just
        # return an empty feature structure.
        match = _PARSE_RE['bracket'].match(s, position)
        if match is not None: return cls(), match.end()

        # Build a list of the features defined by the structure.
        # Each feature has one of the three following forms:
        #     name = value
        #     name (id) = value
        #     name -> (target)
        features = {}
        while position < len(s):
            # Use these variables to hold info about the feature:
            name = id = target = val = None
            
            # Find the next feature's name.
            match = _PARSE_RE['name'].match(s, position)
            if match is None: raise ValueError('feature name', position)
            name = match.group(1)
            position = match.end()

            # Check for a reentrance link ("-> (target)")
            match = _PARSE_RE['reentrance'].match(s, position)
            if match is not None:
                position = match.end()
                match = _PARSE_RE['ident'].match(s, position)
                if match is None: raise ValueError('identifier', position)
                target = match.group(1)
                position = match.end()
                try: features[name] = reentrances[target]
                except: raise ValueError('bound identifier', position)

            # If it's not a reentrance link, it must be an assignment.
            else:
                match = _PARSE_RE['assign'].match(s, position)
                if match is None: raise ValueError('equals sign', position)
                position = match.end()

                # Find the feature's id (if specified)
                match = _PARSE_RE['ident'].match(s, position)
                if match is not None:
                    id = match.group(1)
                    if reentrances.has_key(id):
                        raise ValueError('new identifier', position+1)
                    position = match.end()
                
                val, position = cls._parseval(s, position, reentrances)
                features[name] = val
                if id is not None:
                    reentrances[id] = val

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

    # [classmethod]
    def _parseval(cls, s, position, reentrances):
        """
        Helper function that parses a feature value.  Currently
        supports: None, integers, variables, strings, nested feature
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

        # Nested feature structure
        if s[position] == '[':
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
            return match.group(), match.end()

        # We don't know how to parse this value.
        raise ValueError('value', position)

    _parseval=classmethod(_parseval)
    _parse=classmethod(_parse)
    parse=classmethod(parse)




class UnificationFailure(Exception):
    """
    An exception that is raised when two values cannot be unified.
    """
    pass

class _FORWARD(object):
    """
    _FORWARD is a singleton value, used in unification as a flag that a value
    has been forwarded to another object.

    This class itself is used as the singleton value. It cannot be
    instantiated.
    """
    def __init__(self):
        raise TypeError, "The _FORWARD class is not meant to be instantiated"

class Variable(object):
    """
    A Variable is an object that can be used in unification to hold an
    initially unknown value. Two equivalent Variables, for example, can be used
    to require that two features have the same value.

    When a Variable is assigned a value, it will eventually be replaced by
    that value. However, in order to make that value show up everywhere the
    variable appears, the Variable temporarily stores its assigned value and
    becomes a I{bound variable}. Bound variables do not appear in the results
    of unification.

    Variables are distinguished by their name, and by the dictionary of
    I{bindings} that is being used to determine their values. Two variables can
    have the same name but be associated with two different binding
    dictionaries: those variables are not equal.
    """
    _next_numbered_id = 1
    
    def __init__(self, name=None, value=None):
        """
        Construct a new feature structure variable.
        
        The value should be left at its default of None; it is only used
        internally to copy bound variables.

        @type name: C{string}
        @param name: An identifier for this variable. Two C{Variable} objects
          with the same name will be given the same value in a given dictionary
          of bindings.
        """
        self._uid = Variable._next_numbered_id
        Variable._next_numbered_id += 1
        if name is None: name = self._uid
        self._name = str(name)
        self._value = value
    
    def name(self):
        """
        @return: This variable's name.
        @rtype: C{string}
        """
        return self._name
    
    def value(self):
        """
        If this varable is bound, find its value. If it is unbound or aliased
        to an unbound variable, returns None.
        
        @return: The value of this variable, if any.
        @rtype: C{object}
        """
        if isinstance(self._value, Variable): return self._value.value()
        else: return self._value

    def copy(self):
        """
        @return: A copy of this variable.
        @rtype: C{Variable}
        """
        return Variable(self.name(), self.value())
    
    def forwarded_self(self):
        """
        Variables are aliased to other variables by one variable _forwarding_
        to the other. The first variable simply has the second as its value,
        but it acts like the second variable's _value_ is its value.

        forwarded_self returns the final Variable object that actually stores
        the value.

        @return: The C{Variable} responsible for storing this variable's value.
        @rtype: C{Variable}
        """
        if isinstance(self._value, Variable):
            return self._value.forwarded_self()
        else: return self
    
    def bindValue(self, value, ourbindings, otherbindings):
        """
        Bind this variable to a value. C{ourbindings} are the bindings that
        accompany the feature structure this variable came from;
        C{otherbindings} are the bindings from the structure it's being unified
        with.

        @type value: C{object}
        @param value: The value to be assigned.
        @type ourbindings: C{dict}
        @param ourbindings: The bindings associated with this variable.
        @type otherbindings: C{dict}
        @param otherbindings: The bindings associated with the value being
          assigned. (May be identical to C{ourbindings}.)
        """
        if isinstance(self._value, Variable):
            # Forward the job of binding to the variable we're aliased to.
            return self._value.bindValue(value, ourbindings, otherbindings)
        if self._value is None:
            # This variable is unbound, so bind it.
            self._value = value
        else:
            # This variable is already bound; try to unify the existing value
            # with the new one.
            self._value = unify(self._value, value, ourbindings, otherbindings)

    def forwardTo(self, other, ourbindings, otherbindings):
        """
        A unification wants this variable to be aliased to another variable.
        Forward this variable to the other one, and return the other.

        @type other: C{Variable}
        @param other: The variable to replace this one.
        @type ourbindings: C{dict}
        @param ourbindings: The bindings associated with this variable.
        @type otherbindings: C{dict}
        @param otherbindings: The bindings associated with the other variable.
        (May be identical to C{ourbindings}.)
        @return: C{other}
        @rtype: C{Variable}
        """
        other.bindValue(self.value(), ourbindings, otherbindings)
        self._value = other
        return other
        
    def __hash__(self): return hash(self._uid)

    def __cmp__(self, other):
        """
        Variables are equal if they are the same object or forward to the
        same object. Variables with the same name may still be unequal.
        """
        if not isinstance(other, Variable): return -1
        if isinstance(self._value, Variable): return cmp(self._value, other)
        else: return cmp((self._name, self._value), (other._name, other._value))
    def __repr__(self):
        if self._value is None: return '?%s' % self._name
        else: return '?%s: %r' % (self._name, self._value)

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

class SubstituteBindingsMixin(SubstituteBindingsI):
    def substitute_bindings(self, bindings):
        newval = self
        for semvar in self.variables():
            varstr = str(semvar)
            # discard Variables which don't look like FeatureVariables
            if varstr.startswith('?'):
                var = _make_var(varstr)
                if var.name() in bindings:
                    newval = newval.replace(semvar, bindings[var.name()])
        return newval

def _copy_and_bind(feature, bindings, memo=None):
    """
    Make a deep copy of a feature structure, preserving reentrance using the
    C{memo} dictionary. Meanwhile, variables are replaced by their bound
    values, if these values are already known, and variables with unknown
    values are given placeholder bindings.
    """
    if memo is None:
        memo = {}
    if id(feature) in memo:
        return memo[id(feature)]
    if isinstance(feature, Variable) and bindings is not None:
        if feature.name() not in bindings:
            bindings[feature.name()] = feature.copy()
        result = _copy_and_bind(bindings[feature.name()], None, memo)
    else:
        if _is_mapping(feature):
            # Construct a new object of the same class
            result = feature.__class__()
            for (key, value) in feature.items():
                result[key] = _copy_and_bind(value, bindings, memo)
        elif isinstance(feature, SubstituteBindingsI):
            if bindings is not None:
                result = feature.substitute_bindings(bindings).simplify()
            else:
                result = feature.simplify()
        else:
            result = feature
    memo[id(feature)] = result
    memo[id(result)] = result
    return result

def substitute_bindings(feature, bindings):
    """
    Replace variables in a feature structure with their bound values.
    """
    return _copy_and_bind(feature, bindings.copy())

def unify(feature1, feature2, bindings1=None, bindings2=None, memo=None, fail=None, trace=0):
    if fail is None:
        def failerror(f1, f2):
            raise UnificationFailure
        fail = failerror
        
    if bindings1 is None and bindings2 is None:
        bindings1 = {}
        bindings2 = {}
    else:
        if bindings1 is None:
            bindings1 = {}
        if bindings2 is None:
            bindings2 = bindings1

    if memo is None: memo = {}
    copymemo = {}
    if (id(feature1), id(feature2)) in memo:
        result = memo[id(feature1), id(feature2)]
        if result is UnificationFailure:
            if trace > 2:
                print '(cached) Unifying: %r + %r --> [fail]' % (feature1, feature2)
            raise result()
        if trace > 2:
            print '(cached) Unifying: %r + %r --> ' % (feature1, feature2),
            print repr(result)
        return result

    if trace > 1:
        print 'Unifying: %r + %r --> ' % (feature1, feature2),
    
    # Make copies of the two structures (since the unification algorithm is
    # destructive). Use the same memo, to preserve reentrance links between them.
    copy1 = _copy_and_bind(feature1, bindings1, copymemo)
    copy2 = _copy_and_bind(feature2, bindings2, copymemo)

    # Preserve links between bound variables and the two feature structures.
    for b in (bindings1, bindings2):
        for (vname, value) in b.items():
            value_id = id(value)
            if value_id in copymemo:
                b[vname] = copymemo[value_id]

    # Go on to doing the unification.
    try:
        unified = _destructively_unify(copy1, copy2, bindings1, bindings2, memo,
        fail)
    except UnificationFailure:
        if trace > 1: print '[fail]'
        memo[id(feature1), id(feature2)] = UnificationFailure
        raise

    _apply_forwards_to_bindings(bindings1)
    _apply_forwards_to_bindings(bindings2)
    _apply_forwards(unified, {})
    unified = _lookup_values(unified, {}, remove=False)
    _lookup_values(bindings1, {}, remove=True)
    _lookup_values(bindings2, {}, remove=True)

    if trace > 1:
        print repr(unified)
    elif trace > 0:
        print 'Unifying: %r + %r --> %r' % (feature1, feature2, repr(unified))
    
    memo[id(feature1), id(feature2)] = unified
    return unified

def _destructively_unify(feature1, feature2, bindings1, bindings2, memo, fail,
depth=0):
    """
    Attempt to unify C{self} and C{other} by modifying them
    in-place.  If the unification succeeds, then C{self} will
    contain the unified value, and the value of C{other} is
    undefined.  If the unification fails, then a
    UnificationFailure is raised, and the values of C{self}
    and C{other} are undefined.
    """
    if depth > 50:
        print "Infinite recursion in this unification:"
        print dict(feature1=feature1, feature2=feature2, bindings1=bindings1, bindings2=bindings2, memo=memo)
        raise ValueError, "Infinite recursion in unification"
    if (id(feature1), id(feature2)) in memo:
        result = memo[id(feature1), id(feature2)]
        if result is UnificationFailure: raise result()
    unified = _do_unify(feature1, feature2, bindings1, bindings2, memo, fail,
    depth)
    memo[id(feature1), id(feature2)] = unified
    return unified

def _do_unify(feature1, feature2, bindings1, bindings2, memo, fail, depth=0):
    """
    Do the actual work of _destructively_unify when the result isn't memoized.
    """

    # Trivial cases.
    if feature1 is None: return feature2
    if feature2 is None: return feature1
    if feature1 is feature2: return feature1
    
    # Deal with variables by binding them to the other value.
    if isinstance(feature1, Variable):
        if isinstance(feature2, Variable):
            # If both objects are variables, forward one to the other. This
            # has the effect of unifying the variables.
            return feature1.forwardTo(feature2, bindings1, bindings2)
        else:
            feature1.bindValue(feature2, bindings1, bindings2)
            return feature1
    if isinstance(feature2, Variable):
        feature2.bindValue(feature1, bindings2, bindings1)
        return feature2
    
    # If it's not a mapping or variable, it's a base object, so we just
    # compare for equality.
    if not _is_mapping(feature1):
        if feature1 == feature2: return feature1
        else: 
            return fail(feature1, feature2)
    if not _is_mapping(feature2):
        return fail(feature1, feature2)
    
    # At this point, we know they're both mappings.
    # Do the destructive part of unification.

    while _FORWARD in feature2:
        feature2 = feature2[_FORWARD]
    if feature1 is not feature2:
        feature2[_FORWARD] = feature1
    for (fname, val2) in feature2.items():
        if fname == _FORWARD:
            continue
        val1 = feature1.get(fname)
        feature1[fname] = _destructively_unify(val1, val2, bindings1, bindings2, memo, fail, depth+1)
    return feature1

def _apply_forwards(feature, visited):
    """
    Replace any feature structure that has a forward pointer with
    the target of its forward pointer (to preserve reentrance).
    """
    if not _is_mapping(feature):
        return
    if id(feature) in visited:
        return
    visited[id(feature)] = True

    for fname, fval in feature.items():
        if _is_mapping(fval):
            while _FORWARD in fval:
                fval = fval[_FORWARD]
                feature[fname] = fval
            _apply_forwards(fval, visited)

def _lookup_values(mapping, visited, remove=False):
    """
    The unification procedure creates _bound variables_, which are Variable
    objects that have been assigned a value. Bound variables are not useful
    in the end result, however, so they should be replaced by their values.

    This procedure takes a mapping, which may be a feature structure or a
    binding dictionary, and replaces bound variables with their values.
    
    If the dictionary is a binding dictionary, then 'remove' should be set to
    True. This ensures that unbound, unaliased variables are removed from the
    dictionary. If the variable name 'x' is mapped to the unbound variable ?x,
    then, it should be removed. This is not done with features, because a
    feature named 'x' can of course have a variable ?x as its value.
    """
    if isinstance(mapping, Variable):
        # Because it's possible to unify bare variables, we need to gracefully
        # accept a variable in place of a dictionary, and return a result that
        # is consistent with that variable being inside a dictionary.
        #
        # We can't remove a variable from itself, so we ignore 'remove'.
        var = mapping
        if var.value() is not None:
            return var.value()
        else:
            return var.forwarded_self()
    if not _is_mapping(mapping):
        return mapping
    if id(mapping) in visited:
        return mapping
    visited[id(mapping)] = True

    for fname, fval in mapping.items():
        if _is_mapping(fval):
            _lookup_values(fval, visited)
        elif isinstance(fval, Variable):
            if fval.value() is not None:
                mapping[fname] = fval.value()
                if _is_mapping(mapping[fname]):
                    _lookup_values(mapping[fname], visited)
            else:
                newval = fval.forwarded_self()
                if remove and newval.name() == fname:
                    del mapping[fname]
                else:
                    mapping[fname] = newval
    return mapping

def _apply_forwards_to_bindings(bindings):
    """
    Replace any feature structures that have been forwarded by their new
    identities.
    """
    for (key, value) in bindings.items():
        if _is_mapping(value) and _FORWARD in value:
            while _FORWARD in value:
                value = value[_FORWARD]
            bindings[key] = value

def _make_var(varname):
    """
    Given a variable representation such as C{?x}, construct a corresponding
    Variable object.
    """
    return Variable(varname[1:])

def _is_mapping(obj):
    return hasattr(obj, 'has_key')

#################################################################################
# STRING I/O
#################################################################################

def variable_representer(dumper, var):
    "Output variables in YAML as ?name."
    return dumper.represent_scalar(u'!var', u'?%s' % var.name())
yaml.add_representer(Variable, variable_representer)

def variable_constructor(loader, node):
    "Recognize variables written as ?name in YAML."
    value = loader.construct_scalar(node)
    name = value[1:]
    return Variable(name)
yaml.add_constructor(u'!var', variable_constructor)
yaml.add_implicit_resolver(u'!var', re.compile(r'^\?\w+$'))

def parse(s):
    return FS(yaml.load(s))

#################################################################################
# DEMO CODE
#################################################################################

def demo():
    s1 = '''
    A:
      B: b
      D: d
    '''
    s2 = '''
    A:
      B: b
      C: c
    '''
    fs1 = parse(s1)
    fs2 = parse(s2)
    print fs1
    print fs2
    print fs1.unify(fs2)

    print
    print "Atomic unification:"
    print unify(3, None)
    print unify(None, 'fish')
    print unify(True, True)
    print unify([1], [1])
    #print unify('a', 'b')

    print
    print "FS unification:"
    f1 = FS(dict(A=dict(B='b')))
    f2 = FS(dict(A=dict(C='c')))
    print unify(f1, f2) == FS(dict(A=dict(B='b', C='c')))

    print
    print "Unify update (cf set.intersection_update):"
    f1 = FS(dict(A=dict(B='b')))
    f2 = FS(dict(A=dict(C='c')))
    f1.unify_update(f2)
    print f1

    print unify({}, dict(foo='bar'))

    print
    print "Bindings:"

    bindings = {}
    print unify(Variable('x'), 5, bindings), bindings
    
    print unify({'a': Variable('x')}, {}, bindings)

    fs1 = parse('''
    a: 1
    b: 1
    c: ?x
    d: ?x
    ''')
    fs2 = parse('''
    a: ?x
    b: ?x
    c: 2
    d: 2
    ''')
    bindings1 = {}
    bindings2 = {}
    print unify(fs1, fs2, bindings1, bindings2)
    print bindings1, bindings2

    print
    print "Re-entrancy:"

    fs1 = parse('''
    A: &1                # &1 defines a reference in YAML...
      B: b
    E:
      F: *1              # and *1 uses the previously defined reference.
    ''')
    print fs1['E']['F']['B']
    print fs1['A'] is fs1['E']['F']
    fs2 = parse('''
    A:
      C: c
    E:
      F:
        D: d
    ''')
    fs3 = unify(fs1, fs2)
    print fs3
    print fs3['A'] is fs3['E']['F']    # Showing that the reentrance still holds.

    print
    print "Cycles:"
    fs1 = parse('''
    F: &1 {}
    G: *1
    ''')
    fs2 = parse('''
    F:
      H: &2 {}
    G: *2
    ''')
    fs3 = unify(fs1, fs2)
    print fs3
    print fs3['F'] is fs3['G']
    print fs3['F'] is fs3['G']['H']
    print fs3['F'] is fs3['G']['H']['H']

    print
    print "Parsing:"
    print '[A=[B=b]]'
    fs1 = FS.parse('[A=[B=b]]')
    print fs1
    print '[A=[C=c]]'
    fs2 = FS.parse('[A=[C=c]]')
    print fs2
    fs3 = fs1.unify(fs2)
    print fs3

    print '[A=(1)[B=b], E=[F->(1)]]'
    fs1 = FS.parse('[A=(1)[B=b], E=[F->(1)]]')
    print "[A=[C='c'], E=[F=[D='d']]]"
    fs2 = FS.parse("[A=[C='c'], E=[F=[D='d']]]")
    fs3 = fs1.unify(fs2)
    print fs3
    fs3 = fs2.unify(fs1) # Try unifying both ways.
    print fs3

    # More than 2 paths to a value
    print "[a=[],b=[],c=[],d=[]]"
    fs1 = FS.parse("[a=[],b=[],c=[],d=[]]")
    print '[a=(1)[], b->(1), c->(1), d->(1)]'
    fs2 = FS.parse('[a=(1)[], b->(1), c->(1), d->(1)]')
    fs3 = fs1.unify(fs2)
    print fs3

    # fs1[a] gets unified with itself:
    print '[x=(1)[], y->(1)]'
    fs1 = FS.parse('[x=(1)[], y->(1)]')
    print '[x=(1)[], y->(1)]'
    fs2 = FS.parse('[x=(1)[], y->(1)]')
    fs3 = fs1.unify(fs2)

if __name__ == "__main__":
    demo()

