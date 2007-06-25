# Natural Language Toolkit: Logic
from nltk.utilities import Counter
from featurelite import SubstituteBindingsMixin, FeatureI
from featurelite import Variable as FeatureVariable
_counter = Counter()

def unique_variable(counter=None):
    if counter is None: counter = _counter
    unique = counter.get()
    return VariableExpression(Variable('x'+str(unique)))

class Error(Exception): pass

class Variable(object):
    """A variable, either free or bound."""
    
    def __init__(self, name):
        """
        Create a new C{Variable}.

        @type name: C{string}
        @param name: The name of the variable.
        """
        self.name = name

    def __eq__(self, other):
        return self.equals(other)

    def __ne__(self, other):
        return not self.equals(other)

    def equals(self, other):
        """A comparison function."""
        if not isinstance(other, Variable): return False
        return self.name == other.name
        
    def __str__(self): return self.name

    def __repr__(self): return "Variable('%s')" % self.name

    def __hash__(self): return hash(repr(self))

class Constant:
    """A nonlogical constant."""
    
    def __init__(self, name):
        """
        Create a new C{Constant}.

        @type name: C{string}
        @param name: The name of the constant.
        """
        self.name = name

    def __eq__(self, other):
        return self.equals(other)

    def __ne__(self, other):
        return not self.equals(other)

    def equals(self, other):
        """A comparison function."""
        assert isinstance(other, Constant)
        return self.name == other.name
        
    def __str__(self): return self.name

    def __repr__(self): return "Constant('%s')" % self.name

    def __hash__(self): return hash(repr(self))

class Expression(object):
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


    def replace(self, variable, expression, replace_bound=False):
        """Replace all instances of variable v with expression E in self,
        where v is free in self."""
        raise NotImplementedError
    
    def replace_unique(self, variable, counter=None, replace_bound=False):
        """
        Replace a variable v with a new, uniquely-named variable.
        """
        return self.replace(variable, unique_variable(counter),
        replace_bound)

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

    skolemize = skolemise

    def _skolemise(self, bound_vars, counter):
        raise NotImplementedError

    def clauses(self):
        return [self]

    def __str__(self):
        raise NotImplementedError

    def __repr__(self):
        raise NotImplementedError

    def __hash__(self):
        raise NotImplementedError, self.__class__
    
    def normalize(self):
        if hasattr(self, '_normalized'): return self._normalized
        result = self
        vars = self.variables()
        counter = 0
        for var in vars:
            counter += 1
            result = result.replace(var, Variable(str(counter)), replace_bound=True)
        self._normalized = result
        return result

class VariableExpression(Expression):
    """A variable expression which consists solely of a variable."""
    def __init__(self, variable):
        Expression.__init__(self)
        assert isinstance(variable, Variable)
        self.variable = variable

    def equals(self, other):
        """
        Allow equality between instances of C{VariableExpression} and
        C{IndVariableExpression}.
        """
        if isinstance(self, VariableExpression) and \
           isinstance(other, VariableExpression):
            return self.variable.equals(other.variable)
        else:
            return False

    def variables(self):
        return [self.variable]

    def free(self):
        return set([self.variable])

    def subterms(self):
        return set([self])

    def replace(self, variable, expression, replace_bound=False):
        if self.variable.equals(variable):
            if isinstance(expression, Variable):
                return VariableExpression(expression)
            else:
                return expression
        else:
            return self
        
    def simplify(self):
        return self

    def infixify(self):
        return self

    def name(self):
        return self.__str__()

    def _skolemise(self, bound_vars, counter):
        return self

    def __str__(self): return '%s' % self.variable

    def __repr__(self): return "VariableExpression('%s')" % self.variable

    def __hash__(self): return hash(repr(self))


def is_indvar(expr):
    """
    Check whether an expression has the form of an individual variable.
    
    An individual variable matches the following regex:
    C{'^[wxyz](\d*)'}.
    
    @rtype: Boolean
    @param expr: String
    """
    result = expr[0] in ['w', 'x', 'y', 'z']
    if len(expr) > 1:
        return result and expr[1:].isdigit()
    else:
        return result
    
