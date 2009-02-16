# Natural Language Toolkit: Logic
#
# Author: Dan Garrette <dhgarrette@gmail.com>
#
# URL: <http://www.nltk.org>
# For license information, see LICENSE.TXT

"""
A version of first order predicate logic, built on 
top of the typed lambda calculus.
"""

import re
import operator

from nltk import defaultdict
from nltk.internals import Counter

_counter = Counter()

class Tokens(object):
    # Syntaxes
    OLD_NLTK = 0
    NLTK = 1
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
    NEQ = ['!=', '!=', '!=']
    
    #Collection of tokens
    BINOPS = AND + OR + IMP + IFF
    QUANTS = EXISTS + ALL
    PUNCT = [DOT[NLTK], OPEN, CLOSE, COMMA]
    
    TOKENS = BINOPS + EQ + NEQ + QUANTS + LAMBDA + PUNCT + NOT
    
    #Special
    SYMBOLS = LAMBDA + PUNCT + EQ + NEQ + \
              [AND[NLTK], OR[NLTK], NOT[NLTK], IMP[NLTK], IFF[NLTK]]
               

def boolean_ops():
    """
    Boolean operators
    """
    names =  ["negation", "conjunction", "disjunction", "implication", "equivalence"]
    for pair in zip(names, [Tokens.NOT[Tokens.NLTK], 
                            Tokens.AND[Tokens.NLTK], 
                            Tokens.OR[Tokens.NLTK], 
                            Tokens.IMP[Tokens.NLTK], 
                            Tokens.IFF[Tokens.NLTK]]):
        print "%-15s\t%s" %  pair
        
def equality_preds():
    """
    Equality predicates
    """
    names =  ["equality", "inequality"]
    for pair in zip(names, [Tokens.EQ[Tokens.NLTK], 
                            Tokens.NEQ[Tokens.NLTK]]):
        print "%-15s\t%s" %  pair        
                    
def binding_ops():
    """
    Binding operators
    """
    names =  ["existential", "universal", "lambda"]
    for pair in zip(names, [Tokens.EXISTS[Tokens.NLTK], 
                            Tokens.ALL[Tokens.NLTK],
                            Tokens.LAMBDA[Tokens.NLTK]]):
        print "%-15s\t%s" %  pair


class Variable(object):
    def __init__(self, name):
        """
        @param name: the name of the variable
        """
        assert isinstance(name, str), "%s is not a string" % name
        self.name = name

    def __eq__(self, other):
        return isinstance(other, Variable) and self.name == other.name
    
    def __neq__(self, other):
        return not (self == other)

    def __cmp__(self, other):
        assert isinstance(other, Variable), "%s is not a Variable" % other
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


def unique_variable(pattern=None):
    """
    param pattern: C{Variable} that is being replaced.  The new variable must
    be the same type.
    """
    if pattern is not None and is_eventvar(pattern.name):
        prefix = 'e0'
    else:
        prefix = 'z'
    return Variable(prefix + str(_counter.get()))

def skolem_function(univ_scope=None):
    """
    Return a skolem function over the variables in univ_scope
    param univ_scope
    """
    skolem = VariableExpression(Variable('F%s' % _counter.get()))
    if univ_scope:
        for v in list(univ_scope):
            skolem = skolem(VariableExpression(v))
    return skolem


class Type:
    def __repr__(self):
        return str(self)
    
    def __hash__(self):
        return hash(str(self))
    
class ComplexType(Type):
    def __init__(self, first, second):
        assert(isinstance(first, Type)), "%s is not a Type" % first
        assert(isinstance(second, Type)), "%s is not a Type" % second
        self.first = first
        self.second = second
    
    def __eq__(self, other):
        return isinstance(other, ComplexType) and \
               self.first == other.first and \
               self.second == other.second
    
    def matches(self, other):
        if isinstance(other, ComplexType):
            return self.first.matches(other.first) and \
                   self.second.matches(other.second)
        else:
            return self == ANY_TYPE
               
    def resolve(self, other):
        if other == ANY_TYPE:
           return self
        elif isinstance(other, ComplexType):
            f = self.first.resolve(other.first)
            s = self.second.resolve(other.second)
            if f and s:
                return ComplexType(f,s)
            else:
                return None
        elif self == ANY_TYPE:
            return other
        else:
            return None

    def __str__(self):
        if self == ANY_TYPE:
            return str(ANY_TYPE)
        else:
            return '<%s,%s>' % (self.first, self.second)

    def str(self):
        if self == ANY_TYPE:
            return ANY_TYPE.str()
        else:
            return '(%s -> %s)' % (self.first.str(), self.second.str())
    
class BasicType(Type):
    def __eq__(self, other):
        return isinstance(other, BasicType) and str(self) == str(other)
    
    def matches(self, other):
        return other == ANY_TYPE or self == other
    
    def resolve(self, other):
        if self.matches(other):
            return self
        else:
            return None

class EntityType(BasicType):
    def __str__(self):
        return 'e'
    
    def str(self):
        return 'IND'
    
