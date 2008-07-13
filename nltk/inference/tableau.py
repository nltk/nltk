# Natural Language Toolkit: First-order Tableau-based Theorem Prover 
#
# Author: Dan Garrette <dhgarrette@gmail.com>
#
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

from nltk.sem.logic import *

from api import ProverI

"""
Module for a tableau-based First Order theorem prover.
"""

class ProverParseError(Exception): pass

class Tableau(ProverI):
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

    def prove(self, debug=False):
        tp_result = None
        try:
            agenda = Agenda()
            if self._goal:
                agenda.put(-self._goal)
            agenda.put_all(self._assumptions)
            tp_result = _attempt_proof(agenda, set(), set(), (debug, 0))
        except RuntimeError, e:
            if self._assume_false and str(e).startswith('maximum recursion depth exceeded'):
                tp_result = False
            else:
                if debug:
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


class Agenda(object):
    def __init__(self):
        self.sets = tuple(set() for i in range(17))
        
    def clone(self):
        new_agenda = Agenda()
        set_list = [s.copy() for s in self.sets]
        
        new_allExs = set()
        for allEx in set_list[Categories.ALL]:
            new_allEx = AllExpression(allEx.variable, allEx.term)
            try:
                new_allEx._used_vars = set(used for used in allEx._used_vars)
            except AttributeError:
                new_allEx._used_vars = set()
            new_allExs.add(new_allEx)
        set_list[Categories.ALL] = new_allExs
                
        set_list[Categories.N_EQ] = set(NegatedExpression(n_eq.term) 
                                        for n_eq in set_list[Categories.N_EQ])

        new_agenda.sets = tuple(set_list)
        return new_agenda
        
    def __getitem__(self, index):
        return self.sets[index]
        
    def put(self, expression):
        if isinstance(expression, AllExpression):
            ex_to_add = AllExpression(expression.variable, expression.term)
            try:
                ex_to_add._used_vars = set(used for used in expression._used_vars)
            except AttributeError:
                ex_to_add._used_vars = set()
        else:
            ex_to_add = expression
        self.sets[self._categorize_expression(ex_to_add)].add(ex_to_add)
        
    def put_all(self, expressions):
        for expression in expressions:
            self.put(expression)
            
    def put_atoms(self, atoms):
        for atom in atoms:
            if atom[1]:
                self[Categories.N_ATOM].add(-atom[0])
            else:
                self[Categories.ATOM].add(atom[0])
        
    def pop_first(self):
        """ Pop the first expression that appears in the agenda """
        for i in range(len(self.sets)):
            if self.sets[i]:
                if i in [Categories.N_EQ, Categories.ALL]:
                    for ex in self.sets[i]:
                        try:
                            if not ex._exhausted:
                                self.sets[i].remove(ex)
                                return(ex, i)
                        except AttributeError:
                            self.sets[i].remove(ex)
                            return(ex, i)
                else:
                    return (self.sets[i].pop(), i)
        return (None, None)
    
        
    def replace_all(self, old, new):
        self.sets = tuple(set(ex.replace(old, new) for ex in s) for s in self.sets)

    def mark_alls_fresh(self):
        for u in self.sets[Categories.ALL]:
            u._exhausted = False
            
    def mark_neqs_fresh(self):
        for neq in self.sets[Categories.N_EQ]:
            neq._exhausted = False

    def _categorize_expression(self, current):
        if isinstance(current, AllExpression):
            return Categories.ALL
        elif isinstance(current, AndExpression):
            return Categories.AND
        elif isinstance(current, OrExpression):
            return Categories.OR
        elif isinstance(current, ImpExpression):
            return Categories.IMP
        elif isinstance(current, IffExpression):
            return Categories.IFF
        elif isinstance(current, EqualityExpression):
            return Categories.EQ
        elif isinstance(current, NegatedExpression):
            return self._categorize_NegatedExpression(current)
        elif isinstance(current, ExistsExpression):
            return Categories.EXISTS
        elif isinstance(current, ApplicationExpression):
            return Categories.ATOM
        else:
            raise ProverParseError()
    
    def _categorize_NegatedExpression(self, current):
        negated = current.term
        
        if isinstance(negated, AllExpression):
            return Categories.N_ALL
        elif isinstance(negated, AndExpression):
            return Categories.N_AND
        elif isinstance(negated, OrExpression):
            return Categories.N_OR
        elif isinstance(negated, ImpExpression):
            return Categories.N_IMP
        elif isinstance(negated, IffExpression):
            return Categories.N_IFF
        elif isinstance(negated, EqualityExpression):
            return Categories.N_EQ
        elif isinstance(negated, NegatedExpression):
            return Categories.D_NEG
        elif isinstance(negated, ExistsExpression):
            return Categories.N_EXISTS
        elif isinstance(negated, ApplicationExpression):
            return Categories.N_ATOM
        else:
            raise ProverParseError()

