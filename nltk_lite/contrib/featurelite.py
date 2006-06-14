"""
This module provides utilities for treating Python dictionaries as X{feature
structures}. Specifically, it contains the C{unify} function, which can be used
to merge the properties of two dictionaries, and the C{Variable} class, which
holds an unknown value to be used in unification.

A X{feature structure} is a mapping from feature names to feature values,
where:

  - Each X{feature name} is a case sensitive string.
  - Each X{feature value} can be a base value (such as a string), a
    variable, or a nested feature structure.

However, feature structures are not a specialized class; they are represented
by dictionaries, or more generally by anything that responds to the C{has_key}
method. The YAML representation can be used to create and display feature
structures intuitively:

>>> f1 = yaml.load('''
... A:
...   B: b
...   D: d
... ''')
>>> f2 = yaml.load('''
... A:
...   C: c
...   D: d
... ''')
>>> print yaml.show(unify(f1, f2))
A:
  B: b
  C: c
  D: d

Feature structures are typically used to represent partial information
about objects.  A feature name that is not mapped to a value stands
for a feature whose value is unknown (I{not} a feature without a
value).  Two feature structures that represent (potentially
overlapping) information about the same object can be combined by
X{unification}.  When two inconsistant feature structures are unified,
the unification fails and raises an error.

Features can be specified using X{feature paths}, or tuples of feature names
that specify paths through the nested feature structures to a value.

Feature structures may contain reentrant feature values.  A
X{reentrant feature value} is a single feature value that can be
accessed via multiple feature paths.  Unification preserves the
reentrance relations imposed by both of the unified feature
structures.  After unification, any extensions to a reentrant feature
value will be visible using any of its feature paths.

Feature structure variables are encoded using the L{Variable} class. The scope
of a variable is determined by the X{bindings} used when the structure
including that variable is unified. Bindings can be reused between unifications
to ensure that variables with the same name get the same value.

"""

from copy import copy, deepcopy
import re
import yaml
import unittest
import sys

class UnificationFailure(Exception):
    """
    An exception that is raised when two values cannot be unified.
    """
    pass

def isMapping(obj):
    """
    Determine whether to treat a given object as a feature structure. The
    test is whether it responds to C{has_key}. This can be overridden if the
    object includes an attribute or method called C{_no_feature}.

    @param obj: The object to be tested
    @type obj: C{object}
    @return: True iff the object can be treated as a feature structure
    @rtype: C{bool}
    """
    return ('has_key' in dir(obj)) and ('_no_feature' not in dir(obj)) 

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
        else: return cmp(self._uid, other._uid)
    def __repr__(self):
        if self._value is None: return '?%s' % self._name
        else: return '?%s: %r' % (self._name, self._value)

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

def _copy_and_bind(feature, bindings, memo=None):
    """
    Make a deep copy of a feature structure, preserving reentrance using the
    C{memo} dictionary. Meanwhile, variables are replaced by their bound
    values, if these values are already known, and variables with unknown
    values are given placeholder bindings.
    """
    if memo is None: memo = {}
    if id(feature) in memo: return memo[id(feature)]
    if isinstance(feature, Variable) and bindings is not None:
        if not bindings.has_key(feature.name()):
            bindings[feature.name()] = feature.copy()
        result = _copy_and_bind(bindings[feature.name()], None, memo)
    else:
        if isMapping(feature):
            # Construct a new object of the same class
            result = feature.__class__()
            for (key, value) in feature.items():
                result[key] = _copy_and_bind(value, bindings, memo)
        else: result = feature
    memo[id(feature)] = result
    memo[id(result)] = result
    return result

