# Natural Language Toolkit: First-order Resolution-based Theorem Prover 
#
# Author: Dan Garrette <dhgarrette@gmail.com>
#
# URL: <http://www.nltk.org>
# For license information, see LICENSE.TXT

from nltk.sem.logic import *
from nltk.internals import Counter
from nltk.inference.api import ProverI

"""
Module for a resolution-based First Order theorem prover.
"""

_skolem_function_counter = Counter()

class ProverParseError(Exception): pass

class Resolution(ProverI):
    def __init__(self, goal=None, assumptions=[], **options):
        """
        @param goal: Input expression to prove
        @type goal: L{logic.Expression}
        @param assumptions: Input expressions to use as assumptions in the proof
        @type assumptions: L{list} of logic.Expression objects
        @param options: options to pass to Prover9
        """
        self._goal = goal
        self._assumptions = assumptions
        self._options = options
        self._assume_false=True

    def prove(self, verbose=False):
        tp_result = None
        try:
            clauses = []
            if self._goal:
                clauses.extend(clausify(-self._goal))
            for a in self._assumptions:
                clauses.extend(clausify(a))
            tp_result = _attempt_proof(clauses, verbose)
        except RuntimeError, e:
            if self._assume_false and str(e).startswith('maximum recursion depth exceeded'):
                tp_result = False
            else:
                if verbose:
                    print e
                else:
                    raise e
        return tp_result
        
    def show_proof(self):
        """
        Print out the proof.
        """
        self.prove(True)
    
    def add_assumptions(self, new_assumptions):
        """
        Add new assumptions to the assumption list.
        
        @param new_assumptions: new assumptions
        @type new_assumptions: C{list} of L{sem.logic.Expression}s
        """
        self._assumptions += new_assumptions
    
    def retract_assumptions(self, retracted, debug=False):
        """
        Retract assumptions from the assumption list.
        
        @param debug: If True, give warning when C{retracted} is not present on assumptions list.
        @type debug: C{bool}
        @param retracted: assumptions to be retracted
        @type retracted: C{list} of L{sem.logic.Expression}s
        """
        
        result = set(self._assumptions) - set(retracted)
        if debug and result == set(self._assumptions):
            print Warning("Assumptions list has not been changed:")
            self.assumptions()
        self._assumptions = list(result)
    
    def assumptions(self, output_format='nltk'):
        """
        List the current assumptions.       
        """
        for a in self._assumptions:
            print a


def _attempt_proof(clauses, verbose=False):
    tried = []
    i = 0
    while i < len(clauses):
        clauses[i] = clauses[i].remove_tautologies()
        j = 1
        while j < len(clauses):
            if i != j and (i,j) not in tried: #don't retry parings
                tried.append((i,j))
                try:
                    newclause = clauses[i].unify(clauses[j])
                    clauses.append(newclause)
                    if not len(newclause):
                        if verbose: 
                            for clause in clauses: print clause
                        return True 
                    i=-1 #since we added a new clause, restart from the top 
                    break
                except UnificationException:
                    pass #the clauses could not be unified
            j += 1
        i += 1
    if verbose: 
        for clause in clauses: print clause
    return False

def unify(a, b, bindings=None):
    """
    Two expressions are unifiable if there exists a substitution function S 
    such that S(a) == S(-b).
    
    @param a: C{Expression} 
    @param b: C{Expression} 
    @param bindings: C{BindingDict} a starting set of bindings with which the
                     unification must be consistent
    @return: C{BindingDict} A dictionary of the bindings required to unify, or
             None if the expressions cannot be unified
    """
    assert isinstance(a, Expression)
    assert isinstance(b, Expression)
    
    if not bindings:
        bindings = BindingDict()
    
    try:
        if isinstance(a, NegatedExpression) and isinstance(b, ApplicationExpression):
            return most_general_unification(a.term, b, bindings)
        elif isinstance(a, ApplicationExpression) and isinstance(b, NegatedExpression):
            return most_general_unification(a, b.term, bindings)
    except BindingException:
        pass #a and b could not be unified
    return None


