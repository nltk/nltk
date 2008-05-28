# Natural Language Toolkit: Logic
#
# Author: Daniel H. Garrette <dhgarrette@gmail.com>
#
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
A version of first order predicate logic, built on top of the untyped lambda calculus.
"""

from nltk.internals import Counter
from nltk.tokenize.simple import WhitespaceTokenizer

n = 1

_counter = Counter()

def unique_variable():
    return VariableExpression('z' + str(_counter.get()))

class Expression:
    def __call__(self, other):
        return self.applyto(other)
    
    def applyto(self, other):
        if not isinstance(other, list):
            other = [other]
        return ApplicationExpression(self, other)
    
    def __neg__(self):
        return NegatedExpression(self)
    
    def negate(self):
        return -self
    
    def __eq__(self, other):
        raise NotImplementedError()
    
    def __hash__(self):
        return hash(repr(self))
    
    def __repr__(self):
        return self.__class__.__name__ + ': ' + str(self)

class ApplicationExpression(Expression):
    """
    @param function: C{Expression}, for the function expression
    @param args: C{list} of C{Expression}, for the arguments   
    """
    def __init__(self, function, args):
        self.function = function
        self.args = args
        
    def simplify(self):
        function = self.function.simplify()
        args = [arg.simplify() for arg in self.args]

        if isinstance(function, LambdaExpression):
            if len(self.args) > len(function.variables):
                raise ParseException("The function %s abstracts %s variables but there are %s arguments: (%s)" 
                                     % (function, len(function.variables), len(self.args), 
                                        ','.join([str(arg) for arg in self.args])))
    
            term = function.term
            for (i,arg) in enumerate(args):
                term = term.replace(function.variables[i], arg)
            
            #If not all the abstracted variables were used in the application, keep them
            if i+1 < len(function.variables):
                return function.__class__(function.variables[i+1:], term.simplify())
            else:
                return term.simplify()
        else:
            return self.__class__(function, args)
        
    def replace(self, variable, expression, replace_bound=False):
        return self.__class__(self.function.replace(variable, expression, replace_bound),
                              [arg.replace(variable, expression, replace_bound)
                               for arg in self.args])
        
    def free(self):
        accum = self.function.free()
        for arg in self.args:
            accum |= arg.free()
        return accum
    
    def __eq__(self, other):
        return isinstance(other, self.__class__) and \
                self.function == other.function and self.args == other.args 

    def __str__(self):
        function = str(self.function)

        if isinstance(self.function, LambdaExpression):
            if isinstance(self.function.term, ApplicationExpression):
                if not isinstance(self.function.term.function, VariableExpression):
                    function = Tokens.OPEN + function + Tokens.CLOSE
            elif not isinstance(self.function.term, BooleanExpression):
                function = Tokens.OPEN + function + Tokens.CLOSE
                
        return function + Tokens.OPEN + \
               ','.join([str(arg) for arg in self.args]) + Tokens.CLOSE

class VariableExpression(Expression):
    """
    @param name: C{str}, for the variable name
    """
    def __init__(self, name):
        self.name = name

    def simplify(self):
        return self

    def replace(self, variable, expression, replace_bound=False):
        if self == variable:
            return expression
        else:
            return self
    
    def free(self):
        return set([self])
    
    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.name == other.name
        
    def __str__(self):
        return self.name
    
class LambdaExpression(Expression):
    """
    @param variable: C{list} of C{VariableExpression}, for the abstracted variables
    @param term: C{Expression}, for the term
    """
    def __init__(self, variables, term):
        self.variables = variables
        self.term = term

    def simplify(self):
        return self.__class__(self.variables, self.term.simplify())

    def replace(self, variable, expression, replace_bound=False):
        try:
            #if a bound variable is the thing being replaced
            i = self.variables.index(variable)
            if not replace_bound:
                return self
            else: 
                vars = self.variables[:i]+[expression]+self.variables[i+1:]
                return self.__class__(vars, self.term.replace(variable, expression, True))
        except ValueError:
            #variable not bound by this lambda
            
            # any bound variable that appears in the expression must
            # be alpha converted to avoid a confict
            for var in (set(self.variables) & expression.free()):
                newvar = unique_variable()
                i = self.variables.index(var)
                vars = self.variables[:i]+[newvar]+self.variables[i+1:]
                self = self.__class__(vars, self.term.replace(var, newvar, True))
                
            #replace in the term
            return self.__class__(self.variables,
                                  self.term.replace(variable, expression, replace_bound))

    def free(self):
        return self.term.free() - set(self.variables)

    def __eq__(self, other):
        return isinstance(other, self.__class__) \
                and self.variables == other.variables and self.term == other.term

    def __str__(self):
        return Tokens.LAMBDA[n] + ' '.join([str(v) for v in self.variables]) +\
               Tokens.DOT[n] + str(self.term)

class QuantifiedExpression(Expression):
    """
    @param variable: C{VariableExpression}, for the variable
    @param term: C{Expression}, for the term
    """
    def __init__(self, variable, term):
        self.variable = variable
        self.term = term

    def simplify(self):
        return self.__class__(self.variable, self.term.simplify())

    def replace(self, variable, expression, replace_bound=False):
        #if the bound variable is the thing being replaced
        if self.variable == variable:
            if replace_bound: 
                return self.__class__(expression, 
                                      self.term.replace(variable, expression, True))
            else: 
                return self
                
        else:
            # if the bound variable appears in the expression, then it must
            # be alpha converted to avoid a confict
            if self.variable in expression.free():
                self = self.alpha_convert(unique_variable())
                
            #replace in the term
            return self.__class__(self.variable,
                                  self.term.replace(variable, expression, replace_bound))

    def alpha_convert(self, newvar):
        """Rename all occurrences of the variable introduced by this variable
        binder in the expression to @C{newvar}."""
        return self.__class__(newvar, self.term.replace(self.variable, newvar, True))

    def free(self):
        return self.term.free() - set([self.variable])

    def __eq__(self, other):
        return isinstance(other, self.__class__) \
                and self.variable == other.variable and self.term == other.term

    def __str__(self):
        return self.getPredicate() + ' ' + str(self.variable) + Tokens.DOT[n] + str(self.term)
        
class ExistsExpression(QuantifiedExpression):
    def getPredicate(self):
        return Tokens.EXISTS[n]

class AllExpression(QuantifiedExpression):
    def getPredicate(self):
        return Tokens.ALL[n]

class NegatedExpression(Expression):
    def __init__(self, term):
        self.term = term
        
    def simplify(self):
        return self

    def replace(self, variable, expression, replace_bound=False):
        return self.__class__(self.term.replace(variable, expression, replace_bound))

    def free(self):
        return self.term.free()

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.term == other.term

    def __str__(self):
        return Tokens.NOT[n] + str(self.term)
        
class BooleanExpression(Expression):
    def __init__(self, first, second):
        self.first = first
        self.second = second
    
    def simplify(self):
        return self.__class__(self.first.simplify(), self.second.simplify())

    def replace(self, variable, expression, replace_bound=False):
        return self.__class__(self.first.replace(variable, expression, replace_bound),
                              self.second.replace(variable, expression, replace_bound))

    def free(self):
        return self.first.free() | self.second.free()

    def __eq__(self, other):
        return isinstance(other, self.__class__) \
                and self.first == other.first and self.second == other.second

    def __str__(self):
        return Tokens.OPEN + str(self.first) + ' ' + self.getOp() + ' ' + str(self.second) + Tokens.CLOSE
        
class AndExpression(BooleanExpression):
    def getOp(self):
        return Tokens.AND[n]

class OrExpression(BooleanExpression):
    def getOp(self):
        return Tokens.OR[n]

class ImpExpression(BooleanExpression):
    def getOp(self):
        return Tokens.IMP[n]

class IffExpression(BooleanExpression):
    def getOp(self):
        return Tokens.IFF[n]

class EqualityExpression(BooleanExpression):
    def getOp(self):
        return Tokens.EQ[n]

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
    BOOLS = AND + OR + IMP + IFF
    BINOPS = BOOLS + EQ
    QUANTS = EXISTS + ALL
    PUNCT = [DOT[0], OPEN, CLOSE, COMMA]
    
    TOKENS = BINOPS + QUANTS + LAMBDA + PUNCT + NOT
    
    #Special
    SYMBOLS = LAMBDA + PUNCT + [AND[1], OR[1], NOT[1], IMP[1], IFF[1]] + EQ 

class LogicParser:
    """A lambda calculus expression parser."""

    def __init__(self, data=None):
        """
        @param data: C{str}, a string to parse
        """
        self._currentIndex = 0
        self._buffer = []
        self.feed(data)

    def feed(self, data):
        """Feed another batch of data to the parser."""
        self._buffer += WhitespaceTokenizer().tokenize(self.process(data))
        
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
                assert isinstance(location,int) 
                tok = self._buffer[self._currentIndex+location]
            return tok
        except IndexError:
            raise UnexpectedTokenException, 'The given location is out of range'

    def parse(self, data):
        """
        Parse the expression.

        @type data: str
        @returns: a parsed Expression
        """
        self.feed(data)
        result = self.parse_Expression()
        if self.inRange(0):
            raise UnexpectedTokenException(self.token(0))
        return result

    def isvariable(self, tok):
        return tok not in Tokens.TOKENS
    
    def parse_Expression(self):
        """Parse the next complete expression from the stream and return it."""
        tok = self.token()
        
        if self.isvariable(tok):
            return self.handle_variable(tok)
        
        elif tok in Tokens.NOT:
            #it's a negated expression
            return NegatedExpression(self.parse_Expression())
        
        elif tok in Tokens.LAMBDA:
            return self.handle_lambda(tok)
            
        elif tok in Tokens.QUANTS:
            return self.handle_quant(tok)
            
        elif tok == Tokens.OPEN:
            return self.handle_open(tok)
        
        else:
            raise UnexpectedTokenException(tok)
        
    def handle_variable(self, tok):
        #It's either: 1) a predicate expression: sees(x,y)
        #             2) an application expression: P(x)
        #             3) a solo variable: john OR x
        if self.inRange(0) and self.token(0) == Tokens.OPEN:
            #The predicate has arguments
            self.token() #swallow the Open Paren
            
            #gather the arguments
            args = []
            if self.token(0) != Tokens.CLOSE:
                args.append(self.make_VariableExpression(self.token()))
                while self.token(0) == Tokens.COMMA:
                    self.token() #swallow the comma
                    args.append(self.parse_Expression())
            self.token() #swallow the close paren
            
            expression = self.make_ApplicationExpression(self.make_VariableExpression(tok), args)
            return self.attempt_BooleanExpression(expression)
        else:
            #The predicate has no arguments: it's a solo variable
            return self.make_VariableExpression(tok)
        
    def handle_lambda(self, tok):
        # Expression is a lambda expression: \x.M
        vars = [self.make_VariableExpression(self.token())]
        while self.isvariable(self.token(0)):
            # Support expressions like: \x y.M == \x.\y.M
            vars.append(self.make_VariableExpression(self.token()))
        self.assertToken(self.token(), Tokens.DOT)

        accum = self.make_LambdaExpression(vars, self.parse_Expression())
        accum = self.attempt_ApplicationExpression(accum)
        return self.attempt_BooleanExpression(accum)
        
    def handle_quant(self, tok):
        # Expression is a quantified expression: some x.M
        if tok in Tokens.EXISTS:
            factory = ExistsExpression
        elif tok in Tokens.ALL:
            factory = AllExpression
        else:
            self.assertToken(tok, Tokens.EXISTS + Tokens.ALL)

        vars = [self.token()]
        while self.isvariable(self.token(0)):
            # Support expressions like: some x y.M == some x.some y.M
            vars.append(self.token())
        self.assertToken(self.token(), Tokens.DOT)

        term = self.parse_Expression()
        accum = factory(self.make_VariableExpression(vars.pop()), term)
        while vars:
            accum = factory(self.make_VariableExpression(vars.pop()), accum)
        
        return self.attempt_BooleanExpression(accum)
        
    def handle_open(self, tok):
        #Expression is in parens
        newExpression = self.attempt_BooleanExpression(self.parse_Expression())
        self.assertToken(self.token(), Tokens.CLOSE)
        return self.attempt_ApplicationExpression(newExpression)
        
    def attempt_BooleanExpression(self, expression):
        """Attempt to make a boolean expression.  If the next token is a boolean 
        operator, then a BooleanExpression will be returned.  Otherwise, the 
        parameter will be returned."""
        if self.inRange(0):
            factory = self.get_BooleanExpression_factory()
            if factory: #if a factory was returned
                self.token() #swallow the operator
                return factory(expression, self.parse_Expression())
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
        elif op in Tokens.EQ:
            factory = EqualityExpression
        return factory
        
    def attempt_ApplicationExpression(self, expression):
        """Attempt to make an application expression.  The next tokens are
        a list of arguments in parens, then the argument expression is a
        function being applied to the arguments.  Otherwise, return the
        argument expression."""
        if self.inRange(0) and self.token(0) == Tokens.OPEN:
            if not isinstance(expression, LambdaExpression) and \
               not isinstance(expression, ApplicationExpression):
                raise ParseException("The function '" + str(expression) + 
                                     "' is not a Lambda Expression or an Application Expression, so it may not take arguments")
        
            self.token() #swallow then open paren
            args = []
            if self.token(0) != Tokens.CLOSE:
                args.append(self.parse_Expression())
                while self.token(0) == Tokens.COMMA:
                    self.token() #swallow the comma
                    args.append(self.parse_Expression())
            
            self.token() #swallow the close paren
            return self.make_ApplicationExpression(expression, args) 
        else:
            return expression

    def make_ApplicationExpression(self, function, args):
        return ApplicationExpression(function, args)
    
    def make_VariableExpression(self, name):
        return VariableExpression(name)
    
    def make_LambdaExpression(self, variables, term):
        return LambdaExpression(variables, term)
    
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

class UnexpectedTokenException(Exception):
    def __init__(self, tok, expected=None):
        if expected:
            Exception.__init__(self, "parse error, unexpected token: %s.  Expected token: %s" % (tok, expected))
        else:
            Exception.__init__(self, "parse error, unexpected token: %s" % tok)
        
        
###############################
#TODO: DELETE ALL
################################
class Error: pass
class Variable: pass
def is_indvar(): pass
class SubstituteBindingsI: pass
class Operator: pass


class TestSuite:
    def __init__(self):
        self.count = 0
        self.failures = 0
    
    def run(self):
        self.count = 0
        self.failures = 0
        
        self.test_parser()
        self.test_simplify()
        self.test_process()
        self.test_replace()
        
        print '='*55
        print 'Tests:    %s' % self.count
        print 'Failures: %s' % self.failures

    def assert_equal(self, input, result, expected):
        self.count += 1
        
        alert = ''
        if result==expected: 
            print '[%s] %s\n\t%s' % (self.count, input, result)
        else:
            print '[%s] %s\n\t%s != %s %s' % (self.count, input, expected, result, '*'*50)
            self.failures += 1
    
    def test_parser(self):
        n = Tokens.NEW_NLTK
        print '='*20 + 'TEST PARSE' + '='*20
        self.parse_test(r'man(x)')
        self.parse_test(r'-man(x)')
        self.parse_test(r'--man(x)')
        self.parse_test(r'(man(x))', r'man(x)')
        self.parse_test(r'((man(x)))', r'man(x)')
        self.parse_test(r'man(x) <-> tall(x)', r'(man(x) <-> tall(x))')
        self.parse_test(r'(man(x) <-> tall(x))')
        self.parse_test(r'(man(x) & tall(x) & walks(x))', r'(man(x) & (tall(x) & walks(x)))')
        self.parse_test(r'((man(x) & tall(x)) & walks(x))')
        self.parse_test(r'(man(x) & (tall(x) & walks(x)))')
        self.parse_test(r'exists x.man(x)')
        self.parse_test(r'exists x.(man(x) & tall(x))')
        self.parse_test(r'\x.man(x)')
        self.parse_test(r'john')
        self.parse_test(r'\x.man(x)(john)')
        self.parse_test(r'\x.man(x)(john) & tall(x)', r'(\x.man(x)(john) & tall(x))')
        self.parse_test(r'\x y.sees(x,y)(john)')
        self.parse_test(r'\x.\y.sees(x,y)(john)')
        self.parse_test(r'\x.\y.sees(x,y)(john)(mary)', r'(\x.\y.sees(x,y)(john))(mary)')
        self.parse_test(r'\x y.sees(x,y)(john, mary)', r'\x y.sees(x,y)(john,mary)')
        self.parse_test(r'P(Q)')
        self.parse_test(r'(\x.exists y.walks(x,y))(x)')
        self.parse_test(r'exists x.(x = john)')
            
    def parse_test(self, f, expected=None, throw=False):
        if not expected:
            expected = f
        try:
            p = LogicParser().parse(f)
        except Exception, e:
            if throw:
                raise
            else:
                p = e.__class__.__name__ + ': ' + e.message
        self.assert_equal(f, str(p), expected)
        
    def test_simplify(self):
        n = Tokens.NEW_NLTK
        print '='*20 + 'TEST SIMPLIFY' + '='*20
        self.simplify_test(r'\x.man(x)(john)', r'man(john)')
        self.simplify_test(r'\x y.sees(x,y)(john, mary)', r'sees(john,mary)')
        self.simplify_test(r'\x.\y.sees(x,y)(john, mary)', r'ParseException: The function \y.sees(x,y) abstracts 1 variables but there are 2 arguments: (john,mary)')
        self.simplify_test(r'\x.\y.sees(x,y)(mary)(john)', r'sees(john,mary)')
        self.simplify_test(r'(\x.\y.sees(x,y)(mary))(john)', r'sees(john,mary)')
        self.simplify_test(r'\x y.sees(x,y)(mary)(john)', r'UnexpectedTokenException: parse error, unexpected token: (')
        self.simplify_test(r'\x y.sees(x,y)(john)', r'\y.sees(john,y)')
        self.simplify_test(r'(\x y.sees(x,y)(john))(mary)', r'sees(john,mary)')
        self.simplify_test(r'exists x.(man(x) & (\x.exists y.walks(x,y))(x))', r'exists x.(man(x) & exists y.walks(x,y))')
        self.simplify_test(r'exists x.(man(x) & (\x.exists y.walks(x,y))(y))', r'exists x.(man(x) & exists z1.walks(y,z1))')
    
    def simplify_test(self, f, expected=None, throw=False):
        if not expected:
            expected = f
        try:
            p = LogicParser().parse(f).simplify()
        except Exception, e:
            if throw:
                raise
            else:
                p = e.__class__.__name__ + ': ' + e.message
        self.assert_equal(f, str(p), expected)
        
    def test_process(self):
        print '='*20 + 'TEST PROCESS' + '='*20
        input = '&->X-X<->X'
        self.assert_equal(input, LogicParser().process(input), ' &  -> X - X <-> X')
    
    def test_replace(self):
        n = Tokens.NEW_NLTK
        print '='*20 + 'TEST REPLACE' + '='*20
        self.replace_test(r'man(x)', 'x', 'a', False, 'man(a)')
        self.replace_test(r'(man(x) & tall(x))', 'x', 'a', False, r'(man(a) & tall(a))')
        self.replace_test(r'exists x.man(x)', 'x', 'a', False, r'exists x.man(x)')
        self.replace_test(r'exists x.man(x)', 'x', 'a', True, r'exists a.man(a)')
        self.replace_test(r'exists x.give(x,y,z)', 'y', 'a', False, r'exists x.give(x,a,z)')
        self.replace_test(r'exists x.give(x,y,z)', 'y', 'a', True, r'exists x.give(x,a,z)')
        self.replace_test(r'exists x.give(x,y,z)', 'y', 'x', False, r'exists z1.give(z1,x,z)')
        self.replace_test(r'exists x.give(x,y,z)', 'y', 'x', True, r'exists z1.give(z1,x,z)')
        self.replace_test(r'\x y z.give(x,y,z)', 'y', 'a', False, r'\x y z.give(x,y,z)')
        self.replace_test(r'\x y z.give(x,y,z)', 'y', 'a', True, r'\x a z.give(x,a,z)')
        self.replace_test(r'\x y.give(x,y,z)', 'z', 'a', False, r'\x y.give(x,y,a)')
        self.replace_test(r'\x y.give(x,y,z)', 'z', 'a', True, r'\x y.give(x,y,a)')
        self.replace_test(r'\x y.give(x,y,z)', 'z', 'x', False, r'\z1 y.give(z1,y,x)')
        self.replace_test(r'\x y.give(x,y,z)', 'z', 'x', True, r'\z1 y.give(z1,y,x)')
        self.replace_test(r'\x.give(x,y,z)', 'z', 'y', False, r'\x.give(x,y,y)')
        self.replace_test(r'\x.give(x,y,z)', 'z', 'y', True, r'\x.give(x,y,y)')
    
    def replace_test(self, e, v, r, replace_bound, expected=None, throw=False):
        _counter._value = 0
        if not expected:
            expected = f
            
        try:
            ex = LogicParser().parse(e)
            var = LogicParser().parse(v)
            rep = LogicParser().parse(r)
            result = ex.replace(var, rep, replace_bound)
        except Exception, err:
            if throw:
                raise
            else:
                result = err.message
        self.assert_equal('%s, %s, %s, %s' % (e,v,r,replace_bound), str(result), expected)

if __name__ == '__main__':
    TestSuite().run()
