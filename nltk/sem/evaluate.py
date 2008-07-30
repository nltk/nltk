# Natural Language Toolkit: Models for first-order languages with lambda
#
# Copyright (C) 2001-2008 NLTK Project
# Author: Ewan Klein <ewan@inf.ed.ac.uk>,
# URL: <http://nltk.sourceforge.net>
# For license information, see LICENSE.TXT
#
# $Id$

#TODO:
    #- fix tracing
    #- fix iterator-based approach to existentials
    
    
"""
This module provides data structures for representing first-order
models. 
"""
from pprint import pformat
import inspect
from nltk.decorators import decorator
from nltk.internals import deprecated

from logic import *


class Error(Exception): pass

class Undefined(Error):  pass

def trace(f, *args, **kw):
    argspec = inspect.getargspec(f)
    d = dict(zip(argspec[0], args))
    if d.pop('trace', None):
        print
        for item in d.items():
            print "%s => %s" % item
    return f(*args, **kw)
        
def is_rel(s):
    """
    Check whether a set represents a relation (of any arity).

    @param s: a set containing C{tuple}s of C{str} elements
    @type s: C{set}
    @rtype: C{bool}
        """
    # we have the empty relation, i.e. set()
    if len(s) == 0:
        return True
    # all the elements are tuples of the same length
    elif len(max(s))==len(min(s)):
        return True
    else:
        raise ValueError, "Set %r contains sequences of different lengths" % s

def set2rel(s):
    """
    Convert a set containing individuals (strings or numbers) into a set of 
    unary tuples. Any tuples of strings already in the set are passed through 
    unchanged.
    
    For example:
      - set(['a', 'b']) => set([('a',), ('b',)])
      - set([3, 27]) => set([('3',), ('27',)])
      
    @type s: C{set}
    @rtype: C{set} of C{tuple} of C{str}
    """
    new = set()
    for elem in s:
        if isinstance(elem, str):
            new.add((elem,))
        elif isinstance(elem, int):
            new.add((str(elem,)))
        else:
            new.add(elem)
    return new   

def arity(rel):
    """
    Check the arity of a relation.
    @type rel: C{set} of C{tuple}s
    @rtype: C{int} of C{tuple} of C{str}
    """
    if len(rel) == 0:
        return 0
    return len(list(rel)[0])

@decorator(trace)
def app(rel, arg, trace=False):
    """
    Apply a relation (as set of tuples) to an argument.
    
    If C{rel} has arity n <= 1, then C{app} returns a Boolean value.
    If If C{rel} has arity n > 1, then C{app} returns a relation of arity n-1.
    
    @type rel: C{set} of C{tuple}s
    @param arg: any appropriate semantic argument
    @rtype: C{bool} or a C{set} of C{tuple}s
    """
    assert is_rel(rel)
    reduced = set([tup[1:] for tup in rel if tup[0] == arg])
    if arity(rel) <= 1:
        return bool(len(reduced))
    else:
        return reduced

def make_VariableExpression(var):
    """
    Convert a string into an instance of L{VariableExpression}
    
    @type var: C{str}
    @rtype: C{VariableExpression} or C{IndividualVariableExpression}
    """
    
    variable = Variable(var)
    if is_indvar(var):
        return IndividualVariableExpression(variable)
    else:
        return VariableExpression(variable)
        
