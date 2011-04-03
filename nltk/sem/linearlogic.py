# Natural Language Toolkit: Linear Logic 
#
# Author: Dan Garrette <dhgarrette@gmail.com>
#
# Copyright (C) 2001-2011 NLTK Project
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

from nltk.internals import Counter
from logic import LogicParser, APP

_counter = Counter()

class Expression(object):
    def applyto(self, other, other_indices=None):
        return ApplicationExpression(self, other, other_indices)
    
    def __call__(self, other):
        return self.applyto(other)
    
    def __repr__(self):
        return '<' + self.__class__.__name__ + ' ' + str(self) + '>'
    
class AtomicExpression(Expression):
    def __init__(self, name, dependencies=None):
        """
        @param name: C{str} for the constant name
        @param dependencies: C{list} of C{int} for the indices on which this atom is dependent
        """
        assert isinstance(name, str)
        self.name = name
        
        if not dependencies:
            dependencies = []
        self.dependencies = dependencies
        
    def simplify(self, bindings=None):
        """
        If 'self' is bound by 'bindings', return the atomic to which it is bound.  
        Otherwise, return self.
        
        @param bindings: C{BindingDict} A dictionary of bindings used to simplify
        @return: C{AtomicExpression}
        """
        if bindings and self in bindings:
            return bindings[self]
        else:
            return self
        
    def compile_pos(self, index_counter, glueFormulaFactory):
        """
        From Iddo Lev's PhD Dissertation p108-109
        
        @param index_counter: C{Counter} for unique indices
        @param glueFormulaFactory: C{GlueFormula} for creating new glue formulas
        @return: (C{Expression},C{set}) for the compiled linear logic and any newly created glue formulas
        """
        self.dependencies = []
        return (self, [])

    def compile_neg(self, index_counter, glueFormulaFactory):
        """
        From Iddo Lev's PhD Dissertation p108-109
        
        @param index_counter: C{Counter} for unique indices
        @param glueFormulaFactory: C{GlueFormula} for creating new glue formulas
        @return: (C{Expression},C{set}) for the compiled linear logic and any newly created glue formulas
        """
        self.dependencies = []
        return (self, [])
    
    def initialize_labels(self, fstruct):
        self.name = fstruct.initialize_label(self.name.lower())
    
    def __eq__(self, other):
        return self.__class__ == other.__class__ and self.name == other.name
        
    def __str__(self):
        accum = self.name
        if self.dependencies:
            accum += str(self.dependencies)
        return accum

    def __hash__(self):
        return hash(self.name)

class ConstantExpression(AtomicExpression):
    def unify(self, other, bindings):
        """
        If 'other' is a constant, then it must be equal to 'self'.  If 'other' is a variable,
        then it must not be bound to anything other than 'self'.
        
        @param other: C{Expression}
        @param bindings: C{BindingDict} A dictionary of all current bindings
        @return: C{BindingDict} A new combined dictionary of of 'bindings' and any new binding
        @raise UnificationException: If 'self' and 'other' cannot be unified in the context of 'bindings'
        """
        assert isinstance(other, Expression)
        if isinstance(other, VariableExpression):
            try:
                return bindings + BindingDict([(other, self)])
            except VariableBindingException:
                pass
        elif self == other:
                return bindings
        raise UnificationException(self, other, bindings)

class VariableExpression(AtomicExpression):
    def unify(self, other, bindings):
        """
        'self' must not be bound to anything other than 'other'.
        
        @param other: C{Expression}
        @param bindings: C{BindingDict} A dictionary of all current bindings
        @return: C{BindingDict} A new combined dictionary of of 'bindings' and the new binding
        @raise UnificationException: If 'self' and 'other' cannot be unified in the context of 'bindings'
        """
        assert isinstance(other, Expression)
        try:
            if self == other:
                return bindings
            else:
                return bindings + BindingDict([(self, other)])
        except VariableBindingException:
            raise UnificationException(self, other, bindings)

