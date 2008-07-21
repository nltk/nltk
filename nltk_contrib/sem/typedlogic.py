# Natural Language Toolkit: Typed Logic
#
# Author: Daniel H. Garrette <dhgarrette@gmail.com>
#
# URL: <http://www.nltk.org>
# For license information, see LICENSE.TXT

"""
A module to handle typed first order logic
"""

from nltk.sem import logic

class Type:
    def __repr__(self):
        return str(self)
    
    def __eq__(self, other):
        return str(self) == str(other)
    
    def __hash__(self):
        return hash(str(self))
    
class ComplexType(Type):
    def __init__(self, first, second):
        assert(isinstance(first, Type))
        assert(isinstance(second, Type))
        self.first = first
        self.second = second
    
    def applyto(self, other):
        assert(isinstance(other, Type))
        assert(self.first == other)
        return self.second

    def __str__(self):
        return '<%s,%s>' % (self.first, self.second)

class BasicType(Type):
    def __init__(self):
        pass
    
class EntityType(BasicType):
    def __str__(self):
        return 'e'
    
class TruthValueType(BasicType):
    def __str__(self):
        return 't'
    

class TypedExpression(logic.Expression):
    def _get_abstract_type(self):
        return self.gettype()
    
class TypedApplicationExpression(logic.ApplicationExpression, TypedExpression):
    def gettype(self):
        if isinstance(self.function, TypedLambdaExpression):
            #(\x y.man(x,y))(john)
            f_type = self.function.gettype()
            assert(f_type, ComplexType)
            if f_type.first == self.argument.gettype():
                return f_type.second
            else:
                raise TypeException("The function %s cannot be applied to %s." 
                                    % (self.function, self.argument))
        else:
            #is a predicate expression
            return TruthValueType()
        
    def _get_abstract_type(self):
        function, args = self.uncurry()
        if not isinstance(function, TypedVariableExpression):
            #It's not a predicate expression ("P(x,y)"), so leave arguments curried
            function = self.function
            args = [self.argument]

        if isinstance(function, TypedLambdaExpression):
            return self.gettype()
        else:
            #is a predicate expression
            f_found = TruthValueType()
            for arg in args[::-1]:
                f_found = ComplexType(arg._get_abstract_type(), f_found)
            return f_found
        
    def _findtype(self, variable):
        """Find the type of the given variable as used in self"""
        function, args = self.uncurry()
        if not isinstance(function, TypedVariableExpression):
            #It's not a predicate expression ("P(x,y)"), so leave arguments curried
            function = expression.function
            args = [expression.argument]
        
        if function == TypedVariableExpression(variable):
            f_found = self._get_abstract_type()
        else:
            f_found = function._findtype(variable)

        arg_found = [arg._findtype(variable) for arg in args]
        s = set([found for found in [f_found]+arg_found if found != None])
        if len(s) == 0:
            return None
        elif len(s) == 1:
            return list(s)[0]
        else:
            raise InconsistantTypeHeirarchyException(variable, self)

class TypedVariableExpression(logic.VariableExpression, TypedExpression):
    def gettype(self):
        return EntityType()

    def _findtype(self, variable):
        """Find the type of the given variable as used in self"""
        if self.variable == variable:
            return EntityType()
        else:
            return None

class TypedVariableBinderExpression(logic.VariableBinderExpression, TypedExpression):
    def _findtype(self, variable):
        """Find the type of the given variable as used in self"""
        return self.term._findtype(variable)

class TypedLambdaExpression(logic.LambdaExpression, TypedVariableBinderExpression):
    def gettype(self):
        return ComplexType(self.term._findtype(self.variable), self.term.gettype())

class TypedQuantifiedExpression(logic.QuantifiedExpression, TypedVariableBinderExpression):
    def gettype(self):
        return TruthValueType()

class TypedExistsExpression(logic.ExistsExpression, TypedQuantifiedExpression):
    pass

class TypedAllExpression(logic.AllExpression, TypedQuantifiedExpression):
    pass

class TypedNegatedExpression(logic.NegatedExpression, TypedExpression):
    def gettype(self):
        return TruthValueType()
        
    def _findtype(self, variable):
        """Find the type of the given variable as used in self"""
        return self.expression._findtype(variable)

class TypedBooleanExpression(logic.BooleanExpression, TypedExpression):
    def gettype(self):
        return TruthValueType()
        
    def _findtype(self, variable):
        """Find the type of the given variable as used in self"""
        f = self.first._findtype(variable)
        s = self.second._findtype(variable)
        if f == s or s == None:
            return f
        elif f == None:
            return s
        else:
            raise InconsistantTypeHeirarchyException(variable, self)

class TypedAndExpression(logic.AndExpression, TypedBooleanExpression):
    pass

class TypedOrExpression(logic.OrExpression, TypedBooleanExpression):
    pass

class TypedImpExpression(logic.ImpExpression, TypedBooleanExpression):
    pass

class TypedIffExpression(logic.IffExpression, TypedBooleanExpression):
    pass