class Valuation(dict):
    """
    A dictionary which represents a model-theoretic Valuation of non-logical constants.
    Keys are strings representing the constants to be interpreted, and values correspond 
    to individuals (represented as strings) and n-ary relations (represented as sets of tuples
    of strings).

    An instance of L{Valuation} will raise a KeyError exception (i.e.,
    just behave like a standard  dictionary) if indexed with an expression that
    is not in its list of symbols.
    """
    def __init__(self, iter):
        """
        @param iter: a C{list} of (symbol, value) pairs.
        """
        dict.__init__(self)
        for (sym, val) in iter:
            if isinstance(val, str) or isinstance(val, bool):
                self[sym] = val
            elif isinstance(val, set):
                self[sym] = set2rel(val)

    def __getitem__(self, key):
        if key in self:
            return dict.__getitem__(self, key)
        else:
            raise Undefined,  "Unknown expression: '%s'" % key

    #def __str__(self):
        #return "{%s}" % ', '.join(map(str, self))

    @deprecated("Call the valuation as an initialization parameter instead")        
    def read(self, seq):
        self.update(seq)
 
    def __str__(self):
        return pformat(self)

    def _getDomain(self):
        dom = []
        for val in self.values():
            if isinstance(val, str):
                dom.append(val)
            else:
                dom.extend([elem for tuple in val for elem in tuple if elem is not None])
        return set(dom)

    domain = property(_getDomain,
             doc='Set-theoretic domain of the value-space of a Valuation.')

    def _getSymbols(self):
        return sorted(self.keys())

    symbols = property(_getSymbols,
              doc='The non-logical constants which the Valuation recognizes.')


class Assignment(dict):
    """
    A dictionary which represents an assignment of values to variables.

    An assigment can only assign values from its domain.

    If an unknown expression M{a} is passed to a model M{M}'s
    interpretation function M{i}, M{i} will first check whether M{M}'s
    valuation assigns an interpretation to M{a} as a constant, and if
    this fails, M{i} will delegate the interpretation of M{a} to
    M{g}. M{g} only assigns values to individual variables (i.e.,
    members of the class L{IndividualVariableExpression} in the L{logic}
    module. If a variable is not assigned a value by M{g}, it will raise
    an C{Undefined} exception.
    """
    def __init__(self, domain, iter=None):
        """
        @param domain: the domain of discourse
        @type domain: C{set}
        @param assignment: a map from variable names to values
        @type domain: C{dict}
        """
        dict.__init__(self)
        self.domain = domain
        if iter:
            for (var, val) in iter:
                assert val in self.domain,\
                       "'%s' is not in the domain: %s" % (val, self.domain)
                assert is_indvar(var),\
                       "Wrong format for an Individual Variable: '%s'" % var
                self[var] = val
        self._addvariant()

    def __getitem__(self, key):
        if key in self:
            return dict.__getitem__(self, key)
        else:
            raise Undefined, "Not recognized as a variable: '%s'" % key
        
    def copy(self):
        new = Assignment(self.domain)
        new.update(self)
        return new
        
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

    def add(self, var, val):
        """
        Add a new variable-value pair to the assignment, and update
        C{self.variant}.

        """
        assert val in self.domain,\
               "%s is not in the domain %s" % (val, self.domain)
        #assert isinstance(var, IndividualVariableExpression),\
        assert is_indvar(var),\
               "Wrong format for an Individual Variable: '%s'" % var
        #self[var.variable.name] = val
        self[var] = val
        self._addvariant()
        return self

    
