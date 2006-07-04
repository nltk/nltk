"""
Overview
========

This module provides data structures for representing first-order
models. A model is a pair M{<D,V>}, where M{D} is a domain of discourse and
M{V} is a valuation function for the non-logical constants of a
first-order language. We assume that the language is based on the
lambda calculus, in the style of Montague grammar.


We assume that non-logical constants are either individual constants
or functors. In particular, rather than interpreting a one-place
predicate M{P} as a set M{S}, we interpret it as the corresponding
characteristic function M{f}, where M{f(a) = True} iff M{a} is in
M{S}. For example, instead of interpreting 'dog' as the set of
individuals M{{'d1', 'd2', 'd3'}}, we interpret it as the function
which maps 'd1', 'd2' and 'd3' to M{True} and every other entity to
M{False}.

Thus, as a first approximation, non-logical constants are interpreted as
follows (note that M{e} is the type of I{entities} and M{t} is the
type of truth values):

  - if M{alpha} is an individual constant, then M{V(alpha)}
    is an element of M{D}.
  - If M{gamma} is a functor of type (M{e} x ... x M{e}) -> M{t}, then
    M{V(gamma)} is a function M{f} from  M{D} x ... x M{D} to M{{True, False}}.

However, since we are basing our language on the lambda calculus (see
L{logic}), a binary relation such as 'like' will not in fact be
associated with the type (M{e} x M{e}) -> M{t}, but rather the type
(M{e} -> (M{e} -> M{t}); i.e., a function from entities to a function
from entities to truth values. In other words, functors are assigned
'Curried' functions as their values. We should also point out that
expressions of our languge are not explicitly typed.  We leave it to
the grammar writer to assign 'sensible' values to expressions rather
than enforcing any type-to-denotation consistency.

Characteristic Functions
========================

Within C{models}, Curried characteristic functions are implemented as
a subclass of dictionaries, using the C{CharFun()} constructor.

   >>> cf = CharFun({'d1' : {'d2': True}, 'd2' : {'d1': True}})
   >>> cf['d1']
   {'d2': True}

Values of a C{CharFun} are accessed by indexing in the usual way:

   >>> cf['d1']['d2']
   True
   >>> cf['not in domain']
   False

In practise, it may be more convenient to specify interpretations as
n-ary relations (i.e., sets of n-tuples) rather than as n-ary
functions. C{CharFun} provides a C{parse()} method which will convert
such relations into Curried characteristic functions:

   >>> s = set([('d1', 'd2'), ('d2', 'd1')])
   >>> cf = CharFun()
   >>> cf.parse(s)
   >>> cf
   {'d2': {'d1': True}, 'd1': {'d2': True}}

C{parse()} will raise an exception if the set is not in fact a
relation (i.e., contains tuples of different lengths:

  >>> wrong = set([('d1', 'd2'), ('d2', 'd1', 'd3')])
  >>> cf.parse(wrong)
  Traceback (most recent call last):
  ...
  ValueError: Set contains sequences of different lengths

However, unary relations can be parsed to characteristic functions.

  >>> unary = set(['d1', 'd2'])
  >>> cf.parse(unary)
  >>> cf
  {'d2': True, 'd1': True}

The function C{flatten} returns a set of the entities used as keys in
a C{CharFun} instance. The same information can be accessed via the
C{domain} attribute of C{CharFun}.

   >>> cf = CharFun({'d1' : {'d2': True}, 'd2' : {'d1': True}})
   >>> flatten(cf)
   set(['d2', 'd1'])
   >>> cf.domain
   set(['d2', 'd1'])

Valuations and Models
=====================

A I{Valuation} is a mapping from non-logical constants to appropriate semantic
values in the model. Valuations are created using the C{Valuation} constructor.

   >>> val = Valuation({'Fido' : 'd1', 'dog' : {'d1' : True, 'd2' : True}})
   >>> val
   {'Fido': 'd1', 'dog': {'d2': True, 'd1': True}}

As with C{CharFun}, C{Valuation} will also parse valuations using
relations rather than characteristic functions as interpretations.

   >>> setval = [('adam', 'b1'), ('betty', 'g1'),\
   ('girl', set(['g2', 'g1'])), ('boy', set(['b1', 'b2'])),\
   ('love', set([('b1', 'g1'), ('b2', 'g2'), ('g1', 'b1'), ('g2', 'b1')]))]
   >>> val = models.Valuation()
   >>> val.parse(setval)
   >>> print val
   {'adam': 'b1',
   'betty': 'g1',
   'boy': {'b1': True, 'b2': True},
   'girl': {'g2': True, 'g1': True},
   'love': {'b1': {'g1': True},
            'b2': {'g2': True},
            'g1': {'b1': True},
            'g2': {'b1': True}}}


Valuations have a C{domain} attribute, like C{CharFun}, and also a C{symbols}
attribute.

   >>> val.domain
   set(['g1', 'g2', 'b2', 'b1'])
   >>> v.symbols
   ['boy', 'girl', 'love', 'adam', 'betty']   

The C{Model} constructor takes two parameters, a C{set} and a C{Valuation}.

   >>> m = Model(val.domain, val)


"""