class Clause(set):
    def unify(self, other):
        """
        Attempt to unify this Clause with the other, returning one, unified
        Clause
        
        @param other: C{Clause} with which to unify
        @return: C{Clause} 
        @raise UnificationException: if the Clauses cannot be unified
        """
        bindings_accum = None
        self_used = [] #atoms that have been unified with something in other
        other_used = [] #atoms that have been unified with something in self
        for a in self:
            if a in self_used: 
                continue # don't unify atoms that have already been unified
            for b in other:
                if b in other_used: 
                    continue # don't unify atoms that have already been unified
                bindings = unify(a, b, bindings_accum)
                if bindings:
                    self_used.append(a)
                    other_used.append(b)
                    if bindings_accum:
                        bindings_accum += bindings
                    else:
                        bindings_accum = bindings
        if bindings_accum:
            newclause = Clause((self-set(self_used)) | (other-set(other_used)))
            return newclause.substitute_bindings(bindings_accum)
        else:
            raise UnificationException(self, other)
    
    def remove_tautologies(self):
        bindings_accum = None
        used = [] #atoms that have been unified with something else
        for a in self:
            if a in used:
                continue # don't unify atoms that have already been unified
            for b in self:
                if b in used:
                    continue # don't unify atoms that have already been unified
                if a is not b: # don't try to unify with self
                    bindings = unify(a, b, bindings_accum)
                    if bindings:
                        used.extend([a,b])
                        if bindings_accum:
                            bindings_accum += bindings
                        else:
                            bindings_accum = bindings
        if bindings_accum:
            newclause = Clause(self-set(used))
            return newclause.substitute_bindings(bindings_accum)
        else:
            return self
    
    def free(self):
        s = set()
        for atom in self:
            s |= atom.free()
        return s
    
    def replace(self, variable, expression):
        return Clause([atom.replace(variable, expression) for atom in self])
    
    def substitute_bindings(self, bindings):
        """
        Replace every binding 
        
        @param bindings: A C{list} of tuples mapping VariableExpressions to the
        Expressions to which they are bound
        @return: C{Clause}
        """
        return Clause([atom.substitute_bindings(bindings) for atom in self])
    
    def __str__(self):
        return '{' + ', '.join([str(item) for item in self]) + '}'

    def __repr__(self):
        return str(self)


def clausify(expression):
    """
    Skolemize, clausify, and standardize the variables apart.
    """
    clause_list = []
    for clause in _clausify(skolemize(expression)):
        for free in clause.free():
            if is_indvar(free.name):
                newvar = IndividualVariableExpression(unique_variable())
                clause = clause.replace(free, newvar)
        clause_list.append(clause)
    return clause_list
    
def _clausify(expression):
    """
    @param expression: a skolemized expression in CNF
    """
    if isinstance(expression, AndExpression):
        return _clausify(expression.first) + _clausify(expression.second)
    elif isinstance(expression, OrExpression):
        first = _clausify(expression.first)
        second = _clausify(expression.second)
        assert len(first) == 1
        assert len(second) == 1
        return [first[0] | second[0]]
    elif isinstance(expression, EqualityExpression):
        raise NotImplementedError()
    elif isinstance(expression, ApplicationExpression):
        return [Clause([expression])]
    elif isinstance(expression, NegatedExpression) and \
         isinstance(expression.term, ApplicationExpression):
        return [Clause([expression])]
    else:
        raise ProverParseError()
    
    
