# Natural Language Toolkit: Nonmonotonic Reasoning
#
# Author: Daniel H. Garrette <dhgarrette@gmail.com>
#
# Copyright (C) 2001-2008 NLTK Project
# URL: <http://www.nltk.org>
# For license information, see LICENSE.TXT

"""
A module to perform nonmonotonic reasoning
"""

from nltk.sem.logic import *
from nltk.inference import inference
from nltk.inference.api import ProverI
from nltk import defaultdict

class NonmonotonicProver(ProverI):
    def __init__(self, goal=None, assumptions=[], prover_name='Prover9'):
        self._goal = goal
        self._assumptions = assumptions
        self._prover_name = prover_name
        
    def prove(self, debug=False):
        """
        @return: C{bool} Whether the proof was successful or not.
        """
        (goal, assumptions) = self.augmented_assumptions()
        
        prover = inference.get_prover(goal, assumptions, self._prover_name)
        result = prover.prove(debug)
        
        if debug:
            prover.show_proof()
        
        return result

class ClosedDomainProver(NonmonotonicProver):
    """
    This is a prover that adds domain closure assumptions before proving.
    """
    def augmented_assumptions(self):
        """
         - Domain = union([e.free(False) for e in all_expressions])
         - translate "exists x.P" to "(z=d1 | z=d2 | ... ) & P.replace(x,z)" or "P.replace(x, d1) | P.replace(x, d2) | ..."
         - translate "all x.P" to "P.replace(x, d1) & P.replace(x, d2) & ..."
        """
        assumptions = self._assumptions + [-self._goal]
        
        domain = set()
        for a in assumptions:
            domain |= (a.free(False) - a.free(True))
        
        assumptions1 = set()
        for a in assumptions:
            if isinstance(a, ExistsExpression):
                newterms = [a.term.replace(a.variable, VariableExpression(d)) for d in domain]
                assumptions1.add(reduce(Expression.__or__, newterms))
            else:
                assumptions1.add(a)
                
        assumptions2 = set()
        for a in assumptions1:
            if isinstance(a, AllExpression):
                for d in domain:
                    assumptions2.add(a.term.replace(a.variable, VariableExpression(d)))
            else:
                assumptions2.add(a)

        return (None, assumptions2)
    
class UniqueNamesProver(NonmonotonicProver):
    """
    This is a prover that adds unique names assumptions before proving.
    """
    def augmented_assumptions(self):
        """
         - Domain = union([e.free(False) for e in all_expressions])
         - if "d1 = d2" cannot be proven from the premises, then add "d1 != d2"
        """
        assumptions = self._assumptions
        
        domain = set()
        for a in assumptions:
            domain |= (a.free(False) - a.free(True))
        domain = sorted(list(domain))
        
        #build a dictionary of obvious equalities
        eq_dict = defaultdict(list)
        for a in assumptions:
            if isinstance(a, EqualityExpression):
                av = a.first.variable
                bv = a.second.variable
                if av < bv:
                    eq_dict[av].append(bv)
                else:
                    eq_dict[bv].append(av)
        
        assumptions2 = []
        for i,a in enumerate(domain):
            for b in domain[i+1:]:
                if b not in eq_dict[a]:
                    newEqEx = EqualityExpression(VariableExpression(a), 
                                                 VariableExpression(b))
                    if not inference.get_prover(newEqEx, assumptions).prove():
                        #if we can't prove it, then assume it's false
                        assumptions2.append(-newEqEx)
                
        return (self._goal, assumptions + assumptions2)