def _attempt_proof(agenda, accessible_vars, atoms, debug=(False, 0)):
    (current, category) = agenda.pop_first()
    
    #if there's nothing left in the agenda, and we haven't closed the path
    if not current:
        debug_line('AGENDA EMPTY', (debug[0], debug[1]+1)) 
        return False
    
    proof_method = { Categories.ATOM:     _attempt_proof_atom,
                     Categories.N_ATOM:   _attempt_proof_n_atom,
                     Categories.N_EQ:     _attempt_proof_n_eq,
                     Categories.D_NEG:    _attempt_proof_d_neg,
                     Categories.N_ALL:    _attempt_proof_n_all,
                     Categories.N_EXISTS: _attempt_proof_n_some,
                     Categories.AND:      _attempt_proof_and,
                     Categories.N_OR:     _attempt_proof_n_or,
                     Categories.N_IMP:    _attempt_proof_n_imp,
                     Categories.OR:       _attempt_proof_or,
                     Categories.IMP:      _attempt_proof_imp,
                     Categories.N_AND:    _attempt_proof_n_and,
                     Categories.IFF:      _attempt_proof_iff,
                     Categories.N_IFF:    _attempt_proof_n_iff,
                     Categories.EQ:       _attempt_proof_eq,
                     Categories.EXISTS:   _attempt_proof_some,
                     Categories.ALL:      _attempt_proof_all,
                    }[category]
    
    debug_line(current, debug)
    return proof_method(current, agenda, accessible_vars, atoms, debug)

def debug_line(data, debug):
    if debug[0]: 
        additional = ''
        if isinstance(data, AllExpression):
            try:
                additional += ':   %s' % str([ve.variable.name for ve in data._used_vars])
            except AttributeError:
                additional += ':   []'
        
        if isinstance(data, Expression):
            data = data
        
        print '%s%s%s' % ('   '*debug[1], data, additional)

def _attempt_proof_atom(current, agenda, accessible_vars, atoms, debug=(False, 0)):
    # Check if the branch is closed.  Return 'True' if it is
    if (current, True) in atoms:
        debug_line('CLOSED', (debug[0], debug[1]+1)) 
        return True

    #mark all AllExpressions as 'not exhausted' into the agenda since we are (potentially) adding new accessible vars
    agenda.mark_alls_fresh();
    return _attempt_proof(agenda, accessible_vars|set(current.args), atoms|set([(current, False)]), (debug[0], debug[1]+1)) 
    
def _attempt_proof_n_atom(current, agenda, accessible_vars, atoms, debug=(False, 0)):
    # Check if the branch is closed.  Return 'True' if it is
    if (current.term, False) in atoms:
        debug_line('CLOSED', (debug[0], debug[1]+1)) 
        return True

    #mark all AllExpressions as 'not exhausted' into the agenda since we are (potentially) adding new accessible vars
    agenda.mark_alls_fresh();
    return _attempt_proof(agenda, accessible_vars|set(current.term.args), atoms|set([(current.term, True)]), (debug[0], debug[1]+1)) 
    
def _attempt_proof_n_eq(current, agenda, accessible_vars, atoms, debug=(False, 0)):
    ###########################################################################
    # Since 'current' is of type '~(a=b)', the path is closed if 'a' == 'b'
    ###########################################################################
    if current.term.first == current.term.second:
        debug_line('CLOSED', (debug[0], debug[1]+1)) 
        return True
    
    agenda[Categories.N_EQ].add(current)
    current._exhausted = True
    return _attempt_proof(agenda, accessible_vars|set([current.term.first, current.term.second]), atoms, (debug[0], debug[1]+1)) 
    
def _attempt_proof_d_neg(current, agenda, accessible_vars, atoms, debug=(False, 0)):
    agenda.put(current.term.term)
    return _attempt_proof(agenda, accessible_vars, atoms, (debug[0], debug[1]+1))
    
def _attempt_proof_n_all(current, agenda, accessible_vars, atoms, debug=(False, 0)):
    agenda[Categories.EXISTS].add(ExistsExpression(current.term.variable, -current.term.term))
    return _attempt_proof(agenda, accessible_vars, atoms, (debug[0], debug[1]+1))
    
