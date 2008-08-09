# Natural Language Toolkit: Logic
#
# Author: Daniel H. Garrette <dhgarrette@gmail.com>
#
# URL: <http://www.nltk.org>
# For license information, see LICENSE.TXT

"""
A version of first order predicate logic, built on 
top of the untyped lambda calculus.
"""

from nltk.internals import Counter
from nltk.tokenize.simple import WhitespaceTokenizer

_counter = Counter()

class Tokens:
    # Syntaxes
    OLD_NLTK = 0
    NEW_NLTK = 1
    PROVER9  = 2
    
    
    LAMBDA = ['\\', '\\', '\\']
    
    #Quantifiers
    EXISTS = ['some', 'exists', 'exists']
    ALL = ['all', 'all', 'all']
    
    #Punctuation
    DOT = ['.', '.', ' ']
    OPEN = '('
    CLOSE = ')'
    COMMA = ','
    
    #Operations
    NOT = ['not', '-', '-']
    AND = ['and', '&', '&']
    OR = ['or', '|', '|']
    IMP = ['implies', '->', '->']
    IFF = ['iff', '<->', '<->']
    EQ = ['=', '=', '=']
    
    #Collection of tokens
    BINOPS = AND + OR + IMP + IFF
    QUANTS = EXISTS + ALL
    PUNCT = [DOT[0], OPEN, CLOSE, COMMA]
    
    TOKENS = BINOPS + EQ + QUANTS + LAMBDA + PUNCT + NOT
    
    #Special
    SYMBOLS = LAMBDA + PUNCT + [AND[1], OR[1], NOT[1], IMP[1], IFF[1]] + EQ 


class Variable(object):
    def __init__(self, name):
        """
        @param name: the name of the variable
        """
        self.name = name

    def __eq__(self, other):
        return self.__class__ == other.__class__ and self.name == other.name
    
    def __cmp__(self, other):
        assert isinstance(other, Variable)
        if self.name == other.name:
            return 0
        elif self.name < other.name:
            return -1
        else:
            return 1

    def substitute_bindings(self, bindings):
        return bindings.get(self, self)

    def __hash__(self):
        return hash(self.name)

    def __str__(self):
        return self.name

    def __repr__(self):
        return 'Variable(\'' + self.name + '\')'

def unique_variable():
    return Variable('z' + str(_counter.get()))


class SubstituteBindingsI(object):
    """
    An interface for classes that can perform substitutions for
    variables.
    """
    def substitute_bindings(self, bindings):
        """
        @return: The object that is obtained by replacing
        each variable bound by C{bindings} with its values.
        Aliases are already resolved. (maybe?)
        @rtype: (any)
        """
        raise NotImplementedError()

    def variables(self):
        """
        @return: A list of all variables in this object.
        """
        raise NotImplementedError()

class Expression(SubstituteBindingsI):
    """This is the base abstract object for all logical expressions"""
    def __call__(self, other, *additional):
        accum = self.applyto(other)
        for a in additional:
            accum = accum(a)
        return accum
    
    def applyto(self, other):
        return ApplicationExpression(self, other)
    
    def __neg__(self):
        return NegatedExpression(self)
    
    def negate(self):
        return -self
    
    def __and__(self, other):
        assert isinstance(other, Expression)
        return AndExpression(self, other)
    
    def __or__(self, other):
        assert isinstance(other, Expression)
        return OrExpression(self, other)
    
    def __gt__(self, other):
        assert isinstance(other, Expression)
        return ImpExpression(self, other)
    
    def __lt__(self, other):
        assert isinstance(other, Expression)
        return IffExpression(self, other)
    
    def __eq__(self, other):
        raise NotImplementedError()
    
    def tp_equals(self, other, prover_name='tableau'):
        """Pass the expression (self <-> other) to the theorem prover.   
        If the prover says it is valid, then the self and other are equal."""
        assert isinstance(other, Expression)
        
        from nltk.inference import inference
        bicond = IffExpression(self.simplify(), other.simplify())
        prover = inference.get_prover(bicond, prover_name=prover_name)
        return prover.prove()

    def __hash__(self):
        return hash(repr(self))
    
    def substitute_bindings(self, bindings):
        expr = self
        for var in expr.variables():
            if var in bindings:
                val = bindings[var]
                if isinstance(val, Variable):
                    val = VariableExpression(val)
                elif not isinstance(val, Expression):
                    raise ValueError('Can not substitute a non-expresion '
                                     'value into an expression: %r' % val)
                # Substitute bindings in the target value.
                val = val.substitute_bindings(bindings)
                # Replace var w/ the target value.
                expr = expr.replace(var, val)
        return expr.simplify()

    def __repr__(self):
        return '<' + self.__class__.__name__ + ' ' + str(self) + '>'
    
    def __str__(self):
        return self.str()

    def variables(self):
        """
        Return a set of all the variables that are available to be replaced.
        This includes free (non-bound) variables as well as predicates.
        @return: C{set} of C{Variable}s
        """
        raise NotImplementedError() 

    def free(self, indvar_only=True):
        """
        Return a set of all the free (non-bound) variables in self.  Variables
        serving as predicates are no included.
        @param indvar_only: C{boolean} only return individual variables?
        @return: C{set} of C{Variable}s
        """
        raise NotImplementedError()