class TruthValueType(BasicType):
    def __str__(self):
        return 't'

    def str(self):
        return 'BOOL'
    
class EventType(BasicType):
    def __str__(self):
        return 'v'

    def str(self):
        return 'EVENT'
    
class AnyType(BasicType, ComplexType):
    def __init__(self):
        pass
    
    first = property(lambda self: self)
    second = property(lambda self: self)
    
    def __eq__(self, other):
        return isinstance(other, AnyType) or other == self
    
    def matches(self, other):
        return True
    
    def resolve(self, other):
        return other

    def __str__(self):
        return '?'

    def str(self):
        return 'ANY'
    

TRUTH_TYPE = TruthValueType()
ENTITY_TYPE = EntityType()
EVENT_TYPE = EventType()
ANY_TYPE = AnyType()


def parse_type(type_string):
    assert isinstance(type_string, str)
    type_string = type_string.replace(' ', '') #remove spaces
    
    if type_string[0] == '<':
        assert type_string[-1] == '>'
        paren_count = 0
        for i,char in enumerate(type_string):
            if char == '<':
                paren_count += 1
            elif char == '>':
                paren_count -= 1
                assert paren_count > 0
            elif char == ',':
                if paren_count == 1:
                    break
        return ComplexType(parse_type(type_string[1  :i ]),
                           parse_type(type_string[i+1:-1]))
    elif type_string[0] == str(ENTITY_TYPE):
        return ENTITY_TYPE
    elif type_string[0] == str(TRUTH_TYPE):
        return TRUTH_TYPE
    elif type_string[0] == str(ANY_TYPE):
        return ANY_TYPE
    else:
        raise ParseException("Unexpected character: '%s'." % type_string[0])


class TypeException(Exception):
    def __init__(self, msg):
        Exception.__init__(self, msg)
    
class InconsistentTypeHierarchyException(TypeException):
    def __init__(self, variable, expression=None):
        if expression:
            msg = "The variable \'%s\' was found in multiple places with different"\
                " types in \'%s\'." % (variable, expression)
        else:
            msg = "The variable \'%s\' was found in multiple places with different"\
                " types." % (variable)
        Exception.__init__(self, msg)

class TypeResolutionException(TypeException):
    def __init__(self, expression, other_type):
        Exception.__init__(self, "The type of '%s', '%s', cannot be "
                           "resolved with type '%s'" % \
                           (expression, expression.type, other_type))

class IllegalTypeException(TypeException):
    def __init__(self, expression, other_type, allowed_type):
        Exception.__init__(self, "Cannot set type of %s '%s' to '%s'; "
                           "must match type '%s'." % 
                           (expression.__class__.__name__, expression, 
                            other_type, allowed_type))


