from nltk.sem.logic import *

def attempt_proof(goal, premises=[], assume_false=True):
    try:
        agenda = Agenda()
        agenda.put_all([negate(goal)]+premises)
        return _attempt_proof(agenda, set([]), set([]), [])
    except RuntimeError, e:
        if assume_false and str(e) == 'maximum recursion depth exceeded in cmp':
            return False
        else:
            raise e
        
class Agenda(object):
    ATOM = 0
    N_ATOM = 1
    D_NEG = 2
    N_ALL = 3
    N_SOME = 4
    AND = 5
    N_OR = 6
    N_IMP = 7
    OR = 8
    IMP = 9
    N_AND = 10
    IFF = 11
    N_IFF = 12
    EQ = 13
    SOME = 14
    ALL = 15
        
    def __init__(self):
        self.sets = (set([]),set([]),set([]),set([]),set([]),set([]),set([]),set([]),set([]),set([]),set([]),set([]),set([]),set([]),set([]),set([]))
        
    def clone(self):
        new_agenda = Agenda()
        new_sets = []
        for s in self.sets:
            new_sets.append(s.copy())
        new_agenda.sets = tuple(new_sets)
        return new_agenda
        
    def __getitem__(self, index):
        return self.sets[index]
        
    def put(self, expression):
        self.sets[Agenda._categorize_expression(expression)].add(expression)
        
    def put_all(self, expressions):
        for expression in expressions:
            self.put(expression)
        
    def pop_first(self):
        """ Pop the first expression that appears in the agenda """
        for i in range(len(self.sets)):
            if self.sets[i]:
                return (self.sets[i].pop(), i)
        return (None, None)

    def _categorize_expression(current):
        if isinstance(current, AllExpression):
            return Agenda.ALL
        elif isinstance(current, ApplicationExpression):
            return Agenda._categorize_ApplicationExpression(current)
        elif isinstance(current, SomeExpression):
            return Agenda.SOME
        else:
            raise NotImpementedError
    
    _categorize_expression = staticmethod(_categorize_expression)
        
    def _categorize_ApplicationExpression(current):
        # if current is a binary operation
        if isinstance(current.first, ApplicationExpression) \
            and isinstance(current.first.first, Operator):
                first = current.first.second
                op = current.first.first
                second = current.second
                
                if str(op) == 'and':
                    return Agenda.AND
                elif str(op) == 'or':
                    return Agenda.OR
                elif str(op) == 'implies':
                    return Agenda.IMP
                elif str(op) == 'iff':
                    return Agenda.IFF
    
        #if current is a negation
        elif isinstance(current.first, Operator) and str(current.first.operator) == 'not':
            negated = current.second
                
            #if current is a negated AllExpression
            if isinstance(negated, AllExpression):
                return Agenda.N_ALL
            
            #if current is a negated SomeExpression
            elif isinstance(negated, SomeExpression):
                return Agenda.N_SOME
            
            # if current is a negated binary operation
            elif isinstance(negated.first, ApplicationExpression) \
                and isinstance(negated.first.first, Operator):
                    inner_first = negated.first.second
                    inner_op = negated.first.first
                    inner_second = negated.second
                    
                    if str(inner_op) == 'and':
                        return Agenda.N_AND
                    elif str(inner_op) == 'or':
                        return Agenda.N_OR
                    elif str(inner_op) == 'implies':
                        return Agenda.N_IMP
                    elif str(inner_op) == 'iff':
                        return Agenda.N_IFF
                        
            #if current is a double negation
            elif isinstance(negated.first, Operator) and str(negated.first.operator) == 'not':
                return Agenda.D_NEG
            
            else:
                return Agenda.N_ATOM
            
        else:
            return Agenda.ATOM
    
    _categorize_ApplicationExpression = staticmethod(_categorize_ApplicationExpression)
        