class ApplicationExpression(Expression):
    r"""
    This class is used to represent two related types of logical expressions.
    
    The first is a Predicate Expression, such as "P(x,y)".  A predicate 
    expression is comprised of a VariableExpression as the predicate and a list
    of Expressions as the arguments.
    
    The second is a an application of one expression to another, such as 
    "(\x.dog(x))(fido)".
    
    The reason Predicate Expressions are treated as Application Expressions is
    that the VariableExpression predicate of the expression may be replaced with
    another Expression, such as a LambdaExpression, which would mean that the
    Predicate should be thought of as being applied to the arguments.
    
    The LogicParser will always curry arguments in a application expression.
    So, "\x y.see(x,y)(john,mary)" will be represented internally as 
    "((\x y.(see(x))(y))(john))(mary)".  This simplifies the internals since 
    there will always be exactly one argument in an application.
    
    The str() method will usually print the curried forms of application 
    expressions.  The one exception is when the the application expression is
    really a predicate expression (ie, underlying function is a 
    VariableExpression).  This means that the example from above will be 
    returned as "(\x y.see(x,y)(john))(mary)".
    """
    def __init__(self, function, argument):
        """
        @param function: C{Expression}, for the function expression
        @param argument: C{Expression}, for the argument   
        """
        self.function = function
        self.argument = argument
        
    def simplify(self):
        function = self.function.simplify()
        argument = self.argument.simplify()
        if isinstance(function, LambdaExpression):
            return function.term.replace(function.variable, argument).simplify()
        else:
            return self.__class__(function, argument)
        
    def replace(self, variable, expression, replace_bound=False):
        """
        Replace every instance of 'variable' with 'expression'
        @param variable: C{Variable} The variable to replace
        @param expression: C{Expression} The expression with which to replace it
        @param replace_bound: C{boolean} Should bound variables be replaced?  
        """
        function = self.function.replace(variable, expression, replace_bound)
        argument = self.argument.replace(variable, expression, replace_bound)
        return self.__class__(function, argument)
        
    def variables(self):
        """
        @see: Expression.variables()
        """
        return self.function.variables() | self.argument.variables() 

    def free(self, indvar_only=True):
        """
        @see: Expression.free()
        """
        if isinstance(self.function, VariableExpression):
            return self.argument.free(indvar_only)
        else:
            return self.function.free(indvar_only) | self.argument.free(indvar_only) 
    
    def __eq__(self, other):
        return self.__class__ == other.__class__ and \
                self.function == other.function and \
                self.argument == other.argument 

    def str(self, syntax=Tokens.NEW_NLTK):
        # uncurry the arguments and find the base function
        function, args = self.uncurry()
        if isinstance(function, VariableExpression):
            #It's a predicate expression ("P(x,y)"), so uncurry arguments
            arg_str = ','.join([arg.str(syntax) for arg in args[::-1]])
        else:
            #Leave arguments curried
            function = self.function
            arg_str = self.argument.str(syntax)
        
        function_str = function.str(syntax)
        parenthesize_function = False
        if isinstance(function, LambdaExpression):
            if isinstance(function.term, ApplicationExpression):
                if not isinstance(function.term.function, VariableExpression):
                    parenthesize_function = True
            elif not isinstance(function.term, BooleanExpression):
                parenthesize_function = True
        elif isinstance(function, ApplicationExpression):
            parenthesize_function = True
                
        if parenthesize_function:
            function_str = Tokens.OPEN + function_str + Tokens.CLOSE
            
        return function_str + Tokens.OPEN + arg_str + Tokens.CLOSE

    def uncurry(self):
        """
        return: A tuple (base-function, arg-list)
        """
        function = self.function
        args = [self.argument]
        while isinstance(function, ApplicationExpression):
            #(\x.\y.sees(x,y)(john))(mary)
            args.append(function.argument)
            function = function.function
        return (function, args)