class Model(object):
    """
    A first order model is a domain M{D} of discourse and a valuation M{V}.

    A domain M{D} is a set, and a valuation M{V} is a map that associates
    expressions with values in the model.
    The domain of M{V} should be a subset of M{D}.
    """
    
    def __init__(self, domain, valuation, prop=None):
        """
        Construct a new L{Model}.
        
        @type domain: C{set}
        @param domain: A set of entities representing the domain of discourse of the model.
        @type valuation: L{Valuation}
        @param valuation: the valuation of the model.
        @param prop: If this is set, then we are building a propositional\
        model and don't require the domain of M{V} to be subset of M{D}.
        """
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

    # Interpretations for the binary boolean operators
    #############################

    def AND(self, arg1, arg2):
        return min(arg1, arg2)
    

    def OR(self, arg1, arg2):
        return max(arg1, arg2)
    

    def IMPLIES(self, arg1, arg2):
        return max(not arg1, arg2)
    

    def IFF(self, arg1, arg2):
        return arg1 == arg2
    
    # EQUALITY
    ########

    def EQ(self, arg1, arg2):
        return arg1 == arg2
    
    # Interpretations for the classical quantifiers
    #########################
 
    def ALL(self, sat):
        return sat == self.domain
     
    def EXISTS(self, sat):
        for u in sat:
            return True
        return False
           
    OPS = {
        '&': AND,
        '|': OR,
        '->': IMPLIES,
        '<->': IFF,
        '=': EQ,
    }

    def evaluate(self, expr, g, trace=None):
        """
        Call the L{LogicParser} to parse input expressions, and
        provide a handler for L{satisfy}
        that blocks further propagation of the C{Undefined} error.
        @param expr: An C{Expression} of L{logic}.
        @type g: L{Assignment}
        @param g: an assignment to individual variables.
        @rtype: C{bool} or 'Undefined'
        """
        try:
            lp = LogicParser()
            parsed = lp.parse(expr)
            value = self.satisfy(parsed, g, trace=trace)
            if trace:
                print
                print "'%s' evaluates to %s under M, %s" %  (expr, value, g)
            return value
        except Undefined:
            if trace:
                print
                print "'%s' is undefined under M, %s" %  (expr, g)
            return 'Undefined'
        

    def satisfy(self, parsed, g, trace=None):
        """
        Recursive interpretation function for a formula of first-order logic.

        Raises an C{Undefined} error when C{parsed} is an atomic string
        but is not a symbol or an individual variable.

        @return: Returns a truth value or C{Undefined} if C{parsed} is\
        complex, and calls the interpretation function C{i} if C{parsed}\
        is atomic.
        
        @param parsed: An expression of L{logic}.
        @type g: L{Assignment}
        @param g: an assignment to individual variables.
        """

        OPS = Model.OPS

        if isinstance(parsed, ApplicationExpression):
            argval = self.satisfy(parsed.argument, g) 
            funval = self.satisfy(parsed.function, g)
            if isinstance(funval, dict):
                return funval[argval]
            else:
                return app(funval, argval)
        elif isinstance(parsed, NegatedExpression):
            return not self.satisfy(parsed.term, g)
        elif isinstance(parsed, BooleanExpression):
            op = parsed.getOp()
            return OPS[op](self, self.satisfy(parsed.first, g), self.satisfy(parsed.second, g))
        elif isinstance(parsed, AllExpression):
            return self.ALL(self.satisfiers(parsed.term, parsed.variable, g))
        elif isinstance(parsed, ExistsExpression):
            satisfiers = self.satisfiers(parsed.term, parsed.variable, g)
            return self.EXISTS(satisfiers)
        elif isinstance(parsed, LambdaExpression):
            cf = {}
            #varex = self.make_VariableExpression(parsed.variable)
            var = parsed.variable.name
            for u in self.domain:
                val = self.satisfy(parsed.term, g.add(var, u))
                # NB the dict would be a lot smaller if we do this:
                # if val: cf[u] = val
                # But then need to deal with cases where f(a) should yield
                # a function rather than just False.
                cf[u] = val
            return cf
        else:
            return self.i(parsed, g, trace)

    #@decorator(trace_eval)   
    def i(self, parsed, g, trace=False):
        """
        An interpretation function.

        Assuming that C{parsed} is atomic:

         - if C{parsed} is a non-logical constant, calls the valuation M{V} 
         - else if C{parsed} is an individual variable, calls assignment M{g}
         - else returns C{Undefined}.

        @param parsed: an C{Expression} of L{logic}.
        @type g: L{Assignment}
        @param g: an assignment to individual variables.
        @return: a semantic value
        """
        # If parsed is a propositional letter 'p', 'q', etc, it could be in valuation.symbols 
        # and also be an IndividualVariableExpression. We want to catch this first case.
        # So there is a procedural consequence to the ordering of clauses here:
        if parsed.variable.name in self.valuation.symbols:
            return self.valuation[parsed.variable.name]
        elif isinstance(parsed, IndividualVariableExpression):
            return g[parsed.variable.name]

        else:
            raise Undefined, "Can't find a value for %s" % parsed
        
        #try:
            #if trace > 1:
                #print "   i, %s('%s') = %s" % (g, expr, self.valuation[expr])
            ## expr is a non-logical constant, i.e., in self.valuation.symbols
            #return self.valuation[expr]
        #except Undefined:
            #if trace > 1:
                #print "    (checking whether '%s' is an individual variable)" % expr
 
            ## expr wasn't a constant; maybe a variable that g knows about?
            #return g[expr]
        
 
    def satisfiers(self, parsed, varex, g, trace=None, nesting=0):
        """
        Generate the entities from the model's domain that satisfy an open formula.

        @param parsed: an open formula
        @type parsed: L{Expression}
        @param varex: the relevant free individual variable in C{parsed}.
        @type varex: C{VariableExpression} or C{str}
        @param g: a variable assignment
        @type g:  L{Assignment}
        @return: a C{set} of the entities that satisfy C{parsed}.
        """

        spacer = '   '
        indent = spacer + (spacer * nesting)
        candidates = []
        
        if isinstance(varex, str):
            var = make_VariableExpression(varex).variable
        else:
            var = varex
             
        if var in parsed.free():
            if trace:
                print
                print (spacer * nesting) + "Open formula is '%s' with assignment %s" % (parsed, g)
            for u in self.domain:
                new_g = g.copy()
                #new_g.add(u, self.make_VariableExpression(var))
                new_g.add(var.name, u)
                if trace > 1:
                    lowtrace = trace-1
                else:
                    lowtrace = 0
                value = self.satisfy(parsed, new_g, lowtrace)
                
                if trace:
                    print indent + "(trying assignment %s)" % new_g
                    
                # parsed == False under g[u/var]?
                if value == False:
                    if trace:
                        print  indent + "value of '%s' under %s is False" % (parsed, new_g)
                 
                    
                # so g[u/var] is a satisfying assignment
                else:
                    candidates.append(u)
                    if trace:
                        print indent + "value of '%s' under %s is %s" % (parsed, new_g, value)
                   
            result = set(c for c in candidates)
        # var isn't free in parsed
        else:
            raise Undefined, "%s is not free in %s" % (var.name, parsed)

        return result


    

        
