"""
featurelite.py - by Rob Speer

Here I'm trying something wacky: having feature structures and binding
structures all represented by Python dictionaries or frozendicts. The only
things that need to be specialized objects are variables.
"""

from copy import copy, deepcopy
import re
import yaml
import unittest

class UnificationFailure(Exception): pass

class _FORWARD(object):
    """
    _FORWARD is a singleton value, used in unification as a flag that a value
    has been forwarded to another object. An empty class is a quick way to
    get a singleton.
    """
    pass

class Variable(object):
    """
    Right now, variables store their own values. If the value is another
    variable, then this variable has been unified with that one.

    This means they kind of ignore the bindings. That's not good.
    I'll be changing this.
    """
    _next_numbered_id = 1
    def __init__(self, name=None, value=None):
        self._uid = Variable._next_numbered_id
        Variable._next_numbered_id += 1
        if name is None: name = self._uid
        self._name = str(name)
        self._value = value
    def name(self):
        return self._name
    def value(self):
        if isinstance(self._value, Variable): return self._value.value()
        else: return self._value
    def copy(self):
        return Variable(self.name(), self.value())
    def forwarded_self(self):
        if isinstance(self._value, Variable):
            return self._value.forwarded_self()
        else: return self
    def bindValue(self, value, ourbindings, otherbindings):
        if isinstance(self._value, Variable):
            return self._value.bindValue(value, ourbindings, otherbindings)
        if self._value is None: self._value = value
        else:
            self._value = unify(self._value, value, ourbindings, otherbindings)
    def become(self, other, ourbindings, otherbindings):
        other.bindValue(self.value(), ourbindings, otherbindings)
        self._value = other
        return other
        
    def __hash__(self): return hash(self._uid)
    def __cmp__(self, other):
        if not isinstance(other, Variable): return -1
        if isinstance(self._value, Variable): return cmp(self._value, other)
        else: return cmp(self._uid, other._uid)
    def __repr__(self):
        if self._value is None: return '?%s: <#%d>' % (self._name, self._uid)
        else: return '?%s: %r' % (self._name, self._value)

#Commenting this for now, as yaml isn't part of NLTK.
#Using YAML, you can get some nice, formatted output of these dictionaries
#for free.

import yaml
def variable_representer(dumper, var):
    return dumper.represent_scalar(u'!var', u'?%s' % var.name())
yaml.add_representer(Variable, variable_representer)

def variable_constructor(loader, node):
    value = loader.construct_scalar(node)
    name = value[1:]
    return Variable(name)
yaml.add_constructor(u'!var', variable_constructor)
yaml.add_implicit_resolver(u'!var', re.compile(r'^\?\w+$'))

def _copy_and_bind(feature, bindings, memo=None):
    "Make a deep copy of a feature dictionary. Copy variables, too."
    if memo is None: memo = {}
    if isinstance(feature, Variable):
        if not bindings.has_key(feature.name()):
            bindings[feature.name()] = feature.copy()
        result = bindings[feature.name()]
    else:
        if id(feature) in memo: return memo[id(feature)]
        if isinstance(feature, dict):
            result = {}
            for (key, value) in feature.items():
                result[key] = _copy_and_bind(value, bindings, memo)
        else: result = feature
    memo[id(feature)] = result
    return result

def unify(feature1, feature2, bindings1=None, bindings2=None):
    """
    In general, the 'unify' procedure takes two values, and either returns a
    value that satisfies properties of both or fails.
    
    These values can have any type, but the interesting case is where they
    are dictionaries, in which case they represent feature structures.

    The value 'None' specifies no properties. It acts as the identity.
    >>> unify(3, None)
    3

    >>> unify(None, 'fish')
    'fish'

    A non-dictionary value unifies with itself, but not much else:
    >>> unify(True, True)
    True

    >>> unify([], [])
    []

    >>> unify('a', 'b')
    Traceback (most recent call last):
        ...
    UnificationFailure

    When two dictionaries are unified, any chain of keys that accesses a value
    in either dictionary will access an equivalent or more specific value
    in the unified dictionary. If this is not possible, UnificationFailure
    is raised.

    >>> f1 = dict(A=dict(B='b'))
    >>> f2 = dict(A=dict(C='c'))
    >>> unify(f1, f2) == dict(A=dict(B='b', C='c'))
    True
    
    The empty dictionary specifies no features, It unifies with any dictionary.
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
    binding dictionaries to _unify_ -- one for each feature structure, so
    their variables do not collide.

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
    """
    if bindings1 is None and bindings2 is None:
        bindings1 = {}
        bindings2 = {}
    else:
        if bindings1 is None: bindings1 = {}
        if bindings2 is None: bindings2 = bindings1
    
    copy1, copy2 = (_copy_and_bind(feature1, bindings1),
                   _copy_and_bind(feature2, bindings2))
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
    unified = _nontrivial_unify(feature1, feature2, bindings1, bindings2, memo)
    memo[id(feature1), id(feature2)] = unified
    return unified