class VariableExpression(Expression):
    """This class represents a variable to be used as a predicate or entity"""
    def __init__(self, variable):
        """
        @param variable: C{Variable}, for the variable
        """
        self.variable = variable

    def simplify(self):
        return self

    def replace(self, variable, expression, replace_bound=False):
        """
        Replace every instance of 'variable' with 'expression'
        @param variable: C{Variable} The variable to replace
        @param expression: C{Expression} The expression with which to replace it
        @param replace_bound: C{boolean} Should bound variables be replaced?  
        """
        if self.variable == variable:
            return expression
        else:
            return self
    
    def variables(self):
        """
        @see: Expression.variables()
        """
        return set([self.variable])

    def free(self, indvar_only=True):
        """
        @see: Expression.free()
        """
        if not indvar_only: 
            return set([self.variable])
        else: 
            return set()
    
    def __eq__(self, other):
        """Allow equality between instances of C{VariableExpression} and
        C{IndividualVariableExpression}."""
        return isinstance(other, VariableExpression) and \
               self.variable == other.variable
        
    def str(self, syntax=Tokens.NEW_NLTK):
        return str(self.variable)
    
class IndividualVariableExpression(VariableExpression):
    """This class represents variables that take the form of a single lowercase
    character followed by zero or more digits."""
    def free(self, indvar_only=True):
        """
        @see: Expression.free()
        """
        return set([self.variable])
    
class VariableBinderExpression(Expression):
    """This an abstract class for any Expression that binds a variable in an
    Expression.  This includes LambdaExpressions and Quanitifed Expressions"""
    def __init__(self, variable, term):
        """
        @param variable: C{Variable}, for the variable
        @param term: C{Expression}, for the term
        """
        self.variable = variable
        self.term = term

    def simplify(self):
        return self.__class__(self.variable, self.term.simplify())

    def replace(self, variable, expression, replace_bound=False):
        """
        Replace every instance of 'variable' with 'expression'
        @param variable: C{Variable} The variable to replace
        @param expression: C{Expression} The expression with which to replace it
        @param replace_bound: C{boolean} Should bound variables be replaced?  
        """
        #if the bound variable is the thing being replaced
        if self.variable == variable:
            if replace_bound: 
                return self.__class__(expression, 
                                      self.term.replace(variable, expression, 
                                                        True))
            else: 
                return self
        else:
            # if the bound variable appears in the expression, then it must
            # be alpha converted to avoid a conflict
            if self.variable in expression.free():
                self = self.alpha_convert(unique_variable())
                
            #replace in the term
            return self.__class__(self.variable,
                                  self.term.replace(variable, expression, 
                                                    replace_bound))

    def alpha_convert(self, newvar):
        """Rename all occurrences of the variable introduced by this variable
        binder in the expression to @C{newvar}.
        @param newvar: C{Variable}, for the new variable
        """
        return self.__class__(newvar, self.term.replace(self.variable, 
                                            VariableExpression(newvar), True))

    def variables(self):
        """
        @see: Expression.variables()
        """
        return self.term.variables() - set([self.variable])

    def free(self, indvar_only=True):
        """
        @see: Expression.free()
        """
        return self.term.free(indvar_only) - set([self.variable])

    def __eq__(self, other):
        r"""Defines equality modulo alphabetic variance.  If we are comparing 
        \x.M  and \y.N, then check equality of M and N[x/y]."""
        if self.__class__ == other.__class__:
            if self.variable == other.variable:
                return self.term == other.term
            else:
                # Comparing \x.M  and \y.N.  Relabel y in N with x and continue.
                if is_indvar(self.variable.name):
                    varex = IndividualVariableExpression(self.variable)
                else:
                    varex = VariableExpression(self.variable)
                return self.term == other.term.replace(other.variable, varex)
        else:
            return False

