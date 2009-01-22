# Natural Language Toolkit: First-Order Tableau Theorem Prover 
#
# Author: Dan Garrette <dhgarrette@gmail.com>
#
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

from nltk.sem.logic import *
from api import Prover

"""
Module for a tableau-based First Order theorem prover.
"""

class ProverParseError(Exception): pass

class Tableau(Prover):
    _assume_false=False
    
    def prove(self, goal=None, assumptions=None, verbose=False):
        if not assumptions:
            assumptions = []
            
        result = None
        try:
            agenda = Agenda()
            if goal:
                agenda.put(-goal)
            agenda.put_all(assumptions)
            debugger = Debug(verbose)
            result = self._attempt_proof(agenda, set(), set(), debugger)
        except RuntimeError, e:
            if self._assume_false and str(e).startswith('maximum recursion depth exceeded'):
                result = False
            else:
                if verbose:
                    print e
                else:
                    raise e
        return (result, '\n'.join(debugger.lines))
        
    def _attempt_proof(self, agenda, accessible_vars, atoms, debug):
        (current, category) = agenda.pop_first()
        
        #if there's nothing left in the agenda, and we haven't closed the path
        if not current:
            debug.line('AGENDA EMPTY') 
            return False
        
        proof_method = { Categories.ATOM:     self._attempt_proof_atom,
                         Categories.PROP:     self._attempt_proof_prop,
                         Categories.N_ATOM:   self._attempt_proof_n_atom,
                         Categories.N_PROP:   self._attempt_proof_n_prop,
                         Categories.N_EQ:     self._attempt_proof_n_eq,
                         Categories.D_NEG:    self._attempt_proof_d_neg,
                         Categories.N_ALL:    self._attempt_proof_n_all,
                         Categories.N_EXISTS: self._attempt_proof_n_some,
                         Categories.AND:      self._attempt_proof_and,
                         Categories.N_OR:     self._attempt_proof_n_or,
                         Categories.N_IMP:    self._attempt_proof_n_imp,
                         Categories.OR:       self._attempt_proof_or,
                         Categories.IMP:      self._attempt_proof_imp,
                         Categories.N_AND:    self._attempt_proof_n_and,
                         Categories.IFF:      self._attempt_proof_iff,
                         Categories.N_IFF:    self._attempt_proof_n_iff,
                         Categories.EQ:       self._attempt_proof_eq,
                         Categories.EXISTS:   self._attempt_proof_some,
                         Categories.ALL:      self._attempt_proof_all,
                        }[category]
        
        debug.line(current)
        return proof_method(current, agenda, accessible_vars, atoms, debug)

    def _attempt_proof_atom(self, current, agenda, accessible_vars, atoms, debug):
        # Check if the branch is closed.  Return 'True' if it is
        if (current, True) in atoms:
            debug.line('CLOSED', 1) 
            return True
    
        #mark all AllExpressions as 'not exhausted' into the agenda since we are (potentially) adding new accessible vars
        agenda.mark_alls_fresh();
        return self._attempt_proof(agenda, accessible_vars|set(current.args), atoms|set([(current, False)]), debug+1) 
        
    def _attempt_proof_prop(self, current, agenda, accessible_vars, atoms, debug):
        # Check if the branch is closed.  Return 'True' if it is
        if (current, True) in atoms:
            debug.line('CLOSED', 1) 
            return True
    
        #mark all AllExpressions as 'not exhausted' into the agenda since we are (potentially) adding new accessible vars
        agenda.mark_alls_fresh();
        return self._attempt_proof(agenda, accessible_vars, atoms|set([(current, False)]), debug+1) 
        
    def _attempt_proof_n_atom(self, current, agenda, accessible_vars, atoms, debug):
        # Check if the branch is closed.  Return 'True' if it is
        if (current.term, False) in atoms:
            debug.line('CLOSED', 1) 
            return True
    
        #mark all AllExpressions as 'not exhausted' into the agenda since we are (potentially) adding new accessible vars
        agenda.mark_alls_fresh();
        return self._attempt_proof(agenda, accessible_vars|set(current.term.args), atoms|set([(current.term, True)]), debug+1) 
        
    def _attempt_proof_n_prop(self, current, agenda, accessible_vars, atoms, debug):
        # Check if the branch is closed.  Return 'True' if it is
        if (current.term, False) in atoms:
            debug.line('CLOSED', 1) 
            return True
    
        #mark all AllExpressions as 'not exhausted' into the agenda since we are (potentially) adding new accessible vars
        agenda.mark_alls_fresh();
        return self._attempt_proof(agenda, accessible_vars, atoms|set([(current.term, True)]), debug+1) 
        
    def _attempt_proof_n_eq(self, current, agenda, accessible_vars, atoms, debug):
        ###########################################################################
        # Since 'current' is of type '~(a=b)', the path is closed if 'a' == 'b'
        ###########################################################################
        if current.term.first == current.term.second:
            debug.line('CLOSED', 1) 
            return True
        
        agenda[Categories.N_EQ].add(current)
        current._exhausted = True
        return self._attempt_proof(agenda, accessible_vars|set([current.term.first, current.term.second]), atoms, debug+1) 
        
    def _attempt_proof_d_neg(self, current, agenda, accessible_vars, atoms, debug):
        agenda.put(current.term.term)
        return self._attempt_proof(agenda, accessible_vars, atoms, debug+1)
        
    def _attempt_proof_n_all(self, current, agenda, accessible_vars, atoms, debug):
        agenda[Categories.EXISTS].add(ExistsExpression(current.term.variable, -current.term.term))
        return self._attempt_proof(agenda, accessible_vars, atoms, debug+1)
        
    def _attempt_proof_n_some(self, current, agenda, accessible_vars, atoms, debug):
        agenda[Categories.ALL].add(AllExpression(current.term.variable, -current.term.term))
        return self._attempt_proof(agenda, accessible_vars, atoms, debug+1)
    
    def _attempt_proof_and(self, current, agenda, accessible_vars, atoms, debug):
        agenda.put(current.first)
        agenda.put(current.second)
        return self._attempt_proof(agenda, accessible_vars, atoms, debug+1)
        
    def _attempt_proof_n_or(self, current, agenda, accessible_vars, atoms, debug):
        agenda.put(-current.term.first)
        agenda.put(-current.term.second)
        return self._attempt_proof(agenda, accessible_vars, atoms, debug+1)
    
    def _attempt_proof_n_imp(self, current, agenda, accessible_vars, atoms, debug):
        agenda.put(current.term.first)
        agenda.put(-current.term.second)
        return self._attempt_proof(agenda, accessible_vars, atoms, debug+1)
    
    def _attempt_proof_or(self, current, agenda, accessible_vars, atoms, debug):
        new_agenda = agenda.clone()
        agenda.put(current.first)
        new_agenda.put(current.second)
        return self._attempt_proof(agenda, accessible_vars, atoms, debug+1) and \
                self._attempt_proof(new_agenda, accessible_vars, atoms, debug+1)
        
    def _attempt_proof_imp(self, current, agenda, accessible_vars, atoms, debug):
        new_agenda = agenda.clone()
        agenda.put(-current.first)
        new_agenda.put(current.second)
        return self._attempt_proof(agenda, accessible_vars, atoms, debug+1) and \
                self._attempt_proof(new_agenda, accessible_vars, atoms, debug+1)
        
    def _attempt_proof_n_and(self, current, agenda, accessible_vars, atoms, debug):
        new_agenda = agenda.clone()
        agenda.put(-current.term.first)
        new_agenda.put(-current.term.second)
        return self._attempt_proof(agenda, accessible_vars, atoms, debug+1) and \
                self._attempt_proof(new_agenda, accessible_vars, atoms, debug+1)
        
    def _attempt_proof_iff(self, current, agenda, accessible_vars, atoms, debug):
        new_agenda = agenda.clone()
        agenda.put(current.first)
        agenda.put(current.second)
        new_agenda.put(-current.first)
        new_agenda.put(-current.second)
        return self._attempt_proof(agenda, accessible_vars, atoms, debug+1) and \
                self._attempt_proof(new_agenda, accessible_vars, atoms, debug+1)
    
    def _attempt_proof_n_iff(self, current, agenda, accessible_vars, atoms, debug):
        new_agenda = agenda.clone()
        agenda.put(current.term.first)
        agenda.put(-current.term.second)
        new_agenda.put(-current.term.first)
        new_agenda.put(current.term.second)
        return self._attempt_proof(agenda, accessible_vars, atoms, debug+1) and \
                self._attempt_proof(new_agenda, accessible_vars, atoms, debug+1)
    
    def _attempt_proof_eq(self, current, agenda, accessible_vars, atoms, debug):
        #########################################################################
        # Since 'current' is of the form '(a = b)', replace ALL free instances  
        # of 'a' with 'b'
        #########################################################################
        agenda.put_atoms(atoms)
        agenda.replace_all(current.first, current.second)
        accessible_vars.discard(current.first)
        agenda.mark_neqs_fresh();
        return self._attempt_proof(agenda, accessible_vars, set(), debug+1)
    
    def _attempt_proof_some(self, current, agenda, accessible_vars, atoms, debug):
        new_unique_variable = VariableExpression(unique_variable())
        agenda.put(current.term.replace(current.variable, new_unique_variable))
        agenda.mark_alls_fresh()
        return self._attempt_proof(agenda, accessible_vars|set([new_unique_variable]), atoms, debug+1)
        
    def _attempt_proof_all(self, current, agenda, accessible_vars, atoms, debug):
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
                debug.line('--> Using \'%s\'' % variable_to_use, 2)
                current._used_vars |= set([variable_to_use])
                agenda.put(current.term.replace(current.variable, variable_to_use))
                agenda[Categories.ALL].add(current)
                return self._attempt_proof(agenda, accessible_vars, atoms, debug+1)
            
            else:
                #no more available variables to substitute
                debug.line('--> Variables Exhausted', 2)
                current._exhausted = True
                agenda[Categories.ALL].add(current)
                return self._attempt_proof(agenda, accessible_vars, atoms, debug+1)
                
        else:
            new_unique_variable = VariableExpression(unique_variable())
            debug.line('--> Using \'%s\'' % new_unique_variable, 2)
            current._used_vars |= set([new_unique_variable])
            agenda.put(current.term.replace(current.variable, new_unique_variable))
            agenda[Categories.ALL].add(current)
            agenda.mark_alls_fresh()
            return self._attempt_proof(agenda, accessible_vars|set([new_unique_variable]), atoms, debug+1)