class IndVariableExpression(VariableExpression):
    """
    An individual variable expression, as determined by C{is_indvar()}.
    """
    def __init__(self, variable):
        Expression.__init__(self)
        assert isinstance(variable, Variable), "Not a Variable: %s" % variable
        assert is_indvar(str(variable)), "Wrong format for an Individual Variable: %s" % variable
        self.variable = variable

    def __repr__(self): return "IndVariableExpression('%s')" % self.variable 
        

class ConstantExpression(Expression):
    """A constant expression, consisting solely of a constant."""
    def __init__(self, constant):
        Expression.__init__(self)
        assert isinstance(constant, Constant)
        self.constant = constant

    def equals(self, other):
        if self.__class__ == other.__class__:
            return self.constant.equals(other.constant)
        else:
            return False

    def variables(self):
        return []

    def free(self):
        return set()

    def subterms(self):
        return set([self])

    def replace(self, variable, expression, replace_bound=False):
        return self
        
    def simplify(self):
        return self

    def infixify(self):
        return self

    def name(self):
        return self.__str__()

    def _skolemise(self, bound_vars, counter):
        return self

    def __str__(self): return '%s' % self.constant

    def __repr__(self): return "ConstantExpression('%s')" % self.constant

    def __hash__(self): return hash(repr(self))


class Operator(ConstantExpression):
    """
    A boolean operator, such as 'not' or 'and', or the equality
    relation ('=').
    """
    def __init__(self, operator):
        Expression.__init__(self)
        assert operator in Parser.OPS
        self.constant = operator
        self.operator = operator

    def equals(self, other):
        if self.__class__ == other.__class__:
            return self.constant == other.constant
        else:
            return False

    def simplify(self):
        return self

    def __str__(self): return '%s' % self.operator

    def __repr__(self): return "Operator('%s')" % self.operator



class VariableBinderExpression(Expression):
    """A variable binding expression: e.g. \\x.M."""

    # for generating "unique" variable names during alpha conversion.
    _counter = Counter()

    def __init__(self, variable, term):
        Expression.__init__(self)
        assert isinstance(variable, Variable)
        assert isinstance(term, Expression)
        self.variable = variable
        self.term = term
        self.prefix = self.__class__.PREFIX.rstrip()
        self.binder = (self.prefix, self.variable.name)
        self.body = str(self.term)

    def equals(self, other):
        r"""
        Defines equality modulo alphabetic variance.

        If we are comparing \x.M  and \y.N, then
        check equality of M and N[x/y].
        """
        if self.__class__ == other.__class__:
            if self.variable == other.variable:
                return self.term == other.term
            else:
                # Comparing \x.M  and \y.N.
                # Relabel y in N with x and continue.
                relabeled = self._relabel(other)
                return self.term == relabeled
        else:
            return False

    def _relabel(self, other):
        """
        Relabel C{other}'s bound variables to be the same as C{self}'s
        variable.
        """
        var = VariableExpression(self.variable)
        return other.term.replace(other.variable, var)

    def variables(self):
        vars = [self.variable]
        for var in self.term.variables():
            if var not in vars: vars.append(var)
        return vars

    def free(self):
        return self.term.free().difference(set([self.variable]))

    def subterms(self):
        return self.term.subterms().union([self])

    def replace(self, variable, expression, replace_bound=False):
        if self.variable == variable:
            if not replace_bound: return self
            else: return self.__class__(expression,
                self.term.replace(variable, expression, True))
        if replace_bound or self.variable in expression.free():
            v = 'z' + str(self._counter.get())
            if not replace_bound: self = self.alpha_convert(Variable(v))
        return self.__class__(self.variable,
            self.term.replace(variable, expression, replace_bound))

    def alpha_convert(self, newvar):
        """
        Rename all occurrences of the variable introduced by this variable
        binder in the expression to @C{newvar}.
        """
        term = self.term.replace(self.variable, VariableExpression(newvar))
        return self.__class__(newvar, term)

    def simplify(self):
        return self.__class__(self.variable, self.term.simplify())

    def infixify(self):
        return self.__class__(self.variable, self.term.infixify())

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
        return hash(str(self.normalize()))
    
