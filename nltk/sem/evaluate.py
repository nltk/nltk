# Natural Language Toolkit: Models for first-order languages with lambda
#
# Copyright (C) 2001-2008 University of Pennsylvania
# Author: Ewan Klein <ewan@inf.ed.ac.uk>,
# URL: <http://nltk.sourceforge.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
This module provides data structures for representing first-order
models. 
"""

#from logic import LogicParser, Variable, is_indvar

from logic import *
from pprint import pformat

class Error(Exception): pass

class Undefined(Error): pass

class CharFun(dict):
    """
    A dictionary which represents a curryed characteristic function.
    """

    def __init__(self, charfun=None):
        dict.__init__(self)
        if charfun:
            self.update(charfun)
 
        
    #def _isrel(self, s):
        #"""Check whether a set represents a relation (of any arity)."""
        
        #assert isinstance(s, set), "Argument is not a set"
        #if len(s) == 0:
            #return True
        #elif not isinstance(max(s),tuple) or len(max(s))==len(min(s)):
            #return True
        #else:
            #raise ValueError, "Set contains sequences of different lengths"

    def _item2dict(self, item):
        """
        Given an input such as the triple ('a', 'b', 'c'), return the L{CharFun}
        {'c': {'b': {'a' : True}}}
        
        @return: A characteristic function corresponding to the input.
        @rtype: L{CharFun}
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
                           
    def read(self, s):
        """
        Convert an M{n}-ary relation into its corresponding characteristic function.
        @rtype: L{CharFun}
        @type s: set
        """

        assert isrel(s)

        charfuns = []
        for item in s:
            charfuns.append(self._item2dict(item))
            
        chf = reduce(self._merge, charfuns, {})
        self.update(chf)

    def tuples(self):
        """
        Convert a L{CharFun} back into a set of tuples.

        Given an input such as the L{CharFun} {'c': {'b': {'a': True}}},
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

##     def __repr__(self):
##         items = ['%s: %s' % t for t in sorted(self.items())]
##         return '{%s}' % ', '.join(items)

    def _getDomain(self):
        return flatten(self)

    domain = property(_getDomain, doc='Set-theoretic domain of a curried function')

def isrel(s):
        """
        Check whether a set represents a relation (of any arity).
        
        @param s: a set containing tuples
        @type s: set
        """
        # we have the empty relation set()
        if len(s) == 0:
            return True
        # the longest element of the set is not a tuple, i.e., it's just a set of strings or ints
        #elif not isinstance(max(s),tuple):
            #return True
        # all the elements are tuples of the same length
        # TODO deal with case where s contains an int
        elif len(max(s))==len(min(s)):
                return True
        else:
            raise ValueError, "Set %r contains sequences of different lengths" % s

def inds2tuples(s):
    new = set()
    for elem in s:
        if isinstance(elem, str):
            new.add((elem,))
        elif isinstance(elem, int):
            new.add((str(elem,)))
        else:
            new.add(elem)
    return new   

        
#class Rel(set):
    #"""
    #Set--theoretical treatment of relations as a set of tuples of the same length.
     #"""
 
    #def __init__(self, iter):
        #set.__init__(self, iter)
        #new = inds2tuples(self)
        #assert isrel(new)
        #self = new
        
    #def __str__(self):
        #return "{%s}" % ', '.join(map(str, self))
        
#def flatten(d):
    #"""
    #@return: The set of keys of a L{CharFun} instance.
    #@rtype: set
    #@type d: dict
    #"""
    #flat = []
    #try:
        #flat.extend(d.keys())
        #for v in d.values():
            #if isinstance(v, dict):
                #flat.extend(flatten(v))
            #else:
                #flat.append(v)
    #except AttributeError:
        #flat.append(d)
    #result = set(flat)
    #result.discard(True)
    #return result



def depth(cf):
    """
    Calculate the depth of a L{CharFun}.

    @rtype: C{int}
    @type cf: L{CharFun}
    """
    if True in cf.values():
        return 1
    else:
        key = cf.keys()[0]
        return 1+depth(cf[key])
    