class TypedEqualityExpression(logic.EqualityExpression, TypedBooleanExpression):
    pass


class TypedLogicParser(logic.LogicParser):
    """A typed lambda calculus expression parser."""

    def get_BooleanExpression_factory(self):
        factory = None
        op = self.token(0)
        if op in logic.Tokens.AND:
            factory = TypedAndExpression
        elif op in logic.Tokens.OR:
            factory = TypedOrExpression
        elif op in logic.Tokens.IMP:
            factory = TypedImpExpression
        elif op in logic.Tokens.IFF:
            factory = TypedIffExpression
        elif op in logic.Tokens.EQ:
            factory = TypedEqualityExpression
        return factory
 
    def make_BooleanExpression(self, factory, first, second):
        boolEx = factory(first, second)
        return boolEx 

    def make_ApplicationExpression(self, function, args):
        appEx = TypedApplicationExpression(function, args)
        return appEx
    
    def make_VariableExpression(self, name):
        varEx = TypedVariableExpression(logic.Variable(name))
        return varEx
    
    def make_LambdaExpression(self, variable, term):
        return TypedLambdaExpression(variable, term)
    
    def make_NegatedExpression(self, expression):
        return TypedNegatedExpression(expression)

    def get_QuantifiedExpression_factory(self, tok):
        """This method serves as a hook for other logic parsers that
        have different quantifiers"""
        factory = None
        if tok in logic.Tokens.EXISTS:
            factory = TypedExistsExpression
        elif tok in logic.Tokens.ALL:
            factory = TypedAllExpression
        else:
            self.assertToken(tok, logic.Tokens.EXISTS + logic.Tokens.ALL)
        return factory


class TypeException(Exception):
    def __init__(self, msg):
        Exception.__init__(self, msg)
    
class InconsistantTypeHeirarchyException(TypeException):
    def __init__(self, variable, expression):
        msg = "The variable %s was found in multiple places with different"\
            " types in %s." % (variable, expression)
        Exception.__init__(self, msg)


class TestSuite(object):
    def __init__(self):
        self.count = 0
        self.failures = 0
    
    def run(self):
        self.count = 0
        self.failures = 0
        
        self.test_findtype()
        self.test_gettype()
        
        print '='*55
        print 'Tests:    %s' % self.count
        print 'Failures: %s' % self.failures

    def test_gettype(self):
        print '='*20 + 'TEST gettype()' + '='*20
        self.gettype_test(r'man(x)', 't')
        self.gettype_test(r'-man(x)', 't')
        self.gettype_test(r'(man(x) <-> tall(x))', 't')
        self.gettype_test(r'exists x.(man(x) & tall(x))', 't')
        self.gettype_test(r'\x.man(x)', '<e,t>')
        self.gettype_test(r'john', 'e')
        self.gettype_test(r'\x y.sees(x,y)', '<e,<e,t>>')
        self.gettype_test(r'\x.man(x)(john)', 't')
        self.gettype_test(r'\x.\y.sees(x,y)(john)', '<e,t>')
        self.gettype_test(r'\x.\y.sees(x,y)(john)(mary)', 't')
        self.gettype_test(r'\P.\Q.exists x.(P(x) & Q(x))', '<<e,t>,<<e,t>,t>>')
        
    def gettype_test(self, f, expected_type, throw=True):
        try:
            t = TypedLogicParser().parse(f).gettype()
        except Exception, e:
            if throw:
                raise
            else:
                t = e.__class__.__name__ + ': ' + e.message

        self.count += 1
        if str(t) == expected_type: 
            print '[%s] %s\n\t%s' % (self.count, f, expected_type)
        else:
            print '[%s] %s\n\t%s != %s %s' % (self.count, f, expected_type, t, '*'*50)
            self.failures += 1
        
    def test_findtype(self):
        print '='*20 + 'TEST _findtype()' + '='*20
        self.findtype_test(r'man(x)', 'man', '<e,t>')
        self.findtype_test(r'see(x,y)', 'see', '<e,<e,t>>')
        self.findtype_test(r'\P.\Q.exists x.(P(x) & Q(x))', 'P', '<e,t>')
        self.findtype_test(r'exists x y.(P(x) & P(x,y))', 'P', 'InconsistantTypeHeirarchyException: The variable P was found in multiple places with different types in (P(x) & P(x,y)).')
        self.findtype_test(r'P(Q(R(x)))', 'Q', '<<e,t>,t>')
            
    def findtype_test(self, f, var, expected_type, throw=False):
        try:
            p = TypedLogicParser()
            t = p.parse(f)._findtype(p.parse(var).variable)
        except Exception, e:
            if throw:
                raise
            else:
                t = e.__class__.__name__ + ': ' + e.message

        self.count += 1
        if str(t) == expected_type: 
            print '[%s] %s[%s]\n\t%s' % (self.count, f, var, expected_type)
        else:
            print '[%s] %s[%s]\n\t%s != %s %s' % (self.count, f, var, expected_type, t, '*'*50)
            self.failures += 1
        

if __name__ == '__main__':
    TestSuite().run()