def _attempt_proof_n_some(current, agenda, accessible_vars, atoms, debug=(False, 0)):
    agenda[Categories.ALL].add(AllExpression(current.term.variable, -current.term.term))
    return _attempt_proof(agenda, accessible_vars, atoms, (debug[0], debug[1]+1))

def _attempt_proof_and(current, agenda, accessible_vars, atoms, debug=(False, 0)):
    agenda.put(current.first)
    agenda.put(current.second)
    return _attempt_proof(agenda, accessible_vars, atoms, (debug[0], debug[1]+1))
    
def _attempt_proof_n_or(current, agenda, accessible_vars, atoms, debug=(False, 0)):
    agenda.put(-current.term.first)
    agenda.put(-current.term.second)
    return _attempt_proof(agenda, accessible_vars, atoms, (debug[0], debug[1]+1))

def _attempt_proof_n_imp(current, agenda, accessible_vars, atoms, debug=(False, 0)):
    agenda.put(current.term.first)
    agenda.put(-current.term.second)
    return _attempt_proof(agenda, accessible_vars, atoms, (debug[0], debug[1]+1))

def _attempt_proof_or(current, agenda, accessible_vars, atoms, debug=(False, 0)):
    new_agenda = agenda.clone()
    agenda.put(current.first)
    new_agenda.put(current.second)
    return _attempt_proof(agenda, accessible_vars, atoms, (debug[0], debug[1]+1)) and \
            _attempt_proof(new_agenda, accessible_vars, atoms, (debug[0], debug[1]+1))
    
def _attempt_proof_imp(current, agenda, accessible_vars, atoms, debug=(False, 0)):
    new_agenda = agenda.clone()
    agenda.put(-current.first)
    new_agenda.put(current.second)
    return _attempt_proof(agenda, accessible_vars, atoms, (debug[0], debug[1]+1)) and \
            _attempt_proof(new_agenda, accessible_vars, atoms, (debug[0], debug[1]+1))
    
def _attempt_proof_n_and(current, agenda, accessible_vars, atoms, debug=(False, 0)):
    new_agenda = agenda.clone()
    agenda.put(-current.term.first)
    new_agenda.put(-current.term.second)
    return _attempt_proof(agenda, accessible_vars, atoms, (debug[0], debug[1]+1)) and \
            _attempt_proof(new_agenda, accessible_vars, atoms, (debug[0], debug[1]+1))
    
def _attempt_proof_iff(current, agenda, accessible_vars, atoms, debug=(False, 0)):
    new_agenda = agenda.clone()
    agenda.put(current.first)
    agenda.put(current.second)
    new_agenda.put(-current.first)
    new_agenda.put(-current.second)
    return _attempt_proof(agenda, accessible_vars, atoms, (debug[0], debug[1]+1)) and \
            _attempt_proof(new_agenda, accessible_vars, atoms, (debug[0], debug[1]+1))

def _attempt_proof_n_iff(current, agenda, accessible_vars, atoms, debug=(False, 0)):
    new_agenda = agenda.clone()
    agenda.put(current.term.first)
    agenda.put(-current.term.second)
    new_agenda.put(-current.term.first)
    new_agenda.put(current.term.second)
    return _attempt_proof(agenda, accessible_vars, atoms, (debug[0], debug[1]+1)) and \
            _attempt_proof(new_agenda, accessible_vars, atoms, (debug[0], debug[1]+1))

def _attempt_proof_eq(current, agenda, accessible_vars, atoms, debug=(False, 0)):
    #########################################################################
    # Since 'current' is of the form '(a = b)', replace ALL free instances  
    # of 'a' with 'b'
    #########################################################################
    agenda.put_atoms(atoms)
    agenda.replace_all(current.first, current.second)
    accessible_vars.discard(current.first)
    agenda.mark_neqs_fresh();
    return _attempt_proof(agenda, accessible_vars, set(), (debug[0], debug[1]+1))

def _attempt_proof_some(current, agenda, accessible_vars, atoms, debug=(False, 0)):
    new_unique_variable = current.unique_variable()
    agenda.put(current.term.replace(current.variable, new_unique_variable))
    agenda.mark_alls_fresh()
    return _attempt_proof(agenda, accessible_vars|set([new_unique_variable]), atoms, (debug[0], debug[1]+1))
    
