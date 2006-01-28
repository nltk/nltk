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


class Variable(object):
    """A variable, either free or bound."""
    
    def __init__(self, name):
        self.name = name

    def equals(self, other):
        """A comparison function."""
        assert isinstance(other, Variable)
        return self.name == other.name
        
    def __str__(self): return self.name


class Expression(object):
    """The abstract class of a lambda calculus expression."""
    def __init__(self):
        if self.__class__ is Expression:
            raise NotImplementedError

    def equals(self, other):
        """Are the two expressions equal?"""
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
        """Replace all instances of variable with expression."""
        raise NotImplementedError

    def simplify(self):
        """Evaluate the form by repeatedly applying applications."""
        raise NotImplementedError
        
    def __str__(self):
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
        set = Set([self.variable])
        return set

    def free(self):
        set = Set([self.variable])
        return set

    def subterms(self):
        return Set([self])

    def replace(self, variable, expression):
        if self.variable.equals(variable):
            return expression
        else:
            return self
        
    def simplify(self):
        return self

    def __str__(self): return '%s' % self.variable

    def __repr__(self): return '%s' % self.variable

class LambdaExpression(Expression):
    """A lambda expression: \\x.M."""
    def __init__(self, variable, term):
        Expression.__init__(self)
        assert isinstance(variable, Variable)
        assert isinstance(term, Expression)
        self.variable = variable
        self.term = term

    def equals(self, other):
        if self.__class__ is other.__class__:
            return self.variable.equals(other.variable) and \
                   self.term.equals(other.term)
        else:
            return 0

    def variables(self):
        set = Set([self.variable])
        set.unionWith(self.term.variables())
        return set

    def free(self):
        set = self.term.free()
        set.remove(self.variable)
        return set

    def subterms(self):
        set = self.term.subterms()
        set.add(self)
        return set

    def replace(self, variable, expression):
        return LambdaExpression(self.variable, \
                                self.term.replace(variable, expression))

    def simplify(self):
        return LambdaExpression(self.variable, self.term.simplify())
    
    def __str__(self, continuation=0):
        # Print \x.\y.M as \x y.M.
        if continuation:
            prefix = ' '
        else:
            prefix = '\\'
        if isinstance(self.term, LambdaExpression):
            return '%s%s%s' % (prefix, self.variable, self.term.__str__(1))
        else:
            return '%s%s.%s' % (prefix, self.variable, self.term)

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
        set = Set()
        set.unionWith(self.first.variables())
        set.unionWith(self.second.variables())
        return set

    def free(self):
        set = Set()
        set.unionWith(self.first.free())
        set.unionWith(self.second.free())
        return set

    def subterms(self):
        set = Set()
        set.unionWith(self.first.subterms())
        set.unionWith(self.second.subterms())
        set.add(self)
        return set

    def replace(self, variable, expression):
        return ApplicationExpression(self.first.replace(variable, expression),\
                                     self.second.replace(variable, expression))

    def simplify(self):
        first = self.first.simplify()
        second = self.second.simplify()
        if isinstance(first, LambdaExpression):
            variable = first.variable
            term = first.term
            return term.replace(variable, second).simplify()
        else:
            return self

    def __str__(self):
        # Print ((M N) P) as (M N P).
        strFirst = str(self.first)
        if isinstance(self.first, ApplicationExpression):
            strFirst = strFirst[1:-1]
        return '(%s %s)' % (strFirst, self.second)

    def __repr__(self):
        return self.__str__()


class Parser(object):
    """A lambda calculus expression parser."""

    # Tokens.
    LAMBDA = '\\'
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
               [Parser.LAMBDA, Parser.DOT, Parser.OPEN, Parser.CLOSE]

    def next(self):
        """Parse the next complete expression from the stream and return it."""
        tok = self.token()
        if tok == Parser.LAMBDA:
            # Expression is a lambda expression: \x.M
            vars = [self.token()]
            while self.isVariable(self.token(0)):
                # Support expressions like: \x y.M == \x.\y.M
                vars.append(self.token())
            tok = self.token()
            if tok != Parser.DOT:
                raise Error, "parse error, unexpected token: %s" % tok
            term = self.next()
            accum = LambdaExpression(Variable(vars.pop()), term)
            while vars:
                accum = LambdaExpression(Variable(vars.pop()), accum)
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
            accum = ApplicationExpression(first, second)
            while exps:
                exp, exps = exps[0], exps[1:]
                accum = ApplicationExpression(accum, exp)
            return accum
        else:
            if self.isVariable(tok):
                # Expression is a simple variable expression: x
                return VariableExpression(Variable(tok))
            else:
                raise Error, "parse error, unexpected token: %s" % tok


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
        print "Expression: %s" % l
        v = l.variables()
        v.sort()
        print "Variables: %s" % v
        f = l.free()
        f.sort()
        print "Free: %s" % f
        s = l.subterms()
        s.sort()
        print "Subterms: %s" % s
        ls = l.simplify()
        print "Simplify: %s" % ls
        la = ApplicationExpression(ApplicationExpression(l, P), Q)
        las = la.simplify()
        print "Apply and simplify: %s -> %s" % (la, las)
        ll = Parser(str(l)).next()
        assert l.equals(ll)
        print "Serialize and reparse: %s -> %s" % (l, ll)
        print

if __name__ == '__main__': main()