def unify(feature1, feature2, bindings1=None, bindings2=None):
    """
    In general, the 'unify' procedure takes two values, and either returns a
    value that provides the information provided by both values, or fails if
    that is impossible.
    
    These values can have any type, but fall into a few general cases:
      - Values that respond to C{has_key} represent feature structures. The
        C{unify} procedure will recurse into them and unify their inner values.
      - L{Variable}s represent an unknown value, and are handled specially.
        The values assigned to variables are tracked using X{bindings}.
      - C{None} represents the absence of information.
      - Any other value is considered a X{base value}. Base values are
        compared to each other with the == operation.

    The value 'None' represents the absence of any information. It specifies no
    properties and acts as the identity in unification.
    >>> unify(3, None)
    3

    >>> unify(None, 'fish')
    'fish'

    A base value unifies with itself, but not much else.
    >>> unify(True, True)
    True

    >>> unify([1], [1])
    [1]

    >>> unify('a', 'b')
    Traceback (most recent call last):
        ...
    UnificationFailure

    When two mappings (representing feature structures, and usually implemented
    as dictionaries) are unified, any chain of keys that accesses a value in
    either mapping will access an equivalent or more specific value in the
    unified mapping. If this is not possible, UnificationFailure is raised.

    >>> f1 = dict(A=dict(B='b'))
    >>> f2 = dict(A=dict(C='c'))
    >>> unify(f1, f2) == dict(A=dict(B='b', C='c'))
    True
    
    The empty dictionary specifies no features. It unifies with any mapping.
    >>> unify({}, dict(foo='bar'))
    {'foo': 'bar'}

    >>> unify({}, True)
    Traceback (most recent call last):
        ...
    UnificationFailure
    
    Representing dictionaries in YAML form is useful for making feature
    structures readable:
    
    >>> f1 = yaml.load("number: singular")
    >>> f2 = yaml.load("person: 3")
    >>> print yaml.show(unify(f1, f2))
    number: singular
    person: 3

    >>> f1 = yaml.load('''
    ... A:
    ...   B: b
    ...   D: d
    ... ''')
    >>> f2 = yaml.load('''
    ... A:
    ...   C: c
    ...   D: d
    ... ''')
    >>> print yaml.show(unify(f1, f2))
    A:
      B: b
      C: c
      D: d
    
    Variables are names for unknown values. Variables are assigned values
    that will make unification succeed. The values of variables can be reused
    in later unifications if you provide a dictionary of _bindings_ from
    variables to their values.
    >>> bindings = {}
    >>> print unify(Variable('x'), 5, bindings)
    5
    
    >>> print bindings
    {'x': 5}
    
    >>> print unify({'a': Variable('x')}, {}, bindings)
    {'a': 5}
    
    The same variable name can be reused in different binding dictionaries
    without collision. In some cases, you may want to provide two separate
    binding dictionaries to C{unify} -- one for each feature structure, so
    their variables do not collide.

    In the following examples, two different feature structures use the
    variable ?x to require that two values are equal. The values assigned to
    ?x are consistent within each structure, but would be inconsistent if every
    ?x had to have the same value.

    >>> f1 = yaml.load('''
    ... a: 1
    ... b: 1
    ... c: ?x
    ... d: ?x
    ... ''')
    >>> f2 = yaml.load('''
    ... a: ?x
    ... b: ?x
    ... c: 2
    ... d: 2
    ... ''')
    >>> bindings1 = {}
    >>> bindings2 = {}
    >>> print yaml.show(unify(f1, f2, bindings1, bindings2))
    a: 1
    b: 1
    c: 2
    d: 2
    
    >>> print bindings1
    {'x': 2}
    
    >>> print bindings2
    {'x': 1}

    Feature structures can involve _reentrant_ values, where multiple feature
    paths lead to the same value. This is represented by the features having
    the same Python object as a value. (This kind of identity can be tested
    using the C{is} operator.)
    
    Unification preserves the properties of reentrance. So if a reentrant value
    is changed by unification, it is changed everywhere it occurs, and it is
    still reentrant. Reentrant features can even form cycles, although these
    cycles currently cannot be printed through the current YAML library.

    >>> f1 = yaml.load('''
    ... A: &1                # &1 defines a reference in YAML...
    ...   B: b
    ... E:
    ...   F: *1              # and *1 uses the previously defined reference.
    ... ''')
    >>> f1['E']['F']['B']
    'b'
    >>> f1['A'] is f1['E']['F']
    True
    >>> f2 = yaml.load('''
    ... A:
    ...   C: c
    ... E:
    ...   F:
    ...     D: d
    ... ''')
    >>> f3 = unify(f1, f2)
    >>> print yaml.show(f3)
    A: &1
      B: b
      C: c
      D: d
    E:
      F: *1
    >>> f3['A'] is f3['E']['F']    # Showing that the reentrance still holds.
    True
    
    This unification creates a cycle:
    >>> f1 = yaml.load('''
    ... F: &1 {}
    ... G: *1
    ... ''')
    >>> f2 = yaml.load('''
    ... F:
    ...   H: &2 {}
    ... G: *2
    ... ''')
    >>> f3 = unify(f1, f2)
    >>> print f3
    {'G': {'H': {...}}, 'F': {'H': {...}}}
    >>> print f3['F'] is f3['G']
    True
    >>> print f3['F'] is f3['G']['H']
    True
    >>> print f3['F'] is f3['G']['H']['H']
    True

    A cycle can also be created using variables instead of reentrance.
    Here we supply a single set of bindings, so that it is used on both sides
    of the unification, making ?x mean the same thing in both feature
    structures.
    
    >>> f1 = yaml.load('''
    ... F:
    ...   H: ?x
    ... ''')
    >>> f2 = yaml.load('''
    ... F: ?x
    ... ''')
    >>> f3 = unify(f1, f2, {})
    >>> print f3
    {'F': {'H': {...}}}
    >>> print f3['F'] is f3['F']['H']
    True
    >>> print f3['F'] is f3['F']['H']['H']
    True

    Two sets of bindings can be provided because the variable names on each
    side of the unification may be unrelated. An example involves unifying the
    following two structures, which each require that two values are
    equivalent, and happen to both use ?x to express that requirement.

    >>> f1 = yaml.load('''
    ... a: 1
    ... b: 1
    ... c: ?x
    ... d: ?x
    ... ''')
    >>> f2 = yaml.load('''
    ... a: ?x
    ... b: ?x
    ... c: 2
    ... d: 2
    ... ''')
    >>> bindings1 = {}
    >>> bindings2 = {}
    >>> # We could avoid defining two empty dictionaries by simply using the
    >>> # defaults, with unify(f1, f2) -- but we want to be able to examine
    >>> # the bindings afterward.
    >>> print yaml.show(unify(f1, f2, bindings1, bindings2))
    a: 1
    b: 1
    c: 2
    d: 2
    >>> print bindings1
    {'x': 2}
    >>> print bindings2
    {'x': 1}

    If a variable is unified with another variable, the two variables are
    _aliased_ to each other; they share the same value, similarly to reentrant
    feature structures. This is represented in a set of bindings as one
    variable having the other as its value.
    >>> f1 = yaml.load('''
    ... a: ?x
    ... b: ?x
    ... ''')
    >>> f2 = yaml.load('''
    ... b: ?y
    ... c: ?y
    ... ''')
    >>> bindings = {}
    >>> print yaml.show(unify(f1, f2, bindings))
    a: &1 ?y
    b: *1
    c: *1
    >>> print bindings
    {'x': ?y}

    Reusing the same variable bindings ensures that appropriate bindings are
    made after the fact:
    >>> bindings = {}
    >>> f1 = {'a': Variable('x')}
    >>> f2 = unify(f1, {'a': {}}, bindings)
    >>> f3 = unify(f2, {'b': Variable('x')}, bindings)
    >>> print yaml.show(f3)
    a: &1 {}
    b: *1
    >>> print bindings
    {'x': {}}

    @param feature1: The first object to be unified.
    @type feature1: C{object} (probably a mapping)
    @param feature2: The second object to be unified.
    @type feature2: C{object} (probably a mapping)
    @param bindings1: The variable bindings associated with the first object.
    @type bindings1: C{dict} or None
    @param bindings2: The variable bindings associated with the second object,
      if these are distinct from C{bindings1}.
    @type bindings2: C{dict} or None
    @return: The result of unifying the two objects.
    @rtype: C{object} (probably a mapping)
    """

    if bindings1 is None and bindings2 is None:
        bindings1 = {}
        bindings2 = {}
    else:
        if bindings1 is None: bindings1 = {}
        if bindings2 is None: bindings2 = bindings1
    
    # Make copies of the two structures (since the unification algorithm is
    # destructive). Use the same memo, to preserve reentrance links between
    # them.
    copymemo = {}
    copy1 = _copy_and_bind(feature1, bindings1, copymemo)
    copy2 = _copy_and_bind(feature2, bindings2, copymemo)
    # Preserve links between bound variables and the two feature structures.
    for b in (bindings1, bindings2):
        for (vname, value) in b.items():
            value_id = id(value)
            if value_id in copymemo:
                b[vname] = copymemo[value_id]

    # Go on to doing the unification.
    unified = _destructively_unify(copy1, copy2, bindings1, bindings2, {})

    _apply_forwards_to_bindings(bindings1)
    _apply_forwards_to_bindings(bindings2)
    _apply_forwards(unified, {})
    unified = _lookup_values(unified, {}, remove=False)
    _lookup_values(bindings1, {}, remove=True)
    _lookup_values(bindings2, {}, remove=True)

    return unified

