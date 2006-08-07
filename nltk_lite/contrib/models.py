# Natural Language Toolkit: Models
#
# Copyright (C) 2001-2006 University of Pennsylvania
# Author: Ewan Klein <ewan@inf.ed.ac.uk>,
# URL: <http://nltk.sourceforge.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
Overview
========

This module provides data structures for representing first-order
models. A model is a pair M{<D,V>}, where M{D} is a domain of discourse and
M{V} is a valuation function for the non-logical constants of a
first-order language. We assume that the language is based on the
lambda calculus, in the style of Montague grammar.


We also assume that non-logical constants are either individual constants
or functors. In particular, rather than interpreting a one-place
predicate M{P} as a set M{S}, we interpret it as the corresponding
characteristic function M{f}, where M{f(a) = True} iff M{a} is in
M{S}. For example, instead of interpreting 'dog' as the set of
individuals M{{'d1', 'd2', 'd3'}}, we interpret it as the function
which maps 'd1', 'd2' and 'd3' to M{True} and every other entity to
M{False}.

Thus, as a first approximation, non-logical constants are interpreted
by the valuation M{V} as follows (note that M{e} is the type of
I{entities} and M{t} is the type of truth values):

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

   >>> cf = CharFun({'d1' : CharFun({'d2': True}), 'd2' : CharFun({'d1': True})})

Values of a C{CharFun} are accessed by indexing in the usual way:

   >>> cf['d1']
   {'d2': True}
   >>> cf['d1']['d2']
   True

C{CharFun}s are 'sparse' data structures in the sense that they omit
entries of the form C{e: False}. In fact, they
behave just like ordinary dictionaries on keys which are
out of their domain, rather than yielding the value C{False}:

   >>> cf['not in domain']
   Traceback (most recent call last):
   ...
   KeyError: 'not in domain'

The assignment of C{False} values is delegated to a wrapper method
C{app} of the C{Model} class; e.g., where C{m} is an instance of C{Model}:

   >>> m.app(cf,'not in domain')
   False

C{app()} embodies the Closed World assumption. (It might be asked why
we don't modify instances of C{CharFun} to give the value C{False} in
place of a C{KeyError} for some entity 'd3' which is not a key for the
dictionary. The reason is that this would implement a behaviour
equivalent to C{cf2} below, which yields C{False} for the entity 'd3'
rather than a function which yields C{False} for every entity in the
domain: C{cf2 = {'d1': {'d2': True}, {'d3': False}}}.)

In practise, it will often be more convenient for a user to specify interpretations as
n-ary relations (i.e., sets of n-tuples) rather than as n-ary
functions. C{CharFun} provides a C{parse()} method which will convert
such relations into Curried characteristic functions:

   >>> s = set([('d1', 'd2'), ('d3', 'd4')])
   >>> cf = CharFun()
   >>> cf.parse(s)
   >>> cf
   {'d2': {'d1': True}, 'd4': {'d3': True}}


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

Valuations and Assignments
==========================

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
   >>> val = Valuation()
   >>> val.parse(setval)
   >>> print val
   {'adam': 'b1',
   'betty': 'g1',
   'boy': {'b1': True, 'b2': True},
   'girl': {'g2': True, 'g1': True},
   'love': {'b1': {'g2': True, 'g1': True},
            'g1': {'b1': True},
            'g2': {'b2': True}}}

Valuations have a C{domain} attribute, like C{CharFun}, and also a C{symbols}
attribute.

   >>> val.domain
   set(['g1', 'g2', 'b2', 'b1'])
   >>> val.symbols
   ['boy', 'girl', 'love', 'adam', 'betty']   


A variable I{Assignment} is a mapping from individual variables to
entities in the domain. Individual variables are indicated with the
letters 'x', 'y', 'w' and 'z', optionally followed by an integer
(e.g., 'x0', 'y332').  Assignments are created using the C{Assignment}
constructor, which also takes the domain as a parameter.

   >>> dom = set(['u1', 'u2', 'u3', 'u4'])
   >>> g = Assignment(dom, {'x': 'u1', 'y': 'u2'})
   >>> g
   {'y': 'u2', 'x': 'u1'}

There is also a print format for assignments which uses a notation
closer to that in logic textbooks:
   
   >>> print g
   g[u2/y][u1/x]

Initialization of an C{Assignment} instance checks that the variable
really is an individual variable and also that the value belongs to
the domain of discourse:

    >>> Assignment(dom, {'xxx': 'u1', 'y': 'u2'})
    Traceback (most recent call last):
    ...
    AssertionError: Wrong format for an Individual Variable: 'xxx'
    >>> Assignment(dom, {'x': 'u5', 'y': 'u2'})
    Traceback (most recent call last):
    ...
    AssertionError: 'u5' is not in the domain: set(['u4', 'u1', 'u3', 'u2'])