class Agenda(object):
    def __init__(self):
        self.sets = tuple(set() for i in range(19))
        
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
        self.sets = tuple(set(ex.replace(old.variable, new) for ex in s) for s in self.sets)

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
        elif isinstance(current, AbstractVariableExpression):
            return Categories.PROP
        else:
            raise ProverParseError("cannot categorize %s" % \
                                   current.__class__.__name__)
    
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
        elif isinstance(negated, AbstractVariableExpression):
            return Categories.N_PROP
        else:
            raise ProverParseError("cannot categorize %s" % \
                                   negated.__class__.__name__)


class Debug(object):
    def __init__(self, verbose, indent=0, lines=None):
        self.verbose = verbose
        self.indent = indent
        
        if not lines:
            lines = []
        
        self.lines = lines
        
    def __add__(self, increment):
        return Debug(self.verbose, self.indent+1, self.lines)

    def line(self, data, indent=0):
        additional = ''
        if isinstance(data, AllExpression):
            try:
                additional += ':   %s' % str([ve.variable.name for ve in data._used_vars])
            except AttributeError:
                additional += ':   []'

        newline = '%s%s%s' % ('   '*(self.indent+indent), data, additional)
        self.lines.append(newline)

        if self.verbose: 
            print newline


class Categories(object):
    ATOM     = 0
    PROP     = 1
    N_ATOM   = 2
    N_PROP   = 3
    N_EQ     = 4
    D_NEG    = 5
    N_ALL    = 6
    N_EXISTS = 7
    AND      = 8
    N_OR     = 9
    N_IMP    = 10
    OR       = 11
    IMP      = 12
    N_AND    = 13
    IFF      = 14
    N_IFF    = 15
    EQ       = 16
    EXISTS   = 17
    ALL      = 18