def _destructively_unify(feature1, feature2, bindings1, bindings2, memo):
    """
    Attempt to unify C{self} and C{other} by modifying them
    in-place.  If the unification succeeds, then C{self} will
    contain the unified value, and the value of C{other} is
    undefined.  If the unification fails, then a
    UnificationFailure is raised, and the values of C{self}
    and C{other} are undefined.
    """
    if memo.has_key((id(feature1), id(feature2))):
        return memo[id(feature1), id(feature2)]
    unified = _do_unify(feature1, feature2, bindings1, bindings2, memo)
    memo[id(feature1), id(feature2)] = unified
    return unified

def _do_unify(feature1, feature2, bindings1, bindings2, memo):
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
    if not isMapping(feature1):
        if feature1 == feature2: return feature1
        else: 
            raise UnificationFailure
    if not isMapping(feature2): raise UnificationFailure
    
    # At this point, we know they're both mappings.
    # Do the destructive part of unification.

    while feature2.has_key(_FORWARD): feature2 = feature2[_FORWARD]
    feature2[_FORWARD] = feature1
    for (fname, val2) in feature2.items():
        if fname == _FORWARD: continue
        val1 = feature1.get(fname)
        feature1[fname] = _destructively_unify(val1, val2, bindings1, bindings2, memo)
    return feature1

def _apply_forwards(feature, visited):
    """
    Replace any feature structure that has a forward pointer with
    the target of its forward pointer (to preserve reentrance).
    """
    if not isMapping(feature): return
    if visited.has_key(id(feature)): return
    visited[id(feature)] = True

    for fname, fval in feature.items():
        if isMapping(fval):
            while fval.has_key(_FORWARD):
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
    if not isMapping(mapping): return mapping
    if visited.has_key(id(mapping)): return mapping
    visited[id(mapping)] = True

    for fname, fval in mapping.items():
        if isMapping(fval):
            _lookup_values(fval, visited)
        elif isinstance(fval, Variable):
            if fval.value() is not None:
                mapping[fname] = fval.value()
                if isMapping(mapping[fname]):
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
        if isMapping(value) and value.has_key(_FORWARD):
            while value.has_key(_FORWARD):
                value = value[_FORWARD]
            bindings[key] = value

def test():
    "Run unit tests on unification."
    import doctest
    doctest.testmod()

if __name__ == "__main__":
    test()

