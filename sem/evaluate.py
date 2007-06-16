# Natural Language Toolkit: Models for first-order languages with lambda
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Ewan Klein <ewan@inf.ed.ac.uk>,
# URL: <http://nltk.sourceforge.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
This module provides data structures for representing first-order
models. 
"""

from logic import LogicParser, Variable, is_indvar

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
    
    assert isinstance(s, set), "Argument is not a set"
    if len(s) == 0:
        return True
    elif not isinstance(max(s),tuple) or len(max(s))==len(min(s)):
        return True
    else:
        raise ValueError, "Set contains sequences of different lengths"
        
def flatten(d):
    """
    @return: The set of keys of a L{CharFun} instance.
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
    def __init__(self, valuation=None):
        dict.__init__(self)
        if valuation:
            for k in valuation.keys():
                if is_indvar(k):
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
                    
    def read(self, seq):
        """
        Parse a list such as  C{[('j', 'b1'), ('girl', set(['g1', 'g2']))]} into a L{Valuation}.
        @rtype: L{Valuation}
        @param seq: A list of tuples of the form (I{constant}, I{relation}), where I{relation} is a set of tuples.
        """
        d = dict(seq)
        for k in d.keys():
            if is_indvar(k):
                raise Error, "This looks like an individual variable: '%s'" % k
            val = d[k]
            if isinstance(val, str):
                pass
            else:
                cf = CharFun()
                cf.read(d[k])        
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
        assert is_indvar(var),\
               "Wrong format for an Individual Variable: '%s'" % var
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
            


    NOT =      {True: False, False: True}
    AND =      {True: {True: True, False: False},
                False: {True: False, False: False}}
    OR =       {True: {True: True, False: True},
                False: {True: True, False: False}}
    IMPLIES =  {True: {True: True, False: False},
                False: {True: True, False: True}}
    IFF =      {True: {True: True, False: False},
                False: {True: False, False: True}}

    OPS = {'and': AND,
           'or': OR,
           'implies': IMPLIES,
           'iff': IFF}

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
        @type g: L{Assignment}
        @param g: an assignment to individual variables.
        """

        OPS = Model.OPS

#         OPS = {'and': Model.AND,
#                'or': Model.OR,
#                'implies': Model.IMPLIES,
#                'iff': Model.IFF}


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

                
                # _first_ is something like '\\ x' and _second_ is something like '(boy x)'
                elif first[0] == '\\':
                    var = first[1]
                    phi = second
                    cf = CharFun()
                    for u in self.domain:
                        val = self.satisfy(phi, g.add(u, var), trace)
                        if val:
                            cf[u] = val
                               
                    if trace:
                        print "   '%s' evaluates to %s under M, %s" %  (expr, cf, g)
                    return cf

                # _first_ is something like 'some x' and _second_ is something like '(boy x)'
                elif first[0] == 'some':
                    var = first[1]
                    phi = second
                    # seq is an iterator
                    seq = self.satisfiers(phi, var, g, trace, nesting=1)
                    #any returns True if seq is nonempty
                    value = self.any(seq)
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
                    #issubset can take an iterator as argument
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

        
        @param expr: an C{Expression} of L{logic}.
        @type g: L{Assignment}
        @param g: an assignment to individual variables.
        @return: a semantic value
        """
        try:
            if trace > 1:
                print "   i, %s('%s') = %s" % (g, expr, self.valuation[expr])
            # expr is a non-logical constant, i.e., in self.valuation.symbols
            return self.valuation[expr]
        except Undefined:
            if trace > 1:
                print "    (checking whether '%s' is an individual variable)" % expr
 
            # expr wasn't a constant; maybe a variable that g knows about?
            return g[expr]
        
 

    def freevar(self, var, expr):
        """
        Is C{var} one of the free variables in C{expr}?

        @type var: an C{Indvar} of L{logic}
        @param var: the variable to test for.
        @param expr: an C{Expression} of L{logic}.
        @rtype: C{bool}
        """
        parsed = LogicParser().parse(expr)
        variable = Variable(var)
        return variable in parsed.free()
        
    def satisfiers(self, expr, var, g, trace=False, nesting=0):
        """
        Generate the entities from the model's domain that satisfy an open formula.

        @param expr: the open formula
        @param var: the relevant free variable in C{expr}.
        @param g: the variable assignment
        @return: an iterator over the entities that satisfy C{expr}.
        """

        spacer = '   '
        indent = spacer + (spacer * nesting)
        candidates = []
        
        if self.freevar(var, expr):
            if trace:
                print
                print (spacer * nesting) + "Open formula is '%s' with assignment %s" % (expr, g)
            for u in self.domain:
                new_g = g.copy()
                new_g.add(u, var)
                if trace > 1:
                    lowtrace = trace-1
                else:
                    lowtrace = 0
                value = self.satisfy(expr, new_g, lowtrace)
                
                if trace:
                    print indent + "(trying assignment %s)" % new_g
                    
                # expr == False under g[u/var]?
                if value == False:
                    if trace:
                        print  indent + "value of '%s' under %s is False" % (expr, new_g)
                 
                    
                # so g[u/var] is a satisfying assignment
                else:
                    candidates.append(u)
                    if trace:
                        print indent + "value of '%s' under %s is %s" % (expr, new_g, value)
                   
            result = set(c for c in candidates)
        # var isn't free in expr
        else:
            raise Undefined, "%s is not free in %s" % (var, expr)

        return result


    def decompose(self, expr):
        """
        Function to communicate with a first-order functional language.

        This function tries to make weak assumptions about the parse structure
        provided by the logic module. It makes the assumption that an expression
        can be broken down into a pair of subexpressions:

          - The C{(binder, body)} pair is for decomposing quantified formulae.
          - The C{(op, args)} pair is for decomposing formulae with a boolean operator.
          - The C{(fun, args)} pair should catch other relevant cases.

        @param expr: A string representation of a first-order formula.
        """

        try:
            parsed = LogicParser(constants=self.valuation.symbols).parse(expr)
        except TypeError:
            print "Cannot parse %s" % expr
            
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

    def any(self, seq):
        """
        Returns True if there is at least one element in the iterable.
        
        @param seq: an iterator
        @rtype: C{bool}
        """
        for elem in seq:
            return True
        return False
    

        
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
    val2.read(v2)
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
    """Interpretation of closed expressions in a first-order model."""
    folmodel()

    print
    print '*' * mult
    print "FOL Formulas Demo"
    print '*' * mult

    formulas = [
    '(love adam betty)',
    '(adam = mia)',
    '\\x. ((boy x) or (girl x))',
    '\\x y. ((boy x) and (love y x))',
    '\\x. some y. ((boy x) and (love y x))',
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
               'all y. ((girl y) implies ((boy x) and (love x y)))',
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
        
    for fmla in formulas:
        g2.purge()
        print "The satisfiers of '%s' are: %s" % (fmla, list(m2.satisfiers(fmla, 'x', g2, trace)))

        
def demo(num, trace=None):
    """
    Run some demos.

     - num = 1: propositional logic demo
     - num = 2: first order model demo (only if trace is set)
     - num = 3: first order sentences demo
     - num = 4: satisfaction of open formulas demo
     - any other value: run all the demos

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
    demo(5, trace=0)

        
        
        