class ImpExpression(Expression):
    def __init__(self, antecedent, consequent):
        """
        @param antecedent: C{Expression} for the antecedent
        @param consequent: C{Expression} for the consequent
        """
        assert isinstance(antecedent, Expression)
        assert isinstance(consequent, Expression)
        self.antecedent = antecedent
        self.consequent = consequent
        
    def simplify(self, bindings=None):
        return self.__class__(self.antecedent.simplify(bindings), self.consequent.simplify(bindings))
    
    def unify(self, other, bindings):
        """
        Both the antecedent and consequent of 'self' and 'other' must unify.
        
        @param other: C{ImpExpression}
        @param bindings: C{BindingDict} A dictionary of all current bindings
        @return: C{BindingDict} A new combined dictionary of of 'bindings' and any new bindings
        @raise UnificationException: If 'self' and 'other' cannot be unified in the context of 'bindings'
        """
        assert isinstance(other, ImpExpression)
        try:
            return bindings + self.antecedent.unify(other.antecedent, bindings) + self.consequent.unify(other.consequent, bindings)
        except VariableBindingException:
            raise UnificationException(self, other, bindings)
        
    def compile_pos(self, index_counter, glueFormulaFactory):
        """
        From Iddo Lev's PhD Dissertation p108-109
        
        @param index_counter: C{Counter} for unique indices
        @param glueFormulaFactory: C{GlueFormula} for creating new glue formulas
        @return: (C{Expression},C{set}) for the compiled linear logic and any newly created glue formulas
        """
        (a, a_new) = self.antecedent.compile_neg(index_counter, glueFormulaFactory)
        (c, c_new) = self.consequent.compile_pos(index_counter, glueFormulaFactory)
        return (ImpExpression(a,c), a_new + c_new)

    def compile_neg(self, index_counter, glueFormulaFactory):
        """
        From Iddo Lev's PhD Dissertation p108-109
        
        @param index_counter: C{Counter} for unique indices
        @param glueFormulaFactory: C{GlueFormula} for creating new glue formulas
        @return: (C{Expression},C{list} of C{GlueFormula}) for the compiled linear logic and any newly created glue formulas
        """
        (a, a_new) = self.antecedent.compile_pos(index_counter, glueFormulaFactory)
        (c, c_new) = self.consequent.compile_neg(index_counter, glueFormulaFactory)
        fresh_index = index_counter.get()
        c.dependencies.append(fresh_index)
        new_v = glueFormulaFactory('v%s' % fresh_index, a, set([fresh_index]))
        return (c, a_new + c_new + [new_v])

    def initialize_labels(self, fstruct):
        self.antecedent.initialize_labels(fstruct)
        self.consequent.initialize_labels(fstruct)

    def __eq__(self, other):
        return self.__class__ == other.__class__ and \
                self.antecedent == other.antecedent and self.consequent == other.consequent
        
    def __str__(self):
        return Tokens.OPEN + str(self.antecedent) + ' ' + Tokens.IMP + \
               ' ' + str(self.consequent) + Tokens.CLOSE

    def __hash__(self):
        return hash('%s%s%s' % (hash(self.antecedent), Tokens.IMP, hash(self.consequent)))

class ApplicationExpression(Expression):
    def __init__(self, function, argument, argument_indices=None):
        """
        @param function: C{Expression} for the function
        @param argument: C{Expression} for the argument
        @param argument_indices: C{set} for the indices of the glue formula from which the argument came
        @raise LinearLogicApplicationException: If 'function' cannot be applied to 'argument' given 'argument_indices'.
        """
        function_simp = function.simplify()
        argument_simp = argument.simplify()

        assert isinstance(function_simp, ImpExpression)
        assert isinstance(argument_simp, Expression)
        
        bindings = BindingDict()
        
        try:
            if isinstance(function, ApplicationExpression):
                bindings += function.bindings
            if isinstance(argument, ApplicationExpression):
                bindings += argument.bindings
            bindings += function_simp.antecedent.unify(argument_simp, bindings)
        except UnificationException, e:
            raise LinearLogicApplicationException, 'Cannot apply %s to %s. %s' % (function_simp, argument_simp, e)
        
        # If you are running it on complied premises, more conditions apply
        if argument_indices:
            # A.dependencies of (A -o (B -o C)) must be a proper subset of argument_indices
            if not set(function_simp.antecedent.dependencies) < argument_indices:
                raise LinearLogicApplicationException, 'Dependencies unfulfilled when attempting to apply Linear Logic formula %s to %s' % (function_simp, argument_simp)
            if set(function_simp.antecedent.dependencies) == argument_indices:
                raise LinearLogicApplicationException, 'Dependencies not a proper subset of indices when attempting to apply Linear Logic formula %s to %s' % (function_simp, argument_simp)

        self.function = function
        self.argument = argument
        self.bindings = bindings

    def simplify(self, bindings=None):
        """
        Since function is an implication, return its consequent.  There should be 
        no need to check that the application is valid since the checking is done 
        by the constructor.
        
        @param bindings: C{BindingDict} A dictionary of bindings used to simplify
        @return: C{Expression}
        """
        if not bindings:
            bindings = self.bindings
        
        return self.function.simplify(bindings).consequent
        
    def __eq__(self, other):
        return self.__class__ == other.__class__ and \
                self.function == other.function and self.argument == other.argument
        
    def __str__(self):
        return str(self.function) + Tokens.OPEN + str(self.argument) + Tokens.CLOSE

    def __hash__(self):
        return hash('%s%s%s' % (hash(self.antecedent), Tokens.OPEN, hash(self.consequent)))