class ClosedWorldProver(NonmonotonicProver):
    """
    This is a prover that completes predicates before proving.

    If the premises don't logically entail "P(A)" then add "-P(A)"
    all x.(P(x) -> (x=A)) is the completion of P
    
    walk(Socrates)
    Socrates != Bill
    + all x.(walk(x) -> (x = Socrates))
    ----------------
    -walk(Bill)

    see(Socrates, John)
    see(John, Mary)
    Socrates != John
    John != Mary
    + all x.all y.(see(x,y) -> ((x=Socrates & y=John) | (x=John & y=Mary)))
    ----------------
    -see(Socrates, Mary)
    """ 
    def augmented_assumptions(self):
        assumptions = self._assumptions
        
        predicates = AddableDict(list)
        for a in assumptions:
            predicates.extend(self.map_predicates(a))

        assumptions2 = []
        for p in predicates:
            sig_list = predicates[p]
            new_sig = tuple([unique_variable() for x in sig_list[0]])
            
            #make the antecedent
            antecedent = p
            for v in new_sig:
                antecedent = antecedent(IndividualVariableExpression(v))

            disjuncts = []
            for sig in sig_list:
                equality_exs = []
                for i,v in enumerate(sig):
                    equality_exs.append(EqualityExpression(IndividualVariableExpression(new_sig[i]),v)) 
                disjuncts.append(reduce(Expression.__and__, equality_exs))
            consequent = reduce(Expression.__or__, disjuncts)
            
            #make the implication
            accum = ImpExpression(antecedent, consequent)
            
            #quantify the implication
            for new_sig_var in new_sig[::-1]:
                accum = AllExpression(new_sig_var, accum)
            assumptions2.append(accum)
        
        return (self._goal, assumptions + assumptions2)
    
    def map_predicates(self, expression):
        if isinstance(expression, ApplicationExpression):
            (func, args) = expression.uncurry()
            if isinstance(func, VariableExpression):
                return AddableDict(list, [(func, tuple(args))])
            else:
                return self.map_predicates(expression.function) +\
                       self.map_predicates(expression.argument) 
        elif isinstance(expression, BooleanExpression):
            return self.map_predicates(expression.first) +\
                   self.map_predicates(expression.second)
        else:
            return AddableDict(list) 

class AddableDict(defaultdict):
    def __init__(self, type, list=None):
        self.type = type
        defaultdict.__init__(self, type)
        if list:
            for key,value in list:
                self[key].append(value)
    
    def __add__(self, other):
        new = AddableDict(self.type)
        for key in self:
            new[key].extend([key])
        for key in other:
            new[key].extend([key])
            
    def extend(self, other):
        for key in other:
            self[key].extend(other[key])

def closed_domain_demo():
    lp = LogicParser()
    
    p1 = lp.parse(r'exists x.walk(x)')
    p2 = lp.parse(r'man(Socrates)')
    c = lp.parse(r'walk(Socrates)')
    ClosedDomainProver(c, [p1,p2]).prove()

    p1 = lp.parse(r'exists x.walk(x)')
    p2 = lp.parse(r'man(Socrates)')
    p3 = lp.parse(r'man(Bill)')
    c = lp.parse(r'walk(Socrates)')
    ClosedDomainProver(c, [p1,p2,p3]).prove()

def unique_names_demo():
    lp = LogicParser()
    
    p1 = lp.parse(r'man(Socrates)')
    p2 = lp.parse(r'man(Bill)')
    c = lp.parse(r'exists x.exists y.(x != y)')
    print inference.get_prover(c, [p1,p2]).prove()
    unp = UniqueNamesProver(c, [p1,p2])
    for a in unp.augmented_assumptions()[1]: print a
    print unp.prove()

    p1 = lp.parse(r'all x.(walk(x) -> (x = Socrates))')
    p2 = lp.parse(r'Bill = William')
    p3 = lp.parse(r'Bill = Billy')
    c = lp.parse(r'-walk(William)')
    print inference.get_prover(c, [p1,p2,p3]).prove()
    unp = UniqueNamesProver(c, [p1,p2,p3], 'tableau')
    for a in unp.augmented_assumptions()[1]: print a
    print unp.prove()
    
def closed_world_demo():
    lp = LogicParser()
    
    p1 = lp.parse(r'walk(Socrates)')
    p2 = lp.parse(r'(Socrates != Bill)')
    c = lp.parse(r'-walk(Bill)')
    print inference.get_prover(c, [p1,p2]).prove()
    cwp = ClosedWorldProver(c, [p1,p2])
    for a in cwp.augmented_assumptions()[1]: print a
    print cwp.prove()

    p1 = lp.parse(r'see(Socrates, John)')
    p2 = lp.parse(r'see(John, Mary)')
    p3 = lp.parse(r'(Socrates != John)')
    p4 = lp.parse(r'(John != Mary)')
    c = lp.parse(r'-see(Socrates, Mary)')
    print inference.get_prover(c, [p1,p2,p3,p4]).prove()
    cwp = ClosedWorldProver(c, [p1,p2,p3,p4])
    for a in cwp.augmented_assumptions()[1]: print a
    print cwp.prove()

if __name__ == '__main__':
    closed_domain_demo()
    unique_names_demo()
    closed_world_demo()