def _nontrivial_unify(feature1, feature2, bindings1, bindings2, memo):
    """
    Do the actual work of _destructively_unify when the result isn't memoized.
    """
    if feature1 is None: return feature2
    if feature2 is None: return feature1
    if feature1 is feature2: return feature1
    
    if isinstance(feature1, Variable):
        if isinstance(feature2, Variable):
            return feature1.become(feature2, bindings1, bindings2)
        else:
            feature1.bindValue(feature2, bindings1, bindings2)
            return feature1
    if isinstance(feature2, Variable):
        feature2.bindValue(feature1, bindings2, bindings1)
        return feature2
    
    if not isinstance(feature1, dict):
        if feature1 == feature2: return feature1
        else: 
            raise UnificationFailure
    if not isinstance(feature2, dict): raise UnificationFailure
    
    # At this point, we know they're both dictionaries.
    # Start destroying stuff.

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
    the target of its forward pointer (to preserve reentrancy).
    """
    if not isinstance(feature, dict): return
    if visited.has_key(id(feature)): return
    visited[id(feature)] = True

    for fname, fval in feature.items():
        if isinstance(fval, dict):
            while fval.has_key(_FORWARD):
                fval = fval[_FORWARD]
                feature[fname] = fval
            _apply_forwards(fval, visited)

def _lookup_values(thedict, visited, remove=False):
    if isinstance(thedict, Variable):
        var = thedict
        if remove: return var.value()
        else:
            result = var.value()
            if result is None: return var.forwarded_self()
            else: return result
    if not isinstance(thedict, dict): return thedict
    if visited.has_key(id(thedict)): return thedict
    visited[id(thedict)] = True

    for fname, fval in thedict.items():
        if isinstance(fval, dict):
            _lookup_values(fval, visited)
        elif isinstance(fval, Variable):
            if fval.value() is not None:
                thedict[fname] = fval.value()
                if isinstance(thedict[fname], dict):
                    _lookup_values(thedict[fname], visited)
            else:
                newval = fval.forwarded_self()
                if fval is newval and remove: del thedict[fname]
                else:
                    thedict[fname] = fval.forwarded_self()
    return thedict

def _apply_forwards_to_bindings(bindings):
    for (key, value) in bindings.items():
        if isinstance(value, dict) and value.has_key(_FORWARD):
            while value.has_key(_FORWARD):
                value = value[_FORWARD]
            bindings[key] = value

class FeatureTestCase(unittest.TestCase):
    'Unit testing for the featurelite package'

    def testBasicUnification(self):
        'Basic unification tests'

        f1 = {'number': 'singular'}
        f2 = {}
        self.assertEqual(unify(f1, f2), f1)
        self.assertEqual(unify(f2, f1), f1)
        
        f3 = {'person': 3}
        f4 = {'number': 'singular', 'person': 3}
        self.assertEqual(unify(f1, f3), f4)

        f5 = {'A': {'B': 'b'}}
        f6 = {'A': {'C': 'c'}}
        f7 = {'A': {'B': 'b', 'C': 'c'}}
        self.assertEqual(unify(f5, f6), f7)
        
    def testAtomic(self):
        'Test that non-dictionaries do the right thing'
        self.assertEqual(unify(None, 1), 1)
        self.assertEqual(unify(1, None), 1)
        self.assertEqual(unify([], []), [])
        def badUnify1(): unify('a', 'b')
        def badUnify2(): unify('a', {})
        self.assertRaises(UnificationFailure, badUnify1)
        self.assertRaises(UnificationFailure, badUnify2)

    def testReentrantUnification(self):
        'Reentrant unification tests'
        bb = {'B': 'b'}
        f1 = {'A': bb, 'E': {'F': bb}}
        f2 = {'A': {'C': 'c'}, 'E': {'F': {'D': 'd'}}}
        f3 = {'A': {'B': 'b', 'C': 'c', 'D': 'd'},
              'E': {'F': {'B': 'b', 'C': 'c', 'D': 'd'}}}
        u12 = unify(f1, f2)
        self.assertEquals(u12, f3)
        self.assert_(u12['A'] is u12['E']['F'])

    def testCyclicStructures(self):
        'Cyclic structure tests'
        base = {}
        base2 = {}
        f1 = {'F': base, 'G': base}
        f2 = {'F': {'H': base2}, 'G': base2}
        u12 = unify(f1, f2)

        self.assert_(u12['F'] is u12['G'])
        self.assert_(u12['F'] is u12['G']['H'])
        self.assert_(u12['F'] is u12['G']['H']['H'])

    def testCyclicVariables(self):
        'Cyclic structures with variables'
        x = Variable('x')
        f1 = {'F': {'H': x}}
        f2 = {'F': x}
        u12 = unify(f1, f2, {})
        self.assertEqual(u12['F'], u12['F']['H'])
        self.assertEqual(u12['F'], u12['F']['H']['H'])

    def testVariableMerging(self):
        'Aliased variable tests'
        #self.assert_(isinstance(unify(Variable('x'), Variable('x')),
        #VariableValue))
        f1 = {'a': Variable('x'), 'b': Variable('x')}
        f2 = {'b': Variable('y'), 'c': Variable('y')}
        u12 = unify(f1, f2)
        f3 = {'a': 3, 'b': Variable('y'), 'c': Variable('y')}
        self.assertEqual(u12['a'], u12['b'])
        self.assertEqual(u12['b'], u12['c'])
        unify(f1, f3)
        
    def testAsymmetry(self):
        'Asymmetry in variable merging'
        f1 = {'a': Variable('x'), 'b': True}
        f2 = {'a': False, 'b': Variable('x')}
        u12 = unify(f1, f2)
        self.assertEqual(u12['a'], False)
        self.assertEqual(u12['b'], True)

    def testAsymmetry(self):
        'Asymmetric variable values'
        f1 = {'a': Variable('x'), 'b': True}
        f2 = {'a': False, 'b': Variable('x')}
        u12 = unify(f1, f2)
        f3 = {'a': False, 'b': True}
        self.assertEqual(u12, f3)

def test():
    import doctest
    doctest.testmod()

if __name__ == "__main__":
    test()

