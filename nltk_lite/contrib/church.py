#!/usr/local/bin/python
#
# $Id$ $Date$

"""
Lambda calculus system in Python.
"""

__version__ = '1.0a'
__program__ = 'church'
__author__ = 'Erik Max Francis <max@alcyone.com>'
__copyright__ = 'Copyright (C) 2001-2002 Erik Max Francis'
__license__ = 'GPL'


class Error(Exception): pass


class Counter:
    """
    A counter that auto-increments each time its value is read.
    """
    def __init__(self, initial_value=0):
	self._value = initial_value
    def get(self):
	self._value += 1
	return self._value


class Variable:
    """A variable, either free or bound."""
    
    def __init__(self, name):
        self.name = name

    def __eq__(self, other):
	return self.equals(other)

    def __ne__(self, other):
	return not self.equals(other)

    def equals(self, other):
        """A comparison function."""
        assert isinstance(other, Variable)
        return self.name == other.name
        
    def __str__(self): return self.name

    def __repr__(self): return "Variable('%s')" % self.name

    def __hash__(self): return hash(repr(self))

class Expression:
    """The abstract class of a lambda calculus expression."""
    def __init__(self):
        if self.__class__ is Expression:
            raise NotImplementedError

    def __eq__(self, other):
	return self.equals(other)

    def __ne__(self, other):
	return not self.equals(other)

    def equals(self, other):
        """Are the two expressions equal, modulo alpha conversion?"""
        return NotImplementedError

    def variables(self):
        """Set of all variables."""
        raise NotImplementedError

    def free(self):
        """Set of free variables."""
        raise NotImplementedError

    def subterms(self):
        """Set of all subterms (including self)."""
        raise NotImplementedError

    def replace(self, variable, expression):
        """Replace all instances of variable v with expression E in self,
        where v is free in self."""
        raise NotImplementedError

    def simplify(self):
        """Evaluate the form by repeatedly applying applications."""
        raise NotImplementedError

    def skolemise(self):
        """
        Perform a simple Skolemisation operation.  Existential quantifiers are
        simply dropped and all variables they introduce are renamed so that
        they are unique.
        """
	return self._skolemise(set(), Counter())

    def _skolemise(self, bound_vars, counter):
        raise NotImplementedError

    def __str__(self):
        raise NotImplementedError

    def __repr__(self):
        raise NotImplementedError

    def __hash__(self):
        raise NotImplementedError

class VariableExpression(Expression):
    """A variable expression which consists solely of a variable."""
    def __init__(self, variable):
        Expression.__init__(self)
        assert isinstance(variable, Variable)
        self.variable = variable

    def equals(self, other):
        if self.__class__ is other.__class__:
            return self.variable.equals(other.variable)
        else:
            return 0

    def variables(self):
        return set([self.variable])

    def free(self):
        return set([self.variable])

    def subterms(self):
        return set([self])

    def replace(self, variable, expression):
        if self.variable.equals(variable):
            return expression
        else:
            return self
        
    def simplify(self):
        return self

    def _skolemise(self, bound_vars, counter):
	return self

    def __str__(self): return '%s' % self.variable

    def __repr__(self): return "VariableExpression('%s')" % self.variable

    def __hash__(self): return hash(repr(self))