class Valuation(dict):
    """
    A dictionary which represents a model-theoretic Valuation of non-logical constants.

    An attempt to initialize a L{Valuation} with an individual
    variable expression (e.g., 'x3') will raise an error, as will an
    attemp to read a list containing an individual variable
    expression.
    
    An instance of L{Valuation} will raise a KeyError exception (i.e.,
    just behave like a standard  dictionary) if indexed with an expression that
    is not in its list of symbols.
    """
    def __init__(self, iter):
        dict.__init__(self)
        for (sym, val) in iter:
            if isinstance(val, str) or isinstance(val, bool):
                self[sym] = val
            elif isinstance(val, set):
                self[sym] = inds2tuples(val)

        #if valuation:
            #for k in valuation.keys():
                ##if is_indvar(k):
                    ##raise Error, "This looks like an individual variable: '%s'" % k
                ## Check if the valuation is of the form {'p': True}
                #if isinstance(valuation[k], bool):
                    #self[k] = valuation[k]
                #else:
                    #try:
                        #cf = CharFun(valuation[k])
                        #self[k] = cf
                    #except (TypeError, ValueError):
                        #self[k] = valuation[k]

    def __getitem__(self, key):
        if key in self:
            return dict.__getitem__(self, key)
        else:
            raise Undefined,  "Unknown expression: '%s'" % key
                    
    #def read(self, seq):
        #"""
        #Parse a list such as  C{[('j', 'b1'), ('girl', set(['g1', 'g2']))]} into a L{Valuation}.
        #@rtype: L{Valuation}
        #@param seq: A list of tuples of the form (I{constant}, I{relation}), where I{relation} is a set of tuples.
        #"""
        #d = dict(seq)
        ## Each sym is a non-logical constant
        #for sym in d:
            ##if is_indvar(k):
                ##raise Error, "This looks like an individual variable: '%s'" % k
            #val = d[sym]
            ## Does val represent an individual?
            #if isinstance(val, str):
                #pass
            #else:
                #cf = CharFun()
                #cf.read(d[k])        
                #d[k] = cf
        #self.update(d)

    def __str__(self):
        return pformat(self)
        
    def _getDomain(self):
        dom = []
        for val in self.values():
            if isinstance(val, str):
                dom.append(val)
            else:
                dom.extend([elem for tuple in val for elem in tuple])
        return set(dom)

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

    If an unknown expression M{a} is passed to a model M{M}'s
    interpretation function M{i}, M{i} will first check whether M{M}'s
    valuation assigns an interpretation to M{a} as a constant, and if
    this fails, M{i} will delegate the interpretation of M{a} to
    M{g}. M{g} only assigns values to individual variables (i.e.,
    members of the class L{IndVariableExpression} in the L{logic}
    module. If a variable is not assigned a value by M{g}, it will raise
    an C{Undefined} exception.
    """
    def __init__(self, domain, assignment=None):
        dict.__init__(self)
        self.domain = domain
        if assignment:
            for var in assignment.keys():
                val = assignment[var]
                assert val in self.domain,\
                       "'%s' is not in the domain: %s" % (val, self.domain)
                assert is_indvar(var),\
                       "Wrong format for an Individual Variable: '%s'" % var
            self.update(assignment)
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

    def add(self, val, var):
        """
        Add a new variable-value pair to the assignment, and update
        C{self.variant}.

        We write the arguments in the order 'val, var' by analogy with the
        notation 'g[u/x]'.
        """
        assert val in self.domain,\
               "%s is not in the domain %s" % (val, self.domain)
        assert isinstance(var, IndividualVariableExpression),\
               "Wrong format for an Individual Variable: '%s'" % var
        self[var.name] = val
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

    def app(self, fun, arg):
        """
        Wrapper for handling KeyErrors and TypeErrors raised by
        function application.
        
        This constrains instances of L{CharFun} to return C{False} in
        the right circumstances.

        @param fun: an instance of L{CharFun}.
        @param arg: an arbitrary semantic object
        @return: If C{arg} is in C{fun}'s domain, then returns C{fun[arg]},\
                 else if C{arg} is in C{self.domain}, returns C{False},\
                 else raises C{Undefined} error.
        """
        
        try:
            return fun[arg]
        except KeyError:
            if arg in self.domain:
                return False
            else:
                raise Undefined,\
                      "%s can't be applied as a function to '%s'" % (fun, arg)
        except TypeError:
            if fun == False:
                return False
            else:
                raise Undefined,\
                      "%s can't be applied as a function to %s" % (fun, arg)
            

    # Interpretations for the binary boolean operators
    #############################
    def AND(arg1, arg2):
        return min(arg1, arg2)
    
    def OR(arg1, arg2):
        return max(arg1, arg2)
    
    def IMPLIES(arg1, arg2):
        return max(not arg1, arg2)
    
    def IFF(arg1, arg2):
        return arg1 == arg2
    
    # EQUALITY
    ########
    
    def EQ(arg1, arg2):
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
        Provides a handler for L{satisfy}
        that blocks further propagation of C{Undefined} error.
        @param expr: An C{Expression} of L{logic}.
        @type g: L{Assignment}
        @param g: an assignment to individual variables.
        @rtype: C{bool} or 'Undefined'
        """
        try:
            #lp = LogicParser(constants=self.valuation.symbols)
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

        Raises an C{Undefined} error when C{expr} is an atomic string
        but is not a symbol or an individual variable.

        @return: Returns a truth value or C{Undefined} if C{expr} is\
        complex, and calls the interpretation function C{i} if C{expr}\
        is atomic.
        
        @param expr: An expression of L{logic}.
        @type g: L{Assignment}
        @param g: an assignment to individual variables.
        """

        OPS = Model.OPS

        if isinstance(parsed, ApplicationExpression):
            argvals = tuple([self.satisfy(arg, g) for arg in parsed.args])
            funval = self.satisfy(parsed.function, g)
            # the function is a LambdaExpression
            if isinstance(funval, CharFun):
                return funval[argvals[0]]
            # the function is an n-ary relation
            else:
                return argvals in funval
        elif isinstance(parsed, NegatedExpression):
            return not self.satisfy(parsed.term, g)
        elif isinstance(parsed, BooleanExpression):
            op = parsed.getOp()
            return OPS[op](self.satisfy(parsed.first, g), self.satisfy(parsed.second, g))
        elif isinstance(parsed, AllExpression):
            return self.ALL(self.satisfiers(parsed.term, parsed.variable, g))
        elif isinstance(parsed, ExistsExpression):
            satisfiers = self.satisfiers(parsed.term, parsed.variable, g)
            return self.EXISTS(satisfiers)
        elif isinstance(parsed, LambdaExpression):
            cf = CharFun()
            for u in self.domain:
                val = self.satisfy(parsed.term, g.add(u, parsed.variable))
                # the dict is a lot smaller if we do this:
                # if val: cf[u] = val
                cf[u] = val
            return cf
        else:
            return self.i(parsed, g, trace)

    def i(self, parsed, g, trace=False):
        """
        An interpretation function.

        Assuming that C{expr} is atomic:

         - if C{expr} is a non-logical constant, calls the valuation M{V} 
         - else if C{expr} is an individual variable, calls assignment M{g}
         - else returns C{Undefined}.

        
        @param expr: an C{Expression} of L{logic}.
        @type g: L{Assignment}
        @param g: an assignment to individual variables.
        @return: a semantic value
        """
        # If parsed is a propositional letter 'p', 'q', etc, it could be in valuation.symbols 
        # and also be an IndividualVariableExpression. We want to catch this first case.
        # So there is a procedural consequence to the ordering of clauses here:
        if parsed.name in self.valuation.symbols:
            return self.valuation[parsed.name]
        elif isinstance(parsed, IndividualVariableExpression):
            return g[parsed.name]

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
        
 
    def satisfiers(self, parsed, var, g, trace=None, nesting=0):
        """
        Generate the entities from the model's domain that satisfy an open formula.

        @param parsed: the open formula
        @param var: the relevant free variable in C{parsed}.
        @param g: the variable assignment
        @return: an iterator over the entities that satisfy C{parsed}.
        """

        spacer = '   '
        indent = spacer + (spacer * nesting)
        candidates = []
        
        if var in parsed.free():
            if trace:
                print
                print (spacer * nesting) + "Open formula is '%s' with assignment %s" % (parsed, g)
            for u in self.domain:
                new_g = g.copy()
                new_g.add(u, var)
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
            raise Undefined, "%s is not free in %s" % (var, parsed)

        return result


        
#//////////////////////////////////////////////////////////////////////
# Demo..
#//////////////////////////////////////////////////////////////////////        
# number of spacer chars
mult = 30
    
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

def folmodel(trace=None):
    """Example of a first-order model."""

    global val2, v2, dom2, m2, g2

    v2 = [('adam', 'b1'), ('betty', 'g1'), ('fido', 'd1'),\
         ('girl', set(['g1', 'g2'])), ('boy', set(['b1', 'b2'])), ('dog', set(['d1'])),
         ('love', set([('b1', 'g1'), ('b2', 'g2'), ('g1', 'b1'), ('g2', 'b1')]))]
    val2 = Valuation(v2)
    dom2 = val2.domain
    m2 = Model(dom2, val2)
    g2 = Assignment(dom2, {'x': 'b1', 'y': 'g2'})

    if trace:
        print "*" * mult
        print "Model m2\n", m2
        print "*" * mult
        
    exprs = ['adam', 'girl', 'love', 'walks', 'x', 'y', 'z']
    lp = LogicParser()
    parsed = [lp.parse(e) for e in exprs]
    
    if trace:
        for p in parsed:
            try:
                print "The interpretation of '%s' in m2 is %s" % (p, m2.i(p, g2))
            except Undefined:
                print "The interpretation of '%s' in m2 is Undefined" % p
    
def foldemo(trace=None):
    """Interpretation of closed expressions in a first-order model."""
    folmodel()

    print
    print '*' * mult
    print "FOL Formulas Demo"
    print '*' * mult

    formulas = [
    'love (adam, betty)',
    '(adam = mia)',
    '\\x. (boy(x) | girl(x))',
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
            print
            m2.evaluate(fmla, g2, trace)
        else:
            print "The value of '%s' is: %s" % (fmla, m2.evaluate(fmla, g2))


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
    
    var = IndividualVariableExpression('x')
    for p in parsed:
        g2.purge()
        print "The satisfiers of '%s' are: %s" % (p, m2.satisfiers(p, var, g2, trace))

def unit(trace=None):
    global val0, dom0, m0, g0
    #r1 = Rel([("a","b"), ("c", "d"), 3])
    #r2 = Rel(["a","b", 3])
    #r2 = Rel([2])
    #r2  = Rel([1, 3])
    #print r1, r2
    #print repr(r1), repr(r2)
    
    sents = [
        #'love(adam, betty)',
        #'love(adam, sue)',
        #'dog(fido)',
        #'- dog(fido)',
        #'- - dog(fido)',
        #'- dog(sue)',
        #'dog(fido) & boy(adam)',
        #'- (dog(fido) & boy(adam))',
        #'- dog(fido) & boy(adam)',
        #'dog(fido) | boy(adam)',
        #'- (dog(fido) | boy(adam))',
        #'- dog(fido) | boy(adam)',
        #'- dog(fido) | - boy(adam)',
        #'dog(fido) -> boy(adam)',
        #'- (dog(fido) -> boy(adam))',
        #'- dog(fido) -> boy(adam)', 
        #'exists x . love(adam, x)',
        #'all x . love(adam, x)',
        #'fido = fido',
        #'exists x . all y. love(x, y)',
        #'exists x . (x = fido)',
        #'all x . (dog(x) | - dog(x)) '
        r'\x. \y. love(x, y)',
        r'\x. dog(x) (adam)',
        r'\x. (dog(x) | boy(x)) (adam)',
        r'\x. \y. love(x, y)(fido)',
        r'\x. \y. love(x, y)(adam)',
        r'\x. \y. love(x, y)(betty)',       
        r'\x. \y. love(x, y)(betty)(adam)',        
        r'\x. \y. love(x, y)(betty, adam)',
        r'\y. \x. love(x, y)(fido)(adam)',        
        r'\y. \x. love(x, y)(betty, adam)',
        r'\x. exists y. love(x, y)',
        #r'\z. adam',
        #r'\z. love(x, y)',
        #r'\x. x(adam)',
        #r'\P. P(adam)',
    ]

    v0 = [('adam', 'b1'), ('betty', 'g1'), ('fido', 'd1'),\
         ('girl', set(['g1', 'g2'])), ('boy', set(['b1', 'b2'])), ('dog', set(['d1'])),
         ('love', set([('b1', 'g1'), ('b2', 'g2'), ('g1', 'b1'), ('g2', 'b1')]))]
    
    val0 = Valuation(v0)
    dom0 = val0.domain
    m0 = Model(dom0, val0)
    g0 = Assignment(dom0)
    
    for s in sents:
        print m0.evaluate(s, g0, trace=1)
        
        
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
    demo(5, trace=1)