class LambdaExpression(VariableBinderExpression):
    def str(self, syntax=Tokens.NEW_NLTK):
        return Tokens.LAMBDA[syntax] + str(self.variable) + \
               Tokens.DOT[syntax] + self.term.str(syntax)

class QuantifiedExpression(VariableBinderExpression):
    def str(self, syntax=Tokens.NEW_NLTK):
        return self.getQuantifier(syntax) + ' ' + str(self.variable) + \
               Tokens.DOT[syntax] + self.term.str(syntax)
        
class ExistsExpression(QuantifiedExpression):
    def getQuantifier(self, syntax=Tokens.NEW_NLTK):
        return Tokens.EXISTS[syntax]

class AllExpression(QuantifiedExpression):
    def getQuantifier(self, syntax=Tokens.NEW_NLTK):
        return Tokens.ALL[syntax]

class NegatedExpression(Expression):
    def __init__(self, term):
        self.term = term
        
    def simplify(self):
        return self.__class__(self.term.simplify())

    def replace(self, variable, expression, replace_bound=False):
        """
        Replace every instance of 'variable' with 'expression'
        @param variable: C{Variable} The variable to replace
        @param expression: C{Expression} The expression with which to replace it
        @param replace_bound: C{boolean} Should bound variables be replaced?  
        """
        return self.__class__(self.term.replace(variable, expression, 
                                                replace_bound))

    def variables(self):
        """
        @see: Expression.variables()
        """
        return self.term.variables()

    def free(self, indvar_only=True):
        """
        @see: Expression.free()
        """
        return self.term.free(indvar_only)

    def __eq__(self, other):
        return self.__class__ == other.__class__ and self.term == other.term

    def str(self, syntax=Tokens.NEW_NLTK):
        return Tokens.NOT[syntax] + self.term.str(syntax)
        
class BooleanExpression(Expression):
    def __init__(self, first, second):
        self.first = first
        self.second = second
    
    def simplify(self):
        return self.__class__(self.first.simplify(), self.second.simplify())

    def replace(self, variable, expression, replace_bound=False):
        """
        Replace every instance of 'variable' with 'expression'
        @param variable: C{Variable} The variable to replace
        @param expression: C{Expression} The expression with which to replace it
        @param replace_bound: C{boolean} Should bound variables be replaced?  
        """
        return self.__class__(self.first.replace(variable, expression, 
                                                 replace_bound),
                              self.second.replace(variable, expression, 
                                                  replace_bound))

    def variables(self):
        """
        @see: Expression.variables()
        """
        return self.first.variables() | self.second.variables()

    def free(self, indvar_only=True):
        """
        @see: Expression.free()
        """
        return self.first.free(indvar_only) | self.second.free(indvar_only)

    def __eq__(self, other):
        return self.__class__ == other.__class__ \
                and self.first == other.first and self.second == other.second

    def str(self, syntax=Tokens.NEW_NLTK):
        return Tokens.OPEN + self.first.str(syntax) + ' ' + self.getOp(syntax) \
                + ' ' + self.second.str(syntax) + Tokens.CLOSE
        
class AndExpression(BooleanExpression):
    """This class represents conjunctions"""
    def getOp(self, syntax=Tokens.NEW_NLTK):
        return Tokens.AND[syntax]

class OrExpression(BooleanExpression):
    """This class represents disjunctions"""
    def getOp(self, syntax=Tokens.NEW_NLTK):
        return Tokens.OR[syntax]

