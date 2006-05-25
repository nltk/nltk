"""
featurelite.py - by Rob Speer

Here I'm trying something wacky: having feature structures and binding
structures all represented by Python dictionaries or frozendicts. The only
things that need to be specialized objects are variables.
"""

from copy import copy, deepcopy
import re

class UnificationFailure(Exception): pass

class FORWARD(object):
    """
    FORWARD is a singleton value, used in unification as a flag that a value
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
        self._name = name
        self._value = value
        self._bindings = {}
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
    def bindings(self):
        return self._bindings
    def bindValue(self, value, bindings=None):
        if isinstance(self._value, Variable):
            return self._value.bindValue(value, bindings)
        if bindings is None: bindings = {}
        if self._value is None: self._value = value
        else:
            self._value = unify(self._value, value, self._bindings, bindings)
    def become(self, other):
        other.bindValue(self.value(), self.bindings())
        self._value = other
        return other
        
    def __hash__(self): return hash(self._uid)
    def __cmp__(self, other):
        if not isinstance(other, Variable): return -1
        if isinstance(self._value, Variable): return cmp(self._value, other)
        else: return cmp(self._uid, other._uid)
    def __repr__(self):
        if self._value is None: return '?%s: <%x>' % (self._name, self._uid)
        else: return '?%s: %r' % (self._name, self._value)

#Commenting this for now, as yaml isn't part of NLTK.
#Using YAML, you can get some nice, formatted output of these dictionaries
#for free.
#
#import yaml
#def variable_representer(dumper, var):
#    return dumper.represent_scalar(u'!var', u'?%s' % var.name())
#yaml.add_representer(Variable, variable_representer)
#
#def variable_constructor(loader, node):
#    value = loader.construct_scalar(node)
#    name = value[1:]
#    return Variable(name)
#yaml.add_constructor(u'!var', variable_constructor)
#yaml.add_implicit_resolver(u'!var', re.compile(r'^\?\w+$'))

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
    The main procedure for unifying two values. These values can be anything,
    but the interesting case is where they are dictionaries.

    The value 'None' unifies with anything. It's more general than {}:
    {} unifies with any dictionary, but None unifies with anything at all.
    """
    if bindings1 is None: bindings1 = {}
    if bindings2 is None: bindings2 = bindings1
    
    copy1, copy2 = (_copy_and_bind(feature1, bindings1),
                   _copy_and_bind(feature2, bindings2))
    unified = _destructively_unify(copy1, copy2, bindings1, bindings2, {})

    _apply_forwards_to_bindings(bindings1)
    _apply_forwards_to_bindings(bindings2)
    _apply_forwards(unified, {})
    _apply_bindings(unified, {})

    print feature1, feature2, '=>', unified
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
            return feature1.become(feature2)
        else:
            feature1.bindValue(feature2)
            return feature1
    if isinstance(feature2, Variable):
        feature2.bindValue(feature1)
        return feature2
    
    if not isinstance(feature1, dict):
        if feature1 == feature2: return feature1
        else: raise UnificationFailure
    if not isinstance(feature2, dict): raise UnificationFailure
    
    # At this point, we know they're both dictionaries.
    # Start destroying stuff.

    while feature2.has_key(FORWARD): feature2 = feature2[FORWARD]
    feature2[FORWARD] = feature1
    for (fname, val2) in feature2.items():
        if fname == FORWARD: continue
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
            while fval.has_key(FORWARD):
                fval = fval[FORWARD]
                feature[fname] = fval
            _apply_forwards(fval, visited)

def _apply_bindings(feature, visited):
    if not isinstance(feature, dict): return
    if visited.has_key(id(feature)): return
    visited[id(feature)] = True

    for fname, fval in feature.items():
        if isinstance(fval, dict):
            _apply_bindings(fval, visited)
        elif isinstance(fval, Variable):
            if fval.value() is not None:
                feature[fname] = fval.value()
                if isinstance(feature[fname], dict):
                    _apply_bindings(feature[fname], visited)
            else:
                feature[fname] = fval.forwarded_self()

def _apply_forwards_to_bindings(bindings):
    for (key, value) in bindings.items():
        if isinstance(value, dict) and value.has_key(FORWARD):
            while value.has_key(FORWARD):
                value = value[FORWARD]
            bindings[key] = value

import unittest

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
        f3 = {'F': {}}
        f3['F']['H'] = f3['F']
        f3['G'] = f3['F']

        self.assertEquals(u12, f3)
        self.assert_(u12['F'] is u12['G'])
        self.assert_(u12['F'] is u12['G']['H'])
        self.assert_(u12['F'] is u12['G']['H']['H'])

    def testCyclicVariables(self):
        'Cyclic structures with variables'
        x = Variable('x')
        f1 = {'F': {'H': x}}
        f2 = {'F': x}
        u12 = unify(f1, f2)
        
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
        self.assert_(u12['a'] == u12['b'])
        self.assert_(u12['b'] == u12['c'])
        unify(f1, f3)

def testsuite():
    t1 = unittest.makeSuite(FeatureTestCase)
    return unittest.TestSuite( (t1,) )

def test(verbosity):
    runner = unittest.TextTestRunner(verbosity=verbosity)
    runner.run(testsuite())

if __name__ == '__main__':
    test(verbosity=1)