def _attempt_proof_all(current, agenda, accessible_vars, atoms, debug=(False, 0)):
    try:
        current._used_vars
    except AttributeError:
        current._used_vars = set()
    
    #if there are accessible_vars on the path
    if accessible_vars:
        # get the set of bound variables that have not be used by this AllExpression 
        bv_available = accessible_vars - current._used_vars
        
        if bv_available:
            variable_to_use = list(bv_available)[0]
            debug_line('--> Using \'%s\'' % variable_to_use, (debug[0], debug[1]+2))
            current._used_vars |= set([variable_to_use])
            agenda.put(current.term.replace(current.variable, variable_to_use))
            agenda[Categories.ALL].add(current)
            return _attempt_proof(agenda, accessible_vars, atoms, (debug[0], debug[1]+1))
        
        else:
            #no more available variables to substitute
            debug_line('--> Variables Exhausted', (debug[0], debug[1]+2))
            current._exhausted = True
            agenda[Categories.ALL].add(current)
            return _attempt_proof(agenda, accessible_vars, atoms, (debug[0], debug[1]+1))
            
    else:
        new_unique_variable = current.unique_variable()
        debug_line('--> Using \'%s\'' % new_unique_variable, (debug[0], debug[1]+2))
        current._used_vars |= set([new_unique_variable])
        agenda.put(current.term.replace(current.variable, new_unique_variable))
        agenda[Categories.ALL].add(current)
        agenda.mark_alls_fresh()
        return _attempt_proof(agenda, accessible_vars|set([new_unique_variable]), atoms, (debug[0], debug[1]+1))


class Categories:
    ATOM     = 0
    N_ATOM   = 1
    N_EQ     = 2
    D_NEG    = 3
    N_ALL    = 4
    N_EXISTS = 5
    AND      = 6
    N_OR     = 7
    N_IMP    = 8
    OR       = 9
    IMP      = 10
    N_AND    = 11
    IFF      = 12
    N_IFF    = 13
    EQ       = 14
    EXISTS   = 15
    ALL      = 16

def testTableau():
    tableau_test(r'man(x)')
    tableau_test(r'(man(x) -> man(x))')
    tableau_test(r'(man(x) -> --man(x))')
    tableau_test(r'-(man(x) and -man(x))')
    tableau_test(r'(man(x) or -man(x))')
    tableau_test(r'(man(x) -> man(x))')
    tableau_test(r'-(man(x) and -man(x))')
    tableau_test(r'(man(x) or -man(x))')
    tableau_test(r'(man(x) -> man(x))')
    tableau_test(r'(man(x) iff man(x))')
    tableau_test(r'-(man(x) iff -man(x))')
    tableau_test('all x.man(x)')
    tableau_test('all x.all y.((x = y) -> (y = x))')
    tableau_test('all x.all y.all z.(((x = y) & (y = z)) -> (x = z))')
    tableau_test('-all x.some y.F(x,y) & some x.all y.(-F(x,y))')
    tableau_test('some x.all y.sees(x,y)')

    p1 = LogicParser().parse(r'all x.(man(x) -> mortal(x))')
    p2 = LogicParser().parse(r'man(Socrates)')
    c = LogicParser().parse(r'mortal(Socrates)')
    print '%s, %s |- %s: %s' % (p1, p2, c, Tableau(c, [p1,p2]).prove())
    
    p1 = LogicParser().parse(r'all x.(man(x) -> walks(x))')
    p2 = LogicParser().parse(r'man(John)')
    c = LogicParser().parse(r'some y.walks(y)')
    print '%s, %s |- %s: %s' % (p1, p2, c, Tableau(c, [p1,p2]).prove())
    
    p = LogicParser().parse(r'((x = y) and walks(y))')
    c = LogicParser().parse(r'walks(x)')
    print '%s |- %s: %s' % (p, c, Tableau(c, [p]).prove())
    
    p = LogicParser().parse(r'((x = y) and ((y = z) and (z = w)))')
    c = LogicParser().parse(r'(x = w)')
    print '%s |- %s: %s' % (p, c, Tableau(c, [p]).prove())
    
    p = LogicParser().parse(r'some e1.some e2.(believe(e1,john,e2) & walk(e2,mary))')
    c = LogicParser().parse(r'some e0.walk(e0,mary)')
    print '%s |- %s: %s' % (p, c, Tableau(c, [p]).prove())
    
#    p = LogicParser().parse(r'some e1.some e2.((believe e1 john e2) and (walk e2 mary))')
#    c = LogicParser().parse(r'some x.some e3.some e4.((believe e3 x e4) and (walk e4 mary))')
#    print '%s |- %s: %s' % (p, c, Tableau(c,[p]).prove())

def tableau_test(e):
    f = LogicParser().parse(e)
    t = Tableau(f)
    print '|- %s: %s' % (f, t.prove())

if __name__ == '__main__':
    testTableau()