class ImpExpression(BooleanExpression):
    """This class represents implications"""
    def getOp(self, syntax=Tokens.NEW_NLTK):
        return Tokens.IMP[syntax]

class IffExpression(BooleanExpression):
    """This class represents biconditionals"""
    def getOp(self, syntax=Tokens.NEW_NLTK):
        return Tokens.IFF[syntax]

class EqualityExpression(BooleanExpression):
    """This class represents equality expressions like "(x = y)"."""
    def getOp(self, syntax=Tokens.NEW_NLTK):
        return Tokens.EQ[syntax]


class LogicParser:
    """A lambda calculus expression parser."""

    def __init__(self):
        self._currentIndex = 0
        self._buffer = []

    def parse(self, data):
        """
        Parse the expression.

        @param data: C{str} for the input to be parsed
        @returns: a parsed Expression
        """
        self._currentIndex = 0
        self._buffer = self.process(data).split()
        result = self.parse_Expression()
        if self.inRange(0):
            raise UnexpectedTokenException(self.token(0))
        return result

    def process(self, data):
        """Put whitespace between symbols to make parsing easier"""
        out = ''
        tokenTrie = StringTrie(self.get_all_symbols())
        while data:
            st = tokenTrie
            c = data[0]
            token = ''
            while c in st:
                token += c
                st = st[c]
                if len(data) > len(token):
                    c = data[len(token)]
                else:
                    break
            if token:
                out += ' '+token+' '
                data = data[len(token):]
            else:
                out += c
                data = data[1:]
        return out

    def get_all_symbols(self):
        """This method exists to be overridden"""
        return Tokens.SYMBOLS

    def inRange(self, location):
        """Return TRUE if the given location is within the buffer"""
        return self._currentIndex+location < len(self._buffer)

    def token(self, location=None):
        """Get the next waiting token.  If a location is given, then 
        return the token at currentIndex+location without advancing
        currentIndex; setting it gives lookahead/lookback capability."""
        try:
            if location == None:
                tok = self._buffer[self._currentIndex]
                self._currentIndex += 1
            else:
                tok = self._buffer[self._currentIndex+location]
            return tok
        except IndexError:
            raise UnexpectedTokenException, 'The given location is out of range'

    def isvariable(self, tok):
        return tok not in Tokens.TOKENS
    
    def parse_Expression(self, allow_adjuncts=True):
        """Parse the next complete expression from the stream and return it."""
        tok = self.token()
        
        accum = self.handle(tok)
        
        if not accum:
            raise UnexpectedTokenException(tok)
        
        if allow_adjuncts:
            accum = self.attempt_ApplicationExpression(accum)
            accum = self.attempt_BooleanExpression(accum)
        
        return accum
    
    def handle(self, tok):
        """This method is intended to be overridden for logics that 
        use different operators or expressions"""
        if self.isvariable(tok):
            return self.handle_variable(tok)
        
        elif tok in Tokens.NOT:
            return self.handle_negation()
        
        elif tok in Tokens.LAMBDA:
            return self.handle_lambda(tok)
            
        elif tok in Tokens.QUANTS:
            return self.handle_quant(tok)
            
        elif tok == Tokens.OPEN:
            return self.handle_open(tok)
            
    def handle_negation(self):
        return self.make_NegatedExpression(self.parse_Expression(False))
        
    def make_NegatedExpression(self, expression):
        return NegatedExpression(expression)
        
    def handle_variable(self, tok):
        #It's either: 1) a predicate expression: sees(x,y)
        #             2) an application expression: P(x)
        #             3) a solo variable: john OR x
        accum = self.make_VariableExpression(tok)
        if self.inRange(0) and self.token(0) == Tokens.OPEN:
            #The predicate has arguments
            if is_indvar(tok):
                raise ParseException('\'%s\' is an illegal variable name.  '
                                     'Predicate variables may not be '
                                     'individual variables' % tok)
            self.token() #swallow the Open Paren
            
            #curry the arguments
            accum = self.make_ApplicationExpression(accum, 
                                                    self.parse_Expression())
            while self.token(0) == Tokens.COMMA:
                self.token() #swallow the comma
                accum = self.make_ApplicationExpression(accum, 
                                                        self.parse_Expression())
            self.assertToken(self.token(), Tokens.CLOSE)
        return self.attempt_EqualityExpression(accum)
        
    def handle_lambda(self, tok):
        # Expression is a lambda expression
        vars = [Variable(self.token())]
        while self.isvariable(self.token(0)):
            # Support expressions like: \x y.M == \x.\y.M
            vars.append(Variable(self.token()))
        self.assertToken(self.token(), Tokens.DOT)
        
        accum = self.parse_Expression(False)
        while vars:
            accum = self.make_LambdaExpression(vars.pop(), accum)
        return accum
        
    def get_QuantifiedExpression_factory(self, tok):
        """This method serves as a hook for other logic parsers that
        have different quantifiers"""
        factory = None
        if tok in Tokens.EXISTS:
            factory = ExistsExpression
        elif tok in Tokens.ALL:
            factory = AllExpression
        else:
            self.assertToken(tok, Tokens.QUANTS)
        return factory

    def handle_quant(self, tok):
        # Expression is a quantified expression: some x.M
        factory = self.get_QuantifiedExpression_factory(tok)

        vars = [self.token()]
        while self.isvariable(self.token(0)):
            # Support expressions like: some x y.M == some x.some y.M
            vars.append(self.token())
        self.assertToken(self.token(), Tokens.DOT)

        accum = self.parse_Expression(False)
        while vars:
            var = vars.pop()
            if not is_indvar(var):
                raise ParseException('\'%s\' is an illegal variable name.  '
                                     'Quantifier variables must be individual '
                                     'variables' % var)
            accum = factory(Variable(var), accum)
        return accum
        
    def handle_open(self, tok):
        #Expression is in parens
        accum = self.parse_Expression()
        self.assertToken(self.token(), Tokens.CLOSE)
        return accum
        
    def attempt_EqualityExpression(self, expression):
        """Attempt to make a boolean expression.  If the next token is a boolean 
        operator, then a BooleanExpression will be returned.  Otherwise, the 
        parameter will be returned."""
        if self.inRange(0) and self.token(0) in Tokens.EQ:
            self.token() #swallow the "="
            return self.make_EqualityExpression(expression, self.parse_Expression())
        return expression
    
    def make_EqualityExpression(self, first, second):
        """This method serves as a hook for other logic parsers that
        have different equality expression classes"""
        return EqualityExpression(first, second)

    def attempt_BooleanExpression(self, expression):
        """Attempt to make a boolean expression.  If the next token is a boolean 
        operator, then a BooleanExpression will be returned.  Otherwise, the 
        parameter will be returned."""
        if self.inRange(0):
            factory = self.get_BooleanExpression_factory()
            if factory: #if a factory was returned
                self.token() #swallow the operator
                return self.make_BooleanExpression(factory, expression, 
                                                   self.parse_Expression())
        #otherwise, no boolean expression can be created
        return expression
    
    def get_BooleanExpression_factory(self):
        """This method serves as a hook for other logic parsers that
        have different boolean operators"""
        factory = None
        op = self.token(0)
        if op in Tokens.AND:
            factory = AndExpression
        elif op in Tokens.OR:
            factory = OrExpression
        elif op in Tokens.IMP:
            factory = ImpExpression
        elif op in Tokens.IFF:
            factory = IffExpression
        return factory
    
    def make_BooleanExpression(self, type, first, second):
        """This method exists to be overridden by parsers
        with more complex logic for creating BooleanExpressions"""
        return type(first, second)
        
    def attempt_ApplicationExpression(self, expression):
        """Attempt to make an application expression.  The next tokens are
        a list of arguments in parens, then the argument expression is a
        function being applied to the arguments.  Otherwise, return the
        argument expression."""
        if self.inRange(0) and self.token(0) == Tokens.OPEN:
            if not isinstance(expression, LambdaExpression) and \
               not isinstance(expression, ApplicationExpression):
                raise ParseException("The function '" + str(expression) + 
                                     ' is not a Lambda Expression or an '
                                     'Application Expression, so it may not '
                                     'take arguments')
            self.token() #swallow then open paren
            #curry the arguments
            accum = self.make_ApplicationExpression(expression, 
                                                    self.parse_Expression())
            while self.token(0) == Tokens.COMMA:
                self.token() #swallow the comma
                accum = self.make_ApplicationExpression(accum, 
                                                        self.parse_Expression())
            self.assertToken(self.token(), Tokens.CLOSE)
            return self.attempt_ApplicationExpression(accum)
        else:
            return expression

    def make_ApplicationExpression(self, function, argument):
        return ApplicationExpression(function, argument)
    
    def make_VariableExpression(self, name):
        if is_indvar(name):
            return IndividualVariableExpression(Variable(name))
        else:
            return VariableExpression(Variable(name))
    
    def make_LambdaExpression(self, variable, term):
        return LambdaExpression(variable, term)
    
    def assertToken(self, tok, expected):
        if isinstance(expected, list):
            if tok not in expected:
                raise UnexpectedTokenException(tok, expected)
        else:
            if tok != expected:
                raise UnexpectedTokenException(tok, expected)

    def __repr__(self):
        if self.inRange(0):
            return 'Next token: ' + self.token(0)
        else:
            return 'No more tokens'

            