def skolemize(expression, univ_scope=None):
    """
    Skolemize the expression and convert to conjunctive normal form (CNF)
    """
    if univ_scope is None:
        univ_scope = set()

    if isinstance(expression, AllExpression):
        term = skolemize(expression.term, univ_scope|set([expression.variable]))
        return term.replace(expression.variable, IndividualVariableExpression(unique_variable()))
    elif isinstance(expression, AndExpression):
        return skolemize(expression.first, univ_scope) &\
               skolemize(expression.second, univ_scope)
    elif isinstance(expression, OrExpression):
        return to_cnf(skolemize(expression.first, univ_scope), 
                      skolemize(expression.second, univ_scope))
    elif isinstance(expression, ImpExpression):
        return to_cnf(skolemize(-expression.first, univ_scope), 
                      skolemize(expression.second, univ_scope))
    elif isinstance(expression, IffExpression):
        return to_cnf(skolemize(-expression.first, univ_scope), 
                      skolemize(expression.second, univ_scope)) &\
               to_cnf(skolemize(expression.first, univ_scope), 
                      skolemize(-expression.second, univ_scope))
    elif isinstance(expression, EqualityExpression):
        raise NotImplementedError()
    elif isinstance(expression, NegatedExpression):
        negated = expression.term
        if isinstance(negated, AllExpression):
            term = skolemize(-negated.term, univ_scope)
            if univ_scope:
                return term.replace(negated.variable, _get_skolem_function(univ_scope))
            else:
                skolem_constant = IndividualVariableExpression(unique_variable())
                return term.replace(negated.variable, skolem_constant)
        elif isinstance(negated, AndExpression):
            return to_cnf(skolemize(-negated.first, univ_scope), 
                          skolemize(-negated.second, univ_scope))
        elif isinstance(negated, OrExpression):
            return skolemize(-negated.first, univ_scope) &\
                   skolemize(-negated.second, univ_scope)
        elif isinstance(negated, ImpExpression):
            return skolemize(negated.first, univ_scope) &\
                   skolemize(-negated.second, univ_scope)
        elif isinstance(negated, IffExpression):
            return to_cnf(skolemize(-negated.first, univ_scope), 
                          skolemize(-negated.second, univ_scope)) &\
                   to_cnf(skolemize(negated.first, univ_scope), 
                          skolemize(negated.second, univ_scope))
        elif isinstance(negated, EqualityExpression):
            raise NotImplementedError()
        elif isinstance(negated, NegatedExpression):
            return skolemize(negated.term, univ_scope)
        elif isinstance(negated, ExistsExpression):
            term = skolemize(-negated.term, univ_scope|set([negated.variable]))
            return term.replace(negated.variable, IndividualVariableExpression(unique_variable()))
        elif isinstance(negated, ApplicationExpression):
            return expression
        else:
            raise ProverParseError()
    elif isinstance(expression, ExistsExpression):
        term = skolemize(expression.term, univ_scope)
        if univ_scope:
            return term.replace(expression.variable, _get_skolem_function(univ_scope))
        else:
            skolem_constant = IndividualVariableExpression(unique_variable())
            return term.replace(expression.variable, skolem_constant)
    elif isinstance(expression, ApplicationExpression):
        return expression
    else:
        raise ProverParseError()

def to_cnf(first, second):
    """
    Convert this split disjunction to conjunctive normal form (CNF)
    """
    if isinstance(first, AndExpression):
        r_first = to_cnf(first.first, second)
        r_second = to_cnf(first.second, second)
        return r_first & r_second
    elif isinstance(second, AndExpression):
        r_first = to_cnf(first, second.first)
        r_second = to_cnf(first, second.second)
        return r_first & r_second
    else:
        return first | second

def _get_skolem_function(univ_scope):
    """
    Return a skolem function over the varibles in univ_scope
    """
    skolem_function = VariableExpression(Variable('F%s' % _skolem_function_counter.get()))
    for v in list(univ_scope):
        skolem_function = skolem_function(VariableExpression(v))
    return skolem_function


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
        
        @param variable: C{Variable} The variable to bind
        @param binding: C{Expression} The atomic to which 'variable' should be bound
        @raise BindingException: If the variable cannot be bound in this dictionary
        """
        assert isinstance(variable, Variable)
        assert isinstance(binding, Expression) 
        
        try:
            existing = self[variable]
        except KeyError:
            existing = None
            
        if not existing or binding == existing:
            self.d[variable] = binding
        elif isinstance(binding, IndividualVariableExpression):
            # Since variable is already bound, try to bind binding to variable
            try:
                existing = self[binding.variable]
            except KeyError:
                existing = None
                
            if is_indvar(variable.name):
                binding2 = IndividualVariableExpression(variable)
            else:
                binding2 = VariableExpression(variable)
                
            if not existing or binding2 == existing:
                self.d[binding.variable] = binding2
            else:
                raise BindingException('Variable %s already bound to another '
                                       'value' % (variable))
        else:
            raise BindingException('Variable %s already bound to another '
                                   'value' % (variable))

    def __getitem__(self, variable):
        """
        Return the expression to which 'variable' is bound
        """
        assert isinstance(variable, Variable)

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
        @raise BindingException: If the parameter dictionaries are not consistent with each other
        """
        try:
            combined = BindingDict()
            for v in self.d:
                combined[v] = self.d[v]
            for v in other.d:
                combined[v] = other.d[v]
            return combined
        except BindingException:
            raise BindingException("Attempting to add two contradicting "
                                   "BindingDicts: '%s' and '%s'" 
                                   % (self, other))

    def __str__(self):
        return '{' + ', '.join(['%s: %s' % (v, self.d[v]) for v in self.d]) + '}'

    def __repr__(self):
        return str(self)