#//////////////////////////////////////////////////////////////////////
# Demo..
#//////////////////////////////////////////////////////////////////////        
# number of spacer chars
mult = 30

# Demo 1: Propositional Logic
#################
def propdemo(trace=None):
    """Example of a propositional model."""
    
    global val1, dom1, m1, g1
    val1 = Valuation([('p', True), ('q', True), ('r', False)])
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
    '(p & q)',
    '(p & r)',
    '- p',
    '- r',
    '- - p',
    '- (p & r)',
    '(p | r)',
    '(r | p)',
    '(r | r)',
    '(- p | r)',
    '(p | - p)',
    '(p -> q)',
    '(p -> r)',
    '(r -> p)',
    '(p <-> p)',
    '(r <-> r)',
    '(p <-> r)',
    ]

    for sent in sentences:
        if trace:
            print
            m1.evaluate(sent, g1, trace)
        else:
            print "The value of '%s' is: %s" % (sent, m1.evaluate(sent, g1))

# Demo 2: FOL Model
#############
            
def folmodel(trace=None):
    """Example of a first-order model."""

    global val2, v2, dom2, m2, g2

    v2 = [('adam', 'b1'), ('betty', 'g1'), ('fido', 'd1'),\
         ('girl', set(['g1', 'g2'])), ('boy', set(['b1', 'b2'])), ('dog', set(['d1'])),
         ('love', set([('b1', 'g1'), ('b2', 'g2'), ('g1', 'b1'), ('g2', 'b1')]))]
    val2 = Valuation(v2)
    dom2 = val2.domain
    m2 = Model(dom2, val2)
    g2 = Assignment(dom2, [('x', 'b1'), ('y', 'g2')])

    if trace:
        print "*" * mult
        print "Model m2\n", m2
        print "*" * mult
        print g2
        g2.purge()
        print g2
        
    exprs = ['adam', 'girl', 'love', 'walks', 'x', 'y', 'z']
    lp = LogicParser()
    parsed_exprs = [lp.parse(e) for e in exprs]
    
    if trace:
        for parsed in parsed_exprs:
            try:
                print "The interpretation of '%s' in m2 is %s" % (parsed, m2.i(parsed, g2))
            except Undefined:
                print "The interpretation of '%s' in m2 is Undefined" % parsed
    