def testTableau():
    tableau_test('P | -P')
    tableau_test('P & -P')
    tableau_test('Q', ['P', '(P -> Q)'])
    tableau_test('man(x)')
    tableau_test('(man(x) -> man(x))')
    tableau_test('(man(x) -> --man(x))')
    tableau_test('-(man(x) and -man(x))')
    tableau_test('(man(x) or -man(x))')
    tableau_test('(man(x) -> man(x))')
    tableau_test('-(man(x) and -man(x))')
    tableau_test('(man(x) or -man(x))')
    tableau_test('(man(x) -> man(x))')
    tableau_test('(man(x) iff man(x))')
    tableau_test('-(man(x) iff -man(x))')
    tableau_test('all x.man(x)')
    tableau_test('all x.all y.((x = y) -> (y = x))')
    tableau_test('all x.all y.all z.(((x = y) & (y = z)) -> (x = z))')
#    tableau_test('-all x.some y.F(x,y) & some x.all y.(-F(x,y))')
#    tableau_test('some x.all y.sees(x,y)')

    parse = LogicParser().parse

    p1 = 'all x.(man(x) -> mortal(x))'
    p2 = 'man(Socrates)'
    c = 'mortal(Socrates)'
    tableau_test(c, [p1, p2])
    
    p1 = 'all x.(man(x) -> walks(x))'
    p2 = 'man(John)'
    c = 'some y.walks(y)'
    tableau_test(c, [p1, p2])
    
    p = '((x = y) & walks(y))'
    c = 'walks(x)'
    tableau_test(c, [p])
    
    p = '((x = y) & ((y = z) & (z = w)))'
    c = '(x = w)'
    tableau_test(c, [p])
    
    p = 'some e1.some e2.(believe(e1,john,e2) & walk(e2,mary))'
    c = 'some e0.walk(e0,mary)'
    tableau_test(c, [p])
    
    c = '(exists x.exists z3.((x = Mary) & ((z3 = John) & sees(z3,x))) <-> exists x.exists z4.((x = John) & ((z4 = Mary) & sees(x,z4))))'
    tableau_test(c)

#    p = 'some e1.some e2.((believe e1 john e2) and (walk e2 mary))'
#    c = 'some x.some e3.some e4.((believe e3 x e4) and (walk e4 mary))'
    tableau_test(c, [p])

def tableau_test(c, ps=None, verbose=False):
    lp = LogicParser()
    pc = lp.parse(c)
    if ps:
        pps = [lp.parse(p) for p in ps]
    else:
        ps = []
        pps = []
    print '%s |- %s: %s' % (', '.join(ps), pc, HigherOrderTableau().prove(pc, pps, verbose=verbose)[0])

if __name__ == '__main__':
    testTableau()
    