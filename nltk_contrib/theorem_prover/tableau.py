# Natural Language Toolkit: Tableau-based Theorem Prover 
#
# Author: Dan Garrette <dhgarrette@gmail.com>
#
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

from nltk.sem.logic import *

class ProverParseError(Exception): pass

def attempt_proof(goal, premises=[], assume_false=True, debug=(False, 0)):
    try:
        agenda = Agenda()
        agenda.put_all([negate(goal)]+premises)
        return _attempt_proof(agenda, set([]), set([]), debug)
    except RuntimeError, e:
        if assume_false and str(e).startswith('maximum recursion depth exceeded'):
            return False
        else:
            raise e
        
class Agenda(object):
    def __init__(self):
        self.sets = tuple(set([]) for i in range(17))
        
    def clone(self):
        new_agenda = Agenda()
        set_list = [s.copy() for s in self.sets]
        
        new_allExs = set([])
        for allEx in set_list[Categories.ALL]:
            new_allEx = AllExpression(allEx.variable, allEx.term)
            try:
                new_allEx._used_vars = set(used for used in allEx._used_vars)
            except AttributeError:
                new_allEx._used_vars = set([])
            new_allExs.add(new_allEx)
        set_list[Categories.ALL] = new_allExs
                
        set_list[Categories.N_EQ] = set(ApplicationExpression(n_eq.first, n_eq.second) 
                                        for n_eq in set_list[Categories.N_EQ])

        new_agenda.sets = tuple(set_list)
        return new_agenda
        
    def __getitem__(self, index):
        return self.sets[index]
        
    def put(self, expression):
        self.sets[Agenda._categorize_expression(expression)].add(expression)
        
    def put_all(self, expressions):
        for expression in expressions:
            self.put(expression)
            
    def put_atoms(self, atoms):
        for atom in atoms:
            if atom[1]:
                self[Categories.N_ATOM].add(negate(atom[0]))
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
        self.sets = tuple(set(ex.replace(old.variable, new) for ex in s) for s in self.sets)

    def mark_alls_fresh(self):
        for u in self.sets[Categories.ALL]:
            u._exhausted = False
            
    def mark_neqs_fresh(self):
        for neq in self.sets[Categories.N_EQ]:
            neq._exhausted = False

    def _categorize_expression(current):
        if isinstance(current, AllExpression):
            return Categories.ALL
        elif isinstance(current, ApplicationExpression):
            return Agenda._categorize_ApplicationExpression(current)
        elif isinstance(current, SomeExpression):
            return Categories.SOME
        else:
            raise ProverParseError
    
    _categorize_expression = staticmethod(_categorize_expression)
        
    def _categorize_ApplicationExpression(current):
        # if current is a binary operation
        if isinstance(current.first, ApplicationExpression) \
            and isinstance(current.first.first, Operator):
                first = current.first.second
                op = current.first.first
                second = current.second
                
                if str(op) == 'and':
                    return Categories.AND
                elif str(op) == 'or':
                    return Categories.OR
                elif str(op) == 'implies':
                    return Categories.IMP
                elif str(op) == 'iff':
                    return Categories.IFF
                elif str(op) == '=':
                    return Categories.EQ
    
        #if current is a negation
        elif isinstance(current.first, Operator) and str(current.first.operator) == 'not':
            negated = current.second
                
            #if current is a negated AllExpression
            if isinstance(negated, AllExpression):
                return Categories.N_ALL
            
            #if current is a negated SomeExpression
            elif isinstance(negated, SomeExpression):
                return Categories.N_SOME
            
            # if current is a negated binary operation
            elif isinstance(negated.first, ApplicationExpression) \
                and isinstance(negated.first.first, Operator):
                    inner_first = negated.first.second
                    inner_op = negated.first.first
                    inner_second = negated.second
                    
                    if str(inner_op) == 'and':
                        return Categories.N_AND
                    elif str(inner_op) == 'or':
                        return Categories.N_OR
                    elif str(inner_op) == 'implies':
                        return Categories.N_IMP
                    elif str(inner_op) == 'iff':
                        return Categories.N_IFF
                    elif str(inner_op) == '=':
                        return Categories.N_EQ
                        
            #if current is a double negation
            elif isinstance(negated.first, Operator) and str(negated.first.operator) == 'not':
                return Categories.D_NEG
            
            else:
                return Categories.N_ATOM
            
        else:
            return Categories.ATOM
    
    _categorize_ApplicationExpression = staticmethod(_categorize_ApplicationExpression)
        