# Demo 3: FOL
#########
                
def foldemo(trace=None):
    """
    Interpretation of closed expressions in a first-order model.
    """
    folmodel()

    print
    print '*' * mult
    print "FOL Formulas Demo"
    print '*' * mult

    formulas = [
    'love (adam, betty)',
    '(adam = mia)',
    '\\x. (boy(x) | girl(x))',
    '\\x. boy(x)(adam)',
    '\\x y. love(x, y)',
    '\\x y. love(x, y)(adam)(betty)',
    '\\x y. love(x, y)(adam, betty)',
    '\\x y. (boy(x) & love(x, y))',
    '\\x. exists y. (boy(x) & love(x, y))',
    'exists z1. boy(z1)',
    'exists x. (boy(x) &  -(x = adam))',
    'exists x. (boy(x) & all y. love(y, x))',
    'all x. (boy(x) | girl(x))',
    'all x. (girl(x) -> exists y. boy(y) & love(x, y))',    #Every girl loves exists boy.
    'exists x. (boy(x) & all y. (girl(y) -> love(y, x)))',  #There is exists boy that every girl loves.
    'exists x. (boy(x) & all y. (girl(y) -> love(x, y)))',  #exists boy loves every girl.
    'all x. (dog(x) -> - girl(x))',
    'exists x. exists y. (love(x, y) & love(x, y))'
    ]


    for fmla in formulas:
        g2.purge()
        if trace:
            m2.evaluate(fmla, g2, trace)
        else:
            print "The value of '%s' is: %s" % (fmla, m2.evaluate(fmla, g2))

            
# Demo 3: Satisfaction
#############
            
def satdemo(trace=None):
    """Satisfiers of an open formula in a first order model."""

    print
    print '*' * mult
    print "Satisfiers Demo"
    print '*' * mult

    folmodel()
    
    formulas = [
               'boy(x)',
               '(x = x)',
               '(boy(x) | girl(x))',
               '(boy(x) & girl(x))',
               'love(adam, x)',
               'love(x, adam)',
               '-(x = adam)',
               'exists z22. love(x, z22)',
               'exists y. love(y, x)',
               'all y. (girl(y) -> love(x, y))',
               'all y. (girl(y) -> love(y, x))',
               'all y. (girl(y) -> (boy(x) & love(y, x)))',
               '(boy(x) & all y. (girl(y) -> love(x, y)))',
               '(boy(x) & all y. (girl(y) -> love(y, x)))',
               '(boy(x) & exists y. (girl(y) & love(y, x)))',
               '(girl(x) -> dog(x))',
               'all y. (dog(y) -> (x = y))',
               'exists y. love(y, x)',
               'exists y. (love(adam, y) & love(y, x))'
                ]

    if trace:
        print m2
     
    lp = LogicParser()
    for fmla in formulas:
        print fmla
        lp.parse(fmla)
        
    parsed = [lp.parse(fmla) for fmla in formulas]
    
    for p in parsed:
        g2.purge()
        print "The satisfiers of '%s' are: %s" % (p, m2.satisfiers(p, 'x', g2, trace))

        
def demo(num=0, trace=None):
    """
    Run exists demos.

     - num = 1: propositional logic demo
     - num = 2: first order model demo (only if trace is set)
     - num = 3: first order sentences demo
     - num = 4: satisfaction of open formulas demo
     - any other value: run all the demos

    @param trace: trace = 1, or trace = 2 for more verbose tracing
    """
    demos = {
        1: propdemo,
        2: folmodel,
        3: foldemo,
        4: satdemo}
    
    try:
        demos[num](trace=trace)
    except KeyError:
        for num in demos:
            demos[num](trace=trace)

            
if __name__ == "__main__":
    demo(4, trace=1)