class LambdaExpression(VariableBinderExpression):
    """A lambda expression: \\x.M."""
    PREFIX = '\\'

    def _skolemise(self, bound_vars, counter):
        bv = bound_vars.copy()
        bv.add(self.variable)
        return self.__class__(self.variable, self.term._skolemise(bv, counter))

    def __repr__(self):
        return str(self)
        #return "LambdaExpression('%s', '%s')" % (self.variable, self.term)

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
        return str(self)
        #return "SomeExpression('%s', '%s')" % (self.variable, self.term)


class AllExpression(VariableBinderExpression):
    """A universal quantification expression: all x.M."""
    PREFIX = 'all '

    def _skolemise(self, bound_vars, counter):
        bv = bound_vars.copy()
        bv.add(self.variable)
        return self.__class__(self.variable, self.term._skolemise(bv, counter))

    def __repr__(self):
        return str(self)
        #return "AllExpression('%s', '%s')" % (self.variable, self.term)



class ApplicationExpression(Expression):
    """An application expression: (M N)."""
    def __init__(self, first, second):
        Expression.__init__(self)
        assert isinstance(first, Expression)
        assert isinstance(second, Expression)
        self.first = first
        self.second = second

    def equals(self, other):
        if self.__class__ == other.__class__:
            return self.first.equals(other.first) and \
                   self.second.equals(other.second)
        else:
            return False

    def variables(self):
        vars = self.first.variables()
        for var in self.second.variables():
            if var not in vars: vars.append(var)
        return vars

    def free(self):
        return self.first.free().union(self.second.free())

    def _functor(self):
        if isinstance(self.first, ApplicationExpression):
            return self.first._functor()
        else:
            return self.first

    fun = property(_functor,
                   doc="Every ApplicationExpression has a functor.")


    def _operator(self):
        functor = self._functor()
        if isinstance(functor, Operator):
            return str(functor)
        else: 
            raise AttributeError

    op = property(_operator,
                  doc="Only some ApplicationExpressions have operators." )

    def _arglist(self):
        """Uncurry the argument list."""
        arglist = [str(self.second)]
        if isinstance(self.first, ApplicationExpression):
            arglist.extend(self.first._arglist())
        return arglist

    def _args(self):
        arglist = self._arglist()
        arglist.reverse()
        return arglist

    args = property(_args,
                   doc="Every ApplicationExpression has args.")

    def subterms(self):
        first = self.first.subterms()

        second = self.second.subterms()
        return first.union(second).union(set([self]))

    def replace(self, variable, expression, replace_bound=False):
        return self.__class__(
            self.first.replace(variable, expression, replace_bound),
            self.second.replace(variable, expression, replace_bound))

    def simplify(self):
        first = self.first.simplify()
        second = self.second.simplify()
        if isinstance(first, LambdaExpression):
            variable = first.variable
            term = first.term
            return term.replace(variable, second).simplify()
        else:
            return self.__class__(first, second)

    def infixify(self):
        first = self.first.infixify()
        second = self.second.infixify()
        if isinstance(first, Operator) and not str(first) == 'not':
            return self.__class__(second, first)
        else:
            return self.__class__(first, second)    

    def _skolemise(self, bound_vars, counter):
        first = self.first._skolemise(bound_vars, counter)
        second = self.second._skolemise(bound_vars, counter)
        return self.__class__(first, second)

    def clauses(self):
        if isinstance(self.first, ApplicationExpression) and\
           isinstance(self.first.first, Operator) and\
           self.first.first.operator == 'and':
           return self.first.second.clauses() + self.second.clauses()
        else: return [self]
    def __str__(self):
        # Print ((M N) P) as (M N P).
        strFirst = str(self.first)
        if isinstance(self.first, ApplicationExpression):
            if not isinstance(self.second, Operator):
                strFirst = strFirst[1:-1]
        return '(%s %s)' % (strFirst, self.second)

    def __repr__(self):
        return str(self)
        #return "ApplicationExpression('%s', '%s')" % (self.first, self.second)

    def __hash__(self):
        return hash(str(self.normalize()))