def typecheck(expressions, signature=None):
    """
    Ensure correct typing across a collection of C{Expression}s.
    @param expressions: a collection of expressions
    @param signature: C{dict} that maps variable names to types (or string 
    representations of types)
    """
    #typecheck and create master signature
    for expression in expressions:
        signature = expression.typecheck(signature)
    #apply master signature to all expressions 
    for expression in expressions[:-1]:
        expression.typecheck(signature)
    return signature


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
        assert isinstance(other, Expression), "%s is not an Expression" % other
        return ApplicationExpression(self, other)
    
    def __neg__(self):
        return NegatedExpression(self)
    
    def negate(self):
        """If this is a negated expression, remove the negation.  
        Otherwise add a negation."""
        return -self
    
    def __and__(self, other):
        assert isinstance(other, Expression), "%s is not an Expression" % other
        return AndExpression(self, other)
    
    def __or__(self, other):
        assert isinstance(other, Expression), "%s is not an Expression" % other
        return OrExpression(self, other)
    
    def __gt__(self, other):
        assert isinstance(other, Expression), "%s is not an Expression" % other
        return ImpExpression(self, other)
    
    def __lt__(self, other):
        assert isinstance(other, Expression), "%s is not an Expression" % other
        return IffExpression(self, other)
    
    def __eq__(self, other):
        raise NotImplementedError()
    
    def __neq__(self, other):
        return not (self == other)
    
    def tp_equals(self, other, prover=None):
        """Pass the expression (self <-> other) to the theorem prover.   
        If the prover says it is valid, then the self and other are equal."""
        assert isinstance(other, Expression), "%s is not an Expression" % other
        
        if prover is None:
            from nltk.inference import Prover9
            prover = Prover9()
        bicond = IffExpression(self.simplify(), other.simplify())
        return prover.prove(bicond)

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
                    raise ValueError('Can not substitute a non-expression '
                                     'value into an expression: %r' % (val,))
                # Substitute bindings in the target value.
                val = val.substitute_bindings(bindings)
                # Replace var w/ the target value.
                expr = expr.replace(var, val)
        return expr.simplify()

    def typecheck(self, signature=None):
        """
        Infer and check types.  Raise exceptions if necessary.
        @param signature: C{dict} that maps variable names to types (or string 
        representations of types)
        @return: the signature, plus any additional type mappings 
        """
        sig = defaultdict(list)
        if signature:
            for (key, val) in signature.iteritems():
                varEx = VariableExpression(Variable(key))
                if isinstance(val, Type):
                    varEx.type = val
                else:
                    varEx.type = parse_type(val)
                sig[key].append(varEx)

        self._set_type(signature=sig)
        
        return dict([(key, vars[0].type) for (key, vars) in sig.iteritems()])
    
    def findtype(self, variable):
        """
        Find the type of the given variable as it is used in this expression.
        For example, finding the type of "P" in "P(x) & Q(x,y)" yields "<e,t>"
        @param variable: C{Variable}  
        """
        raise NotImplementedError() 
    
    def _set_type(self, other_type=ANY_TYPE, signature=None):
        """
        Set the type of this expression to be the given type.  Raise type 
        exceptions where applicable.
        @param other_type: C{Type} to set
        @param signature: C{dict<str, list<AbstractVariableExpression>>} store 
        all variable expressions with a given name
        """
        raise NotImplementedError()
    
    def replace(self, variable, expression, replace_bound=False):
        """
        Replace every instance of 'variable' with 'expression'
        @param variable: C{Variable} The variable to replace
        @param expression: C{Expression} The expression with which to replace it
        @param replace_bound: C{boolean} Should bound variables be replaced?  
        """
        assert isinstance(variable, Variable), "%s is not a Variable" % variable
        assert isinstance(expression, Expression), "%s is not an Expression" % expression

        def combinator(a, *additional):
            if len(additional) == 0:
                return self.__class__(a)
            elif len(additional) == 1:
                return self.__class__(a, additional[0])
        
        return self.visit(lambda e: e.replace(variable, expression, replace_bound), 
                          combinator, set())
    
    def normalize(self):
        """Rename auto-generated unique variables"""
        def f(e):
            if isinstance(e,Variable):
                if re.match(r'^z\d+$', e.name) or re.match(r'^e0\d+$', e.name):
                    return set([e])
                else:
                    return set([])
            else: 
                combinator = lambda *parts: reduce(operator.or_, parts)
                return e.visit(f, combinator, set())
        
        result = self
        for i,v in enumerate(sorted(list(f(self)))):
            if is_eventvar(v.name):
                newVar = 'e0%s' % (i+1)
            else:
                newVar = 'z%s' % (i+1)
            result = result.replace(v, VariableExpression(Variable(newVar)), True)
        return result
    
    def visit(self, function, combinator, default):
        """
        Recursively visit sub expressions
        @param function: C{Function} to call on each sub expression
        @param combinator: C{Function} to combine the results of the 
        function calls
        @return: result of combination
        """
        raise NotImplementedError()

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self)
    
    def __str__(self):
        return self.str()

    def variables(self):
        """
        Return a set of all the variables that are available to be replaced.
        This includes free (non-bound) variables as well as predicates.
        @return: C{set} of C{Variable}s
        """
        return self.visit(lambda e: isinstance(e,Variable) and 
                          set([e]) or e.variables(), 
                          lambda *parts: reduce(operator.or_, parts), set())

    def free(self, indvar_only=True):
        """
        Return a set of all the free (non-bound) variables in self.  Variables
        serving as predicates are not included.
        @param indvar_only: C{boolean} only return individual variables?
        @return: C{set} of C{Variable}s
        """
        return self.visit(lambda e: isinstance(e,Variable) and 
                          set([e]) or e.free(indvar_only), 
                          lambda *parts: reduce(operator.or_, parts), set())

    def simplify(self):
        """
        @return: beta-converted version of this expression
        """
        def combinator(a, *additional):
            if len(additional) == 0:
                return self.__class__(a)
            elif len(additional) == 1:
                return self.__class__(a, additional[0])
        
        return self.visit(lambda e: isinstance(e,Variable) 
                          and e or e.simplify(), combinator, set())