def most_general_unification(a, b, bindings=None):
    """
    Find the most general unification of the two given expressions
    
    @param a: C{Expression}
    @param b: C{Expression}
    @param bindings: C{BindingDict} a starting set of bindings with which the
                     unification must be consistent
    @return: a list of bindings
    @raise BindingException: if the Expressions cannot be unified
    """
    if not bindings:
        bindings = BindingDict()
    
    if a == b:
        return bindings
    elif isinstance(a, VariableExpression) and is_indvar(a.variable.name):
        return _mgu_var(a, b, bindings)
    elif isinstance(b, VariableExpression) and is_indvar(b.variable.name):
        return _mgu_var(b, a, bindings)
    elif isinstance(a, ApplicationExpression) and\
         isinstance(b, ApplicationExpression):
        return most_general_unification(a.function, b.function, bindings) +\
               most_general_unification(a.argument, b.argument, bindings)
    raise BindingException((a, b))

def _mgu_var(var, expression, bindings):
    if var.variable in expression.free():
        raise BindingException((var, expression))
    else:
        return BindingDict([(var.variable, expression)]) + bindings
    
    
class BindingException(Exception):
    def __init__(self, arg):
        if isinstance(arg, tuple):
            Exception.__init__(self, "'%s' cannot be bound to '%s'" % arg)
        else:
            Exception.__init__(self, arg)
    
class UnificationException(Exception):
    def __init__(self, a, b):
        Exception.__init__(self, "'%s' cannot unify with '%s'" % (a,b))
    

def testResolution():
    resolution_test(r'man(x)')
    resolution_test(r'(man(x) -> man(x))')
    resolution_test(r'(man(x) -> --man(x))')
    resolution_test(r'-(man(x) and -man(x))')
    resolution_test(r'(man(x) or -man(x))')
    resolution_test(r'(man(x) -> man(x))')
    resolution_test(r'-(man(x) and -man(x))')
    resolution_test(r'(man(x) or -man(x))')
    resolution_test(r'(man(x) -> man(x))')
    resolution_test(r'(man(x) iff man(x))')
    resolution_test(r'-(man(x) iff -man(x))')
    resolution_test('all x.man(x)')
    resolution_test('-all x.some y.F(x,y) & some x.all y.(-F(x,y))')
    resolution_test('some x.all y.sees(x,y)')

    p1 = LogicParser().parse(r'all x.(man(x) -> mortal(x))')
    p2 = LogicParser().parse(r'man(Socrates)')
    c = LogicParser().parse(r'mortal(Socrates)')
    print '%s, %s |- %s: %s' % (p1, p2, c, Resolution(c, [p1,p2]).prove())
    
    p1 = LogicParser().parse(r'all x.(man(x) -> walks(x))')
    p2 = LogicParser().parse(r'man(John)')
    c = LogicParser().parse(r'some y.walks(y)')
    print '%s, %s |- %s: %s' % (p1, p2, c, Resolution(c, [p1,p2]).prove())
    
    p = LogicParser().parse(r'some e1.some e2.(believe(e1,john,e2) & walk(e2,mary))')
    c = LogicParser().parse(r'some e0.walk(e0,mary)')
    print '%s |- %s: %s' % (p, c, Resolution(c, [p]).prove())
    
def resolution_test(e):
    f = LogicParser().parse(e)
    t = Resolution(f)
    print '|- %s: %s' % (f, t.prove())

def test_clausify():
    lp = LogicParser()
    
    print clausify(lp.parse('P(x) | Q(x)'))
    print clausify(lp.parse('(P(x) & Q(x)) | R(x)'))
    print clausify(lp.parse('P(x) | (Q(x) & R(x))'))
    print clausify(lp.parse('(P(x) & Q(x)) | (R(x) & S(x))'))
        
    print clausify(lp.parse('P(x) | Q(x) | R(x)'))
    print clausify(lp.parse('P(x) | (Q(x) & R(x)) | S(x)'))

    print clausify(lp.parse('exists x.P(x) | Q(x)'))

    print clausify(lp.parse('-(-P(x) & Q(x))'))
    print clausify(lp.parse('P(x) <-> Q(x)'))
    print clausify(lp.parse('-(P(x) <-> Q(x))'))
    print clausify(lp.parse('-(all x.P(x))'))
    print clausify(lp.parse('-(some x.P(x))'))
    
    print clausify(lp.parse('some x.P(x)'))
    print clausify(lp.parse('some x.all y.P(x,y)'))
    print clausify(lp.parse('all y.some x.P(x,y)'))
    print clausify(lp.parse('all z.all y.some x.P(x,y,z)'))
    print clausify(lp.parse('all x.(all y.P(x,y) -> -all y.(Q(x,y) -> R(x,y)))'))

if __name__ == '__main__':
    test_clausify()
    print
    testResolution()