def _attempt_proof(agenda, accessible_vars, atoms, exhausted_universals):
    (current, category) = agenda.pop_first()
    
    #if there's nothing left in the agenda, and we haven't closed the path
    if not current:
        return False
    
    proof_method = { Agenda.ATOM:   _attempt_proof_atom,
                     Agenda.N_ATOM: _attempt_proof_n_atom,
                     Agenda.D_NEG:  _attempt_proof_d_neg,
                     Agenda.N_ALL:  _attempt_proof_n_all,
                     Agenda.N_SOME: _attempt_proof_n_some,
                     Agenda.AND:    _attempt_proof_and,
                     Agenda.N_OR:   _attempt_proof_n_or,
                     Agenda.N_IMP:  _attempt_proof_n_imp,
                     Agenda.OR:     _attempt_proof_or,
                     Agenda.IMP:    _attempt_proof_imp,
                     Agenda.N_AND:  _attempt_proof_n_and,
                     Agenda.IFF:    _attempt_proof_iff,
                     Agenda.N_IFF:  _attempt_proof_n_iff,
                     Agenda.EQ:     _attempt_proof_eq,
                     Agenda.SOME:   _attempt_proof_some,
                     Agenda.ALL:    _attempt_proof_all,
                    }[category]
    
    return proof_method(current, agenda, accessible_vars, atoms, exhausted_universals)

def _attempt_proof_atom(current, agenda, accessible_vars, atoms, exhausted_universals):
    # Check if the branch is closed.  Return 'True' if it is
    if (current, True) in atoms:
        return True

    #dump the list of exhausted_universals into the agenda since we are (potentially) adding new accessible vars
    agenda.put_all(exhausted_universals)
    return _attempt_proof(agenda, accessible_vars|set(current.args), atoms|set([(current, False)]), []) 
    
def _attempt_proof_n_atom(current, agenda, accessible_vars, atoms, exhausted_universals):
    # Check if the branch is closed.  Return 'True' if it is
    if (current.second, False) in atoms:
        return True

    #dump the list of exhausted_universals into the agenda since we are (potentially) adding new accessible vars
    agenda.put_all(exhausted_universals)
    return _attempt_proof(agenda, accessible_vars|set(current.second.args), atoms|set([(current.second, True)]), []) 
    
def _attempt_proof_d_neg(current, agenda, accessible_vars, atoms, exhausted_universals):
    agenda.put(current.second.second)
    return _attempt_proof(agenda, accessible_vars, atoms, exhausted_universals)
    
def _attempt_proof_n_all(current, agenda, accessible_vars, atoms, exhausted_universals):
    agenda[Agenda.SOME].add(SomeExpression(current.second.variable, negate(current.second.term)))
    return _attempt_proof(agenda, accessible_vars, atoms, exhausted_universals)
    
def _attempt_proof_n_some(current, agenda, accessible_vars, atoms, exhausted_universals):
    agenda[Agenda.ALL].add(AllExpression(current.second.variable, negate(current.second.term)))
    return _attempt_proof(agenda, accessible_vars, atoms, exhausted_universals)

def _attempt_proof_and(current, agenda, accessible_vars, atoms, exhausted_universals):
    agenda.put(current.first.second)
    agenda.put(current.second)
    return _attempt_proof(agenda, accessible_vars, atoms, exhausted_universals)
    
def _attempt_proof_n_or(current, agenda, accessible_vars, atoms, exhausted_universals):
    agenda.put(current.second.first.second)
    agenda.put(current.second.second)
    return _attempt_proof(agenda, accessible_vars, atoms, exhausted_universals)

def _attempt_proof_n_imp(current, agenda, accessible_vars, atoms, exhausted_universals):
    agenda.put(current.second.first.second)
    agenda.put(negate(current.second.second))
    return _attempt_proof(agenda, accessible_vars, atoms, exhausted_universals)

def _attempt_proof_or(current, agenda, accessible_vars, atoms, exhausted_universals):
    new_agenda = agenda.clone()
    agenda.put(current.first.second)
    new_agenda.put(current.second)
    return _attempt_proof(agenda, accessible_vars, atoms, exhausted_universals) and \
            _attempt_proof(new_agenda, accessible_vars, atoms, exhausted_universals)
    