class StringTrie(dict):
    LEAF = "<leaf>" 

    def __init__(self, strings=None):
        if strings:
            for string in strings:
                self.insert(string)
    
    def insert(self, string):
        if len(string):
            k = string[0]
            if k not in self:
                self[k] = StringTrie()
            self[k].insert(string[1:])
        else:
            #mark the string is complete
            self[StringTrie.LEAF] = None 

class ParseException(Exception):
    def __init__(self, message):
        Exception.__init__(self, message)

class UnexpectedTokenException(ParseException):
    def __init__(self, tok, expected=None):
        if expected:
            ParseException.__init__(self, "parse error, unexpected token: %s.  "
                                    "Expected token: %s" % (tok, expected))
        else:
            ParseException.__init__(self, "parse error, unexpected token: %s" 
                                            % tok)
        
        
def is_indvar(expr):
    """
    An individual variable must be a single lowercase character followed by
    zero or more digits.
    
    @param expr: C{str}
    @return: C{boolean} True if expr is of the correct form 
    """
    try:
        return expr[0].isalpha() and expr[0].islower() and \
            (len(expr) == 1 or expr[1:].isdigit())
    except TypeError:
        return False

def demo():
    lp = LogicParser()
    print '='*20 + 'Test parser' + '='*20
    print lp.parse(r'john')
    print lp.parse(r'man(x)')
    print lp.parse(r'-man(x)')
    print lp.parse(r'(man(x) & tall(x) & walks(x))')
    print lp.parse(r'exists x.(man(x) & tall(x))')
    print lp.parse(r'\x.man(x)')
    print lp.parse(r'\x.man(x)(john)')
    print lp.parse(r'\x y.sees(x,y)')
    print lp.parse(r'\x  y.sees(x,y)(a,b)')
    print lp.parse(r'(\x.exists y.walks(x,y))(x)')
    print lp.parse(r'exists x.(x = john)')
    print lp.parse(r'\P Q.exists x.(P(x) & Q(x))')
    
    print '='*20 + 'Test simplify' + '='*20
    print lp.parse(r'\x.\y.sees(x,y)(john)(mary)').simplify()
    print lp.parse(r'\x.\y.sees(x,y)(john, mary)').simplify()
    print lp.parse(r'exists x.(man(x) & (\x.exists y.walks(x,y))(x))').simplify()
    print lp.parse(r'(\P.\Q.exists x.(P(x) & Q(x)))(\x.dog(x))(\x.bark(x))').simplify()
    
    print '='*20 + 'Test alpha conversion and binder expression equality' + '='*20
    e1 = lp.parse('exists x.P(x)')
    print e1
    e2 = e1.alpha_convert(VariableExpression('z'))
    print e2
    print e1 == e2
        
if __name__ == '__main__':
    demo()