class ApplicationExpression(Expression):
    r"""
    This class is used to represent two related types of logical expressions.
    
    The first is a Predicate Expression, such as "P(x,y)".  A predicate 
    expression is comprised of a C{FunctionVariableExpression} or 
    C{ConstantExpression} as the predicate and a list of Expressions as the 
    arguments.
    
    The second is a an application of one expression to another, such as 
    "(\x.dog(x))(fido)".
    
    The reason Predicate Expressions are treated as Application Expressions is
    that the Variable Expression predicate of the expression may be replaced 
    with another Expression, such as a LambdaExpression, which would mean that 
    the Predicate should be thought of as being applied to the arguments.
    
    The LogicParser will always curry arguments in a application expression.
    So, "\x y.see(x,y)(john,mary)" will be represented internally as 
    "((\x y.(see(x))(y))(john))(mary)".  This simplifies the internals since 
    there will always be exactly one argument in an application.
    
    The str() method will usually print the curried forms of application 
    expressions.  The one exception is when the the application expression is
    really a predicate expression (ie, underlying function is an 
    C{AbstractVariableExpression}).  This means that the example from above  
    will be returned as "(\x y.see(x,y)(john))(mary)".
    """
    def __init__(self, function, argument):
        """
        @param function: C{Expression}, for the function expression
        @param argument: C{Expression}, for the argument   
        """
        assert isinstance(function, Expression), "%s is not an Expression" % function
        assert isinstance(argument, Expression), "%s is not an Expression" % argument
        self.function = function
        self.argument = argument
        
    def simplify(self):
        function = self.function.simplify()
        argument = self.argument.simplify()
        if isinstance(function, LambdaExpression):
            return function.term.replace(function.variable, argument).simplify()
        else:
            return self.__class__(function, argument)
        
    def free(self, indvar_only=True):
        """@see: Expression.free()"""
        if isinstance(self.function, AbstractVariableExpression):
            return self.argument.free(indvar_only)
        else:
            return self.function.free(indvar_only) | \
                   self.argument.free(indvar_only) 
    
    def _get_type(self):
        if isinstance(self.function.type, ComplexType):
            return self.function.type.second
        else:
            return ANY_TYPE
            
    type = property(_get_type)
    
    def _set_type(self, other_type=ANY_TYPE, signature=None):
        """@see Expression._set_type()"""
        assert isinstance(other_type, Type)
        
        if signature == None:
            signature = defaultdict(list)
        
        self.argument._set_type(ANY_TYPE, signature)
        try:
            self.function._set_type(ComplexType(self.argument.type, other_type), signature)
        except TypeResolutionException, e:
            raise TypeException(
                    "The function '%s' is of type '%s' and cannot be applied " 
                    "to '%s' of type '%s'.  Its argument must match type '%s'."
                    % (self.function, self.function.type, self.argument, 
                       self.argument.type, self.function.type.first))

    def findtype(self, variable):
        """@see Expression.findtype()"""
        assert isinstance(variable, Variable), "%s is not a Variable" % variable
        function, args = self.uncurry()
        if not isinstance(function, AbstractVariableExpression):
            #It's not a predicate expression ("P(x,y)"), so leave args curried
            function = self.function
            args = [self.argument]
        
        found = [arg.findtype(variable) for arg in [function]+args]
        
        unique = []
        for f in found:
            if f != ANY_TYPE:
                if unique:
                    for u in unique:
                        if f.matches(u):
                            break
                else:
                    unique.append(f)
            
        if len(unique) == 1:
            return list(unique)[0]
        else:
            return ANY_TYPE
        
    def visit(self, function, combinator, default):
        """@see: Expression.visit()"""
        return combinator(function(self.function), function(self.argument))
        
    def __eq__(self, other):
        return isinstance(other, ApplicationExpression) and \
                self.function == other.function and \
                self.argument == other.argument 

    def str(self, syntax=Tokens.NLTK):
        # uncurry the arguments and find the base function
        function, args = self.uncurry()
        if isinstance(function, AbstractVariableExpression):
            #It's a predicate expression ("P(x,y)"), so uncurry arguments
            arg_str = ','.join([arg.str(syntax) for arg in args])
        else:
            #Leave arguments curried
            function = self.function
            arg_str = self.argument.str(syntax)
        
        function_str = function.str(syntax)
        parenthesize_function = False
        if isinstance(function, LambdaExpression):
            if isinstance(function.term, ApplicationExpression):
                if not isinstance(function.term.function, 
                                  AbstractVariableExpression):
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
        Uncurry this application expression
        
        return: A tuple (base-function, arg-list)
        """
        function = self.function
        args = [self.argument]
        while isinstance(function, ApplicationExpression):
            #(\x.\y.sees(x,y)(john))(mary)
            args.insert(0, function.argument)
            function = function.function
        return (function, args)
    
    args = property(lambda self: self.uncurry()[1], doc="uncurried arg-list")

class AbstractVariableExpression(Expression):
    """This class represents a variable to be used as a predicate or entity"""
    def __init__(self, variable):
        """
        @param variable: C{Variable}, for the variable
        """
        assert isinstance(variable, Variable), "%s is not a Variable" % variable
        self.variable = variable

    def simplify(self):
        return self

    def replace(self, variable, expression, replace_bound=False):
        """@see: Expression.replace()"""
        assert isinstance(variable, Variable), "%s is not an Variable" % variable
        assert isinstance(expression, Expression), "%s is not an Expression" % expression
        if self.variable == variable:
            return expression
        else:
            return self
    
    def _set_type(self, other_type=ANY_TYPE, signature=None):
        """@see Expression._set_type()"""
        assert isinstance(other_type, Type)
        
        if signature == None:
            signature = defaultdict(list)
        
        resolution = other_type
        for varEx in signature[self.variable.name]:
            resolution = varEx.type.resolve(resolution)
            if not resolution:
                raise InconsistentTypeHierarchyException(self)
            
        signature[self.variable.name].append(self)
        for varEx in signature[self.variable.name]:
            varEx.type = resolution

    def findtype(self, variable):
        """@see Expression.findtype()"""
        assert isinstance(variable, Variable), "%s is not a Variable" % variable
        if self.variable == variable:
            return self.type
        else:
            return ANY_TYPE

    def visit(self, function, combinator, default):
        """@see: Expression.visit()"""
        return combinator(function(self.variable))

    def __eq__(self, other):
        """Allow equality between instances of C{AbstractVariableExpression} 
        subtypes."""
        return isinstance(other, AbstractVariableExpression) and \
               self.variable == other.variable
        
    def str(self, syntax=Tokens.NLTK):
        return str(self.variable)
    
    
class IndividualVariableExpression(AbstractVariableExpression):
    """This class represents variables that take the form of a single lowercase
    character (other than 'e') followed by zero or more digits."""
    def _set_type(self, other_type=ANY_TYPE, signature=None):
        """@see Expression._set_type()"""
        assert isinstance(other_type, Type)
        
        if signature == None:
            signature = defaultdict(list)

        if not other_type.matches(ENTITY_TYPE):
            raise IllegalTypeException(self, other_type, ENTITY_TYPE)
            
        signature[self.variable.name].append(self)
                
    type = property(lambda self: ENTITY_TYPE, _set_type)

class FunctionVariableExpression(AbstractVariableExpression):
    """This class represents variables that take the form of a single uppercase
    character followed by zero or more digits."""
    type = ANY_TYPE

    def free(self, indvar_only=True):
        """@see: Expression.free()"""
        if not indvar_only: 
            return set([self.variable])
        else: 
            return set()
    
class EventVariableExpression(IndividualVariableExpression):
    """This class represents variables that take the form of a single lowercase
    'e' character followed by zero or more digits."""
    type = EVENT_TYPE

class ConstantExpression(AbstractVariableExpression):
    """This class represents variables that do not take the form of a single
    character followed by zero or more digits."""
    type = ENTITY_TYPE

    def _set_type(self, other_type=ANY_TYPE, signature=None):
        """@see Expression._set_type()"""
        assert isinstance(other_type, Type)
        
        if signature == None:
            signature = defaultdict(list)
        
        if other_type == ANY_TYPE:
            #entity type by default, for individuals
            resolution = ENTITY_TYPE
        else:
            resolution = other_type
            if self.type != ENTITY_TYPE:
                resolution = resolution.resolve(self.type)
            
        for varEx in signature[self.variable.name]:
            resolution = varEx.type.resolve(resolution)
            if not resolution:
                raise InconsistentTypeHierarchyException(self)
            
        signature[self.variable.name].append(self)
        for varEx in signature[self.variable.name]:
            varEx.type = resolution

    def free(self, indvar_only=True):
        """@see: Expression.free()"""
        if not indvar_only: 
            return set([self.variable])
        else: 
            return set()


def VariableExpression(variable):
    """
    This is a factory method that instantiates and returns a subtype of 
    C{AbstractVariableExpression} appropriate for the given variable.
    """
    assert isinstance(variable, Variable), "%s is not a Variable" % variable
    if is_indvar(variable.name):
        return IndividualVariableExpression(variable)
    elif is_funcvar(variable.name):
        return FunctionVariableExpression(variable)
    elif is_eventvar(variable.name):
        return EventVariableExpression(variable)
    else:
        return ConstantExpression(variable)

    
class VariableBinderExpression(Expression):
    """This an abstract class for any Expression that binds a variable in an
    Expression.  This includes LambdaExpressions and Quantified Expressions"""
    def __init__(self, variable, term):
        """
        @param variable: C{Variable}, for the variable
        @param term: C{Expression}, for the term
        """
        assert isinstance(variable, Variable), "%s is not a Variable" % variable
        assert isinstance(term, Expression), "%s is not an Expression" % term
        self.variable = variable
        self.term = term

    def replace(self, variable, expression, replace_bound=False):
        """@see: Expression.replace()"""
        assert isinstance(variable, Variable), "%s is not a Variable" % variable
        assert isinstance(expression, Expression), "%s is not an Expression" % expression
        #if the bound variable is the thing being replaced
        if self.variable == variable:
            if replace_bound: 
                assert isinstance(expression, AbstractVariableExpression),\
                       "%s is not a AbstractVariableExpression" % expression
                return self.__class__(expression.variable, 
                                      self.term.replace(variable, expression, True))
            else: 
                return self
        else:
            # if the bound variable appears in the expression, then it must
            # be alpha converted to avoid a conflict
            if self.variable in expression.free():
                self = self.alpha_convert(unique_variable(self.variable))
                
            #replace in the term
            return self.__class__(self.variable,
                                  self.term.replace(variable, expression, replace_bound))

    def alpha_convert(self, newvar):
        """Rename all occurrences of the variable introduced by this variable
        binder in the expression to @C{newvar}.
        @param newvar: C{Variable}, for the new variable
        """
        assert isinstance(newvar, Variable), "%s is not a Variable" % newvar
        return self.__class__(newvar, 
                              self.term.replace(self.variable, 
                                                VariableExpression(newvar), 
                                                True))

    def variables(self):
        """@see: Expression.variables()"""
        return self.term.variables() - set([self.variable])

    def free(self, indvar_only=True):
        """@see: Expression.free()"""
        return self.term.free(indvar_only) - set([self.variable])

    def findtype(self, variable):
        """@see Expression.findtype()"""
        assert isinstance(variable, Variable), "%s is not a Variable" % variable
        if variable == self.variable:
            return ANY_TYPE
        else:
            return self.term.findtype(variable)

    def visit(self, function, combinator, default):
        """@see: Expression.visit()"""
        return combinator(function(self.variable), function(self.term))
        
    def __eq__(self, other):
        r"""Defines equality modulo alphabetic variance.  If we are comparing 
        \x.M  and \y.N, then check equality of M and N[x/y]."""
        if isinstance(self, other.__class__) or \
           isinstance(other, self.__class__):
            if self.variable == other.variable:
                return self.term == other.term
            else:
                # Comparing \x.M  and \y.N.  Relabel y in N with x and continue.
                varex = VariableExpression(self.variable)
                return self.term == other.term.replace(other.variable, varex)
        else:
            return False


class LambdaExpression(VariableBinderExpression):
    type = property(lambda self: 
                    ComplexType(self.term.findtype(self.variable), 
                                self.term.type))

    def _set_type(self, other_type=ANY_TYPE, signature=None):
        """@see Expression._set_type()"""
        assert isinstance(other_type, Type)
        
        if signature == None:
            signature = defaultdict(list)
        
        self.term._set_type(other_type.second, signature)
        if not self.type.resolve(other_type):
            raise TypeResolutionException(self, other_type)

    def str(self, syntax=Tokens.NLTK):
        variables = [self.variable]
        term = self.term
        if syntax != Tokens.PROVER9:
            while term.__class__ == self.__class__:
                variables.append(term.variable)
                term = term.term
        return Tokens.LAMBDA[syntax] + ' '.join(str(v) for v in variables) + \
               Tokens.DOT[syntax] + term.str(syntax)


class QuantifiedExpression(VariableBinderExpression):
    type = property(lambda self: TRUTH_TYPE)

    def _set_type(self, other_type=ANY_TYPE, signature=None):
        """@see Expression._set_type()"""
        assert isinstance(other_type, Type)
        
        if signature == None:
            signature = defaultdict(list)
        
        if not other_type.matches(TRUTH_TYPE):
            raise IllegalTypeException(self, other_type, TRUTH_TYPE)
        self.term._set_type(TRUTH_TYPE, signature)

    def str(self, syntax=Tokens.NLTK):
        variables = [self.variable]
        term = self.term
        if syntax != Tokens.PROVER9:
            while term.__class__ == self.__class__:
                variables.append(term.variable)
                term = term.term
        return self.getQuantifier(syntax) + ' ' + \
               ' '.join(str(v) for v in variables) + \
               Tokens.DOT[syntax] + term.str(syntax)
        
class ExistsExpression(QuantifiedExpression):
    def getQuantifier(self, syntax=Tokens.NLTK):
        return Tokens.EXISTS[syntax]

class AllExpression(QuantifiedExpression):
    def getQuantifier(self, syntax=Tokens.NLTK):
        return Tokens.ALL[syntax]


class NegatedExpression(Expression):
    def __init__(self, term):
        assert isinstance(term, Expression), "%s is not an Expression" % term
        self.term = term
        
    type = property(lambda self: TRUTH_TYPE)
    
    def _set_type(self, other_type=ANY_TYPE, signature=None):
        """@see Expression._set_type()"""
        assert isinstance(other_type, Type)
        
        if signature == None:
            signature = defaultdict(list)
        
        if not other_type.matches(TRUTH_TYPE):
            raise IllegalTypeException(self, other_type, TRUTH_TYPE)
        self.term._set_type(TRUTH_TYPE, signature)

    def findtype(self, variable):
        assert isinstance(variable, Variable), "%s is not a Variable" % variable
        return self.term.findtype(variable)
        
    def visit(self, function, combinator, default):
        """@see: Expression.visit()"""
        return combinator(function(self.term))
        
    def negate(self):
        """@see: Expression.negate()"""
        return self.term
    
    def __eq__(self, other):
        return isinstance(other, NegatedExpression) and self.term == other.term

    def str(self, syntax=Tokens.NLTK):
        if syntax == Tokens.PROVER9:
            return Tokens.NOT[syntax] + Tokens.OPEN + self.term.str(syntax) +\
                   Tokens.CLOSE
        else:
            return Tokens.NOT[syntax] + self.term.str(syntax)
        
        
class BinaryExpression(Expression):
    def __init__(self, first, second):
        assert isinstance(first, Expression), "%s is not an Expression" % first
        assert isinstance(second, Expression), "%s is not an Expression" % second
        self.first = first
        self.second = second

    type = property(lambda self: TRUTH_TYPE)
    
    def findtype(self, variable):
        """@see Expression.findtype()"""
        assert isinstance(variable, Variable), "%s is not a Variable" % variable
        f = self.first.findtype(variable)
        s = self.second.findtype(variable)
        if f == s or s == ANY_TYPE:
            return f
        elif f == ANY_TYPE:
            return s
        else:
            return ANY_TYPE

    def visit(self, function, combinator, default):
        """@see: Expression.visit()"""
        return combinator(function(self.first), function(self.second))
        
    def __eq__(self, other):
        return (isinstance(self, other.__class__) or \
                isinstance(other, self.__class__)) and \
               self.first == other.first and self.second == other.second

    def str(self, syntax=Tokens.NLTK):
        return Tokens.OPEN + self.first.str(syntax) + ' ' + self.getOp(syntax) \
                + ' ' + self.second.str(syntax) + Tokens.CLOSE
        
        
class BooleanExpression(BinaryExpression):
    def _set_type(self, other_type=ANY_TYPE, signature=None):
        """@see Expression._set_type()"""
        assert isinstance(other_type, Type)
        
        if signature == None:
            signature = defaultdict(list)
        
        if not other_type.matches(TRUTH_TYPE):
            raise IllegalTypeException(self, other_type, TRUTH_TYPE)
        self.first._set_type(TRUTH_TYPE, signature)
        self.second._set_type(TRUTH_TYPE, signature)

class AndExpression(BooleanExpression):
    """This class represents conjunctions"""
    def getOp(self, syntax=Tokens.NLTK):
        return Tokens.AND[syntax]

class OrExpression(BooleanExpression):
    """This class represents disjunctions"""
    def getOp(self, syntax=Tokens.NLTK):
        return Tokens.OR[syntax]

class ImpExpression(BooleanExpression):
    """This class represents implications"""
    def getOp(self, syntax=Tokens.NLTK):
        return Tokens.IMP[syntax]

class IffExpression(BooleanExpression):
    """This class represents biconditionals"""
    def getOp(self, syntax=Tokens.NLTK):
        return Tokens.IFF[syntax]


class EqualityExpression(BinaryExpression):
    """This class represents equality expressions like "(x = y)"."""
    def _set_type(self, other_type=ANY_TYPE, signature=None):
        """@see Expression._set_type()"""
        assert isinstance(other_type, Type)
        
        if signature == None:
            signature = defaultdict(list)
        
        if not other_type.matches(TRUTH_TYPE):
            raise IllegalTypeException(self, other_type, TRUTH_TYPE)
        self.first._set_type(ENTITY_TYPE, signature)
        self.second._set_type(ENTITY_TYPE, signature)

    def getOp(self, syntax=Tokens.NLTK):
        return Tokens.EQ[syntax]


class LogicParser(object):
    """A lambda calculus expression parser."""

    def __init__(self, type_check=False):
        """
        @param type_check: C{boolean} should type checking be performed?
        to their types.
        """
        assert isinstance(type_check, bool)
        
        self._currentIndex = 0
        self._buffer = []
        self.type_check = type_check

    def parse(self, data, signature=None):
        """
        Parse the expression.

        @param data: C{str} for the input to be parsed
        @param signature: C{dict<str, str>} that maps variable names to type 
        strings
        @returns: a parsed Expression
        """
        self._currentIndex = 0
        self._buffer = self.process(data).split()

        result = self.parse_Expression()
        if self.inRange(0):
            raise UnexpectedTokenException(self.token(0))

        if self.type_check:
            result.typecheck(signature)

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
            if StringTrie.LEAF in st: 
                #token is a complete symbol
                out += ' '+token+' '
                data = data[len(token):]
            else:
                out += data[0]
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
            raise ParseException, 'More tokens expected.'

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
            if isinstance(accum, IndividualVariableExpression):
                raise ParseException('\'%s\' is an illegal predicate name.  '
                                     'Individual variables may not be used as '
                                     'predicates.' % tok)
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
        
    def ensure_abstractable(self, tok):
        if isinstance(VariableExpression(Variable(tok)), ConstantExpression):
            raise ParseException('\'%s\' is an illegal variable name.  '
                                 'Constants may not be abstracted.' % tok)
    
    def handle_lambda(self, tok):
        # Expression is a lambda expression
        self.ensure_abstractable(self.token(0))
        vars = [Variable(self.token())]
        while self.isvariable(self.token(0)):
            # Support expressions like: \x y.M == \x.\y.M
            self.ensure_abstractable(self.token(0))
            vars.append(Variable(self.token()))
        self.assertToken(self.token(), Tokens.DOT)
        
        accum = self.parse_Expression(False)
        while vars:
            accum = self.make_LambdaExpression(vars.pop(), accum)
        return accum
        
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
            varex = self.make_VariableExpression(var)
            if isinstance(varex, ConstantExpression):
                raise ParseException('\'%s\' is an illegal variable name.  '
                                     'Constant expressions may not be ' 
                                     'quantified.' % var)
            accum = self.make_QuanifiedExpression(factory, Variable(var), accum)
        return accum
    
    def get_QuantifiedExpression_factory(self, tok):
        """This method serves as a hook for other logic parsers that
        have different quantifiers"""
        if tok in Tokens.EXISTS:
            return ExistsExpression
        elif tok in Tokens.ALL:
            return AllExpression
        else:
            self.assertToken(tok, Tokens.QUANTS)

    def make_QuanifiedExpression(self, factory, variable, term):
        return factory(variable, term)
        
    def handle_open(self, tok):
        #Expression is in parens
        accum = self.parse_Expression()
        self.assertToken(self.token(), Tokens.CLOSE)
        return accum
        
    def attempt_EqualityExpression(self, expression):
        """Attempt to make an equality expression.  If the next token is an 
        equality operator, then an EqualityExpression will be returned.  
        Otherwise, the parameter will be returned."""
        if self.inRange(0) and self.token(0) in Tokens.EQ:
            self.token() #swallow the "="
            return self.make_EqualityExpression(expression, 
                                                self.parse_Expression())
        elif self.inRange(0) and self.token(0) in Tokens.NEQ:
            self.token() #swallow the "!="
            return self.make_NegatedExpression(
                        self.make_EqualityExpression(expression, 
                                                     self.parse_Expression()))
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
            factory = self.get_BooleanExpression_factory(self.token(0))
            if factory: #if a factory was returned
                self.token() #swallow the operator
                return self.make_BooleanExpression(factory, expression, self.parse_Expression())
        #otherwise, no boolean expression can be created
        return expression
    
    def get_BooleanExpression_factory(self, tok):
        """This method serves as a hook for other logic parsers that
        have different boolean operators"""
        if tok in Tokens.AND:
            return AndExpression
        elif tok in Tokens.OR:
            return OrExpression
        elif tok in Tokens.IMP:
            return ImpExpression
        elif tok in Tokens.IFF:
            return IffExpression
        else:
            return None
    
    def make_BooleanExpression(self, factory, first, second):
        return factory(first, second)
    
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
                                     'Application Expression, so it may '
                                     'not take arguments')
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
            msg = 'Next token: ' + self.token(0)
        else:
            msg = 'No more tokens'
        return '<' + self.__class__.__name__ + ': ' + msg + '>'

            
class StringTrie(defaultdict):
    LEAF = "<leaf>" 

    def __init__(self, strings=None):
        defaultdict.__init__(self, StringTrie)
        if strings:
            for string in strings:
                self.insert(string)
    
    def insert(self, string):
        if len(string):
            self[string[0]].insert(string[1:])
        else:
            #mark the string is complete
            self[StringTrie.LEAF] = None
            

class ParseException(Exception):
    def __init__(self, message):
        Exception.__init__(self, message)

class UnexpectedTokenException(ParseException):
    def __init__(self, tok, expected=None):
        if expected:
            ParseException.__init__(self, "parse error, unexpected token: '%s'. "
                                    "Expected token: %s" % (tok, expected))
        else:
            ParseException.__init__(self, "parse error, unexpected token: '%s'" 
                                            % tok)
        
        
def is_indvar(expr):
    """
    An individual variable must be a single lowercase character other than 'e',
    followed by zero or more digits.
    
    @param expr: C{str}
    @return: C{boolean} True if expr is of the correct form 
    """
    assert isinstance(expr, str), "%s is not a string" % expr
    return re.match(r'^[a-df-z]\d*$', expr)

def is_funcvar(expr):
    """
    A function variable must be a single uppercase character followed by
    zero or more digits.
    
    @param expr: C{str}
    @return: C{boolean} True if expr is of the correct form 
    """
    assert isinstance(expr, str), "%s is not a string" % expr
    return re.match(r'^[A-Z]\d*$', expr)

def is_eventvar(expr):
    """
    An event variable must be a single lowercase 'e' character followed by
    zero or more digits.
    
    @param expr: C{str}
    @return: C{boolean} True if expr is of the correct form 
    """
    assert isinstance(expr, str), "%s is not a string" % expr
    return re.match(r'^e\d*$', expr)


def demo():
    p = LogicParser().parse
    print '='*20 + 'Test parser' + '='*20
    print p(r'john')
    print p(r'man(x)')
    print p(r'-man(x)')
    print p(r'(man(x) & tall(x) & walks(x))')
    print p(r'exists x.(man(x) & tall(x))')
    print p(r'\x.man(x)')
    print p(r'\x.man(x)(john)')
    print p(r'\x y.sees(x,y)')
    print p(r'\x y.sees(x,y)(a,b)')
    print p(r'(\x.exists y.walks(x,y))(x)')
    print p(r'exists x.(x = y)')
    print p(r'\P Q.exists x.(P(x) & Q(x))')
    
    print '='*20 + 'Test simplify' + '='*20
    print p(r'\x.\y.sees(x,y)(john)(mary)').simplify()
    print p(r'\x.\y.sees(x,y)(john, mary)').simplify()
    print p(r'all x.(man(x) & (\x.exists y.walks(x,y))(x))').simplify()
    print p(r'(\P.\Q.exists x.(P(x) & Q(x)))(\x.dog(x))(\x.bark(x))').simplify()
    
    print '='*20 + 'Test alpha conversion and binder expression equality' + '='*20
    e1 = p('exists x.P(x)')
    print e1
    e2 = e1.alpha_convert(Variable('z'))
    print e2
    print e1 == e2
    
def printtype(ex):
    print ex.str() + ' : ' + str(ex.type)

if __name__ == '__main__':
    demo()