def _attempt_proof_imp(current, agenda, accessible_vars, atoms, exhausted_universals):
    new_agenda = agenda.clone()
    agenda.put(negate(current.first.second))
    new_agenda.put(current.second)
    return _attempt_proof(agenda, accessible_vars, atoms, exhausted_universals) and \
            _attempt_proof(new_agenda, accessible_vars, atoms, exhausted_universals)
    
def _attempt_proof_n_and(current, agenda, accessible_vars, atoms, exhausted_universals):
    new_agenda = agenda.clone()
    agenda.put(negate(current.second.first.second))
    new_agenda.put(negate(current.second.second))
    return _attempt_proof(agenda, accessible_vars, atoms, exhausted_universals) and \
            _attempt_proof(new_agenda, accessible_vars, atoms, exhausted_universals)
    
def _attempt_proof_iff(current, agenda, accessible_vars, atoms, exhausted_universals):
    new_agenda = agenda.clone()
    agenda.put(current.first.second)
    agenda.put(current.second)
    new_agenda.put(negate(current.first.second))
    new_agenda.put(negate(current.second))
    return _attempt_proof(agenda, accessible_vars, atoms, exhausted_universals) and \
            _attempt_proof(new_agenda, accessible_vars, atoms, exhausted_universals)

def _attempt_proof_n_iff(current, agenda, accessible_vars, atoms, exhausted_universals):
    new_agenda = agenda.clone()
    agenda.put(current.second.first.second)
    agenda.put(negate(current.second.second))
    new_agenda.put(negate(current.second.first.second))
    new_agenda.put(current.second.second)
    return _attempt_proof(agenda, accessible_vars, atoms, exhausted_universals) and \
            _attempt_proof(new_agenda, accessible_vars, atoms, exhausted_universals)

def _attempt_proof_eq(current, agenda, accessible_vars, atoms, exhausted_universals):
    raise NotImplementedError

def _attempt_proof_some(current, agenda, accessible_vars, atoms, exhausted_universals):
    new_unique_variable = unique_variable()
    new_term = current.term.replace(current.variable, new_unique_variable)
    agenda.put(new_term)
    agenda.put_all(exhausted_universals)
    return _attempt_proof(agenda, accessible_vars|set([new_unique_variable]), atoms, [])
    
def _attempt_proof_all(current, agenda, accessible_vars, atoms, exhausted_universals):
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
            current._used_vars |= set([variable_to_use])
            new_term = current.term.replace(current.variable, variable_to_use)
            agenda.put(new_term)
            agenda.put(current)
            return _attempt_proof(agenda, accessible_vars, atoms, exhausted_universals)
        
        else:
            #no more available variables to substitute
            return _attempt_proof(agenda, accessible_vars, atoms, exhausted_universals+[current])
            
    else:
        new_unique_variable = unique_variable()

        current._used_vars |= set([new_unique_variable])
        new_term = current.term.replace(current.variable, new_unique_variable)
        agenda.put(new_term)
        agenda.put(current)
        agenda.put_all(exhausted_universals)
        return _attempt_proof(agenda, accessible_vars|set([new_unique_variable]), atoms, [])

def negate(expression):
    assert isinstance(expression, Expression)
    return ApplicationExpression(Operator('not'), expression)
    
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
    p2 = LogicParser().parse(r'(man Socrates)')
    c = LogicParser().parse(r'some y.(walks y)')
    print '%s, %s |- %s: %s' % (p1.infixify(), p2.infixify(), c.infixify(), attempt_proof(c, [p1,p2]))
    f = LogicParser().parse('all x.(man x)')
    print '%s |- %s: %s' % (f.infixify(), f.infixify(), attempt_proof(f, [f]))
    f = LogicParser().parse('some x.all y.(sees x y)')
    print '|- %s: %s' % (f.infixify(), attempt_proof(f))

if __name__ == '__main__':
    testTableau()