class VariableBinderExpression(Expression):
    """A variable binding expression: e.g. \\x.M."""

    # A counter used for generating "unique" variable names during alpha
    # conversion.
    _counter = Counter()

    def __init__(self, variable, term):
        Expression.__init__(self)
        assert isinstance(variable, Variable)
        assert isinstance(term, Expression)
        self.variable = variable
        self.term = term

    def equals(self, other):
        if self.__class__ is other.__class__:
            if self.variable == other.variable:
                return self.term == other.term
            else:
                # Comparing \x.M  and \y.N.
                # Rename y to x in N and continue.
                return self.term == other.term.replace(other.variable,
                                        VariableExpression(self.variable))
        else:
            return 0

    def variables(self):
        return set([self.variable]).union(self.term.variables())

    def free(self):
        return self.term.free().difference(set([self.variable]))

    def subterms(self):
        return self.term.subterms().union([self])

    def replace(self, variable, expression):
        if self.variable == variable:
            return self
        if self.variable in expression.free():
            v = '_g' + str(self._counter.get())
            self = self.alpha_convert(Variable(v))
        return self.__class__(self.variable, \
                                self.term.replace(variable, expression))

    def alpha_convert(self, newvar):
        """
        Rename all occurrences of the variable introduced by this variable
        binder in the expression to @C{newvar}.
        """
        term = self.term.replace(self.variable, VariableExpression(newvar))
        return self.__class__(newvar, term)

    def simplify(self):
        return self.__class__(self.variable, self.term.simplify())

    def __str__(self, continuation=0):
        # Print \x.\y.M as \x y.M.
        if continuation:
            prefix = ' '
        else:
            prefix = self.__class__.PREFIX
        if self.term.__class__ == self.__class__:
            return '%s%s%s' % (prefix, self.variable, self.term.__str__(1))
        else:
            return '%s%s.%s' % (prefix, self.variable, self.term)

    def __hash__(self):
	return hash(repr(self))

class LambdaExpression(VariableBinderExpression):
    """A lambda expression: \\x.M."""
    PREFIX = '\\'

    def _skolemise(self, bound_vars, counter):
	bv = bound_vars.copy()
	bv.add(self.variable)
	return self.__class__(self.variable, self.term._skolemise(bv, counter))

    def __repr__(self):
	return "LambdaExpression('%s', '%s')" % (self.variable, self.term)

class SomeExpression(VariableBinderExpression):
    """An existential quantification expression: some x.M."""
    PREFIX = 'some '

    def _skolemise(self, bound_vars, counter):
	if self.variable in bound_vars:
	    var = Variable("_s" + str(counter.get()))
	    term = self.term.replace(self.variable, VariableExpression(var))
	else:
	    var = self.variable
	    term = self.term
	bound_vars.add(var)
	return term._skolemise(bound_vars, counter)

    def __repr__(self):
	return "SomeExpression('%s', '%s')" % (self.variable, self.term)

class ApplicationExpression(Expression):
    """An application expression: (M N)."""
    def __init__(self, first, second):
        Expression.__init__(self)
        assert isinstance(first, Expression)
        assert isinstance(second, Expression)
        self.first = first
        self.second = second

    def equals(self, other):
        if self.__class__ is other.__class__:
            return self.first.equals(other.first) and \
                   self.second.equals(other.second)
        else:
            return 0

    def variables(self):
        return self.first.variables().union(self.second.variables())

    def free(self):
        return self.first.free().union(self.second.free())

    def subterms(self):
        first = self.first.subterms()
        second = self.second.subterms()
        return first.union(second).union(set([self]))

    def replace(self, variable, expression):
        return self.__class__(self.first.replace(variable, expression),\
                              self.second.replace(variable, expression))

    def simplify(self):
        first = self.first.simplify()
        second = self.second.simplify()
        if isinstance(first, LambdaExpression):
	    variable = first.variable
	    term = first.term
	    return term.replace(variable, second).simplify()
        else:
            return self.__class__(first, second)

    def _skolemise(self, bound_vars, counter):
	first = self.first._skolemise(bound_vars, counter)
	second = self.second._skolemise(bound_vars, counter)
	return self.__class__(first, second)

    def __str__(self):
        # Print ((M N) P) as (M N P).
        strFirst = str(self.first)
        if isinstance(self.first, ApplicationExpression):
            strFirst = strFirst[1:-1]
        return '(%s %s)' % (strFirst, self.second)

    def __repr__(self): return "ApplicationExpression('%s', '%s')" % (self.first, self.second)

    def __hash__(self): return hash(repr(self))

