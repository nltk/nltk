# Natural Language Toolkit: Typed Logic
#
# Author: Daniel H. Garrette <dhgarrette@gmail.com>
#
# URL: <http://www.nltk.org>
# For license information, see LICENSE.TXT

"""
A module to handle typed first order logic
"""

from nltk.sem.logic import *
from nltk import defaultdict

class ArityParser(LogicParser):
    """A lambda calculus expression parser."""

    def __init__(self):
        self._currentIndex = 0
        self._buffer = []
        self._arity_dict = None

    def parse(self, data, arityinfo=None):
        """
        Parse the expression.

        @param data: C{str} for the input to be parsed
        @param arityinfo: C{list} of {str} describing the arity of entities 
        and relations.  All item should be of the form "john/0" or "see/2".
        @returns: a parsed Expression
        """
        self._currentIndex = 0
        self._buffer = self.process(data).split()
        
        if arityinfo != None:
            self._arity_dict = defaultdict(list)
            for aritystr in arityinfo:
                name, arity = aritystr.split('/')
                self._arity_dict[name].append(int(arity))
        else:
            self._arity_dict = None
        
        result = self.parse_Expression()
        if self.inRange(0):
            raise UnexpectedTokenException(self.token(0))
        return result

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
            arity_count = 1
            accum = self.make_ApplicationExpression(accum, 
                                                self.parse_Expression())
            while self.token(0) == Tokens.COMMA:
                self.token() #swallow the comma
                accum = self.make_ApplicationExpression(accum, 
                                                 self.parse_Expression())
                arity_count += 1
            self.assertToken(self.token(), Tokens.CLOSE)
            
            self.verify_arity(tok, arity_count)
        else:
            #it's a solo variable
            self.verify_arity(tok, 0)
                
        return self.attempt_EqualityExpression(accum)

    def verify_arity(self, tok, actual_arity):
        if self._arity_dict != None and tok in self._arity_dict:
            expected_arity = self._arity_dict[tok]
            if actual_arity not in expected_arity:
                raise ArityException(tok, expected_arity, actual_arity)


class ArityException(ParseException):
    def __init__(self, tok, expected_arity, found_arity):
        ParseException.__init__(self, 'The arity of %s should be %s but was ' \
                                'found to be %s' % (tok, expected_arity, 
                                                    found_arity))

class TestSuite(object):
    def __init__(self):
        self.count = 0
        self.failures = 0
    
    def run(self):
        self.count = 0
        self.failures = 0
        
        self.test_arityparser()
        
        print '='*55
        print 'Tests:    %s' % self.count
        print 'Failures: %s' % self.failures

    def test_arityparser(self):
        print '='*20 + 'TEST ArityParser' + '='*20
        self.arityparse_test(r'man(x)', None, False)
        self.arityparse_test(r'man(x)', ['man/1'], False)
        self.arityparse_test(r'man(x,y)', ['man/1'], True)
        self.arityparse_test(r'man(x)', ['see/2'], False)
        self.arityparse_test(r'all x.(girl(x) -> exists y.(dog(x) & chase(x,y)))', ['girl/1','dog/1','chase/2'], False)
        self.arityparse_test(r'man(john) & see(john, x)', ['john/0','man/1','see/2'], False)
        self.arityparse_test(r'eat(john) & exists x.eat(john, x)', ['john/0', 'eat/1'], True)
        self.arityparse_test(r'eat(john) & exists x.eat(john, x)', ['john/0', 'eat/1', 'eat/2'], False)
        
    def arityparse_test(self, f, arityinfo, error_expected, throw=False):
        error = False
        try:
            t = ArityParser().parse(f, arityinfo)
        except Exception, e:
            if throw:
                raise
            else:
                error = True

        self.count += 1
        if error == error_expected: 
            print '[%s] %s %s' % (self.count, f, arityinfo)
        else:
            print '[%s] %s %s %s' % (self.count, f, arityinfo, '*'*50)
            self.failures += 1
        
if __name__ == '__main__':
    TestSuite().run()