class ApplicationExpressionSubst(ApplicationExpression, SubstituteBindingsMixin):
    pass

class LambdaExpressionSubst(LambdaExpression, SubstituteBindingsMixin):
    pass

class SomeExpressionSubst(SomeExpression, SubstituteBindingsMixin):
    pass

class AllExpressionSubst(AllExpression, SubstituteBindingsMixin):
    pass

class Parser:
    """A lambda calculus expression parser."""

    
    # Tokens.
    LAMBDA = '\\'
    SOME = 'some'
    ALL = 'all'
    DOT = '.'
    OPEN = '('
    CLOSE = ')'
    BOOL = ['and', 'or', 'not', 'implies', 'iff']
    EQ = '='
    OPS = BOOL
    OPS.append(EQ)
    
    def __init__(self, data=None, constants=None):
        if data is not None:
            self.buffer = data
            self.process()
        else:
            self.buffer = ''
        if constants is not None:
            self.constants = constants
        else:
            self.constants = []
        

    def feed(self, data):
        """Feed another batch of data to the parser."""
        self.buffer += data
        self.process()

    def parse(self, data):
        """
        Provides a method similar to other NLTK parsers.

        @type data: str
        @returns: a parsed Expression
        """
        self.feed(data)
        result = self.next()
        return result

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
        TOKENS = [Parser.LAMBDA, Parser.SOME, Parser.ALL,
               Parser.DOT, Parser.OPEN, Parser.CLOSE, Parser.EQ]
        TOKENS.extend(self.constants)
        TOKENS.extend(Parser.BOOL)
        return token not in TOKENS 

    def next(self):
        """Parse the next complete expression from the stream and return it."""
        tok = self.token()
        
        if tok in [Parser.LAMBDA, Parser.SOME, Parser.ALL]:
            # Expression is a lambda expression: \x.M
            # or a some expression: some x.M
            if tok == Parser.LAMBDA:
                factory = self.make_LambdaExpression
            elif tok == Parser.SOME:
                factory = self.make_SomeExpression
            elif tok == Parser.ALL:
                factory = self.make_AllExpression
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
            if isinstance(second, Operator):
                accum = self.make_ApplicationExpression(second, first)
            else:
                accum = self.make_ApplicationExpression(first, second)
            while exps:
                exp, exps = exps[0], exps[1:]
                accum = self.make_ApplicationExpression(accum, exp)
            return accum

        elif tok in self.constants:
            # Expression is a simple constant expression: a
            return ConstantExpression(Constant(tok))

        elif tok in Parser.OPS:
            # Expression is a boolean operator or the equality symbol
            return Operator(tok)

        elif is_indvar(tok):
            # Expression is a boolean operator or the equality symbol
            return IndVariableExpression(Variable(tok))
        
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
    def make_LambdaExpression(self, first, second):
        return LambdaExpression(first, second)
    def make_SomeExpression(self, first, second):
        return SomeExpression(first, second)
    def make_AllExpression(self, first, second):
        return AllExpression(first, second)

def expressions():
    """Return a sequence of test expressions."""
    a = Variable('a')
    x = Variable('x')
    y = Variable('y')
    z = Variable('z')
    A = VariableExpression(a)
    X = IndVariableExpression(x)
    Y = IndVariableExpression(y)
    Z = IndVariableExpression(z)
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

def demo():
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
        print 'l is:', l
        print 'll is:', ll
        assert l.equals(ll)
        print "Serialize and reparse: %s -> %s" % (l, ll)
        print "Variables:", ll.variables()
        print "Normalize: %s" % ll.normalize()


if __name__ == '__main__':
    demo()