class Parser:
    """A lambda calculus expression parser."""

    # Tokens.
    LAMBDA = '\\'
    SOME = 'some'
    DOT = '.'
    OPEN = '('
    CLOSE = ')'
    
    def __init__(self, data=None):
        if data is not None:
            self.buffer = data
            self.process()
        else:
            self.buffer = ''

    def feed(self, data):
        """Feed another batch of data to the parser."""
        self.buffer += data
        self.process()

    def process(self):
        """Process the waiting stream to make it trivial to parse."""
        self.buffer = self.buffer.replace('\t', ' ')
        self.buffer = self.buffer.replace('\n', ' ')
        self.buffer = self.buffer.replace('\\', ' \\ ')
        self.buffer = self.buffer.replace('.', ' . ')
        self.buffer = self.buffer.replace('(', ' ( ')
        self.buffer = self.buffer.replace(')', ' ) ')

    def token(self, destructive=1):
        """Get the next waiting token.  The destructive flag indicates
        whether the token will be removed from the buffer; setting it to
        0 gives lookahead capability."""
        if self.buffer == '':
            raise Error, "end of stream"
        tok = None
        buffer = self.buffer
        while not tok:
            seq = buffer.split(' ', 1)
            if len(seq) == 1:
                tok, buffer = seq[0], ''
            else:
                assert len(seq) == 2
                tok, buffer = seq
            if tok:
                if destructive:
                    self.buffer = buffer
                return tok
        assert 0 # control never gets here
        return None

    def isVariable(self, token):
        """Is this token a variable (that is, not one of the other types)?"""
        return token not in \
               [Parser.LAMBDA, Parser.SOME,
	       Parser.DOT, Parser.OPEN, Parser.CLOSE]

    def next(self):
        """Parse the next complete expression from the stream and return it."""
        tok = self.token()
	if tok in [Parser.LAMBDA, Parser.SOME]:
            # Expression is a lambda expression: \x.M
	    # or a some expression: some x.M
	    if tok == Parser.LAMBDA:
		factory = LambdaExpression
	    elif tok == Parser.SOME:
		factory = SomeExpression
	    else:
		raise ValueError(tok)

            vars = [self.token()]
            while self.isVariable(self.token(0)):
                # Support expressions like: \x y.M == \x.\y.M
		# and: some x y.M == some x.some y.M
                vars.append(self.token())
            tok = self.token()
            if tok != Parser.DOT:
                raise Error, "parse error, unexpected token: %s" % tok
            term = self.next()
            accum = factory(Variable(vars.pop()), term)
            while vars:
                accum = factory(Variable(vars.pop()), accum)
            return accum
	    
        elif tok == Parser.OPEN:
            # Expression is an application expression: (M N)
            first = self.next()
            second = self.next()
            exps = []
            while self.token(0) != Parser.CLOSE:
                # Support expressions like: (M N P) == ((M N) P)
                exps.append(self.next())
            tok = self.token() # swallow the close token
            assert tok == Parser.CLOSE
            accum = self.make_ApplicationExpression(first, second)
            while exps:
                exp, exps = exps[0], exps[1:]
                accum = self.make_ApplicationExpression(accum, exp)
            return accum
        else:
            if self.isVariable(tok):
                # Expression is a simple variable expression: x
                return VariableExpression(Variable(tok))
            else:
                raise Error, "parse error, unexpected token: %s" % tok
    
    # This is intended to be overridden, so that you can derive a Parser class
    # that constructs expressions using your subclasses.  So far we only need
    # to overridde ApplicationExpression, but the same thing could be done for
    # other expression types.
    def make_ApplicationExpression(self, first, second):
        return ApplicationExpression(first, second)