It is also possible to update an assignment using the C{add()} method:

    >>> dom = set(['u1', 'u2', 'u3', 'u4'])
    >>> g = models.Assignment(dom, {})
    >>> g.add('u1', 'x')
    {'x': 'u1'}
    >>> g.add('u5', 'x')
    Traceback (most recent call last):
    ...
    AssertionError: u5 is not in the domain set(['u4', 'u1', 'u3', 'u2'])
    >>> g.add('u1', 'xyz')
    Traceback (most recent call last):
    ...
    AssertionError: Wrong format for an Individual Variable: 'xyz'
    >>> g.add('u2', 'x').add('u3', 'y').add('u4', 'x0')
    {'y': 'u3', 'x': 'u2', 'x0': 'u4'}

Variables (and their values) can be selectively removed from an
assignment with the C{purge()} method:

    >>> g
    {'y': 'u3', 'x': 'u2', 'x0': 'u4'}
    >>> g.purge('x')
    >>> g
    {'y': 'u3', 'x0': 'u4'}

With no arguments,  C{purge()} is equivalent to C{clear()} on a dictionary:

    >>> g.purge()
    >>> g
    {}




Models
======

The C{Model} constructor takes two parameters, a C{set} and a C{Valuation}.

   >>> m = Model(val.domain, val)

The top-level method of a C{Model} instance is C{evaluate()}, which
assigns a semantic value to expressions of the L{logic} module, under an assignment C{g}:

    >>> m.evaluate('all x. ((boy x) implies (not (girl x)))', g)
    True

C{evaluate} calls a recursive function C{satisfy()}, which in turn
calls a function C{i} to interpret non-logical constants and
individual variables. C{i} in turn first tries to call the model's C{Valuation} and
if that fails, calls the variable assignment C{g}. Any atomic expression which cannot be
assigned a value by C{i} raises an C{Undefined} exception; this is
caught by C{evaluate()}, which returns the string 'Undefined'.

    >>> m.evaluate('(walk adam)', g, trace=2)
       ... assuming that 'walk' is an individual variable
    Expression 'walk' can't be evaluated by i and g.
    'Undefined'

Boolean operators such as M{not}, M{qand} and M{implies} are implemented as dictionaries. For example:

    >>> m.AND
    {False: {False: False, True: False}, True: {False: False, True: True}}

A formula such as '(p and q)' is interpreted by indexing
the value of 'and' with the values of the two propositional arguments,
in the following manner:

   >>> m.AND[m.evaluate('p', g)][m.evaluate('q', g)]