def _attempt_proof(agenda, accessible_vars, atoms, debug=(False, 0)):
    (current, category) = agenda.pop_first()
    
    #if there's nothing left in the agenda, and we haven't closed the path
    if not current:
        debug_line('AGENDA EMPTY', (debug[0], debug[1]+1)) 
        return False
    
    proof_method = { Categories.ATOM:   _attempt_proof_atom,
                     Categories.N_ATOM: _attempt_proof_n_atom,
                     Categories.N_EQ:   _attempt_proof_n_eq,
                     Categories.D_NEG:  _attempt_proof_d_neg,
                     Categories.N_ALL:  _attempt_proof_n_all,
                     Categories.N_SOME: _attempt_proof_n_some,
                     Categories.AND:    _attempt_proof_and,
                     Categories.N_OR:   _attempt_proof_n_or,
                     Categories.N_IMP:  _attempt_proof_n_imp,
                     Categories.OR:     _attempt_proof_or,
                     Categories.IMP:    _attempt_proof_imp,
                     Categories.N_AND:  _attempt_proof_n_and,
                     Categories.IFF:    _attempt_proof_iff,
                     Categories.N_IFF:  _attempt_proof_n_iff,
                     Categories.EQ:     _attempt_proof_eq,
                     Categories.SOME:   _attempt_proof_some,
                     Categories.ALL:    _attempt_proof_all,
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
            data = data.infixify()
        
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
    if (current.second, False) in atoms:
        debug_line('CLOSED', (debug[0], debug[1]+1)) 
        return True

    #mark all AllExpressions as 'not exhausted' into the agenda since we are (potentially) adding new accessible vars
    agenda.mark_alls_fresh();
    return _attempt_proof(agenda, accessible_vars|set(current.second.args), atoms|set([(current.second, True)]), (debug[0], debug[1]+1)) 
    
def _attempt_proof_n_eq(current, agenda, accessible_vars, atoms, debug=(False, 0)):
    ###########################################################################
    # Since 'current' is of type '~(a=b)', the path is closed if 'a' == 'b'
    ###########################################################################
    if current.second.first.second == current.second.second:
        debug_line('CLOSED', (debug[0], debug[1]+1)) 
        return True
    
    agenda[Categories.N_EQ].add(current)
    current._exhausted = True
    return _attempt_proof(agenda, accessible_vars|set(current.second.args), atoms, (debug[0], debug[1]+1)) 
    
def _attempt_proof_d_neg(current, agenda, accessible_vars, atoms, debug=(False, 0)):
    agenda.put(current.second.second)
    return _attempt_proof(agenda, accessible_vars, atoms, (debug[0], debug[1]+1))
    
def _attempt_proof_n_all(current, agenda, accessible_vars, atoms, debug=(False, 0)):
    agenda[Categories.SOME].add(SomeExpression(current.second.variable, negate(current.second.term)))
    return _attempt_proof(agenda, accessible_vars, atoms, (debug[0], debug[1]+1))
    
def _attempt_proof_n_some(current, agenda, accessible_vars, atoms, debug=(False, 0)):
    agenda[Categories.ALL].add(AllExpression(current.second.variable, negate(current.second.term)))
    return _attempt_proof(agenda, accessible_vars, atoms, (debug[0], debug[1]+1))

def _attempt_proof_and(current, agenda, accessible_vars, atoms, debug=(False, 0)):
    agenda.put(current.first.second)
    agenda.put(current.second)
    return _attempt_proof(agenda, accessible_vars, atoms, (debug[0], debug[1]+1))
    
def _attempt_proof_n_or(current, agenda, accessible_vars, atoms, debug=(False, 0)):
    agenda.put(current.second.first.second)
    agenda.put(current.second.second)
    return _attempt_proof(agenda, accessible_vars, atoms, (debug[0], debug[1]+1))

def _attempt_proof_n_imp(current, agenda, accessible_vars, atoms, debug=(False, 0)):
    agenda.put(current.second.first.second)
    agenda.put(negate(current.second.second))
    return _attempt_proof(agenda, accessible_vars, atoms, (debug[0], debug[1]+1))

def _attempt_proof_or(current, agenda, accessible_vars, atoms, debug=(False, 0)):
    new_agenda = agenda.clone()
    agenda.put(current.first.second)
    new_agenda.put(current.second)
    return _attempt_proof(agenda, accessible_vars, atoms, (debug[0], debug[1]+1)) and \
            _attempt_proof(new_agenda, accessible_vars, atoms, (debug[0], debug[1]+1))
    
def _attempt_proof_imp(current, agenda, accessible_vars, atoms, debug=(False, 0)):
    new_agenda = agenda.clone()
    agenda.put(negate(current.first.second))
    new_agenda.put(current.second)
    return _attempt_proof(agenda, accessible_vars, atoms, (debug[0], debug[1]+1)) and \
            _attempt_proof(new_agenda, accessible_vars, atoms, (debug[0], debug[1]+1))
    
def _attempt_proof_n_and(current, agenda, accessible_vars, atoms, debug=(False, 0)):
    new_agenda = agenda.clone()
    agenda.put(negate(current.second.first.second))
    new_agenda.put(negate(current.second.second))
    return _attempt_proof(agenda, accessible_vars, atoms, (debug[0], debug[1]+1)) and \
            _attempt_proof(new_agenda, accessible_vars, atoms, (debug[0], debug[1]+1))
    
def _attempt_proof_iff(current, agenda, accessible_vars, atoms, debug=(False, 0)):
    new_agenda = agenda.clone()
    agenda.put(current.first.second)
    agenda.put(current.second)
    new_agenda.put(negate(current.first.second))
    new_agenda.put(negate(current.second))
    return _attempt_proof(agenda, accessible_vars, atoms, (debug[0], debug[1]+1)) and \
            _attempt_proof(new_agenda, accessible_vars, atoms, (debug[0], debug[1]+1))

def _attempt_proof_n_iff(current, agenda, accessible_vars, atoms, debug=(False, 0)):
    new_agenda = agenda.clone()
    agenda.put(current.second.first.second)
    agenda.put(negate(current.second.second))
    new_agenda.put(negate(current.second.first.second))
    new_agenda.put(current.second.second)
    return _attempt_proof(agenda, accessible_vars, atoms, (debug[0], debug[1]+1)) and \
            _attempt_proof(new_agenda, accessible_vars, atoms, (debug[0], debug[1]+1))

def _attempt_proof_eq(current, agenda, accessible_vars, atoms, debug=(False, 0)):
    #########################################################################
    # Since 'current' is of the form '(a = b)', replace ALL free instances  
    # of 'a' with 'b'
    #########################################################################
    agenda.put_atoms(atoms)
    agenda.replace_all(current.first.second, current.second)
    accessible_vars.discard(current.first.second)
    agenda.mark_neqs_fresh();
    return _attempt_proof(agenda, accessible_vars, set([]), (debug[0], debug[1]+1))

def _attempt_proof_some(current, agenda, accessible_vars, atoms, debug=(False, 0)):
    new_unique_variable = unique_variable()
    agenda.put(current.term.replace(current.variable, new_unique_variable))
    agenda.mark_alls_fresh()
    return _attempt_proof(agenda, accessible_vars|set([new_unique_variable]), atoms, (debug[0], debug[1]+1))
    
def _attempt_proof_all(current, agenda, accessible_vars, atoms, debug=(False, 0)):
    try:
        current._used_vars
    except AttributeError:
        current._used_vars = set([])
    
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
        new_unique_variable = unique_variable()
        debug_line('--> Using \'%s\'' % new_unique_variable, (debug[0], debug[1]+2))
        current._used_vars |= set([new_unique_variable])
        agenda.put(current.term.replace(current.variable, new_unique_variable))
        agenda[Categories.ALL].add(current)
        agenda.mark_alls_fresh()
        return _attempt_proof(agenda, accessible_vars|set([new_unique_variable]), atoms, (debug[0], debug[1]+1))

def negate(expression):
    assert isinstance(expression, Expression)
    return ApplicationExpression(Operator('not'), expression)
    
class Categories:
    ATOM   = 0
    N_ATOM = 1
    N_EQ   = 2
    D_NEG  = 3
    N_ALL  = 4
    N_SOME = 5
    AND    = 6
    N_OR   = 7
    N_IMP  = 8
    OR     = 9
    IMP    = 10
    N_AND  = 11
    IFF    = 12
    N_IFF  = 13
    EQ     = 14
    SOME   = 15
    ALL    = 16

def testTableau():
    f = LogicParser().parse(r'((man x) implies (not (not (man x))))')
    print '|- %s: %s' % (f.infixify(), attempt_proof(f))
    f = LogicParser().parse(r'(not ((man x) and (not (man x))))')
    print '|- %s: %s' % (f.infixify(), attempt_proof(f))
    f = LogicParser().parse(r'((man x) or (not (man x)))')
    print '|- %s: %s' % (f.infixify(), attempt_proof(f))
    f = LogicParser().parse(r'((man x) implies (man x))')
    print '|- %s: %s' % (f.infixify(), attempt_proof(f))
    f = LogicParser().parse(r'(not ((man x) and (not (man x))))')
    print '|- %s: %s' % (f.infixify(), attempt_proof(f))
    f = LogicParser().parse(r'((man x) or (not (man x)))')
    print '|- %s: %s' % (f.infixify(), attempt_proof(f))
    f = LogicParser().parse(r'((man x) implies (man x))')
    print '|- %s: %s' % (f.infixify(), attempt_proof(f))
    f = LogicParser().parse(r'((man x) iff (man x))')
    print '|- %s: %s' % (f.infixify(), attempt_proof(f))
    f = LogicParser().parse(r'(not ((man x) iff (not (man x))))')
    print '|- %s: %s' % (f.infixify(), attempt_proof(f))
    p1 = LogicParser().parse(r'all x.((man x) implies (mortal x))')
    p2 = LogicParser().parse(r'(man Socrates)')
    c = LogicParser().parse(r'(mortal Socrates)')
    print '%s, %s |- %s: %s' % (p1.infixify(), p2.infixify(), c.infixify(), attempt_proof(c, [p1,p2]))
    p1 = LogicParser().parse(r'all x.((man x) implies (walks x))')
    p2 = LogicParser().parse(r'(man John)')
    c = LogicParser().parse(r'some y.(walks y)')
    print '%s, %s |- %s: %s' % (p1.infixify(), p2.infixify(), c.infixify(), attempt_proof(c, [p1,p2]))
    f = LogicParser().parse('all x.(man x)')
    print '%s |- %s: %s' % (f.infixify(), f.infixify(), attempt_proof(f, [f]))
    p = LogicParser().parse(r'((x = y) and (walks y))')
    c = LogicParser().parse(r'(walks x)')
    print '%s |- %s: %s' % (p.infixify(), c.infixify(), attempt_proof(c, [p]))
    p = LogicParser().parse(r'((x = y) and ((y = z) and (z = w)))')
    c = LogicParser().parse(r'(x = w)')
    print '%s |- %s: %s' % (p.infixify(), c.infixify(), attempt_proof(c, [p]))
    f = LogicParser().parse('all x.all y.((x = y) implies (y = x))')
    print '|- %s: %s' % (f.infixify(), attempt_proof(f))
    f = LogicParser().parse('all x.all y.all z.(((x=y)and(y=z))implies(x=z))')
    print '|- %s: %s' % (f.infixify(), attempt_proof(f))
    f = LogicParser().parse('(not(all x.some y.(F y x) and some x.all y.(not(F y x))))')
    print '|- %s: %s' % (f.infixify(), attempt_proof(f))
    f = LogicParser().parse('some x.all y.(sees x y)')
    print '|- %s: %s' % (f.infixify(), attempt_proof(f))

if __name__ == '__main__':
    testTableau()