def expressions():
    """Return a sequence of test expressions."""
    a = Variable('a')
    x = Variable('x')
    y = Variable('y')
    z = Variable('z')
    A = VariableExpression(a)
    X = VariableExpression(x)
    Y = VariableExpression(y)
    Z = VariableExpression(z)
    XA = ApplicationExpression(X, A)
    XY = ApplicationExpression(X, Y)
    XZ = ApplicationExpression(X, Z)
    YZ = ApplicationExpression(Y, Z)
    XYZ = ApplicationExpression(XY, Z)
    I = LambdaExpression(x, X)
    K = LambdaExpression(x, LambdaExpression(y, X))
    L = LambdaExpression(x, XY)
    S = LambdaExpression(x, LambdaExpression(y, LambdaExpression(z, \
            ApplicationExpression(XZ, YZ))))
    B = LambdaExpression(x, LambdaExpression(y, LambdaExpression(z, \
            ApplicationExpression(X, YZ))))
    C = LambdaExpression(x, LambdaExpression(y, LambdaExpression(z, \
            ApplicationExpression(XZ, Y))))
    O = LambdaExpression(x, LambdaExpression(y, XY))
    N = ApplicationExpression(LambdaExpression(x, XA), I)
    T = Parser('\\x y.(x y z)').next()
    return [X, XZ, XYZ, I, K, L, S, B, C, O, N, T]

def main():
    p = Variable('p')
    q = Variable('q')
    P = VariableExpression(p)
    Q = VariableExpression(q)
    for l in expressions():
        print "Expression:", l
        print "Variables:", l.variables()
        print "Free:", l.free()
        print "Subterms:", l.subterms()
        print "Simplify:",l.simplify()
        la = ApplicationExpression(ApplicationExpression(l, P), Q)
        las = la.simplify()
        print "Apply and simplify: %s -> %s" % (la, las)
        ll = Parser(str(l)).next()
        assert l.equals(ll)
        print "Serialize and reparse: %s -> %s" % (l, ll)
        print