"""

#from nltk_lite.contrib import logic
import logic
from pprint import pformat

class Error(Exception): pass

class Undefined(Error): pass

class CharFun(dict):
    """
    A dictionary which represents a Curried characteristic function.
    """

    def __init__(self, charfun=None):
        dict.__init__(self)
        if charfun:
            #assert isinstance(charfun, dict)
            self.update(charfun)
 
        
    def _isrel(self, s):
        """Check whether a set represents a relation (of any arity)."""
        
        assert isinstance(s, set), "Argument is not a set"
        if len(s) == 0:
            return True
        elif not isinstance(max(s),tuple) or len(max(s))==len(min(s)):
            return True
        else:
            raise ValueError, "Set contains sequences of different lengths"

    def _item2dict(self, item):
        """
        Given an input such as the triple ('a', 'b', 'c'), return the C{CharFun}
        {'c': {'b': {'a' : True}}}
        
        @return: A characteristic function corresponding to the input.
        @rtype: C{CharFun}
        @param item: a literal or a tuple
        """
        
        chf = {}
        if isinstance(item, tuple):
            # reverse the tuple
            l = list(item)
            l.reverse()
            item = tuple(l)
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
            
        chf = reduce(self._merge, charfuns, {})
        self.update(chf)

    def tuples(self):
        """
        Convert a C{CharFun} back into a set of tuples.

        Given an input such as the C{CharFun} {'c': {'b': {'a': True}}},
        return set([('a', 'b', 'c')])
        """
        n = depth(self)
        if n == 1:
            tuples = self.domain
        elif n == 2:
            tuples = [(k2, k1) for k1 in self.keys() for k2 in self[k1].keys()]
        elif n == 3:
            tuples = [(k3, k2, k1) for k1 in self.keys() for k2 in self[k1].keys() for k3 in self[k1][k2].keys()]
        else:
            raise Error, "Only defined for CharFuns of depth <= 3"
        result = set(tuples)
        return result
        
    def _getDomain(self):
        return flatten(self)

    domain = property(_getDomain, doc='Set-theoretic domain of a curried function')

    

def flatten(d):
    """
    @return: The set of keys of a C{CharFun} instance.
    @rtype: set
    @type d: dict
    """
    flat = []
    try:
        flat.extend(d.keys())
        for v in d.values():
            if isinstance(v, dict):
                flat.extend(flatten(v))
            else:
                flat.append(v)
    except AttributeError:
        flat.append(d)
    result = set(flat)
    result.discard(True)
    return result


def depth(cf):
    """
    Calculate the depth of a C{CharFun}.

    @return: Int
    @type cf: C{CharFun}
    """
    if True in cf.values():
        return 1
    else:
        key = cf.keys()[0]
        return 1+depth(cf[key])
    

class Valuation(dict):
    """
    A dictionary which represents a model-theoretic Valuation of non-logical constants.

    
    An attempt to initialize a C{Valuation} with an individual
    variable expression (e.g., 'x3') will raise an error, as will an
    attemp to parse a list containing an individual variable
    expression.
    
    An instance of C{Valuation} will raise a KeyError exception (i.e.,
    just behave like a standard  dictionary) if indexed with an expression that
    is not in its list of symbols.
    """
    def __init__(self, valuation=None):
        dict.__init__(self)
        if valuation:
            for k in valuation.keys():
                if logic.is_indvar(k):
                    raise Error, "This looks like an individual variable: '%s'" % k
                # Check if the valuation is of the form {'p': True}
                if isinstance(valuation[k], bool):
                    self[k] = valuation[k]
                else:
                    try:
                        cf = CharFun(valuation[k])
                        self[k] = cf
                    except (TypeError, ValueError):
                        self[k] = valuation[k]

    def __getitem__(self, key):
        if key in self:
            return dict.__getitem__(self, key)
        else:
            raise Undefined,  "Unknown expression: '%s'" % key
                    
    def parse(self, seq):
        """
        Parse a list such as  C{[('j', 'b1'), ('girl', set(['g1', 'g2']))]} into a C{Valuation}.
        @rtype: C{Valuation}
        @param seq: A list of tuples of the form (I{constant}, I{relation}), where I{relation} is a set of tuples.
        """
        d = dict(seq)
        for k in d.keys():
            if logic.is_indvar(k):
                raise Error, "This looks like an individual variable: '%s'" % k
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
             doc='Set-theoretic domain of the value-space of a Valuation.')

    def _getSymbols(self):
        return self.keys()

    symbols = property(_getSymbols,
              doc='The non-logical constants which the Valuation recognizes.')


class Assignment(dict):
    """
    A dictionary which represents an assignment of values to variables.

    An assigment can only assign values from its domain.

    Although an assignment M{g} is finite, it is not I{partial}, in
    the following sense: if a variable M{x} is not one of M{g}'s keys,
    M{g} will choose an arbitrary member of the model's domain and use
    that as the value of M{x}. A downside of this approach is that if
    a unknown expression M{a} is passed to a model M{M}'s
    interpretation function M{i}, M{i} will first check whether M{M}'s
    valuation assigns an interpretation to M{a} as a constant, and if
    this fails, M{i} will delegate the interpretation of M{a} to
    M{g}. Since we have no way at present of telling whether M{a} is
    in fact an individual variable, the behaviour of M{g} just
    described will by default treat it as one.  An alternative would
    be to raise an exception in this case.
    """
    def __init__(self, domain, assignment=None):
        dict.__init__(self)
        self.domain = domain
        if assignment:
            for var in assignment.keys():
                val = assignment[var]
                assert val in self.domain,\
                       "'%s' is not in the domain: %s" % (val, self.domain)
                assert logic.is_indvar(var),\
                       "Wrong format for an Individual Variable: '%s'" % var
            self.update(assignment)
        self._addvariant()

    def __getitem__(self, key):
        if key in self:
            return dict.__getitem__(self, key)
        else:
            raise Undefined, "Unknown expression: '%s'" % key
        
    def purge(self, var=None):
        """
        Remove one or all keys (i.e. logic variables) from an
        assignment, and update C{self.variant}.

        @param var: a Variable acting as a key for the assignment.
        """
        if var:
            val = self[var]
            del self[var]
        else:
            self.clear()
        self._addvariant()
        return None

    def __str__(self):
        """
        Pretty printing for assignments. {'x', 'u'} appears as 'g[u/x]'
        """
        gstring = "g"
        for (val, var) in self.variant:
            gstring = gstring + "[" + str(val) + "/" + str(var) + "]"
        return gstring

    def _addvariant(self):
        """
        Create a more pretty-printable version of the assignment.
        """
        list = []
        for item in self.items():
            pair = (item[1], item[0])
            list.append(pair)
        self.variant = list
        return None

    def add(self, val, var):
        """
        Add a new variable-value pair to the assignment, and update
        C{self.variant}.

        We write the arguments in the order 'val, var' by analogy with the
        notation 'g[u/x]'.
        """
        assert val in self.domain,\
               "%s is not in the domain %s" % (val, self.domain)
        assert logic.is_indvar(var),\
               "Wrong format for an Individual Variable: '%s'" % var
        self[var] = val
        self._addvariant()
        return self

    
class Model:
    """
    A first order model is a domain M{D} of discourse and a valuation M{V}.

    A domain M{D} is a set, and a valuation M{V} is a map that associates
    expressions with values in the model.
    The domain of M{V} should be a subset of M{D}.

    @param prop: If this is set, then we are building a propositional\
    model and don't require the domain of M{V} to be subset of M{D}.
    """
    
    def __init__(self, domain, valuation, prop=None):
        assert isinstance(domain, set)
        self.domain = domain
        self.valuation = valuation
        if prop is None:
            if not domain.issuperset(valuation.domain):
                raise Error,\
                "The valuation domain, %s, must be a subset of the model's domain, %s"\
                % (valuation.domain, domain)

        
    def __repr__(self):
        return "(%r, %r)" % (self.domain, self.valuation)

    def __str__(self):
        return "Domain = %s,\nValuation = \n%s" % (self.domain, self.valuation)

    def app(self, fun, arg):
        """
        Wrapper for handling KeyErrors and TypeErrors raised by
        function application.
        
        This constrains instances of C{CharFun} to return C{False} in
        the right circumstances.

        @param fun: an instance of CharFun
        @param arg: an arbitrary object
        @return: If C{arg} is in C{fun}'s domain, then returns C{fun[arg]},\
                 else if C{arg} is in C{self.domain}, returns C{False},\
                 else raises\
                 Undefined.
        """
        
        try:
            return fun[arg]
        except KeyError:
            if arg in self.domain:
                return False
            else:
                raise Undefined,\
                      "%s can't be applied as a function to %s" % (fun, arg)
        except TypeError:
            if fun == False:
                return False
            else:
                raise Undefined,\
                      "%s can't be applied as a function to %s" % (fun, arg)
            


    NOT =      {True: False, False: True}
    AND =      {True: {True: True, False: False},
                False: {True: False, False: False}}
    OR =       {True: {True: True, False: True},
                False: {True: True, False: False}}
    IMPLIES =  {True: {True: True, False: False},
                False: {True: True, False: True}}
    IFF =      {True: {True: True, False: False},
                False: {True: False, False: True}}
    

    def evaluate(self, expr, g, trace=None):
        """
        Provides a handler for C{satisfy()}
        that blocks further propagation of C{Undefined} error.
        """
        try:
            value = self.satisfy(expr, g, trace=trace)
            if trace:
                 print "'%s' evaluates to %s under M, %s" %  (expr, value, g)
            return value
        except Undefined:
            return 'Undefined'
        


    def satisfy(self, expr, g, trace=None):
        """
        Recursive interpretation function for a formula of first-order logic.

        Raises an C{Undefined} error when C{expr} is an atomic string
        but is not a symbol or an individual variable.

        @return: Returns a truth value or C{Undefined} if C{expr} is\
        complex, and calls the interpretation function C{i} if C{expr}\
        is atomic.
        
        @param expr: An expression of L{logic}.
        """

        OPS = {'and': Model.AND,
               'or': Model.OR,
               'implies': Model.IMPLIES,
               'iff': Model.IFF}

        try:
            parsed = self.decompose(expr)
            # expr is a variable or constant; we don't want to decompose it further
            if isinstance(parsed, str):
                return self.i(expr, g, trace)
            # parsed is a pair of strings
            else:
                first, second = parsed
                # maybe _first_ is an operator like 'and', 'not' or '=' and _second_ is a list of args
                phi = second[0]
                try:
                    psi = second[1]
                # second can't be decomposed further
                except IndexError:
                    pass

                if first == 'not':
                    if trace:
                        print "    '%s' evaluates to %s under M, %s." % (phi, self.satisfy(phi, g), g)
                    return not self.satisfy(phi, g, trace)

                elif first in OPS:
                    value = OPS[first][self.satisfy(phi, g, trace)][self.satisfy(psi, g, trace)]
                    if trace:
                        print "   '%s' evaluates to %s under M, %s" %  (phi, self.satisfy(phi, g, trace), g)
                        print "   '%s' evaluates to %s under M, %s" %  (psi, self.satisfy(psi, g, trace), g)
                    return value

                elif first == '=':
                    value = (self.satisfy(phi, g, trace) == self.satisfy(psi, g, trace))
                    if trace:
                        print "   '%s' evaluates to %s under M, %s" %  (phi, self.satisfy(phi, g, trace), g)
                        print "   '%s' evaluates to %s under M, %s" %  (psi, self.satisfy(psi, g, trace), g)
                    return value

                
                # _first_ is something like 'some x' and _second_ is something like '(boy x)'
                elif first[0] == 'some':
                    var = first[1]
                    phi = second
                    sat = self.satisfiers(phi, var, g, trace, nesting=1)
                    value = len(sat) > 0
                    if trace:
                        if value:
                            print "   '%s' evaluates to %s under M, %s" %  (phi, value, g)
                            if trace > 1:
                                print "    satisfiers of %s under %s are %s" % (phi, g, sat)
                        else:
                            print "   '%s' evaluates to %s under M, %s" %  (phi, value, g)
                            if trace > 1:
                                print "    satisfiers of %s under %s are %s" % (phi, g, sat)
                    return value

                elif first[0] == 'all':
                    var = first[1]
                    phi = second
                    sat = self.satisfiers(phi, var, g, trace, nesting=1)
                    value = self.domain.issubset(sat)
                    if trace:
                        if value:
                            print "   '%s' evaluates to %s under M, %s" %  (phi, self.satisfy(phi, g, trace), g)
                        else:
                            notphi = '(not %s)' % phi
                            witness = self.satisfiers(notphi, var, g).pop()
                            g.add(witness, var)
                            print "   '%s' evaluates to %s under M, %s" %  (phi, self.satisfy(phi, g, trace), g)

                    return value
                
                # maybe _first_ is something like 'boy' and _second_ is an argument expression like 'x'
                else:
                    try:
                        funval = self.satisfy(first, g, trace)
                        argval =  self.satisfy(second, g, trace)
                        app = self.app(funval, argval)
                        if trace > 1:
                            print "'%s': %s applied to %s yields %s"\
                            %  (expr, funval, argval, app)
                        return app
                    # we can't get a proper interpretation
                    except TypeError:
                        print "The interpretation of %s cannot be applied to the interpretation of %s"\
                              % (first, second)
                        print "'%s': %s applied to %s yields %s"\
                            %  (expr, funval, argval, app)
                        raise

        except ValueError:
             raise Undefined, "Cannot parse %s", expr
        


    def i(self, expr, g, trace=False):
        """
        An interpretation function.

        Assuming that C{expr} is atomic:

         - if C{expr} is a non-logical constant, calls the valuation M{V} 
         - else if C{expr} is an individual variable, calls assignment M{g}
         - else returns C{Undefined}.

        
        @param expr: C{Expression} from L{logic}
        @param g: C{Assignment}
        @return: a semantic value
        """
        try:
            if trace > 1:
                print "   i, %s('%s') = %s" % (g, expr, self.valuation[expr])
            # expr is a non-logical constant, i.e., in self.valuation.symbols
            return self.valuation[expr]
        except Undefined:
            if trace > 1:
                print "   ... assuming that '%s' is an individual variable" % expr
            pass
        try:
            if trace > 1:
                print "   i, %s('%s') = %s" % (g, expr, g[expr])
            # expr wasn't a constant; maybe a variable that g knows about?
            return g[expr]
        # We should only get to this point if expr is not an
        # individual variable or not assigned a value by g
        except Undefined:
            if trace:
                print "Expression '%s' can't be evaluated by i and %s." % (expr, g)
            raise

    def freevar(self, var, expr):
        """
        Is C{var} one of the free variables in C{expr}?

        @return: Boolean
        """
        parsed = logic.Parser().parse(expr)
        variable = logic.Variable(var)
        return variable in parsed.free()
        
    def satisfiers(self, expr, var, g, trace=False, nesting=0):
        """
        Show the entities from the model's domain that satisfy an open formula.

        @param expr: the open formula
        @param var: the relevant free variable in C{expr}
        @param g: the variable assignment
        @rtype: set
        """

        spacer = '   '
        indent = spacer + (spacer * nesting)
        candidates = []
        
        if self.freevar(var, expr):
            if trace:
                print
                print (spacer * nesting) + "Open formula is '%s' with assignment %s" % (expr, g)
            for u in self.domain:
                g.add(u, var)
                if trace > 1:
                    lowtrace = trace-1
                else:
                    lowtrace = 0
                value = self.satisfy(expr, g, lowtrace)
                
                if trace:
                    print indent + "...trying assignment %s" % g
                    
                # expr == False under g[u/var]?
                if value == False:
                    if trace:
                        print  indent + "value of '%s' under %s is False" % (expr, g)
                    #g.purge(var)
                    
                # so g[u/var] is a satisfying assignment
                else:
                    candidates.append(u)
                    if trace:
                        print indent + "value of '%s' under %s is %s" % (expr, g, value)
                    
            result = set(candidates)

        # var isn't free in expr
        else:
            raise Undefined, "%s is not free in %s" % (var, expr)

        return result


    def decompose(self, expr):
        """
        Function to communicate with a first-order functional language.

        This function tries to make weak assumptions about the parse structure
        provided by the logic module.

        The (binder, body) pair is for decomposing quantifier formulae.
        The (op, args) pair is for decomposing formulae with a boolean operator.
        The (fun, args) pair should catch other relevant cases.

        @param expr: A string representation of a first-order formula.
        """

        parsed = logic.Parser(constants=self.valuation.symbols).parse(expr)
        try:
            first, second = parsed.binder, parsed.body
            #print 'first is %s, second is %s' % (first, second)
            return (first, second)
        except AttributeError:
            pass
        try: 
            first, second = parsed.op, parsed.args
            #print 'first is %s, second is %s' % (first, second)
            return (first, second)
        except AttributeError:
            pass
        try: 
            first, second = str(parsed.first), str(parsed.second)
            #print 'first is %s, second is %s' % (first, second)
            return (first, second)
        except (AttributeError, TypeError):
            return expr

#//////////////////////////////////////////////////////////////////////
# TESTING
#//////////////////////////////////////////////////////////////////////

import unittest

class TestModels(unittest.TestCase):

    def testLogicSelectors(self):
        "Tests for properties of formulae from 'logic' module."
        v = Valuation()
        m = Model(set([]), v)

        # Existential quantification
        pair = m.decompose('some x.(M N)')
        self.assertEqual(pair[0], ('some', 'x'))
        self.assertEqual(pair[1], '(M N)')

        # Universal quantification
        pair = m.decompose('all x.(M N)')
        self.assertEqual(pair[0], ('all', 'x'))
        self.assertEqual(pair[1], '(M N)')

        # Boolean operators
        pair = m.decompose('(and (M N) (P Q))')
        self.assertEqual(pair[0], 'and')
        self.assertEqual(pair[1], ['(M N)', '(P Q)'])

        pair = m.decompose('(not M N P Q)')
        self.assertEqual(pair[0], 'not')
        self.assertEqual(pair[1], ['M', 'N', 'P', 'Q'])

        # Just an application expression
        pair = m.decompose('(M N P)')
        self.assertEqual(pair[0], '(M N)')
        self.assertEqual(pair[1], 'P')
        

    def testValuations(self):
        "Tests for characteristic functions and valuations."
        cf = CharFun({'d1' : {'d1': True, 'd2': True}, 'd2' : {'d1': True}})
 

        self.assertEqual(cf['d1'], {'d1': True, 'd2': True})
        self.assertEqual(cf['d1']['d2'], True)
        # doesn't work since cf not called on 'foo'
        ## self.assertRaises(KeyError, cf['foo'])
        ## self.assertRaises(KeyError, cf['d1']['foo'])

        self.assertEqual(flatten(cf), set(['d1', 'd2']))
        self.assertEqual(flatten(cf), cf.domain)


        s1 = set([('d1', 'd2'), ('d1', 'd1'), ('d2', 'd1')])
        cf1 = CharFun()
        cf1.parse(s1)
        self.assertEqual(cf, cf1)
        
        self.assertEqual(cf1.tuples(), s1)
        
        s2 = set([('d1', 'd2'), ('d1', 'd2'), ('d1', 'd1'), ('d2', 'd1')])
        cf2 = CharFun()
        cf2.parse(s2)
        self.assertEqual(cf1, cf2)

        unary = set(['d1', 'd2'])
        cf.parse(unary)
        self.assertEqual(cf, {'d2': True, 'd1': True})

        wrong = set([('d1', 'd2'), ('d2', 'd1', 'd3')])
        self.assertRaises(ValueError, cf.parse, wrong)

        val = Valuation({'Fido' : 'd1', 'dog' : {'d1' : True, 'd2' : True}})
        self.assertEqual(val['dog'], cf)
        self.assertEqual(val['dog'][val['Fido']], True)
        self.assertEqual(val.domain, set(['d1', 'd2']))
        self.assertEqual(val.symbols, ['Fido', 'dog'])
        
        setval = [('Fido', 'd1'), ('dog', set(['d1', 'd2']))]
        val1 = Valuation()
        val1.parse(setval)
        self.assertEqual(val, val1)

        val1 = Valuation({'love': {'g1': {'b1': True}, 'b1': {'g1': True}, 'b2': {'g2': True}, 'g2': {'b1': True}}})
        love1 = val1['love']
        relation = set([('b1', 'g1'),  ('g1', 'b1'), ('g2', 'b2'), ('b1', 'g2')])
        self.assertEqual(love1.tuples(), relation)
        val2 = Valuation()
        val2.parse([('love', set([('b1', 'g1'), ('g1', 'b1'), ('g2', 'b2'), ('b1', 'g2')]))])
        love2 = val2['love']
        self.assertEqual(love1.tuples(), love2.tuples())
                        

    def testFunArgApp(self):
        "Tests for function argument application in a Model"
        val = Valuation()
        v = [('adam', 'b1'), ('betty', 'g1'), ('fido', 'd1'),\
             ('girl', set(['g1', 'g2'])), ('boy', set(['b1', 'b2'])), ('dog', set(['d1'])),
             ('love', set([('b1', 'g1'), ('b2', 'g2'), ('g1', 'b1'), ('g2', 'b1')]))]
        val.parse(v)
        dom = val.domain
        m = Model(dom, val)
        g = Assignment(dom)

        self.assertEqual(m.app(val['boy'], 'b1'), True)
        self.assertEqual(m.app(val['boy'], 'g1'), False)
        self.assertRaises(Undefined, m.app, val['boy'], 'foo')
        

    def testBBModelCheck(self):
        "Test the model checking with Blackburn & Bos testsuite"
        val1 = Valuation()
        v1 = [('jules', 'd1'), ('vincent', 'd2'), ('pumpkin', 'd3'),
              ('honey_bunny', 'd4'), ('yolanda', 'd5'),
              ('customer', set(['d1', 'd2'])),
              ('robber', set(['d3', 'd4'])),
              ('love', set([('d3', 'd4')]))]
        val1.parse(v1)
        dom1 = val1.domain
        m1 = Model(dom1, val1)
        g1 = Assignment(dom1)

        val2 = Valuation()
        v2 = [('jules', 'd1'), ('vincent', 'd2'), ('pumpkin', 'd3'),
              ('honey_bunny', 'd4'), ('yolanda', 'd4'),
              ('customer', set(['d1', 'd2', 'd5', 'd6'])),
              ('robber', set(['d3', 'd4'])),
              ('love', set())]
        val2.parse(v2)
        dom2 = set(['d1', 'd2', 'd3', 'd4', 'd5', 'd6'])
        m2 = Model(dom2, val2)
        g2 = Assignment(dom2)
        g21 = Assignment(dom2)
        g21.add('d3', 'y')

        val3 = Valuation()
        v3 = [('mia', 'd1'), ('jody', 'd2'), ('jules', 'd3'),
              ('vincent', 'd4'),
              ('woman', set(['d1', 'd2'])), ('man', set(['d3', 'd4'])),
              ('joke', set(['d5', 'd6'])), ('episode', set(['d7', 'd8'])),
              ('in', set([('d5', 'd7'), ('d5', 'd8')])),
              ('tell', set([('d1', 'd5'), ('d2', 'd6')]))]
        val3.parse(v3)
        dom3 = set(['d1', 'd2', 'd3', 'd4', 'd5', 'd6', 'd7', 'd8'])
        m3 = Model(dom3, val3)
        g3 = Assignment(dom3)

        tests = [
            ('some x. (robber x)', m1, g1, True),
            ('some x. some y. (love x y)', m1, g1, True),
            ('some x0. some x1. (love x0 x1)', m2, g2, False),
            ('all x. all y. (love x y)', m2, g2, False),
            ('(not all x. all y. (love x y))', m2, g2, True),
            ('all x. all y. (not (love x y))', m2, g2, True),
            ('(yolanda = honey_bunny)', m2, g2, True),
            ('(mia = honey_bunny)', m2, g2, 'Undefined'),
            ('(not (yolanda = honey_bunny))', m2, g2, False),
            ('(not (mia = honey_bunny))', m2, g2, 'Undefined'),
            ('all x. ((robber x) or (customer x))', m2, g2, True),
            ('(not all x. ((robber x) or (customer x)))', m2, g2, False),
            ('((robber x) or (customer x))', m2, g2, 'Undefined'),
            ('((robber y) or (customer y))', m2, g21, True),
            ('some x. ((man x) and some x. (woman x))', m3, g3, True),
            ('(some x. (man x) and some x. (woman x))', m3, g3, True),
            ('(not some x. (woman x))', m3, g3, False),
            ('some x. ((tasty x) and (burger x))', m3, g3, 'Undefined'),
            ('(not some x. ((tasty x) and (burger x)))', m3, g3, 'Undefined'),
            ('some x. ((man x) and (not some y. (woman y)))', m3, g3, False),
            ('some x. ((man x) and (not some x. (woman x)))', m3, g3, False),
            ('some x. ((woman x) and (not some x. (customer x)))', m2, g2, 'Undefined'),
        ]

        for item in tests:
            sentence, model, g, testvalue = item
            semvalue = model.evaluate(sentence, g)
            self.assertEqual(semvalue, testvalue)
            g.purge()
         
        
def testsuite():
    suite = unittest.makeSuite(TestModels)
    return unittest.TestSuite(suite)

def test(verbosity):
    runner = unittest.TextTestRunner(verbosity=verbosity)
    runner.run(testsuite())
        
       
        
#//////////////////////////////////////////////////////////////////////
# Demo..
#//////////////////////////////////////////////////////////////////////        
# number of spacer chars
mult = 30
    
def propdemo(trace=None):
    """Example of a propositional model."""
    
    global val1, dom1, m1, g1
    val1 = Valuation({'p': True, 'q': True, 'r': False})
    dom1 = set([])
    m1 = Model(dom1, val1, prop=True)
    g1 = Assignment(dom1)

    print
    print '*' * mult
    print "Propositional Formulas Demo"
    print '*' * mult
    print "Model m1:\n", m1
    print '*' * mult

    sentences = [
    '(p and q)',
    '(p and r)',
    '(not p)',
    '(not r)',
    '(not (not p))',
    '(not (p and r))',
    '(p or r)',
    '(r or p)',
    '(r or r)',
    '((not p) or r))',
    '(p or (not p))',
    '(p implies q)',
    '(p implies r)',
    '(r implies p)',
    '(p iff p)',
    '(r iff r)',
    '(p iff r)',
    ]

    for sent in sentences:
        if trace:
            print
            m1.evaluate(sent, g1, trace)
        else:
            print "The value of '%s' is: %s" % (sent, m1.evaluate(sent, g1))

def folmodel(trace=None):
    """Example of a first-order model."""

    global val2, v2, dom2, m2, g2
    val2 = Valuation()
    v2 = [('adam', 'b1'), ('betty', 'g1'), ('fido', 'd1'),\
         ('girl', set(['g1', 'g2'])), ('boy', set(['b1', 'b2'])), ('dog', set(['d1'])),
         ('love', set([('b1', 'g1'), ('b2', 'g2'), ('g1', 'b1'), ('g2', 'b1')]))]
    val2.parse(v2)
    dom2 = val2.domain
    m2 = Model(dom2, val2)
    g2 = Assignment(dom2, {'x': 'b1', 'y': 'g2'})

    if trace:
        print "*" * mult
        print "Model m2\n", m2
        print "*" * mult
        
    symbols = ['adam', 'girl', 'love', 'walks', 'x', 'y', 'z']

    if trace:
        for s in symbols:
            try:
                print "The interpretation of '%s' in m2 is %s" % (s, m2.i(s, g2))
            except Undefined:
                print "The interpretation of '%s' in m2 is Undefined" % s
    
def foldemo(trace=None):
    """Interpretation of formulas in a first-order model."""
    folmodel()

    print
    print '*' * mult
    print "FOL Formulas Demo"
    print '*' * mult

    sentences = [
    '(love adam betty)',
    '(adam = betty)',
    'some z1. (boy z1)',
    'some x. ((boy x) and (not (x = adam)))',
    'some x. ((boy x) and all y. (love x y))',
    'all x. ((boy x) or (girl x))',
    'all x. ((girl x) implies some y. (boy y) and (love y x))',    #Every girl loves some boy.
    'some x. ((boy x) and all y. ((girl y) implies (love x y)))',  #There is some boy that every girl loves.
    'some x. ((boy x) and all y. ((girl y) implies (love y x)))',  #Some boy loves every girl.
    'all x. ((dog x) implies (not (girl x)))',
    'some x. some y. ((love y x) and (love y x))'
    ]


    for sent in sentences:
        g2.purge()
        if trace:
            print
            m2.evaluate(sent, g2, trace)
        else:
            print "The value of '%s' is: %s" % (sent, m2.evaluate(sent, g2))


def satdemo(trace=None):
    """Satisfiers of an open formula in a first order model."""

    print
    print '*' * mult
    print "Satisfiers Demo"
    print '*' * mult

    folmodel()
    
    clauses = [
               '(boy x)',
               '(x = x)',
               '((boy x) or (girl x))',
               '((boy x) and (girl x))',
               '(love x adam)',
               '(love adam x)',
               '(not (x = adam))',
               'some z22. (love z22 x)',
               'some y. (love x y)',
               'all y. ((girl y) implies (love y x))',
               'all y. ((girl y) implies (love x y))',
               '((boy x) and all y. ((girl y) implies (love y x)))',
               '((boy x) and all y. ((girl y) implies (love x y)))',
               '((boy x) and some y. ((girl y) and (love x y)))',
               '((girl x) implies (dog x))',
               'all y. ((dog y) implies (x = y))',
               '(not some y. (love x y))',
               'some y. ((love y adam) and (love x y))'
                ]

    if trace:
        print m2
        
    for clause in clauses:
        g2.purge()
        print "The satisfiers of '%s' are: %s" % (clause, m2.satisfiers(clause, 'x', g2, trace))

        
def demo(num, trace=None):
    """
    Run some demos.

     - num = 1: propositional logic demo
     - num = 2: first order model demo (only if trace is set)
     - num = 3: first order sentences demo
     - num = 4: satisfaction of open formulas demo

    @param trace: trace = 1, or trace = 2 for more verbose tracing
    """
    demos = {1: propdemo,
             2: folmodel,
             3: foldemo,
             4: satdemo}
    
    
    try:
        demos[num](trace=trace)
    except KeyError:
        for num in demos.keys():
            demos[num](trace=trace)
    


if __name__ == "__main__":
    demo(0, trace=None)
    print '*' * mult 
    test(verbosity=2) 
        
        
        