import logic

from pprint import pformat

class Error(Exception): pass

class CharFun(dict):
    """
    A dictionary which represents a Curried characteristic function.
    """

    def __init__(self, charfun=None):
        dict.__init__(self)
        if charfun:
            self.update(charfun)
 
    def __getitem__(self, key):
        if key in self:
            return dict.__getitem__(self, key)
        else:
            return False
        
    def _isrel(self, s):
        """check whether a set represents a relation (of any arity)"""
        
        assert isinstance(s, set), "Argument is not a set"
        if not isinstance(max(s),tuple) or len(max(s))==len(min(s)):
            return True
        else:
            raise ValueError, "Set contains sequences of different lengths"

    def _item2dict(self, item):
        """
        @return: A characteristic function corresponding to the input.
        @rtype: C{CharFun}
        @param item: a literal or a tuple
        """
        
        chf = {}
        if isinstance(item, tuple):
            if len(item)==1:
                chf[item[0]] = True
            elif len(item) > 1:
                chf[item[0]] = self._item2dict(item[1:])
        else:
            chf[item] = True
        return chf


    def _merge(self, chf1, chf2):
        k = chf2.keys()[0]
        if k not in chf1:
            chf1.update(chf2)
        else:
            self._merge(chf1[k], chf2[k])
        return chf1
        
    def parse(self, s):
        """
        Convert an n-ary relation into its corresponding characteristic function.
        @rtype: C{CharFun}
        @type s: set
        """

        assert self._isrel(s)

        charfuns = []
        for item in s:
            charfuns.append(self._item2dict(item))
            
        chf = reduce(self._merge, charfuns)
        self.update(chf)

        
    def _getDomain(self):
        return flatten(self)

    domain = property(_getDomain, doc='Set-theoretic domain of a curried function')



def flatten(value):
    """
    @return: The set of keys of a C{CharFun} instance.
    @rtype: set
    @type value: dict
    """
    
    flat = []
    try:
        flat.extend(value.keys())
        for v in value.values():
            if isinstance(v, dict):
                flat.extend(flatten(v))
            else:
                flat.append(v)
    except AttributeError:
        flat.append(value)

    result = set(flat)
    result.discard(True)
    return result

class Valuation(dict):
    """
    A dictionary which represents a model-theoretic Valuation of non-logical constants.
    """

    def __init__(self, valuation=None):
        dict.__init__(self)
        if valuation:
            self.update(valuation)

    def parse(self, seq):
        """
        Parse a list such as  C{[('j', 'b1'), ('girl', set(['g1', 'g2']))]} into a C{Valuation}.
        @rtype: C{Valuation}
        @param seq: A list of tuples of the form (I{constant}, I{relation}), where I{relation} is a set of tuples.
        """
        d = dict(seq)
        for k in d.keys():
            val = d[k]
            if isinstance(val, str):
                pass
            else:
                cf = CharFun()
                cf.parse(d[k])        
                d[k] = cf
        self.update(d)

    def __str__(self):
        return pformat(self)
        
    def _getDomain(self):
        dom = set()
        for v in self.values():
            flat = flatten(v)
            dom = dom.union(flat)
        return dom

    domain = property(_getDomain,
             doc='Set-theoretic domain of the value-space of a Valuation')

    def _getSymbols(self):
        return self.keys()

    symbols = property(_getSymbols,
              doc='The non-logical constants which the Valuation applies to')


class Assignment(dict):
    """
    A dictionary which represents an assignment of values to variables..
    """

    def __init__(self, assignment=None):
        dict.__init__(self)
        if assignment:
            self.update(assignment)

    def add(self, pair):
        """Add a new variable-value pair to the assignment"""
        
        self[pair[0]] = pair[1]
        
    
class Model:
    """A first order model is a domain M{D} of discourse and a valuation M{V}.

    A domain M{D} is a set, and a valuation M{V} is a map that associates
    expressions with values in the model.
    The domain of M{V} should be a subset of M{D}."""

    
    
    def __init__(self, domain, valuation):
        assert isinstance(domain, set)