class BindingDict(object):
    def __init__(self, binding_list=None):
        """
        @param binding_list: C{list} of (C{VariableExpression}, C{AtomicExpression}) to initialize the dictionary
        """
        self.d = {}

        if binding_list:
            for (v, b) in binding_list:
                self[v] = b
    
    def __setitem__(self, variable, binding):
        """
        A binding is consistent with the dict if its variable is not already bound, OR if its 
        variable is already bound to its argument.
        
        @param variable: C{VariableExpression} The variable bind
        @param binding: C{Expression} The expression to which 'variable' should be bound
        @raise VariableBindingException: If the variable cannot be bound in this dictionary
        """
        assert isinstance(variable, VariableExpression)
        assert isinstance(binding, Expression) 
        
        assert variable != binding
        
        try:
            existing = self.d[variable]
        except KeyError:
            existing = None
            
        if not existing or binding == existing:
            self.d[variable] = binding
        else:
            raise VariableBindingException, 'Variable %s already bound to another value' % (variable)

    def __getitem__(self, variable):
        """
        Return the expression to which 'variable' is bound
        """
        assert isinstance(variable, VariableExpression)

        intermediate = self.d[variable]
        while intermediate:
            try:
                intermediate = self.d[intermediate]
            except KeyError:
                return intermediate
            
    def __contains__(self, item):
        return item in self.d

    def __add__(self, other):
        """
        @param other: C{BindingDict} The dict with which to combine self
        @return: C{BindingDict} A new dict containing all the elements of both parameters
        @raise VariableBindingException: If the parameter dictionaries are not consistent with each other
        """
        try:
            combined = BindingDict()
            for v in self.d:
                combined[v] = self.d[v]
            for v in other.d:
                combined[v] = other.d[v]
            return combined
        except VariableBindingException:
            raise VariableBindingException, 'Attempting to add two contradicting'\
                        ' VariableBindingsLists: %s, %s' % (self, other)

    def __str__(self):
        return '{' + ', '.join(['%s: %s' % (v, self.d[v]) for v in self.d]) + '}'

    def __repr__(self):
        return 'BindingDict: ' + str(self)
            
class VariableBindingException(Exception): pass

class UnificationException(Exception): 
    def __init__(self, a, b, bindings):
        Exception.__init__(self, 'Cannot unify %s with %s given %s' % (a, b, bindings))

class LinearLogicApplicationException(Exception): pass


class Tokens(object):
    #Punctuation
    OPEN = '('
    CLOSE = ')'
    
    #Operations
    IMP = '-o'
    
    PUNCT = [OPEN, CLOSE]
    TOKENS = PUNCT + [IMP] 


class LinearLogicParser(LogicParser):
    """A linear logic expression parser."""
    def __init__(self):
        LogicParser.__init__(self)
        
        self.operator_precedence = {APP: 1, Tokens.IMP: 2, None: 3}
        self.right_associated_operations += [Tokens.IMP]
    
    def get_all_symbols(self):
        return Tokens.TOKENS
    
    def handle(self, tok, context):
        if tok not in Tokens.TOKENS:
            return self.handle_variable(tok, context)
        elif tok == Tokens.OPEN:
            return self.handle_open(tok, context)
     
    def get_BooleanExpression_factory(self, tok):
        if tok == Tokens.IMP:
            return ImpExpression
        else:
            return None

    def make_BooleanExpression(self, factory, first, second):
        return factory(first, second)
    
    def attempt_ApplicationExpression(self, expression, context):
        """Attempt to make an application expression.  If the next tokens 
        are an argument in parens, then the argument expression is a
        function being applied to the arguments.  Otherwise, return the
        argument expression."""
        if self.has_priority(APP, context):
            if self.inRange(0) and self.token(0) == Tokens.OPEN:
                self.token() #swallow then open paren
                argument = self.parse_Expression(APP)
                self.assertNextToken(Tokens.CLOSE)
                expression = ApplicationExpression(expression, argument, None)
        return expression

    def make_VariableExpression(self, name):
        if name[0].isupper():
            return VariableExpression(name)
        else:
            return ConstantExpression(name)

def demo():
    llp = LinearLogicParser()
    
    print llp.parse(r'f')
    print llp.parse(r'(g -o f)')
    print llp.parse(r'((g -o G) -o G)')
    print llp.parse(r'g -o h -o f')
    print llp.parse(r'(g -o f)(g)').simplify()
    print llp.parse(r'(H -o f)(g)').simplify()
    print llp.parse(r'((g -o G) -o G)((g -o f))').simplify()
    print llp.parse(r'(H -o H)((g -o f))').simplify()


if __name__ == '__main__':
    demo()