def runtests():
    # Test a beta-reduction which used to be wrong
    l = Parser(r'(\x.\x.(x x) 1)').next().simplify()
    id = Parser(r'\x.(x x)').next()
    assert l == id

    # Test Church numerals
    zero = Parser(r'\f x.x').next()
    one = Parser(r'\f x.(f x)').next()
    two = Parser(r'\f x.(f (f x))').next()
    three = Parser(r'\f x.(f (f (f x)))').next()
    four = Parser(r'\f x.(f (f (f (f x))))').next()
    succ = Parser(r'\n f x.(f (n f x))').next()
    plus = Parser(r'\m n f x.(m f (n f x))').next()
    mult = Parser(r'\m n f.(m (n f))').next()
    pred = Parser(r'\n f x.(n \g h.(h (g f)) \u.x \u.u)').next()
    v1 = ApplicationExpression(succ, zero).simplify()
    assert v1 == one
    v2 = ApplicationExpression(succ, v1).simplify()
    assert v2 == two
    v3 = ApplicationExpression(ApplicationExpression(plus, v1), v2).simplify()
    assert v3 == three
    v4 = ApplicationExpression(ApplicationExpression(mult, v2), v2).simplify()
    assert v4 == four
    v5 = ApplicationExpression(pred, ApplicationExpression(pred, v4)).simplify()
    assert v5 == two

    # betaConversionTestSuite.pl from
    # _Representation and Inference for Natural Language_
    #
    x1 = Parser(r'(\p.(p mia) \x.(walk x))').next().simplify()
    x2 = Parser(r'(walk mia)').next().simplify()
    assert x1 == x2

    x1 = Parser(r'some x.(and (man x) (\p.some x.(and (woman x) (p x)) \y.(love x y)))').next().simplify()
    x2 = Parser(r'some x.(and (man x) some y.(and (woman y) (love x y)))').next().simplify()
    assert x1 == x2

    x1 = Parser(r'(\a.(sleep a) mia)').next().simplify()
    x2 = Parser(r'(sleep mia)').next().simplify()
    assert x1 == x2

    x1 = Parser(r'(\a.\b.(like b a) mia)').next().simplify()
    x2 = Parser(r'\b.(like b mia)').next().simplify()
    assert x1 == x2

    x1 = Parser(r'\a.(\b.(like b a) vincent)').next().simplify()
    x2 = Parser(r'\a.(like vincent a)').next().simplify()
    assert x1 == x2

    x1 = Parser(r'\a.(and (\b.(like b a) vincent) (sleep a))').next().simplify()
    x2 = Parser(r'\a.(and (like vincent a) (sleep a))').next().simplify()
    assert x1 == x2
    
    x1 = Parser(r'(\a.\b.(like b a) mia vincent)').next().simplify()
    x2 = Parser(r'(like vincent mia)').next().simplify()
    assert x1 == x2

    x1 = Parser(r'(p (\a.(sleep a) vincent))').next().simplify()
    x2 = Parser(r'(p (sleep vincent))').next().simplify()
    assert x1 == x2

    x1 = Parser(r'\a.(a (\b.(sleep b) vincent))').next().simplify()
    x2 = Parser(r'\a.(a (sleep vincent))').next().simplify()
    assert x1 == x2

    x1 = Parser(r'\a.(a (sleep vincent))').next().simplify()
    x2 = Parser(r'\a.(a (sleep vincent))').next().simplify()
    assert x1 == x2

    x1 = Parser(r'(\a.(a vincent) \b.(sleep b))').next().simplify()
    x2 = Parser(r'(sleep vincent)').next().simplify()
    assert x1 == x2

    x1 = Parser(r'(\a.(believe mia (a vincent)) \b.(sleep b))').next().simplify()
    x2 = Parser(r'(believe mia (sleep vincent))').next().simplify()
    assert x1 == x2

    x1 = Parser(r'(\a.(and (a vincent) (a mia)) \b.(sleep b))').next().simplify()
    x2 = Parser(r'(and (sleep vincent) (sleep mia))').next().simplify()
    assert x1 == x2

    x1 = Parser(r'(\a.\b.(and (\c.(c (a vincent)) \d.(probably d)) (\c.(c (b mia)) \d.(improbably d))) \e.(walk e) \e.(talk e)))').next().simplify()
    x2 = Parser(r'(and (probably (walk vincent)) (improbably (talk mia)))').next().simplify()
    assert x1 == x2

    x1 = Parser(r'(\a.\b.(\c.(c a b) \d.\e.(love d e)) jules mia)').next().simplify()
    x2 = Parser(r'(love jules mia)').next().simplify()
    assert x1 == x2

    x1 = Parser(r'(\a.\b.some c.(and (a c) (b c)) \d.(boxer d) \d.(sleep d))').next().simplify()
    x2 = Parser(r'some c.(and (boxer c) (sleep c))').next().simplify()
    assert x1 == x2

    x1 = Parser(r'(\a.(z a) \c.\a.(like a c))').next().simplify()
    x2 = Parser(r'(z \c.\a.(like a c))').next().simplify()
    assert x1 == x2

    x1 = Parser(r'(\a.\b.(a b) \c.\b.(like b c))').next().simplify()
    x2 = Parser(r'\b.(\c.\b.(like b c) b)').next().simplify()
    assert x1 == x2

    x1 = Parser(r'(\a.\b.(\c.(c a b) \b.\a.(loves b a)) jules mia)').next().simplify()
    x2 = Parser(r'(loves jules mia)').next().simplify()
    assert x1 == x2

    x1 = Parser(r'(\a.\b.(and some b.(a b) (a b)) \c.(boxer c) vincent)').next().simplify()
    x2 = Parser(r'(and some b.(boxer b) (boxer vincent))').next().simplify()
    assert x1 == x2

if __name__ == '__main__':
    runtests()
    main()