#        assert isinstance(valuation, __main__.Valuation)
        self.domain = domain
        self.valuation = valuation
        if not domain.issuperset(valuation.domain):
            raise Error, "The domain of the valuation, %s, should be a subset of the model's domain, %s" % (valuation.domain, domain)

        
    def __repr__(self):
        return "(%r, %r)" % (self.domain, self.valuation)

    def __str__(self):
        return "Domain = %s,\nValuation = \n%s" % (self.domain, self.valuation)

    def satisfy(self, expr, g):
        """
        Recursive interpretation function for a formula of first-order logic.

        @return: Returns a truth value
        @param fmla: An expression of L{logic}. 
        
        """

        try:
            first, second = decompose(expr)

            if first == 'and':
                phi = second[0]
                psi = second[1]
                return self.satisfy(phi, g) and self.satisfy(psi, g)

        except ValueError:
            return self.i(expr, g)
        
##         if isinstance(phi, logic.ApplicationExpression):
##             fun = phi.first.name()
##             repr(fun)
##             arg = phi.second.name()
##             repr(arg)
##             funsem = self.valuation[fun]
##             argsem = self.valuation[arg]
##             result = funsem[argsem]
##         else: print 'failed to parse'
##         print result

    def i(self, expr, g):
        """
        An interpretation function.

        Assuming that C{expr} is atomic, M{i} calls M{V} if
        C{expr} is a non-logical constant, and M{g} if C{expr}
        is a free variable.
        @param expr: C{Expression} from L{logic}
        @param g: C{Assignment}
        @return: a semantic value
        """
        try:
            return self.valuation[expr]
        except KeyError:
            try:
                return g[expr]
            except KeyError:
                print "Sorry, expression '%s' can't be evaluated." % expr


def decompose(expr):
    """
    Function to communicate with a first-order functional language.

    This function tries to make weak assumptions about the parse structure
    provided by the logic module.

    The (binder, body) pair is for decomposing quantifier formulae.
    The (op, args) pair is for decomposing formulae with a boolean operator.
    The (fun, args) pair should catch other relevant cases.

    @param expr: A string representation of a first-order formula.
    """

    parsed = logic.Parser().parse(expr)
    try:
        first, second = parsed.binder, parsed.body
        return (first, second)
    except AttributeError:
        pass
    try: 
        first, second = parsed.op, parsed.args
        return (first, second)
    except AttributeError:
        pass
    try: 
        first, second = parsed.fun, parsed.args
        return (first, second)
    except (AttributeError, TypeError):
        return expr

#//////////////////////////////////////////////////////////////////////
# TESTING...
#//////////////////////////////////////////////////////////////////////

import unittest

class TestModels(unittest.TestCase):

    def testLogicSelectors(self):
        'Tests for properties of formulae from C{logic}.'

        # Existential quantification
        pair = decompose('some x.(M N)')
        self.assertEqual(pair[0], ('some', 'x'))
        self.assertEqual(pair[1], '(M N)')

        # Universal quantification
        pair = decompose('all x.(M N)')
        self.assertEqual(pair[0], ('all', 'x'))
        self.assertEqual(pair[1], '(M N)')


        # Boolean operators
        pair = decompose('(and (M N) (P Q))')
        self.assertEqual(pair[0], 'and')
        self.assertEqual(pair[1], ['(M N)', '(P Q)'])

        pair = decompose('(not M N P Q)')
        self.assertEqual(pair[0], 'not')
        self.assertEqual(pair[1], ['M', 'N', 'P', 'Q'])


def testsuite():
    suite = unittest.makeSuite(TestModels)
    return unittest.TestSuite(suite)

def test(verbosity):
    runner = unittest.TextTestRunner(verbosity=verbosity)
    runner.run(testsuite())
        
       
        
#//////////////////////////////////////////////////////////////////////
# Demo..
#//////////////////////////////////////////////////////////////////////        

    
def demo():
    """Trivial example of a model."""
    val = Valuation({'p': True, 'q': True, 'r': False})
    v = [('j', 'b1'), ('m', 'g1'),\
         ('girl', set(['g1', 'g2'])), ('boy', set(['b1', 'b2'])),\
         ('love', set([('b1', 'g1'), ('b2', 'g2'), ('g1', 'b1'), ('g2', 'b1'),]))]
    val.parse(v)
    dom = val.domain
    m = Model(dom, val)
    print "*****************************"
    print m
    print "*****************************"
    g = Assignment()
    p = 'p'
    q = 'q'
    r = 'r'
    sent1 = '(and p q)'
    sent2 = '(and p r)'
    
    print "The value of '%s' is: %s" % (p, m.satisfy(p, g))
    print "The value of '%s' is: %s" % (q, m.satisfy(q, g))
    print "The value of '%s' is: %s" % (r, m.satisfy(r, g))
    print "The value of '%s' is: %s" % (sent1, m.satisfy(sent1, g))
    print "The value of '%s' is: %s" % (sent2, m.satisfy(sent2, g))
    print "*****************************\n"
    



if __name__ == "__main__":
    demo()
    test(verbosity=2) 
        
        
        
